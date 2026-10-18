"""Independent adversarial review; written without reading author tests.

Synthetic mathematics and local IO only. Not real financial validation.
"""
import copy
import json
import os
import stat
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from radar_equity_replay import InvalidInput, analyze
from radar_equity_replay.io import read_input, write_report


def fixture():
    return {
        'schema':'radar-equity-replay-input/v1', 'synthetic_only':True,
        'project_id':'PRIVATE-IDENTIFIER-REVIEW', 'currency':'USD',
        'initial_capital':'1000.00',
        'decision_at':'2024-01-02T22:00:00Z', 'execute_on':'2024-01-03',
        'price_basis':'synthetic_adjusted_close_no_dividends',
        'assets':['PRIVATE-ASSET-REVIEW'], 'target_weights':{'PRIVATE-ASSET-REVIEW':'1'},
        'fee_bps':'0','slippage_bps':'0',
        'evidence':[{'evidence_id':'PRIVATE-EVIDENCE-REVIEW','available_at':'2024-01-02T21:00:00Z','source_url':'https://private-evidence.invalid/never-echo','text':'PRIVATE EVIDENCE TEXT NEVER ECHO'}],
        'sessions':[{'date':'2024-01-02','available_at':'2024-01-02T21:00:00Z','prices':{'PRIVATE-ASSET-REVIEW':'100'},'benchmark_price':'100'},
                    {'date':'2024-01-03','available_at':'2024-01-03T21:00:00Z','prices':{'PRIVATE-ASSET-REVIEW':'200'},'benchmark_price':'100'},
                    {'date':'2024-01-04','available_at':'2024-01-04T21:00:00Z','prices':{'PRIVATE-ASSET-REVIEW':'400'},'benchmark_price':'100'}]
    }


def run(value):
    return analyze(json.dumps(value,separators=(',',':')).encode())


class IndependentMathematics(unittest.TestCase):
    def test_second_session_entry_avoids_first_price_profit(self):
        r=run(fixture())
        self.assertEqual(r['portfolio']['return_pct'],'100.00000000')
        self.assertEqual(r['portfolio']['final_nav'],'2000.00000000')
        self.assertEqual(r['benchmark']['return_pct'],'0.00000000')
    def test_flat_prices_and_no_cost_equal_zero(self):
        f=fixture()
        for s in f['sessions']:s['prices']['PRIVATE-ASSET-REVIEW']='10'
        r=run(f)
        self.assertEqual(r['portfolio']['return_pct'],'0.00000000')
        self.assertEqual(r['portfolio']['max_drawdown_pct'],'0.00000000')
    def test_roundtrip_costs_independent_closed_form(self):
        f=fixture();f['fee_bps']='100';f['slippage_bps']='100'
        for s in f['sessions']:s['prices']['PRIVATE-ASSET-REVIEW']='10'
        r=run(f)['portfolio']
        with localcontext() as c:
            c.prec=50
            expected=Decimal(1000)*(1-Decimal('.01'))/(1+Decimal('.01'))*(1-Decimal('.01'))/(1+Decimal('.01'))
            self.assertEqual(Decimal(r['final_nav']),expected.quantize(Decimal('.00000001')))
            self.assertAlmostEqual(float(sum(map(Decimal,r['costs'].values()))),float(Decimal(1000)-expected),places=6)
    def test_exit_friction_in_drawdown(self):
        f=fixture();f['fee_bps']='100';f['slippage_bps']='100'
        for s in f['sessions']:s['prices']['PRIVATE-ASSET-REVIEW']='10'
        r=run(f)['portfolio']
        self.assertEqual(Decimal(r['max_drawdown_pct']),-Decimal(r['return_pct']))
    def test_peak_to_trough_not_initial_only(self):
        f=fixture();f['sessions'][2]['prices']['PRIVATE-ASSET-REVIEW']='100'
        f['sessions'].append({'date':'2024-01-05','available_at':'2024-01-05T21:00:00Z','prices':{'PRIVATE-ASSET-REVIEW':'600'},'benchmark_price':'100'})
        r=run(f)['portfolio']
        self.assertEqual(r['max_drawdown_pct'],'50.00000000')
        self.assertEqual(r['return_pct'],'200.00000000')
    def test_zero_allocation_stays_cash_with_no_asset_cost(self):
        f=fixture();f['target_weights']['PRIVATE-ASSET-REVIEW']='0';f['fee_bps']='100';f['slippage_bps']='100'
        r=run(f)['portfolio']
        self.assertEqual(r['return_pct'],'0.00000000')
        self.assertEqual(r['unallocated_cash'],'1000.00000000')
        self.assertEqual(set(r['costs'].values()),{'0.00000000'})
    def test_half_allocation_cash_not_reinvested(self):
        f=fixture();f['target_weights']['PRIVATE-ASSET-REVIEW']='0.5'
        r=run(f)['portfolio']
        self.assertEqual(r['final_nav'],'1500.00000000')
        self.assertEqual(r['return_pct'],'50.00000000')
    def test_identical_benchmark_same_costs_same_results(self):
        f=fixture();f['fee_bps']='34.333333';f['slippage_bps']='12.123456'
        for s in f['sessions']:s['benchmark_price']=s['prices']['PRIVATE-ASSET-REVIEW']
        r=run(f)
        self.assertEqual(r['portfolio'],r['benchmark'])
        self.assertEqual(r['excess_return_percentage_points'],'0.00000000')
    def test_extreme_valid_values_remain_finite(self):
        f=fixture();f['initial_capital']='1000000000000.00';f['sessions'][1]['prices']['PRIVATE-ASSET-REVIEW']='0.000001';f['sessions'][2]['prices']['PRIVATE-ASSET-REVIEW']='1000000000'
        r=run(f)['portfolio']
        self.assertEqual(Decimal(r['final_nav']),Decimal('1000000000000000000000000000'))
    def test_first_price_change_does_not_change_entry_result(self):
        f=fixture();a=run(f)['portfolio'];f['sessions'][0]['prices']['PRIVATE-ASSET-REVIEW']='999999999'
        self.assertEqual(run(f)['portfolio'],a)


