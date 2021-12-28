import backtrader as bt
from strategies.test_strategy import TestStrategy
import pandas as pd
import pyfolio as pf
import warnings

warnings.filterwarnings("ignore")
import matplotlib

matplotlib.use("Agg")


cerebro = bt.Cerebro()

tickers = ["BTCUSDT"]
live_start_date = "2020-9-3"
for sym in tickers:
    generic_csv_obj_kwargs = {
        # pre-fetched from Binance API
        "dataname": f"../data_store/ticker_data/{sym} 1d_2017-08-17 00:00:00_2021-12-14 00:00:00.csv",
        "datetime": 12,
        "open": 1,
        "high": 2,
        "low": 3,
        "close": 4,
        "volume": 5,
        "openinterest": 7,
        "dtformat": "%Y-%m-%d %H:%M:%S",
    }
    datafeed = bt.feeds.GenericCSVData(**generic_csv_obj_kwargs)
    cerebro.adddata(datafeed)

# 1. initial cash amt
cerebro.broker.set_cash(100 * 1000)

# 2. for implementing fractional commission scheme
class CommInfoFractional(bt.CommissionInfo):
    def getsize(self, price, cash):
        """Returns fractional size for cash operation @price"""
        return self.p.leverage * (cash / price)  # leverage defaults to 1


# set the commission to 0.1%, both for buying and selling
cerebro.broker.addcommissioninfo(CommInfoFractional(commission=0.001))

# 3. add benchmarking
cerebro.addanalyzer(
    bt.analyzers.TimeReturn,
    timeframe=bt.TimeFrame.Days,
    data=datafeed,
    _name="Buy and hold",
)  # asset return
cerebro.addanalyzer(
    bt.analyzers.TimeReturn,
    timeframe=bt.TimeFrame.Days,
    _name="Up & dn model",
)  # portfolio strategy

cerebro.addstrategy(TestStrategy)

results = cerebro.run()

# 4. Computing analysis from returns data
strat0 = results[0]


def _convert_dt_2_timestamp(s):
    s.index = pd.to_datetime(s.index, format="%Y-%m-%d", utc=True)
    return s


tdata_analyzer = strat0.analyzers.getbyname("Buy and hold")
bh_returns = _convert_dt_2_timestamp(pd.Series(tdata_analyzer.get_analysis()))
bh_returns.name = "BTC"

tret_analyzer = strat0.analyzers.getbyname("Up & dn model")
strat_returns = _convert_dt_2_timestamp(pd.Series(tret_analyzer.get_analysis()))

fig = pf.create_returns_tear_sheet(
    returns=strat_returns,
    live_start_date=live_start_date,
    benchmark_rets=bh_returns,
    return_fig=True,
)
fig.savefig("./pyfolio_tear_sheet.png")

# 5. Built-in visualization for indicators & asset price ts
cerebro.plot()
