from __future__ import annotations
import copy
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal, localcontext
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from radar_equity_replay import InvalidInput, analyze
from radar_equity_replay.__main__ import main
from radar_equity_replay.core import MAX_BYTES
from radar_equity_replay.io import read_input, write_report

FIXTURE = Path(__file__).resolve().parents[1] / 'examples' / 'replay.json'
def encoded(value): return json.dumps(value).encode()

class ReplayTests(unittest.TestCase):
    def setUp(self): self.value = json.loads(FIXTURE.read_text())
    def reject(self, value=None, raw=None):
        with self.assertRaises(InvalidInput) as error:
            analyze(encoded(self.value if value is None else value) if raw is None else raw)
        self.assertNotIn('PRIVATE', str(error.exception))
    def test_t_plus_one_ignores_decision_close_for_entry(self):
        self.value['target_weights'] = {'SYN_A':'1','SYN_B':'0'}
        self.value['fee_bps'] = self.value['slippage_bps'] = '0'
        result = analyze(encoded(self.value))
        self.assertEqual(result['portfolio']['final_nav'], '1200.00000000')
        self.assertEqual(result['portfolio']['return_pct'], '20.00000000')
        self.assertEqual(result['portfolio']['curve'][0]['date'], '2026-01-06')
        self.assertEqual(result['point_in_time_guard']['entry_session_index'], '1')
        self.value['sessions'][0]['prices']['SYN_A'] = '999999'
        self.assertEqual(analyze(encoded(self.value))['portfolio'], result['portfolio'])
    def test_cash_zero_cost_hand_calculation(self):
        self.value['fee_bps'] = self.value['slippage_bps'] = '0'
        result=analyze(encoded(self.value))['portfolio']
        self.assertEqual(result['unallocated_cash'], '100.00000000')
        self.assertEqual(result['final_nav'], '1090.00000000')
        self.assertEqual(result['return_pct'], '9.00000000')
        self.assertEqual(set(result['costs'].values()), {'0.00000000'})
    def test_nonzero_costs_paid_from_allocation(self):
        self.value['target_weights'] = {'SYN_A':'1','SYN_B':'0'}
        self.value['fee_bps'] = self.value['slippage_bps'] = '100'
        for item in self.value['sessions'][1:]: item['prices']['SYN_A'] = item['benchmark_price'] = '100'
        result=analyze(encoded(self.value))
        with localcontext() as ctx:
            ctx.prec=50
            units=Decimal(1000)/Decimal('1.01')/Decimal(101)
            final=units*99*Decimal('0.99')
            fee_in=units*101*Decimal('0.01'); fee_out=units*99*Decimal('0.01')
            for actual,expected in [(result['portfolio']['final_nav'],final),(result['portfolio']['costs']['entry_fee'],fee_in),(result['portfolio']['costs']['exit_fee'],fee_out)]:
                self.assertEqual(Decimal(actual),expected.quantize(Decimal('0.00000001')))
        self.assertEqual(result['portfolio'],result['benchmark'])
        self.assertLess(Decimal(result['portfolio']['return_pct']),0)
        self.assertGreater(Decimal(result['portfolio']['max_drawdown_pct']),0)
    def test_benchmark_full_capital_same_timing_and_costs(self):
        self.value['target_weights']={'SYN_A':'1','SYN_B':'0'}
        for session in self.value['sessions']: session['benchmark_price']=session['prices']['SYN_A']
        result=analyze(encoded(self.value))
        self.assertEqual(result['portfolio'],result['benchmark'])
        self.assertEqual(result['excess_return_percentage_points'],'0.00000000')
    def test_zero_allocation_retains_cash(self):
        self.value['target_weights']={'SYN_A':'0','SYN_B':'0'}
        result=analyze(encoded(self.value)); portfolio=result['portfolio']
        self.assertEqual(portfolio['final_nav'],'1000.00000000')
        self.assertEqual(portfolio['unallocated_cash'],'1000.00000000')
        self.assertEqual(portfolio['max_drawdown_pct'],'0.00000000')
        self.assertEqual(set(portfolio['costs'].values()),{'0.00000000'})
        self.assertNotEqual(result['benchmark']['final_nav'],'1000.00000000')
    def test_drawdown_includes_costs_and_initial_capital(self):
        self.value['fee_bps']=self.value['slippage_bps']='0'
        self.value['target_weights']={'SYN_A':'1','SYN_B':'0'}
        self.value['sessions'][2]['prices']['SYN_A']='120'; self.value['sessions'][3]['prices']['SYN_A']='60'
        result=analyze(encoded(self.value))['portfolio']
        self.assertEqual(result['final_nav'],'600.00000000')
        self.assertEqual(result['max_drawdown_pct'],'50.00000000')
        self.assertEqual(result['curve'][-1]['phase'],'final_liquidation')
    def test_raw_hash_determinism_privacy(self):
        self.value['project_id']='PRIVATE_PROJECT'; self.value['assets']=['PRIVATE_A','PRIVATE_B']
        self.value['target_weights']={'PRIVATE_A':'0.6','PRIVATE_B':'0.3'}
        for session in self.value['sessions']:
            session['prices']={'PRIVATE_A':session['prices']['SYN_A'],'PRIVATE_B':session['prices']['SYN_B']}
        self.value['evidence'][0].update(evidence_id='PRIVATE_EVIDENCE',source_url='https://private.invalid/PRIVATE_URL',text='PRIVATE_THESIS')
        raw=encoded(self.value); result=analyze(raw)
        self.assertEqual(result,analyze(raw)); self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertFalse(result['execution_allowed']); self.assertEqual(result['review_status'],'pending')
        self.assertFalse(result['point_in_time_guard']['timestamp_authenticity_verified'])
        self.assertNotEqual(result['input_sha256'],analyze(raw+b' ')['input_sha256'])
    def test_future_evidence_rejected(self):
        self.value['evidence'][0]['available_at']='2026-01-05T21:00:01Z'; self.reject()
    def test_decision_window(self):
        for timestamp in ('2026-01-05T19:59:59Z','2026-01-06T20:00:00Z'):
            with self.subTest(timestamp=timestamp): self.value['decision_at']=timestamp; self.reject()
    def test_execute_on_second_session(self):
        self.value['execute_on']=self.value['sessions'][0]['date']; self.reject()
    def test_dates_order_available_coherence(self):
        for change in ('duplicate','order','mismatch','noncanonical','invalid','timezone'):
            with self.subTest(change=change):
                value=copy.deepcopy(self.value)
                if change=='duplicate': value['sessions'][2]=value['sessions'][1]
                if change=='order': value['sessions'][2],value['sessions'][3]=value['sessions'][3],value['sessions'][2]
                if change=='mismatch': value['sessions'][2]['available_at']='2026-01-08T20:00:00Z'
                if change=='noncanonical': value['sessions'][2]['date']='2026-1-07'
                if change=='invalid': value['sessions'][2]['date']='2026-02-30'
                if change=='timezone': value['decision_at']='2026-01-05T21:00:00+00:00'
                self.reject(value)
    def test_prices_positive_bounded_decimal_strings(self):
        for price in ('0','-1','0.0000001','1e2','01.00','+1','1000000001','NaN','Infinity',1,1.5,True,None,[]):
            with self.subTest(price=price): self.value['sessions'][1]['prices']['SYN_A']=price; self.reject()
    def test_json_numeric_tokens_and_nonfinite_values(self):
        for token in (b'1',b'1.5',b'NaN',b'Infinity',b'-Infinity',b'false',b'null'):
            with self.subTest(token=token): self.reject(raw=encoded(self.value).replace(b'"10"',token,1))
    def test_capital_currency_basis_costs_bounds(self):
        changes=[('initial_capital','0.00'),('initial_capital','1000'),('initial_capital','1000000000000.01'),('currency','JPY'),('currency',[]),('price_basis','unadjusted'),('fee_bps','100.000001'),('slippage_bps','-1'),('synthetic_only',False)]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                item=copy.deepcopy(self.value); item[key]=value; self.reject(item)
    def test_weight_universe_and_no_leverage(self):
        for weights in ({'SYN_A':'0.5'},{'SYN_A':'0.5','SYN_B':'0.5','OTHER':'0'},{'SYN_A':'0.6','SYN_B':'0.5'},{'SYN_A':'-0.1','SYN_B':'0'},{'SYN_A':True,'SYN_B':'0'},[],None):
            with self.subTest(weights=weights): self.value['target_weights']=weights; self.reject()
    def test_every_session_same_universe_exact_keys(self):
        for change in ('missing','extra','session_extra','top_extra','evidence_extra'):
            with self.subTest(change=change):
                value=copy.deepcopy(self.value)
                if change=='missing': del value['sessions'][2]['prices']['SYN_B']
                if change=='extra': value['sessions'][2]['prices']['OTHER']='1'
                if change=='session_extra': value['sessions'][2]['annotation']='PRIVATE'
                if change=='top_extra': value['annotation']='PRIVATE'
                if change=='evidence_extra': value['evidence'][0]['annotation']='PRIVATE'
                self.reject(value)
    def test_asset_and_session_count_bounds(self):
        for assets in ([],['SYN_A']*2,['A']*21,'SYN_A',[True]):
            with self.subTest(assets=assets):
                value=copy.deepcopy(self.value); value['assets']=assets; self.reject(value)
        for sessions in ([],self.value['sessions'][:2],[self.value['sessions'][0]]*2501):
            with self.subTest(length=len(sessions)):
                value=copy.deepcopy(self.value); value['sessions']=sessions; self.reject(value)
    def test_evidence_bounds_ids_url_text(self):
        for key,bad in (('evidence_id','bad id'),('source_url','https://real.example/test'),('source_url','http://x.invalid'),('source_url','https://user@x.invalid'),('source_url','https://x.invalid:443'),('source_url','https://x.invalid/?token=PRIVATE'),('text',''),('text','  '),('text','x'*1001)):
            with self.subTest(key=key,bad=str(bad)[:30]):
                value=copy.deepcopy(self.value); value['evidence'][0][key]=bad; self.reject(value)
        for evidence in ([],[self.value['evidence'][0]]*2,[self.value['evidence'][0]]*51,True):
            value=copy.deepcopy(self.value); value['evidence']=evidence; self.reject(value)
    def test_encoding_duplicate_keys_nesting_controls(self):
        for raw in (b'\xff',b'\xef\xbb\xbf{}',b'{"schema":"a","schema":"b"}',b'['*2000+b']'*2000,b'{}',b'null',b'',b'x'*(MAX_BYTES+1)):
            with self.subTest(length=len(raw)): self.reject(raw=raw)
        for text in ('bad\nline','\ud800','bad\u202evalue','\x00','\x7f'):
            self.value['evidence'][0]['text']=text; self.reject()
    def test_evidence_url_forbids_empty_port_query_and_fragment(self):
        for url in ('https://x.invalid/?', 'https://x.invalid/#',
                    'https://x.invalid:', 'https://x.invalid:/ok',
                    'https://x.invalid:?#', 'https://x.invalid:443/path'):
            with self.subTest(url=url):
                self.value['evidence'][0]['source_url']=url
                self.reject()
        self.value['evidence'][0]['source_url']='https://x.invalid/path%3F%23'
        self.assertEqual(analyze(encoded(self.value))['review_status'], 'pending')
    def test_all_shipped_examples(self):
        for path in FIXTURE.parent.glob('*.json'):
            with self.subTest(example=path.name):
                result=analyze(path.read_bytes()); self.assertEqual(result['review_status'],'pending')
                self.assertGreaterEqual(Decimal(result['portfolio']['final_nav']),0)
    def test_extreme_valid_prices_and_capital_remain_finite(self):
        self.value['initial_capital']='1000000000000.00'
        self.value['target_weights']={'SYN_A':'1','SYN_B':'0'}
        self.value['fee_bps']=self.value['slippage_bps']='0'
        self.value['sessions'][1]['prices']['SYN_A']='0.000001'
        self.value['sessions'][-1]['prices']['SYN_A']='1000000000'
        result=analyze(encoded(self.value))
        self.assertEqual(result['portfolio']['final_nav'],'1000000000000000000000000000.00000000')
    def test_valid_twenty_asset_universe(self):
        self.value['assets']=['SYN_'+str(index) for index in range(20)]
        self.value['target_weights']={asset:'0.05' for asset in self.value['assets']}
        for session in self.value['sessions']:
            session['prices']={asset:'100' for asset in self.value['assets']}
        self.assertEqual(analyze(encoded(self.value))['asset_count'],'20')
    def test_decimal_context_is_independent_of_caller(self):
        from decimal import Inexact, ROUND_DOWN
        raw=encoded(self.value)
        expected=analyze(raw)
        with localcontext() as context:
            context.prec=3; context.rounding=ROUND_DOWN; context.traps[Inexact]=True
            self.assertEqual(analyze(raw),expected)
    def test_valid_maximum_session_count(self):
        from datetime import date, timedelta
        self.value['assets']=['SYN_A']; self.value['target_weights']={'SYN_A':'1'}
        self.value['sessions']=[]
        start=date(2026,1,5)
        for index in range(2500):
            day=(start+timedelta(days=index)).isoformat()
            self.value['sessions'].append({'date':day,'available_at':day+'T20:00:00Z','prices':{'SYN_A':'100'},'benchmark_price':'100'})
        result=analyze(encoded(self.value))
        self.assertEqual(result['session_count'],'2500')
        self.assertEqual(len(result['portfolio']['curve']),2500)

