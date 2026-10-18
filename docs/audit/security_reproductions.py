"""Bounded local observations against pinned upstream; no real credentials/data.

These assert the observed unsafe behavior, not the desired fixed behavior.
Run from the upstream checkout with its isolated dependencies available.
"""
from __future__ import annotations

import contextlib
import io
import json
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def no_network(*args, **kwargs):
    raise AssertionError("security reproductions must not use real sockets")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network

import requests

from hedge_fund.data.cached import CachedDataClient
from hedge_fund.data.client import FDClient
from hedge_fund.data.models import CompanyFacts, FinancialMetrics
from hedge_fund.features.snapshot import build_snapshot
from hedge_fund.fund.spec import FundSpec
from hedge_fund.paths import write_atomic


class SecurityObservations(unittest.TestCase):
    def test_fd_pagination_forwards_fake_key_to_different_origin(self):
        observed = []

        def send(prepared, **kwargs):
            observed.append((prepared.url, prepared.headers.get("X-API-Key")))
            response = requests.Response()
            response.status_code = 200
            response.request = prepared
            response.url = prepared.url
            body = {"rows": [{"synthetic": True}]}
            if len(observed) == 1:
                body["next_page_url"] = "http://foreign.invalid/page-2"
            response._content = json.dumps(body).encode()
            return response

        with FDClient(api_key="SYNTHETIC-KEY-NOT-REAL") as client:
            with patch.object(client._session, "send", side_effect=send):
                rows = client._get("/synthetic/", {}, "rows")
        self.assertEqual(len(rows), 2)
        self.assertEqual(observed[1], ("http://foreign.invalid/page-2", "SYNTHETIC-KEY-NOT-REAL"))

    def test_predictable_atomic_temp_follows_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            outside = root / "synthetic-unrelated.txt"
            outside.write_text("original synthetic data")
            book = root / "book.json"
            book.with_name(".book.json.tmp").symlink_to(outside)
            write_atomic(book, "overwritten synthetic data")
            self.assertEqual(outside.read_text(), "overwritten synthetic data")
            self.assertTrue(book.is_symlink())

    def test_data_cache_reuses_other_provider_scalar(self):
        class Provider:
            def __init__(self, value):
                self.value, self.calls = value, 0

            def get_market_cap(self, ticker, end_date):
                self.calls += 1
                return self.value

        with tempfile.TemporaryDirectory() as folder:
            first, second = Provider(100.0), Provider(200.0)
            a = CachedDataClient(first, cache_dir=folder)
            b = CachedDataClient(second, cache_dir=folder)
            self.assertEqual(a.get_market_cap("SYNTH", "2020-01-01"), 100.0)
            self.assertEqual(b.get_market_cap("SYNTH", "2020-01-01"), 100.0)
            self.assertEqual(second.calls, 0)

    def test_market_cap_uses_attribute_absent_from_facts_schema(self):
        with FDClient(api_key="SYNTHETIC-KEY-NOT-REAL") as client:
            with patch.object(client, "get_company_facts", return_value=CompanyFacts(ticker="SYNTH")):
                with self.assertRaises(AttributeError):
                    client.get_market_cap("SYNTH", "2020-01-01")

    def test_snapshot_trusts_provider_future_filing_rows(self):
        rows = [FinancialMetrics(ticker="SYNTH", report_period=f"2024-{month:02d}-01", period="ttm", filing_date="2030-01-01") for month in (12, 9, 6, 3)]
        data = SimpleNamespace(get_financial_metrics=lambda *a, **k: rows, get_company_facts=lambda *a: None)
        snapshot = build_snapshot("SYNTH", "2020-01-01", data)
        self.assertEqual(len(snapshot.periods), 4)
        self.assertTrue(all(p.filing_date > snapshot.as_of for p in snapshot.periods))

    def test_mandate_name_escapes_default_research_directory(self):
        from hedge_fund import run

        spec = FundSpec.model_validate({
            "schema_version": 2, "name": "../synthetic-escaped",
            "strategies": [{"name": "synthetic", "models": [{"name": "pead"}], "blend": {"mode": "long_short"}}],
            "risk": {"max_position_pct": 0.2, "max_gross_exposure": 1.0},
        })
        result = SimpleNamespace(
            model_dump_json=lambda **k: "{}", start="2020-01-01", end="2020-01-02", dates=[],
            metrics=SimpleNamespace(n_cycles=0, n_orders=0, total_return_pct=0, benchmark_return_pct=0, sharpe_ratio=0, max_drawdown_pct=0),
        )
        args = SimpleNamespace(universe="SYNTH", mandate="synthetic.yaml", start="2020-01-01", end="2020-01-02", out=None)
        console = SimpleNamespace(status=lambda *a, **k: contextlib.nullcontext(), print=lambda *a, **k: None)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            research = root / "research"
            with patch.object(run, "RESEARCH_DIR", research), patch.object(run, "load_spec", return_value=spec), patch.object(run, "Fund", return_value=object()), patch.object(run, "FDClient", return_value=contextlib.nullcontext(object())), patch.object(run, "CachedDataClient", return_value=object()), patch.object(run, "backtest_fund", return_value=result), contextlib.redirect_stdout(io.StringIO()):
                run._backtest(args, None, console)
            escaped = list(root.glob("synthetic-escaped-*.json"))
            self.assertEqual(len(escaped), 1)
            self.assertEqual(escaped[0].read_text(), "{}")
            self.assertEqual(list(research.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
