import backtrader as bt
from strategies.test_strategies import TestStrategy


cerebro = bt.Cerebro()

# Create data feeds
tickers = ["BTCUSDT", "ETHUSDT"]
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

# initial cash amt
cerebro.broker.set_cash(100 * 1000)

# define strategy
cerebro.addstrategy(TestStrategy)
# hyperparameter tuning
# strats = cerebro.optstrategy(
#     TestStrategy,
#     smafast=range(10, 31, 10),
#     smaslow=range(30, 71, 20),
# )

# Set the commission to 0.1%, both for buying and selling
cerebro.broker.setcommission(commission=0.001)

cerebro.run()
# print(cerebro.run(maxcpus=6))

# visualization
cerebro.plot()
