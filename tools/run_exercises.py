#!/usr/bin/env python3
"""Run local fictional exercises and check their arithmetic independently.

This runner invokes the original CLI in child Python processes. Its arithmetic
oracle uses exact fractions and never imports the replay engine. It neither
authenticates timestamps nor establishes that the operator did not know future
prices. Only the repository's local synthetic fixtures are used.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).absolute().parent.parent
FIXTURES = ("replay", "loss", "cash")
SOURCE_FILES = (
    "src/radar_equity_replay/core.py",
    "src/radar_equity_replay/io.py",
    "src/radar_equity_replay/__main__.py",
    "src/radar_equity_replay/__init__.py",
    "tools/run_exercises.py",
)
RUN_SCHEMA = "radar-equity-replay-exercises/v1"
MAX_LOCAL_BYTES = 16 * 1024 * 1024


class ExerciseError(ValueError):
    """An exercise failed; supplied content is deliberately not echoed."""


def require(condition: bool) -> None:
    if not condition:
        raise ExerciseError("Local exercise verification failed")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def strict_equal(actual, expected) -> bool:
    """Compare JSON structures without Python's boolean/integer equivalence."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(strict_equal(actual[key], value) for key, value in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(strict_equal(left, right) for left, right in zip(actual, expected))
    return actual == expected


def decimal8(value: Fraction) -> str:
    """Round an exact rational to eight decimal places, ties to even."""
    require(isinstance(value, Fraction))
    magnitude = abs(value)
    units, remainder = divmod(magnitude.numerator * 100_000_000, magnitude.denominator)
    if remainder * 2 > magnitude.denominator or (remainder * 2 == magnitude.denominator and units % 2):
        units += 1
    sign = "-" if value < 0 and units else ""
    whole, fraction = divmod(units, 100_000_000)
    return f"{sign}{whole}.{fraction:08d}"


def rational_portfolio(value: dict, *, benchmark: bool = False) -> tuple[dict, Fraction]:
    """Independent buy-and-hold calculation for the documented local fixtures.

    Contract validation belongs to the original CLI. This helper only computes
    the observed formulas using Fraction, including every mark and liquidation.
    """
    capital = Fraction(value["initial_capital"])
    fee = Fraction(value["fee_bps"]) / 10_000
    slip = Fraction(value["slippage_bps"]) / 10_000
    sessions = value["sessions"]
    assets = value["assets"]
    if benchmark:
        budgets = [capital]
        entry_prices = [Fraction(sessions[1]["benchmark_price"])]
    else:
        budgets = [capital * Fraction(value["target_weights"][asset]) for asset in assets]
        entry_prices = [Fraction(sessions[1]["prices"][asset]) for asset in assets]
    cash = capital - sum(budgets, Fraction())
    units = [budget / (price * (1 + fee) * (1 + slip)) for budget, price in zip(budgets, entry_prices)]
    # The fee is charged on the transaction notional; slippage is measured
    # against the supplied close. Neither component is deducted a second time.
    entry_fee = sum(budgets, Fraction()) * fee / (1 + fee)
    entry_slip = sum((quantity * price * slip for quantity, price in zip(units, entry_prices)), Fraction())
    all_navs = [capital]
    marks = []
    last_prices = []
    for index, session in enumerate(sessions[1:], start=1):
        last_prices = [Fraction(session["benchmark_price"])] if benchmark else [Fraction(session["prices"][asset]) for asset in assets]
        nav = cash + sum((quantity * price for quantity, price in zip(units, last_prices)), Fraction())
        all_navs.append(nav)
        marks.append({"session_index": str(index), "date": session["date"], "phase": "close_mark", "nav": decimal8(nav)})
    close_value = sum((quantity * price for quantity, price in zip(units, last_prices)), Fraction())
    exit_slip = close_value * slip
    exit_notional = close_value - exit_slip
    exit_fee = exit_notional * fee
    final = cash + exit_notional - exit_fee
    all_navs.append(final)
    marks.append({"session_index": str(len(sessions) - 1), "date": sessions[-1]["date"], "phase": "final_liquidation", "nav": decimal8(final)})
    peak = capital
    drawdown = Fraction()
    for nav in all_navs:
        peak = max(peak, nav)
        drawdown = max(drawdown, 100 * (peak - nav) / peak)
    return_pct = 100 * (final / capital - 1)
    return {
        "initial_capital": decimal8(capital),
        "unallocated_cash": decimal8(cash),
        "final_nav": decimal8(final),
        "return_pct": decimal8(return_pct),
        "max_drawdown_pct": decimal8(drawdown),
        "costs": {
            "entry_fee": decimal8(entry_fee),
            "exit_fee": decimal8(exit_fee),
            "entry_slippage_vs_close": decimal8(entry_slip),
            "exit_slippage_vs_close": decimal8(exit_slip),
        },
        "curve": marks,
    }, return_pct


