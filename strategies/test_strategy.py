import backtrader as bt
import pickle
from dateutil.relativedelta import relativedelta
import pandas as pd


class TestStrategy(bt.Strategy):
    # hyperparams tuned
    params = dict(
        rsi_window=19,
        macd_window_slow=26,
        macd_window_fast=17,
        macd_window_sign=14,
        bollinger_window=25,
        bollinger_window_dev=4,
    )
    # days, position holding period
    position_holding_period = 3
    # pre-learnt stat model
    with open("../prototypes/scti_(up & dn).pkl", "rb") as fid:
        mdl = pickle.load(fid)

    def _model_prediction(self):
        rsi = self.rsi[0]
        crossing_lband = self.crossing_lband[0]
        pband = self.pband[0]
        wband = self.wband[0]

        feature_vec = pd.DataFrame(
            {
                "rsi": [rsi],
                "crossing_lband": [crossing_lband],
                "pband": [pband],
                "wband": [wband],
            }
        )
        up_or_dn = int(self.mdl.predict(feature_vec))
        self.log(f"Coming 3 days BTC going up or dn: {up_or_dn}. ")
        return up_or_dn

    def log(self, txt, dt=None):
        """Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.strftime("%Y-%m-%d %H:%M:%S"), txt))

    def __init__(self):
        # a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # predictors for stat model
        self.rsi = bt.ind.RSI(period=self.params.rsi_window)  # line
        self.bollinger = bt.ind.BollingerBands(
            period=self.params.bollinger_window,
            devfactor=self.params.bollinger_window_dev,
        )  # indicator
        self.crossing_lband = bt.ind.CrossOver(
            self.dataclose, self.bollinger.lines.bot
        ).crossover  # line
        self.pband = (self.dataclose - self.bollinger.lines.bot) / (
            self.bollinger.lines.top - self.bollinger.lines.bot
        )  # line
        self.wband = (
            (self.bollinger.lines.top - self.bollinger.lines.bot)
            / self.bollinger.lines.mid
        ) * 100

        # to keep track of all created orders
        self.orders = []

    # observer for order status
    def notify_order(self, order):
        notification_map = {
            bt.Order.Submitted: "Submitted",
            bt.Order.Accepted: "Accepted",
            bt.Order.Expired: "Expired",
            bt.Order.Cancelled: "Cancelled",
            bt.Order.Rejected: "Rejected",
            bt.Order.Margin: "Margin",
            bt.Order.Partial: "Partial",
        }

        if order.status in notification_map:
            msg = "Order " + notification_map[order.status] + "."
            self.log(msg)

        elif order.status == bt.Order.Completed:
            if order.isbuy():
                self.log(
                    "-> Buy executed, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
            elif order.issell():
                self.log(
                    "-> Sell executed, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )

            self.last_order_completed_bar = len(
                self
            )  # bar_no, doesnt matter min/daily data

    # observer for trade pnl
    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log("-> Trade profit, Gross %.2f, Net %.2f" % (trade.pnl, trade.pnlcomm))

    def next(self):
        # # log closing price
        # self.log("Close, %.2f" % self.dataclose[0])

        """Rules for buy & sell"""
        alive_order_status = [
            bt.Order.Submitted,
            bt.Order.Accepted,
            bt.Order.Margin,
            bt.Order.Partial,
        ]

        if self.orders:
            if (
                self.orders[-1].status in alive_order_status
            ):  # prev order not yet completed, wait ...
                self.log(f"Previous order is still pending, no new order ...")
                return

        if not self.position:
            up_or_dn = self._model_prediction()

            # invest 0.6 fraction as acc is 60%
            size = 0.6 * self.stats.broker.value[0] / self.dataclose[0]

            limit_order_spec = dict(
                price=self.dataclose[0],
                exectype=bt.Order.Limit,
                # valid between the next and next next bar
                valid=self.datas[0].datetime.date(0) + relativedelta(days=2),
                size=size,
            )

            if up_or_dn == 1:
                self.log("Buy created @ price: %.2f" % self.dataclose[0])
                self.orders.append(
                    self.buy(**limit_order_spec)
                )  # long, to be executed at next bar

            elif up_or_dn == 0:
                self.log("Sell created @ price: %.2f" % self.dataclose[0])
                self.orders.append(
                    self.sell(**limit_order_spec)
                )  # short, to be executed at next bar

        else:
            # no position will be hold for more than 3 days
            if (
                len(self)
                >= self.last_order_completed_bar
                + self.position_holding_period
                - 1  # -1 so closing at end of 3rd bar from last order completed bar
            ):
                self.log("Order created to close position last executed. ")
                self.orders.append(self.close())  # unwind, to be executed at next bar
