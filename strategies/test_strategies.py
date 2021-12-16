import backtrader as bt


class TestStrategy(bt.Strategy):
    # configurable for the strategy
    params = dict(
        smafast=10,  # fast moving average
        smaslow=30,  # slow moving average
        emafast=10,
    )

    def log(self, txt, dt=None):
        """Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.strftime("%m/%d/%Y, %H:%M:%S"), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # crossover signal
        sma1 = bt.ind.SMA(period=self.p.smafast)
        sma2 = bt.ind.SMA(period=self.p.smaslow)
        self.crossover = bt.ind.CrossOver(sma1, sma2)

        bt.indicators.MACDHisto(self.datas[0])  # fast ema over slow ema
        rsi = bt.indicators.RSI(
            self.datas[0]
        )  # relative strength indicator based on historical no of up and dn
        bt.indicators.ExponentialMovingAverage(self.datas[0], period=self.p.emafast)

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.sellprice = None
        self.sellcomm = None

    # override
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                self.sellprice = order.executed.price
                self.sellcomm = order.executed.comm

            self.bar_executed = len(self)  # bar_no, doesnt matter min/daily data

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None  # reset for next notification

    # override
    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" % (trade.pnl, trade.pnlcomm))

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if self.crossover > 0:  # fast crosses above slow, potential up-momentum
            self.log("BUY CREATE, %.2f" % self.dataclose[0])
            self.buy()  # enter 1 BTC long, order executed 'at market on next bar

        elif self.crossover < 0:  # fast crosses below slow, potential dn-momentum
            self.log("SELL CREATE, %.2f" % self.dataclose[0])
            self.sell()  # enter 1 BTC short, order executed 'at market on next bar
