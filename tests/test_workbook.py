"""Contract, privacy and IO checks for the offline educational workbook."""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal, localcontext
from html.parser import HTMLParser

from radar_equity_replay.core import InvalidInput, MAX_BYTES, analyze
from radar_equity_replay.workbook import main, render_workbook


ROOT = Path(__file__).resolve().parents[1]


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.attributes = []
        self.ids = []
        self.hrefs = []
        self.script_count = 0

    def handle_starttag(self, tag, attrs):
        self.attributes.extend(attrs)
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if "href" in attrs:
            self.hrefs.append(attrs["href"])
        if tag == "script":
            self.script_count += 1


class WorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "examples/replay.json").read_bytes()
        cls.fixture = json.loads(cls.raw)

    def fixture_bytes(self, mutate):
        value = json.loads(self.raw)
        mutate(value)
        return json.dumps(value).encode("utf-8")

    def test_all_public_fixtures_generate_offline_document(self):
        for filename in ("replay.json", "loss.json", "cash.json"):
            with self.subTest(fixture=filename):
                raw = (ROOT / "examples" / filename).read_bytes()
                document = render_workbook(raw)
                self.assertTrue(document.startswith("<!doctype html>"))
                self.assertIn('lang="pt-BR"', document)
                self.assertIn(hashlib.sha256(raw).hexdigest(), document)
                self.assertIn("review_status=pending", document)
                self.assertIn("execution_allowed=false", document)
                self.assertIn("synthetic_only=true", document)

    def test_navigation_accessibility_and_no_network_references(self):
        document = render_workbook(self.raw)
        parsed = _Document()
        parsed.feed(document)
        self.assertEqual(len(parsed.ids), len(set(parsed.ids)))
        for section in ("entender", "custos", "perdas", "cronologia"):
            self.assertIn(section, parsed.ids)
            self.assertIn("#" + section, parsed.hrefs)
        for link in parsed.hrefs:
            self.assertTrue(link.startswith("#") or link.startswith("data:application/json;base64,"))
            if link.startswith("#"):
                self.assertIn(link[1:], parsed.ids)
        self.assertIn("Pular para o conteúdo", document)
        self.assertIn("<noscript>", document)
        self.assertIn("prefers-reduced-motion", document)
        self.assertIn("connect-src 'none'", document)
        self.assertIn("base-uri 'none'", document)
        self.assertEqual(parsed.script_count, 1)
        self.assertFalse(any(name.startswith("on") for name, _ in parsed.attributes))
        self.assertFalse(any(name in ("src", "action", "srcdoc") for name, _ in parsed.attributes))

    def test_calculated_json_download_is_exact_sanitized_report(self):
        document = render_workbook(self.raw)
        encoded = re.search(r'href="data:application/json;base64,([A-Za-z0-9+/=]+)"', document).group(1)
        downloaded = json.loads(base64.b64decode(encoded))
        self.assertEqual(downloaded, analyze(self.raw))
        self.assertFalse(downloaded["execution_allowed"])
        self.assertEqual(downloaded["review_status"], "pending")

    def test_raw_bytes_hash_changes_with_whitespace(self):
        original = render_workbook(self.raw)
        changed_raw = self.raw + b"\n"
        changed = render_workbook(changed_raw)
        self.assertIn(hashlib.sha256(changed_raw).hexdigest(), changed)
        self.assertIn(hashlib.sha256(self.raw).hexdigest(), original)
        self.assertNotEqual(original, changed)

    def test_no_supplied_ids_urls_or_evidence_text_in_html_or_download(self):
        def mutate(value):
            value["project_id"] = "SECRET_PROJECT_SENTINEL"
            old = value["assets"][0]
            value["assets"][0] = "PRIVATE_ASSET_SENTINEL"
            value["target_weights"][value["assets"][0]] = value["target_weights"].pop(old)
            for session in value["sessions"]:
                session["prices"][value["assets"][0]] = session["prices"].pop(old)
            value["evidence"][0]["evidence_id"] = "EVIDENCE_SECRET_SENTINEL"
            value["evidence"][0]["source_url"] = "https://private-sentinel.invalid/private-source"
            value["evidence"][0]["text"] = '</script><img src=x onerror="alert(1)"><script>maliciousEvidenceSentinel</script>'
        raw = self.fixture_bytes(mutate)
        document = render_workbook(raw)
        for secret in ("SECRET_PROJECT_SENTINEL", "PRIVATE_ASSET_SENTINEL", "EVIDENCE_SECRET_SENTINEL", "private-sentinel.invalid", "private-source", "maliciousEvidenceSentinel", "onerror", "<img"):
            self.assertNotIn(secret, document)
        encoded = re.search(r'base64,([A-Za-z0-9+/=]+)"', document).group(1)
        downloaded = base64.b64decode(encoded).decode("utf-8")
        for secret in ("SECRET_PROJECT_SENTINEL", "PRIVATE_ASSET_SENTINEL", "private-sentinel.invalid", "maliciousEvidenceSentinel"):
            self.assertNotIn(secret, downloaded)

    def test_comparison_reuses_prices_capital_dates_and_weights(self):
        document = render_workbook(self.raw)
        free = json.loads(self.raw)
        free["fee_bps"] = "0"
        free["slippage_bps"] = "0"
        free_report = analyze(json.dumps(free).encode("utf-8"))
        self.assertEqual(free_report["portfolio"]["final_nav"], "1090.00000000")
        self.assertIn("BRL 1.090,00000000", document)
        self.assertIn("BRL 1.087,03444981", document)
        self.assertIn("BRL 2,96555019", document)
        self.assertIn("pode diferir da soma dos custos", document)
        self.assertIn("cenários alternativos", document)

    def test_cash_fixture_retains_capital_without_portfolio_cost(self):
        document = render_workbook((ROOT / "examples/cash.json").read_bytes())
        self.assertIn("0,0000% do capital", document)
        self.assertIn("caixa residual", document)
        self.assertIn("BRL 1.000,00000000", document)

    def test_curve_distinguishes_initial_capital_and_final_liquidation(self):
        document = render_workbook(self.raw)
        self.assertIn("Capital inicial<small>—</small>", document)
        self.assertIn("Fechamento de entrada T+1", document)
        self.assertIn("Liquidação hipotética<small>2026-01-08</small>", document)
        self.assertIn("não cria outro pregão", document)
        self.assertIn("arredondados a oito casas", document)
        self.assertIn("antes desse arredondamento", document)

    def test_datetime_and_guard_explanation(self):
        document = render_workbook(self.raw)
        self.assertIn("2026-01-05T21:00:00Z", document)
        self.assertIn("2026-01-06T20:00:00Z", document)
        self.assertIn("Todos os horários abaixo usam UTC", document)
        self.assertIn("não foram autenticadas", document)
        self.assertIn("não foi verificada", document)
        self.assertIn("Não há estimativa de recuperação", document)

    def test_determinism_independent_of_decimal_context(self):
        document = render_workbook(self.raw)
        with localcontext() as context:
            context.prec = 6
            self.assertEqual(render_workbook(self.raw), document)

    def test_valid_unicode_near_byte_limit_does_not_expand_internal_copy(self):
        value = json.loads(self.raw)
        assets = [f"SYN_{index:02}" for index in range(20)]
        value["assets"] = assets
        value["target_weights"] = {asset: "0.05" for asset in assets}
        value["evidence"] = [{
            "evidence_id": f"E{index}",
            "available_at": "2026-01-05T20:00:00Z",
            "source_url": "https://fixtures.invalid/replay",
            "text": "教" * 1000,
        } for index in range(50)]
        value["sessions"] = []
        for index in range(2500):
            day = (date(2026, 1, 5) + timedelta(days=index)).isoformat()
            value["sessions"].append({
                "date": day,
                "available_at": day + "T20:00:00Z",
                "prices": {asset: "1" for asset in assets},
                "benchmark_price": "1",
            })
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        escaped = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(raw), MAX_BYTES)
        self.assertGreater(len(escaped), MAX_BYTES)
        self.assertEqual(analyze(raw)["session_count"], "2500")
        document = render_workbook(raw)
        self.assertIn(hashlib.sha256(raw).hexdigest(), document)
        self.assertNotIn("教", document)

    def test_bad_contract_inputs_rejected_before_html(self):
        mutations = (
            lambda value: value.update(synthetic_only=False),
            lambda value: value.update(approved=True),
            lambda value: value.update(execution_allowed=True),
            lambda value: value.update(initial_capital="0.00"),
            lambda value: value.update(fee_bps="101"),
            lambda value: value.update(execute_on="2026-01-05"),
            lambda value: value["evidence"][0].update(available_at="2026-01-06T21:00:00Z"),
            lambda value: value["sessions"][1].update(available_at="2026-01-05T21:01:00Z"),
            lambda value: value["target_weights"].update(SYN_A="0.9"),
            lambda value: value["evidence"][0].update(source_url="https://example.com"),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate), self.assertRaises(InvalidInput):
                render_workbook(self.fixture_bytes(mutate))

    def test_duplicate_keys_invalid_bytes_and_numeric_literals_rejected(self):
        for raw in (b"", b"{}", b"\xff", self.raw.replace(b'"synthetic_only": true', b'"synthetic_only": true, "synthetic_only": true'), self.raw.replace(b'"1000.00"', b"1000.00"), self.raw.replace(b'"1000.00"', b"NaN")):
            with self.subTest(raw=raw[:20]), self.assertRaises(InvalidInput):
                render_workbook(raw)


