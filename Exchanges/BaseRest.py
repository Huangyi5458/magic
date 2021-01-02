import time

import requests
from Logger import logger
from ExchangeFailureManager import exchange_failure_manager

HTTP_TIMEOUT = 5


def try_n_decorator(n):
    def real_decorator(fn):
        def wrapper(*args, **kwargs):
            error_info = '{}({}, {}) error'.format(fn.__name__, args[1:], kwargs.values())
            for i in range(n):
                res = fn(*args, **kwargs)
                if isinstance(res, str) and not res.isalnum():
                    raise Exception('[{}/{}] Try ({}, {}) bad returned: {}'.format(i + 1, n, args[1:], kwargs, res))
                else:
                    return res

        return wrapper

    return real_decorator


def catch_function_error_decorator(func):
    def wrapper(*args, **kwargs):
        name = kwargs['name'] if 'name' in kwargs else args[0].name
        func_name = func.__name__.title()
        try:
            start_time = time.time()
            res = func(*args, **kwargs)
            total_time = time.time() - start_time
            logger.info('({})  {}({}, {}) success({})'.format(name, func_name, args[1:], kwargs.values(), total_time))
            return res
        except Exception as e:
            # s = traceback.format_exc()
            exchange_failure_manager.add_error_info(name)
            logger.info('({}) {}({}, {}) error: {}'.format(name, func_name, args[1:], kwargs, e))
            return None

    return wrapper


class BaseRest:
    test_url = ""
    real_url = ""

    def __init__(self, key=None, secret=None, name=None, testnet=True, **kwargs):
        self._key = key
        self._secret = secret
        self._session = requests.session()
        self.symbol_details = dict()
        self.name = name
        self.testnet = testnet
        self.url = self.test_url if self.testnet else self.real_url

        self.symbol_details = self.get_symbol_details()
        logger.info(f"({self.name}) used url: {self.url} -->> testnet is {self.testnet}")

    def _sign(self, *args, **kwargs):
        pass

    def _http_requests(self, *args, **kwargs):
        pass

    def get_symbol_details(self):
        pass

    def get_balances(self):
        pass

    def get_ticker(self, symbol):
        pass

    def place_order(self, symbol, side, size, order_type, price=None, client_order_id=None, time_in_force=None,
                    post_only=False, ** kwargs):
        pass

    def cancel_order(self, order_id, client_order_id=None, symbol=None):
        pass

    def get_order(self, order_id=None, client_order_id=None, symbol=None):
        pass

    def get_active_orders(self, symbol):
        pass

    def cancel_all(self, symbol):
        pass

    def get_kline(self, symbol, period, size, *args, **kwargs):
        pass
