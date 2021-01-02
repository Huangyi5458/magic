import time
import pandas as pd
from abc import abstractmethod, ABCMeta

from Logger import logger
from .BaseRest import BaseRest


class BaseExchangeApi(metaclass=ABCMeta):
    def __init__(self, key=None, secret=None, name=None, symbol=None, **kwargs):
        self.name = name
        self.symbol_details = None
        self.working = False
        self.local_pos = None

        self.symbol = symbol
        self.rest: BaseRest = None

    def _initialize(self):
        self.symbol_details = self.format_symbol_details(self.rest.get_symbol_details())
        if not self.symbol_details: raise Exception(f"({self.name}) get_symbol_details failed")

    @staticmethod
    def generate_client_order_id(side):
        return f"{side}_{int(time.time()*1000)}"

    def dict_value_to_float(self, data: dict):
        return {k: self.value_to_float(v) for k, v in data.items()}

    @staticmethod
    def value_to_float(value):
        try:
            value = float(value)
        except ValueError:
            pass
        return value

    @abstractmethod
    def format_symbol_details(self, symbol_details) -> dict:
        """
        {
            "btcusdt":         {
            "base_currency": "btc",
            "quote_currency": "usdt",
            "price_precision": 2,
            "size_precision": 6,
            "tick_size": 0.01,
            "symbol": "btcusdt",
            "limit_max_order_size": 1000,
            "limit_min_order_size": 0.0001
        }
        }
        """
        pass

    @abstractmethod
    def format_ticker(self, ticker) -> dict:
        """
        {
            'ask_price': float(tick['ask'][0]),
            'bid_price': float(tick['bid'][0]),
            'ask_size': float(tick['ask'][1]),
            'bid_size': float(tick['bid'][1]),
            'timestamp': float(ticker['ts']),  # ms
            'symbol': 'btcusdt',
        }
        """

    @abstractmethod
    def format_kline(self, data) -> pd.DataFrame:
        """
        :return:
            type: pd.DateFrame
            columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']  # timestamp 单位 秒。
        """

    @abstractmethod
    def format_balance(self, balance) -> dict:
        """
        :return:
             {
                'btc': {
                    "currency": "usdt",
                    "frozen": 123.4,
                    "free": 123.0,
                    "total": 246.4
                }
             }
        """

    @abstractmethod
    def format_order(self, order) -> dict:
        """
        :return:
            {
            'symbol': symbol,
            'order_id': order_id,
            'status': option(close, open),
            'filled_size': filled_size,
            'side': option(buy, sell),
            'average_price': average_price,

            # 'client_order_id': client_order_id,
            # 'order_price': order_price,
            # 'order_size': order_size,
            # 'created_at': created_at,  # ms
            # 'order_type': option(limit, market),
            }
        """

    @abstractmethod
    def format_active_orders(self, orders) -> list:
        pass

    @abstractmethod
    def format_active_place_order_res(self, res) -> dict:
        """
        :return:
            {
            'symbol': symbol,
            'order_id': order_id,
            'status': option(close, open),
            'filled_size': filled_size,
            'side': option(buy, sell),
            'average_price': average_price,

            # 'client_order_id': client_order_id,
            # 'order_price': order_price,
            # 'order_size': order_size,
            # 'created_at': created_at,  # ms
            # 'order_type': option(limit, market),
        """

    def format_cancel_order_res(self, res):
        return res

    def format_cancel_all_res(self, res):
        return res

    def get_ticker(self, symbol):
        return self.format_ticker(self.rest.get_ticker(symbol.upper()))

    def get_kline(self, symbol, period, size):
        return self.format_kline(self.rest.get_kline(symbol=symbol, period=period, size=size))

    def check_order_size(self, symbol, size, price):
        min_limit_order_size = self.get_min_limit_order_size(symbol)
        min_order_value = self.get_min_order_value(symbol)
        # if size < min_limit_order_size:
        #     logger.info(f"({self.name}) Order total size {size} cannot be lower than: `{min_limit_order_size}`")
        #     return False
        # if size * price < min_order_value:
        #     logger.info(f"({self.name}) Order total value {size * price} cannot be lower than: `{min_order_value}`")
        #     return False
        return size >= min_limit_order_size and size * price >= min_order_value

    def place_order(self, symbol, side, size, order_type, price=None, client_order_id=None, time_in_force=None, post_only=False):
        symbol = symbol.upper()
        size_precision = self.get_size_precision(symbol)
        tick_size = self.get_tick_size(symbol)

        if not self.check_order_size(symbol, size, price): return

        size = int(size * 10**size_precision) / 10**size_precision
        price = price - tick_size if side == 'buy' else price + tick_size
        price = round(round(price/tick_size)*tick_size, self.get_price_precision(symbol))

        res = self.rest.place_order(
            symbol=symbol,
            side=side,
            size=size,
            order_type=order_type,
            price=price,
            client_order_id=client_order_id,
            time_in_force=time_in_force,
            post_only=post_only
        )
        return self.format_active_place_order_res(res)

    def get_order(self, order_id=None, client_order_id=None, symbol=None):
        assert any([order_id, client_order_id]), "One and only one of client_order_id and order_id must be provided"
        return self.format_order(self.rest.get_order(order_id=order_id, client_order_id=client_order_id, symbol=symbol))

    def get_balances(self):
        return self.format_balance(self.rest.get_balances())

    def get_active_orders(self, symbol):
        return self.format_active_orders(self.rest.get_active_orders(symbol=symbol))

    def cancel_all(self, symbol):
        return self.format_cancel_all_res(self.rest.cancel_all(symbol=symbol))

    def cancel_order(self, order_id=None, client_order_id=None, symbol=None):
        return self.format_cancel_order_res(
            self.rest.cancel_order(order_id=order_id, client_order_id=client_order_id, symbol=symbol))

    def get_ma(self, symbol, period, size, source='close'):
        return self.get_kline(symbol=symbol, period=period, size=size)[source].mean()

    def get_price_precision(self, symbol) ->int:
        return self.symbol_details[symbol]['price_precision']

    def get_size_precision(self, symbol) -> int:
        return self.symbol_details[symbol]['size_precision']

    def get_limit_min_order_size(self, symbol) -> int:
        return self.symbol_details[symbol]['limit_min_order_size']

    def get_min_limit_order_size(self, symbol) -> int:
        return self.symbol_details[symbol]['min_limit_order_size']

    def get_min_order_value(self, symbol):
        return self.symbol_details[symbol]['min_order_value']

    def get_tick_size(self, symbol):
        return self.symbol_details[symbol]['tick_size']
