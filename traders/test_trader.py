import backtrader as bt
from strategies.test_strategy import TestStrategy
from datetime import datetime


cerebro = bt.Cerebro()

# create data feeds, which can be live
tickers = ["BTCUSDT"]
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
        "fromdate": datetime(2020, 9, 3),
        # timeframe=bt.TimeFrame.Minutes
    }
    datafeed = bt.feeds.GenericCSVData(**generic_csv_obj_kwargs)
    cerebro.adddata(datafeed)

# initial cash amt
cerebro.broker.set_cash(100 * 1000)

# for implementing fractional commission scheme
class CommInfoFractional(bt.CommissionInfo):
    def getsize(self, price, cash):
        """Returns fractional size for cash operation @price"""
        return self.p.leverage * (cash / price)  # leverage defaults to 1


# set the commission to 0.1% (Binance fee), both for buying and selling
cerebro.broker.addcommissioninfo(CommInfoFractional(commission=0.001))

cerebro.addstrategy(TestStrategy)

results = cerebro.run()
strat = results[0]

# built-in visualization
cerebro.plot()