class FileTests(unittest.TestCase):
    def test_cli_argument_errors_do_not_echo_unknown_values(self):
        with redirect_stderr(StringIO()) as stderr:
            with self.assertRaises(SystemExit) as error:
                main(['PRIVATE_INPUT','--output','PRIVATE_OUTPUT','--PRIVATE_CREDENTIAL=SECRET'])
            self.assertEqual(error.exception.code,2)
            self.assertNotIn('PRIVATE',stderr.getvalue())
            self.assertNotIn('SECRET',stderr.getvalue())
    def test_unsupported_platform_and_missing_no_follow_fail_closed(self):
        with patch('radar_equity_replay.io.os.name','nt'):
            with self.assertRaises(InvalidInput): read_input(FIXTURE)
        with patch('radar_equity_replay.io.os.O_NOFOLLOW',0):
            with self.assertRaises(InvalidInput): read_input(FIXTURE)
    def test_exclusive_output_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json'; write_report(path,b'new report')
            self.assertEqual(path.read_bytes(),b'new report'); self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            with self.assertRaises(InvalidInput): write_report(path,b'overwrite')
            self.assertEqual(path.read_bytes(),b'new report')
    def test_symlinks_in_input_output_and_parents(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); regular=root/'input.json'; regular.write_bytes(FIXTURE.read_bytes())
            link=root/'link.json'; link.symlink_to(regular)
            parent_link=root/'linked'; parent_link.symlink_to(root,target_is_directory=True)
            for path in (link,parent_link/'input.json'):
                with self.subTest(path=str(path)):
                    with self.assertRaises(InvalidInput): read_input(path)
            for path in (link,parent_link/'new.json'):
                with self.subTest(path=str(path)):
                    with self.assertRaises(InvalidInput): write_report(path,b'test')
            self.assertFalse((root/'new.json').exists()); self.assertEqual(read_input(regular),FIXTURE.read_bytes())
    def test_regular_bounded_no_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); empty=root/'empty'; empty.write_bytes(b''); large=root/'large'; large.write_bytes(b'x'*(MAX_BYTES+1))
            fifo=root/'fifo'; os.mkfifo(fifo)
            for path in (empty,large,fifo,root,str(root)+'/../input.json'):
                with self.subTest(path=str(path)):
                    with self.assertRaises(InvalidInput): read_input(path)
    def test_cli_success_generic_failure_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(StringIO()),redirect_stderr(StringIO()) as stderr:
            output=Path(folder)/'report.json'; self.assertEqual(main([str(FIXTURE),'--output',str(output)]),0)
            self.assertFalse(json.loads(output.read_text())['execution_allowed']); prior=output.read_bytes()
            self.assertEqual(main([str(FIXTURE),'--output',str(output)]),2); self.assertEqual(prior,output.read_bytes())
            bad=Path(folder)/'PRIVATE_INPUT.json'; bad.write_text('{"PRIVATE":"secret"}')
            self.assertEqual(main([str(bad),'--output',str(Path(folder)/'new.json')]),2)
            self.assertNotIn('PRIVATE',stderr.getvalue()); self.assertFalse((Path(folder)/'new.json').exists())

if __name__=='__main__': unittest.main()
