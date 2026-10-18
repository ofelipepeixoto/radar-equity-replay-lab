"""Independent arithmetic and real-CLI exercise-runner regression tests."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).absolute().parent.parent
SPEC = importlib.util.spec_from_file_location("run_exercises", ROOT / "tools" / "run_exercises.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RationalOracleTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / "examples" / "replay.json").read_bytes()
        self.value = json.loads(self.raw)

    def test_exact_half_even_rounding_and_negative_zero(self):
        self.assertEqual(runner.decimal8(Fraction("1.000000005")), "1.00000000")
        self.assertEqual(runner.decimal8(Fraction("1.000000015")), "1.00000002")
        self.assertEqual(runner.decimal8(Fraction("-1.000000015")), "-1.00000002")
        self.assertEqual(runner.decimal8(Fraction("-0.000000005")), "0.00000000")

    def test_zero_cost_replay_and_distinct_final_phase(self):
        self.value["fee_bps"] = self.value["slippage_bps"] = "0"
        portfolio, returns = runner.rational_portfolio(self.value)
        benchmark, benchmark_return = runner.rational_portfolio(self.value, benchmark=True)
        self.assertEqual(portfolio["final_nav"], "1090.00000000")
        self.assertEqual(returns, Fraction(9))
        self.assertEqual(benchmark["final_nav"], "1080.00000000")
        self.assertEqual(benchmark_return, Fraction(8))
        self.assertEqual(portfolio["unallocated_cash"], "100.00000000")
        self.assertEqual(portfolio["curve"][-1]["date"], portfolio["curve"][-2]["date"])
        self.assertEqual([point["phase"] for point in portfolio["curve"][-2:]], ["close_mark", "final_liquidation"])
        self.assertTrue(all(value == "0.00000000" for value in portfolio["costs"].values()))

    def test_cash_has_no_asset_cost_and_benchmark_still_invests(self):
        value = json.loads((ROOT / "examples" / "cash.json").read_bytes())
        portfolio, returns = runner.rational_portfolio(value)
        benchmark, _ = runner.rational_portfolio(value, benchmark=True)
        self.assertEqual(portfolio["final_nav"], "1000.00000000")
        self.assertEqual(portfolio["max_drawdown_pct"], "0.00000000")
        self.assertEqual(returns, 0)
        self.assertTrue(all(cost == "0.00000000" for cost in portfolio["costs"].values()))
        self.assertNotEqual(benchmark["costs"]["entry_fee"], "0.00000000")

    def test_oracle_uses_t_plus_one_and_final_liquidation(self):
        first, _ = runner.rational_portfolio(self.value)
        changed = copy.deepcopy(self.value)
        changed["sessions"][0]["prices"] = {asset: "999" for asset in changed["assets"]}
        changed["sessions"][0]["benchmark_price"] = "999"
        second, _ = runner.rational_portfolio(changed)
        self.assertEqual(first, second)
        self.assertLess(Fraction(first["final_nav"]), Fraction(first["curve"][-2]["nav"]))
        self.assertEqual(first["final_nav"], "1087.03444981")


@unittest.skipUnless(os.name == "posix", "Runner requires documented POSIX no-follow IO")
class RunnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temporary.name) / "exercise-run"
        cls.log = runner.run_exercises(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_four_actual_reports_and_independent_validation(self):
        self.assertEqual([item["name"] for item in self.log["scenarios"]], ["replay", "loss", "cash", "zero-cost"])
        for scenario in self.log["scenarios"]:
            raw = (self.path / f"{scenario['name']}.report.json").read_bytes()
            self.assertEqual(runner.sha256(raw), scenario["output_sha256"])
            self.assertEqual(scenario["command"]["return_code"], 0)
            self.assertIn("-m", scenario["command"]["argv"])
            self.assertEqual(scenario["verification"]["benchmark_metrics_costs_and_curve"], "passed")
        self.assertEqual(json.loads((self.path / "run.json").read_bytes()), self.log)
        self.assertTrue(self.log["original_sources_and_fixtures_unchanged"])

    def test_private_modes_for_all_created_files(self):
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o700)
        for path in self.path.iterdir():
            self.assertTrue(path.is_file())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_three_negative_cli_cases_create_no_output(self):
        self.assertEqual(len(self.log["negative_cases"]), 3)
        for negative in self.log["negative_cases"]:
            self.assertEqual(negative["command"]["return_code"], 2)
            self.assertFalse(negative["output_created"])
            self.assertFalse((self.path / f"rejected-{negative['name']}.report.json").exists())
        future = json.loads((self.path / "rejected-future-evidence-plus-one-second.input.json").read_bytes())
        self.assertEqual(future["evidence"][0]["available_at"], "2026-01-05T21:00:01Z")

    def test_overwrite_refused_and_existing_run_unchanged(self):
        overwrite = self.log["overwrite_case"]
        self.assertEqual(overwrite["command"]["return_code"], 2)
        self.assertEqual(overwrite["sha256_before"], overwrite["sha256_after"])
        before = {path.name: runner.sha256(path.read_bytes()) for path in self.path.iterdir()}
        with self.assertRaises(FileExistsError):
            runner.run_exercises(self.path)
        after = {path.name: runner.sha256(path.read_bytes()) for path in self.path.iterdir()}
        self.assertEqual(before, after)

    def test_oracle_rejects_tampered_metrics_costs_curves_and_excess(self):
        raw = (ROOT / "examples" / "replay.json").read_bytes()
        report = json.loads((self.path / "replay.report.json").read_bytes())
        paths = [(side, key) for side in ("portfolio", "benchmark") for key in ("initial_capital", "unallocated_cash", "final_nav", "return_pct", "max_drawdown_pct")]
        paths += [(side, "costs", key) for side in ("portfolio", "benchmark") for key in report[side]["costs"]]
        paths += [(side, "curve", index, "nav") for side in ("portfolio", "benchmark") for index in range(len(report[side]["curve"]))]
        paths.append(("excess_return_percentage_points",))
        for path in paths:
            with self.subTest(path=path):
                changed = copy.deepcopy(report)
                container = changed
                for key in path[:-1]:
                    container = container[key]
                container[path[-1]] = "999999.00000000"
                with self.assertRaises(runner.ExerciseError):
                    runner.verify_report(raw, changed)

    def test_metadata_boolean_types_cannot_be_replaced_by_integers(self):
        raw = (ROOT / "examples" / "replay.json").read_bytes()
        report = json.loads((self.path / "replay.report.json").read_bytes())
        for key, replacement in (("timestamp_authenticity_verified", 0), ("decision_origin_verified", 0), ("declared_evidence_available_by_decision", 1), ("uses_future_prices_for_valuation_only", 1)):
            with self.subTest(key=key):
                changed = copy.deepcopy(report)
                changed["point_in_time_guard"][key] = replacement
                with self.assertRaises(runner.ExerciseError):
                    runner.verify_report(raw, changed)

    def test_symlink_parent_and_lexical_escape_are_refused(self):
        link = Path(self.temporary.name) / "directory-link"
        link.symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(OSError):
            runner.run_exercises(link / "new-run")
        self.assertFalse((self.path / "new-run").exists())
        with self.assertRaises(runner.ExerciseError):
            runner.run_exercises(str(self.path) + "/../escape")


if __name__ == "__main__":
    unittest.main()
