import pandas as pd
import numpy as np
import requests
import time
from math import ceil
from pathlib import Path
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

"""
This script can modified to execute async for fast download time. 
"""


class RequestHFData:
    ### Exchange specified ###
    data_limit = 1000  # 1000 rows
    max_req_per_min = 1200

    # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data
    col_header = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ]

    # saving location
    save_rel_path = Path("./ticker_data")

    def __init__(self, symbols, start_dt, end_dt, interval) -> None:
        self.symbols = symbols
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.interval = interval
        self._interval_parser()

    @staticmethod
    def _convert_datetime_to_sec(t):
        """t in UTC format"""
        unix_epoch = datetime(1970, 1, 1)
        return int((t - unix_epoch).total_seconds())

    def _interval_parser(self):
        valid_suffix = ("s", "m", "h", "d")
        parsing_suffix = None
        for suffix in valid_suffix:
            if suffix in self.interval:
                if parsing_suffix is None:
                    parsing_suffix = suffix
                else:
                    raise ValueError(
                        f"Interval argument {self.interval} contains more than 1 valid suffixes. "
                    )
        if parsing_suffix is None:
            raise ValueError(
                f"Interval argument {self.interval} contains no valid suffixes. "
            )

        self._interval_suffix = parsing_suffix
        self._interval_scaler = int(self.interval.strip(parsing_suffix))

    def _req_hf_data_4_single_ticker(self, sym):
        # # main loop for requesting HF data of a single ticker
        sdt = self.start_dt
        while sdt < self.end_dt:
            # avoid spamming
            if self._req_past_min > RequestHFData.max_req_per_min:
                time.sleep(self.sleep_length)
                self._req_past_min = 0

            start_time_mil_sec = self._convert_datetime_to_sec(sdt) * 1000  # to milsec
            edt = RequestHFData.data_limit * self._row_t_delta + sdt
            end_time_mil_sec = (
                self._convert_datetime_to_sec(min(edt, self.end_dt)) * 1000
            )  # to milsec

            api_url = (
                "https://api.binance.com/api/v3/klines?"
                f"symbol={sym}&interval={self.interval}"
                f"&startTime={start_time_mil_sec}&endTime={end_time_mil_sec}"
                f"&limit={RequestHFData.data_limit}"
            )

            req_obj = requests.get(api_url)

            if req_obj.status_code != 200:
                time.sleep(self.sleep_length)  # then retry
                continue

            df = pd.DataFrame(req_obj.json())
            self._df_dict[sym].append(df)

            sdt = edt
            self._req_past_min += 1
            self.no_requested += 1

            finish_pc = min(
                self.no_requested / self.total_req_no / len(self.symbols) * 100, 100
            )
            print(f"{finish_pc:.1f}% completed. ", end="\r")

    def req_hf_data(self):
        # for storing data requested from api
        self._df_dict = {sym: [] for sym in self.symbols}

        # helper variables
        self._req_past_min = 0  # requests done for past min.
        self.no_requested = 0  # no. of requests so far
        self.sleep_length = 30  # s

        # no of all request to be made
        if self._interval_suffix == "s":
            time_span = (self.end_dt - self.start_dt).total_seconds()
            row_t_diff = self._interval_scaler
            self._row_t_delta = relativedelta(seconds=row_t_diff)
        elif self._interval_suffix == "m":
            time_span = (self.end_dt - self.start_dt).total_seconds()
            row_t_diff = self._interval_scaler * 60
            self._row_t_delta = relativedelta(seconds=row_t_diff)
        elif self._interval_suffix == "h":
            time_span = (self.end_dt - self.start_dt).total_seconds()
            row_t_diff = self._interval_scaler * 60 * 60
            self._row_t_delta = relativedelta(seconds=row_t_diff)
        elif self._interval_suffix == "d":
            time_span = (self.end_dt - self.start_dt).days
            row_t_diff = self._interval_scaler
            self._row_t_delta = relativedelta(days=row_t_diff)

        self.total_req_no = ceil(time_span / row_t_diff / RequestHFData.data_limit)

        for sym in self.symbols:
            self._req_hf_data_4_single_ticker(sym)

    def _concat_data(self):
        _millisec_2_dt_str = lambda x: datetime.utcfromtimestamp(x / 1000.0).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self._concat_dfs = {}
        for sym, dfs in self._df_dict.items():
            df = pd.concat(dfs, axis=0)
            # paste colnames provided by exchange
            df.columns = RequestHFData.col_header

            # convert ms to datetime format
            df["datetime"] = df["open_time"].map(_millisec_2_dt_str)

            # drop duplicates (in case)
            df.drop_duplicates(inplace=True)
            # sort (in case)
            df.sort_values(by=["open_time"], axis=0, ascending=True, inplace=True)

            self._concat_dfs[sym] = df

    def save_data(self):
        self._concat_data()

        dt_format = "%Y-%m-%d %H:%M:%S"
        filename_suffix = "_".join(
            [
                self.interval,
                self.start_dt.strftime(dt_format),
                self.end_dt.strftime(dt_format),
            ]
        )
        for sym in self.symbols:
            filename = " ".join([sym, filename_suffix]) + ".csv"
            filepath = RequestHFData.save_rel_path.joinpath(filename)
            self._concat_dfs[sym].to_csv(filepath, index=False)

    def candlestick_plot(self):
        for sym in self.symbols:
            df = self._concat_dfs[sym]
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=df["datetime"],
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                    )
                ]
            )
            fig.update_layout(
                title=sym,
            )
            fig.show()


if __name__ == "__main__":
    # user specified
    start_dt = datetime(2017, 8, 17)
    end_dt = datetime(2021, 12, 14)
    symbols = ["BTCUSDT", "ETHUSDT"]
    interval = "1d"

    rhf = RequestHFData(symbols, start_dt, end_dt, interval)
    rhf.req_hf_data()
    rhf.save_data()
    rhf.candlestick_plot()
