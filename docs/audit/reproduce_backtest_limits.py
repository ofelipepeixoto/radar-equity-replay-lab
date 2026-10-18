"""Two synthetic, offline observations of the legacy per-model harness.

Not an economic backtest and not a claim of exploitable profit.
"""
import json
from hedge_fund.backtesting.engine import BacktestEngine
from hedge_fund.backtesting.models import Trade
from hedge_fund.data.models import Price
from hedge_fund.models import Signal

class ClosingSignal:
    name='closing-fixture'
    def predict(self,ticker,day,data):
        return Signal(model_name=self.name,ticker=ticker,date=day,value=1.0,reasoning='Synthetic signal known at this session close')

class FixturePrices:
    def get_prices(self,ticker,start,end,**kw):
        return [Price(open=p,high=p,low=p,close=p,volume=100,time=d) for d,p in [('2024-01-02',100.0),('2024-01-03',110.0),('2024-01-04',120.0)] if start<=d<=end]

engine=BacktestEngine(capital=1000,per_trade=100)
r=engine.run_alpha(ClosingSignal(),['FIXTURE'],FixturePrices(),'2024-01-02','2024-01-02',holding_days=1)
t=r.trades[0]
assert t.entry_date=='2024-01-02' and t.entry_price==100
first={'observation':'legacy_same_close_entry','signal_as_of':'2024-01-02 close','entry_date':t.entry_date,'entry_price':t.entry_price,'next_close':110.0,'scope':'BacktestEngine.run_alpha; not backtest_fund'}

def trade(ticker,entry,exit,pnl):
    return Trade(ticker=ticker,direction='long',entry_date=entry,exit_date=exit,entry_price=100,exit_price=100+pnl,shares=1,pnl=pnl,return_pct=pnl/100,holding_days=1)
trades=[trade('A','2024-01-02','2024-01-10',100),trade('B','2024-01-03','2024-01-04',-200)]
entry_order=engine._build_equity_curve(trades)
exit_order=engine._build_equity_curve(sorted(trades,key=lambda x:x.exit_date))
assert entry_order==[1000,1100,900] and exit_order==[1000,800,900]
second={'observation':'legacy_equity_curve_uses_input_order','entry_sorted_curve':entry_order,'exit_sorted_curve':exit_order,'scope':'legacy private helper; run_alpha sorts trades by entry_date before calling it; neither curve is daily mark-to-market'}
print(json.dumps({'synthetic_only':True,'observations':[first,second]},indent=2))