def verify_report(input_raw: bytes, report: dict) -> dict:
    """Verify every portfolio/benchmark scalar, cost, curve and excess return."""
    value = json.loads(input_raw)
    expected_portfolio, portfolio_return = rational_portfolio(value)
    expected_benchmark, benchmark_return = rational_portfolio(value, benchmark=True)
    require(strict_equal(report["portfolio"], expected_portfolio))
    require(strict_equal(report["benchmark"], expected_benchmark))
    require(report["excess_return_percentage_points"] == decimal8(portfolio_return - benchmark_return))
    expected_metadata = {
        "schema": "radar-equity-replay-report/v1",
        "mode": "synthetic_buy_and_hold_replay",
        "synthetic_only": True,
        "execution_allowed": False,
        "review_status": "pending",
        "input_sha256": sha256(input_raw),
        "currency": value["currency"],
        "price_basis": value["price_basis"],
        "asset_count": str(len(value["assets"])),
        "evidence_count": str(len(value["evidence"])),
        "session_count": str(len(value["sessions"])),
        "decision_at": value["decision_at"],
        "execute_on": value["execute_on"],
        "first_session": value["sessions"][0]["date"],
        "last_session": value["sessions"][-1]["date"],
        "fee_bps": value["fee_bps"],
        "slippage_bps": value["slippage_bps"],
        "point_in_time_guard": {
            "entry_session_index": "1",
            "declared_evidence_available_by_decision": True,
            "timestamp_authenticity_verified": False,
            "decision_origin_verified": False,
            "uses_future_prices_for_valuation_only": True,
        },
    }
    for key, expected in expected_metadata.items():
        require(key in report and strict_equal(report[key], expected))
    encoded = json.dumps(report, ensure_ascii=True)
    private_texts = [value["project_id"], *value["assets"]]
    for evidence in value["evidence"]:
        private_texts.extend(evidence[key] for key in ("evidence_id", "source_url", "text"))
    require(all(text not in encoded for text in private_texts))
    return {
        "method": "Independent exact Fraction arithmetic, half-even to 8 places",
        "portfolio_metrics_costs_and_curve": "passed",
        "benchmark_metrics_costs_and_curve": "passed",
        "excess_return_percentage_points": "passed",
        "metadata_and_pending_guards": "passed",
        "evidence_content_not_echoed": "passed",
    }


