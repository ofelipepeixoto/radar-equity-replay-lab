"""Original, deterministic synthetic equity replay. No market or execution connectors."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from urllib.parse import urlsplit

MAX_BYTES = 1024 * 1024
SCHEMA = "radar-equity-replay-input/v1"
OUTPUT_SCHEMA = "radar-equity-replay-report/v1"
PRICE_BASIS = "synthetic_adjusted_close_no_dividends"
TOP_KEYS = {"schema", "synthetic_only", "project_id", "currency", "initial_capital", "decision_at", "execute_on", "price_basis", "assets", "target_weights", "fee_bps", "slippage_bps", "evidence", "sessions"}
SESSION_KEYS = {"date", "available_at", "prices", "benchmark_price"}
EVIDENCE_KEYS = {"evidence_id", "available_at", "source_url", "text"}
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z", re.ASCII)
DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?\Z", re.ASCII)
MONEY_RE = re.compile(r"(?:0|[1-9][0-9]{0,12})\.[0-9]{2}\Z", re.ASCII)
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
UTC_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z", re.ASCII)


class InvalidInput(ValueError):
    """Untrusted input rejected. Details deliberately never contain supplied values."""


def _reject(*_args):
    raise InvalidInput("Invalid synthetic replay input")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


def _walk(value, depth=0):
    if depth > 8:
        _reject()
    if isinstance(value, str):
        if len(value) > 4096 or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value):
            _reject()
    elif type(value) is dict:
        for key, item in value.items():
            _walk(key, depth + 1)
            _walk(item, depth + 1)
    elif type(value) is list:
        for item in value:
            _walk(item, depth + 1)
    elif value is not True:
        # The sole boolean permitted by the schema is synthetic_only:true.
        _reject()


def _keys(value, expected):
    if type(value) is not dict or set(value) != expected:
        _reject()


def _id(value):
    if type(value) is not str or not ID_RE.fullmatch(value):
        _reject()
    return value


def _decimal(value, minimum, maximum, *, money=False):
    pattern = MONEY_RE if money else DECIMAL_RE
    if type(value) is not str or not pattern.fullmatch(value):
        _reject()
    number = Decimal(value)
    if not minimum <= number <= maximum:
        _reject()
    return number


def _date(value):
    if type(value) is not str or not DATE_RE.fullmatch(value):
        _reject()
    try:
        return date.fromisoformat(value)
    except ValueError:
        _reject()


def _utc(value):
    if type(value) is not str or not UTC_RE.fullmatch(value):
        _reject()
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _reject()


def _source(value):
    if type(value) is not str or len(value) > 2048 or not value.isascii() or any(c.isspace() for c in value) or "\\" in value:
        _reject()
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ""
        if parsed.scheme != "https" or not hostname.endswith(".invalid") or hostname == ".invalid" or parsed.username is not None or parsed.password is not None or parsed.port is not None or parsed.query or parsed.fragment:
            _reject()
        if not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+invalid", hostname):
            _reject()
    except ValueError:
        _reject()


def _load(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
        _reject()
    try:
        # json's numeric hooks reject all JSON numbers before arithmetic.
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_float=_reject, parse_int=_reject, parse_constant=_reject)
        _walk(value)
    except (UnicodeError, ValueError, RecursionError):
        _reject()
    return value


def _validate(value):
    _keys(value, TOP_KEYS)
    if value["schema"] != SCHEMA or value["synthetic_only"] is not True or value["price_basis"] != PRICE_BASIS or value["currency"] not in ("USD", "BRL", "EUR"):
        _reject()
    _id(value["project_id"])
    initial = _decimal(value["initial_capital"], Decimal("0.01"), Decimal("1000000000000"), money=True)
    fee = _decimal(value["fee_bps"], Decimal(0), Decimal(100)) / 10000
    slip = _decimal(value["slippage_bps"], Decimal(0), Decimal(100)) / 10000
    assets = value["assets"]
    if type(assets) is not list or not 1 <= len(assets) <= 20:
        _reject()
    for asset in assets:
        _id(asset)
    if len(set(assets)) != len(assets):
        _reject()
    weights = value["target_weights"]
    _keys(weights, set(assets))
    weights = {asset: _decimal(weights[asset], Decimal(0), Decimal(1)) for asset in assets}
    if sum(weights.values(), Decimal(0)) > 1:
        _reject()
    decision = _utc(value["decision_at"])
    execute_on = _date(value["execute_on"])
    evidence = value["evidence"]
    if type(evidence) is not list or not 1 <= len(evidence) <= 50:
        _reject()
    evidence_ids = set()
    for item in evidence:
        _keys(item, EVIDENCE_KEYS)
        evidence_id = _id(item["evidence_id"])
        if evidence_id in evidence_ids or _utc(item["available_at"]) > decision:
            _reject()
        evidence_ids.add(evidence_id)
        _source(item["source_url"])
        if type(item["text"]) is not str or not 1 <= len(item["text"]) <= 1000 or not item["text"].strip():
            _reject()
    sessions = value["sessions"]
    if type(sessions) is not list or not 3 <= len(sessions) <= 2500:
        _reject()
    parsed = []
    previous_date = previous_available = None
    for item in sessions:
        _keys(item, SESSION_KEYS)
        session_date = _date(item["date"])
        available = _utc(item["available_at"])
        if available.date() != session_date or (previous_date is not None and (session_date <= previous_date or available <= previous_available)):
            _reject()
        _keys(item["prices"], set(assets))
        prices = {asset: _decimal(item["prices"][asset], Decimal("0.000001"), Decimal("1000000000")) for asset in assets}
        benchmark = _decimal(item["benchmark_price"], Decimal("0.000001"), Decimal("1000000000"))
        parsed.append((session_date, available, prices, benchmark))
        previous_date, previous_available = session_date, available
    if not parsed[0][1] <= decision < parsed[1][1] or execute_on != parsed[1][0]:
        _reject()
    return initial, fee, slip, assets, weights, parsed


def _number(value):
    # Output is decimal text, rounded only here. Internal calculations use 50 digits.
    rounded = value.quantize(Decimal("0.00000001"))
    return format(abs(rounded) if rounded == 0 else rounded, ".8f")


def _drawdown(curve):
    peak = curve[0]
    worst = Decimal(0)
    for nav in curve:
        peak = max(peak, nav)
        worst = max(worst, (peak - nav) / peak * 100)
    return worst


def _portfolio(initial, fee, slip, assets, weights, sessions, benchmark=False):
    allocations = [initial] if benchmark else [initial * weights[a] for a in assets]
    entry_prices = [sessions[1][3]] if benchmark else [sessions[1][2][a] for a in assets]
    cash = initial - sum(allocations, Decimal(0))
    units = [allocation / (1 + fee) / (price * (1 + slip)) for allocation, price in zip(allocations, entry_prices)]
    entry_notional = sum((unit * price * (1 + slip) for unit, price in zip(units, entry_prices)), Decimal(0))
    entry_fee = entry_notional * fee
    entry_slippage = sum((unit * price * slip for unit, price in zip(units, entry_prices)), Decimal(0))
    curve = [initial]
    marks = []
    for index in range(1, len(sessions)):
        prices = [sessions[index][3]] if benchmark else [sessions[index][2][a] for a in assets]
        nav = cash + sum((unit * price for unit, price in zip(units, prices)), Decimal(0))
        curve.append(nav)
        marks.append({"session_index": str(index), "date": sessions[index][0].isoformat(), "phase": "close_mark", "nav": _number(nav)})
    final_prices = [sessions[-1][3]] if benchmark else [sessions[-1][2][a] for a in assets]
    exit_notional = sum((unit * price * (1 - slip) for unit, price in zip(units, final_prices)), Decimal(0))
    exit_fee = exit_notional * fee
    exit_slippage = sum((unit * price * slip for unit, price in zip(units, final_prices)), Decimal(0))
    final = cash + exit_notional - exit_fee
    curve.append(final)
    marks.append({"session_index": str(len(sessions) - 1), "date": sessions[-1][0].isoformat(), "phase": "final_liquidation", "nav": _number(final)})
    return_pct = (final / initial - 1) * 100
    return {"initial_capital": _number(initial), "unallocated_cash": _number(cash), "final_nav": _number(final), "return_pct": _number(return_pct), "max_drawdown_pct": _number(_drawdown(curve)), "costs": {"entry_fee": _number(entry_fee), "exit_fee": _number(exit_fee), "entry_slippage_vs_close": _number(entry_slippage), "exit_slippage_vs_close": _number(exit_slippage)}, "curve": marks}, return_pct


def analyze(raw: bytes) -> dict:
    """Validate and replay bytes. No supplied identifier, URL or evidence text is echoed."""
    try:
        with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
            value = _load(raw)
            initial, fee, slip, assets, weights, sessions = _validate(value)
            portfolio, portfolio_return = _portfolio(initial, fee, slip, assets, weights, sessions)
            benchmark, benchmark_return = _portfolio(initial, fee, slip, assets, weights, sessions, benchmark=True)
            return {"schema": OUTPUT_SCHEMA, "mode": "synthetic_buy_and_hold_replay", "synthetic_only": True, "execution_allowed": False, "review_status": "pending", "input_sha256": hashlib.sha256(raw).hexdigest(), "currency": value["currency"], "price_basis": PRICE_BASIS, "asset_count": str(len(assets)), "evidence_count": str(len(value["evidence"])), "session_count": str(len(sessions)), "decision_at": value["decision_at"], "execute_on": value["execute_on"], "first_session": sessions[0][0].isoformat(), "last_session": sessions[-1][0].isoformat(), "fee_bps": value["fee_bps"], "slippage_bps": value["slippage_bps"], "point_in_time_guard": {"entry_session_index": "1", "declared_evidence_available_by_decision": True, "timestamp_authenticity_verified": False, "decision_origin_verified": False, "uses_future_prices_for_valuation_only": True}, "portfolio": portfolio, "benchmark": benchmark, "excess_return_percentage_points": _number(portfolio_return - benchmark_return), "pointers": ["/target_weights", "/sessions/1/prices", "/sessions/1/benchmark_price", "/evidence"], "limitations": ["Synthetic educational replay only; no investment recommendation or execution.", "Fixed weights are declared inputs; no decision algorithm or thesis is evaluated.", "Timestamps and synthetic status are declarations, not independently authenticated.", "Fractional units; no rebalancing, dividends, interest, taxes, FX, liquidity or market impact.", "Benchmark invests 100% with identical entry/exit fee and slippage rates.", "Drawdown includes initial capital, entry close mark, later close marks and final liquidation.", "Decimal outputs use half-even rounding to 8 places; internal arithmetic uses 50 significant digits."]}
    except (InvalidOperation, OverflowError, RecursionError, TypeError, KeyError, ValueError):
        _reject()