@unittest.skipUnless(os.name == "posix", "Workbook IO supports POSIX only")
class WorkbookCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.input = self.root / "input.json"
        self.input.write_bytes((ROOT / "examples/replay.json").read_bytes())

    def tearDown(self):
        self.directory.cleanup()

    def run_cli(self, source, output):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main([str(source), "--output", str(output)])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_new_private_output_and_no_overwrite(self):
        output = self.root / "result.html"
        result, stdout, stderr = self.run_cli(self.input, output)
        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("offline criado", stdout)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        content = output.read_bytes()
        result, stdout, stderr = self.run_cli(self.input, output)
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(output.read_bytes(), content)
        self.assertNotIn(str(output), stderr)

    def test_final_input_symlink_rejected(self):
        link = self.root / "input-link.json"
        link.symlink_to(self.input)
        output = self.root / "not-created.html"
        result, _, stderr = self.run_cli(link, output)
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertNotIn(str(link), stderr)

    def test_input_parent_symlink_rejected(self):
        real = self.root / "real"
        real.mkdir()
        (real / "input.json").write_bytes(self.input.read_bytes())
        link = self.root / "linked"
        link.symlink_to(real, target_is_directory=True)
        output = self.root / "not-created.html"
        self.assertEqual(self.run_cli(link / "input.json", output)[0], 2)
        self.assertFalse(output.exists())

    def test_output_symlink_and_parent_symlink_rejected(self):
        target = self.root / "target.html"
        target.write_text("keep this", encoding="utf-8")
        link = self.root / "output-link.html"
        link.symlink_to(target)
        self.assertEqual(self.run_cli(self.input, link)[0], 2)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep this")
        real = self.root / "real"
        real.mkdir()
        parent = self.root / "parent-link"
        parent.symlink_to(real, target_is_directory=True)
        self.assertEqual(self.run_cli(self.input, parent / "not-created.html")[0], 2)
        self.assertFalse((real / "not-created.html").exists())

    def test_invalid_input_has_generic_error_without_content_or_path(self):
        self.input.write_text('{"PRIVATE_TEXT_SENTINEL": "invalid"}', encoding="utf-8")
        output = self.root / "not-created.html"
        result, stdout, stderr = self.run_cli(self.input, output)
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertNotIn("PRIVATE_TEXT_SENTINEL", stderr)
        self.assertNotIn(str(self.input), stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