@contextmanager
def parent_handle(path: str | Path):
    """Traverse existing parents without following symlinks (POSIX only)."""
    require(os.name == "posix" and os.open in os.supports_dir_fd)
    require(all(isinstance(getattr(os, flag, None), int) and getattr(os, flag) > 0 for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")))
    path = os.fspath(path)
    require(isinstance(path, str) and bool(path) and "\x00" not in path)
    absolute = path.startswith("/")
    parts = path.split("/")[1:] if absolute else path.split("/")
    require(bool(parts) and all(part not in ("", ".", "..") for part in parts))
    descriptor = os.open("/" if absolute else ".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def read_regular(path: str | Path) -> bytes:
    with parent_handle(path) as (parent, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_LOCAL_BYTES)
            chunks, total = [], 0
            while True:
                chunk = os.read(descriptor, min(65_536, MAX_LOCAL_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                require(total <= MAX_LOCAL_BYTES)
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(descriptor)


@contextmanager
def new_private_directory(path: str | Path):
    """Create only the final component; existing paths are always refused."""
    with parent_handle(path) as (parent, name):
        os.mkdir(name, 0o700, dir_fd=parent)
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        os.fchmod(descriptor, 0o700)
        yield descriptor
    finally:
        os.close(descriptor)


def write_exclusive(directory: int, filename: str, raw: bytes) -> None:
    require(filename not in ("", ".", "..") and "/" not in filename and "\x00" not in filename)
    descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        os.fchmod(descriptor, 0o600)
        position = 0
        while position < len(raw):
            written = os.write(descriptor, raw[position:])
            require(written > 0)
            position += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def package_version(raw: bytes) -> str:
    # Read a string literal without importing package initialization or core.
    for node in ast.parse(raw.decode("utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            require(isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
            return node.value.value
    raise ExerciseError("Package version unavailable")


def run_cli(input_path: Path, output_path: Path) -> dict:
    argv = [sys.executable, "-m", "radar_equity_replay", str(input_path), "--output", str(output_path)]
    environment = {"PATH": os.defpath, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=False)
    return {
        "argv": argv,
        "cwd": str(ROOT),
        "environment": {"PYTHONPATH": "src", "PYTHONDONTWRITEBYTECODE": "1"},
        "return_code": completed.returncode,
        "stdout_sha256": sha256(completed.stdout),
        "stderr_sha256": sha256(completed.stderr),
        "stdout_byte_count": len(completed.stdout),
        "stderr_byte_count": len(completed.stderr),
    }


def run_exercises(output_dir: str | Path) -> dict:
    # Reject lexical ambiguity before converting a relative path to absolute.
    with parent_handle(output_dir):
        pass
    output_path = Path(output_dir).absolute()
    source_raw = {name: read_regular(ROOT / name) for name in SOURCE_FILES}
    fixture_raw = {name: read_regular(ROOT / "examples" / f"{name}.json") for name in FIXTURES}
    source_hashes = {name: sha256(raw) for name, raw in source_raw.items()}
    fixture_hashes = {f"examples/{name}.json": sha256(raw) for name, raw in fixture_raw.items()}
    replay = json.loads(fixture_raw["replay"])
    log = {
        "schema": RUN_SCHEMA,
        "status": "passed",
        "synthetic_only": True,
        "execution_allowed": False,
        "review_status": "pending",
        "started_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "versions": {
            "python": ".".join(str(part) for part in sys.version_info[:3]),
            "python_implementation": sys.implementation.name,
            "package": package_version(source_raw["src/radar_equity_replay/__init__.py"]),
            "runner_schema": RUN_SCHEMA,
        },
        "source_sha256": source_hashes,
        "original_fixture_sha256": fixture_hashes,
        "scenarios": [],
        "negative_cases": [],
        "limitations": [
            "These are current local fixture tests, not historical authentication.",
            "Declared timestamps are not authenticated and absence of hindsight is not established.",
            "Only local fictional fixtures; no network, paid API, service or broker is used.",
            "No financial selection, recommendation, order, annualization or production approval.",
            "Each scenario is separate; their returns must not be added as one operation.",
        ],
    }
    with new_private_directory(output_path) as directory:
        zero_cost = copy.deepcopy(replay)
        zero_cost["fee_bps"] = zero_cost["slippage_bps"] = "0"
        zero_raw = json_bytes(zero_cost)
        write_exclusive(directory, "zero-cost.input.json", zero_raw)
        scenarios = [(name, ROOT / "examples" / f"{name}.json", fixture_raw[name]) for name in FIXTURES]
        scenarios.append(("zero-cost", output_path / "zero-cost.input.json", zero_raw))
        for name, input_path, raw in scenarios:
            destination = output_path / f"{name}.report.json"
            event = run_cli(input_path, destination)
            require(event["return_code"] == 0)
            result_raw = read_regular(destination)
            require(stat.S_IMODE(destination.stat(follow_symlinks=False).st_mode) == 0o600)
            checks = verify_report(raw, json.loads(result_raw))
            log["scenarios"].append({
                "name": name,
                "input_sha256": sha256(raw),
                "input_byte_count": len(raw),
                "output_sha256": sha256(result_raw),
                "output_byte_count": len(result_raw),
                "command": event,
                "verification": checks,
            })
        negatives = []
        future = copy.deepcopy(replay)
        decision = datetime.strptime(replay["decision_at"], "%Y-%m-%dT%H:%M:%SZ")
        future["evidence"][0]["available_at"] = (decision + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        negatives.append(("future-evidence-plus-one-second", future))
        same_session = copy.deepcopy(replay)
        same_session["execute_on"] = replay["sessions"][0]["date"]
        negatives.append(("execute-on-decision-session", same_session))
        authority = copy.deepcopy(replay)
        authority["approved"] = True
        negatives.append(("approved-extra-field", authority))
        for name, value in negatives:
            raw = json_bytes(value)
            input_path = output_path / f"rejected-{name}.input.json"
            destination = output_path / f"rejected-{name}.report.json"
            write_exclusive(directory, input_path.name, raw)
            event = run_cli(input_path, destination)
            require(event["return_code"] == 2 and not os.path.lexists(destination))
            log["negative_cases"].append({"name": name, "input_sha256": sha256(raw), "input_byte_count": len(raw), "output_created": False, "command": event})
        protected_output = output_path / "replay.report.json"
        before = sha256(read_regular(protected_output))
        overwrite = run_cli(ROOT / "examples" / "replay.json", protected_output)
        after = sha256(read_regular(protected_output))
        require(overwrite["return_code"] == 2 and before == after)
        log["overwrite_case"] = {"command": overwrite, "sha256_before": before, "sha256_after": after, "original_bytes_preserved": True}
        require(all(sha256(read_regular(ROOT / name)) == expected for name, expected in source_hashes.items()))
        require(all(sha256(read_regular(ROOT / name)) == expected for name, expected in fixture_hashes.items()))
        log["original_sources_and_fixtures_unchanged"] = True
        write_exclusive(directory, "run.json", json_bytes(log))
        write_exclusive(directory, "SUMMARY.txt", (
            "Local synthetic exercises completed: 4 reports independently verified.\n"
            "3 invalid inputs rejected with code 2 and no report; overwrite refused without changing bytes.\n"
            "Exact input/output/source hashes and command arguments are in run.json.\n"
            "Tests describe this local run, not authenticated dates or absence of hindsight.\n"
            "review_status=pending; execution_allowed=false.\n"
        ).encode("utf-8"))
    return log


class SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, "Arguments rejected. Use --help for the local fixture exercises.\n")


def main(argv=None) -> int:
    parser = SafeParser(description="Run four local synthetic CLI exercises with independent rational checks.")
    parser.add_argument("--output-dir", required=True, help="New private directory; its parent must already exist")
    arguments = parser.parse_args(argv)
    try:
        run_exercises(arguments.output_dir)
    except (ExerciseError, OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("Exercise run rejected or verification failed. Use a new path with an existing parent; inspect any partial local run before retrying.", file=sys.stderr)
        return 2
    print("Four synthetic reports verified; three refusals and overwrite preservation checked. Human review is pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