class IndependentContract(unittest.TestCase):
    def test_evidence_after_decision_rejected(self):
        f=fixture();f['evidence'][0]['available_at']='2024-01-02T22:00:01Z'
        with self.assertRaises(InvalidInput):run(f)
    def test_wrong_entry_session_rejected(self):
        f=fixture();f['execute_on']='2024-01-04'
        with self.assertRaises(InvalidInput):run(f)
    def test_decision_after_entry_price_available_rejected(self):
        f=fixture();f['decision_at']='2024-01-03T21:00:00Z'
        with self.assertRaises(InvalidInput):run(f)
    def test_numeric_and_nonfinite_json_rejected(self):
        for x in [float('nan'),1,True,-1]:
            with self.subTest(value=repr(x)):
                f=fixture();f['initial_capital']=x
                with self.assertRaises(InvalidInput):run(f)
    def test_weight_over_one_and_short_rejected(self):
        for x in ['1.000001','-0.5','NaN','1e-3']:
            with self.subTest(value=x):
                f=fixture();f['target_weights']['PRIVATE-ASSET-REVIEW']=x
                with self.assertRaises(InvalidInput):run(f)
    def test_duplicate_json_keys_rejected(self):
        raw=json.dumps(fixture()).encode().replace(b'"currency": "USD"',b'"currency":"USD","currency":"BRL"')
        with self.assertRaises(InvalidInput):analyze(raw)
    def test_external_source_and_query_rejected(self):
        for url in ['https://example.com/a','https://fixture.invalid/a?token=x','https://u:p@fixture.invalid/a','https://fixture.invalid:443/a']:
            with self.subTest(url=url):
                f=fixture();f['evidence'][0]['source_url']=url
                with self.assertRaises(InvalidInput):run(f)
    def test_private_identifiers_text_and_urls_not_echoed(self):
        report=json.dumps(run(fixture()))
        for s in ['PRIVATE-IDENTIFIER-REVIEW','PRIVATE-ASSET-REVIEW','PRIVATE-EVIDENCE-REVIEW','private-evidence.invalid','PRIVATE EVIDENCE TEXT NEVER ECHO']:
            self.assertNotIn(s,report)
    def test_invalid_dates_and_zero_price_rejected(self):
        f=fixture();f['sessions'][0]['date']='2024-02-30'
        with self.assertRaises(InvalidInput):run(f)
        f=fixture();f['sessions'][2]['prices']['PRIVATE-ASSET-REVIEW']='0'
        with self.assertRaises(InvalidInput):run(f)
    def test_overlarge_raw_and_deep_object_rejected(self):
        for raw in [b' '*(1024*1024+1),b'['*10000+b']'*10000]:
            with self.assertRaises(InvalidInput):analyze(raw)
    def test_no_authority_in_output(self):
        r=run(fixture())
        self.assertIs(r['execution_allowed'],False)
        self.assertEqual(r['review_status'],'pending')
        self.assertIs(r['point_in_time_guard']['timestamp_authenticity_verified'],False)


class IndependentFilesystem(unittest.TestCase):
    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report';p.write_bytes(b'ORIGINAL')
            with self.assertRaises(InvalidInput):write_report(p,b'NEW')
            self.assertEqual(p.read_bytes(),b'ORIGINAL')
    def test_symlink_input_output_and_parent_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'target';target.write_bytes(b'ORIGINAL');link=root/'link';link.symlink_to(target)
            for operation in [lambda:read_input(link),lambda:write_report(link,b'NEW')]:
                with self.assertRaises(InvalidInput):operation()
            directory=root/'directory';directory.mkdir();parent=root/'parent';parent.symlink_to(directory,target_is_directory=True)
            with self.assertRaises(InvalidInput):write_report(parent/'report',b'NEW')
            self.assertEqual(target.read_bytes(),b'ORIGINAL')
    def test_fifo_directory_and_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pipe';os.mkfifo(p)
            for name in [p,Path(d)]:
                with self.assertRaises(InvalidInput):read_input(name)
            p=Path(d)/'large';p.write_bytes(b'x'*(1024*1024+1))
            with self.assertRaises(InvalidInput):read_input(p)
    def test_private_mode_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report';write_report(p,b'ABC')
            self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            self.assertEqual(read_input(p),b'ABC')


if __name__=='__main__':unittest.main(verbosity=2)
