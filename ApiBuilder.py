import importlib
import json
import os

import Settings
from Logger import logger


def single(cls):
    cls_dict = dict()

    def wrapped(*args, **kwargs):
        if cls not in cls_dict:
            cls_dict[cls] = cls(*args, **kwargs)
        return cls_dict[cls]

    return wrapped


@single
class ApiBuilder:
    def __init__(self):
        self.modules = dict()
        self.apis = dict()
        self.config = Settings.configs.copy()
        self._initialize_config(self.config)

    def _initialize_config(self, config):
        self.exchange = self.config['exchange']
        self.symbol = self.config['symbol']
        self.keys_path = self.config['key_path']

    def get_api(self, exchange_name: str, symbol: str, key_path: str, name: str = "", **kwargs):
        if key_path not in self.apis:
            self.apis[key_path] = self._build_api(exchange_name.lower(), symbol, key_path, name=name, **kwargs)
        return self.apis[key_path]

    def get_default_api(self, **kwargs):
        return self.get_api(self.exchange, self.symbol, self.keys_path, **kwargs)

    def _build_api(self, exchange_name: str, symbol: str, key_path: str, name: str = "", **kwargs):
        if exchange_name not in self.modules:
            self.modules[exchange_name] = importlib.import_module(f"Exchanges.{exchange_name.title()}.ExchangeApi")
        return self.modules[exchange_name].ExchangeApi(**self._read_key_file(key_path),
                                                       symbol=symbol,
                                                       name=name or exchange_name,
                                                       **kwargs
                                                       )

    def _read_key_file(self, key_path):
        if key_path and os.path.exists(key_path):
            with open(key_path) as f:
                keys = json.load(f)
            return keys
        raise FileNotFoundError(f'({self.__class__.__name__}) {key_path} file not found')


api_builder = ApiBuilder()

if __name__ == '__main__':
    pass
