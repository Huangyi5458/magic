import math

import pandas as pd

from Exchanges.BaseExchangeApi import BaseExchangeApi
from Exchanges.Huobi.Rest import Rest


class ExchangeApi(BaseExchangeApi):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rest = Rest(*args, **kwargs)

        self._initialize()

    def format_symbol_details(self, symbol_details):
        """
        [
        {
            "base-currency": "btc",
            "quote-currency": "usdt",
            "price-precision": 2,
            "amount-precision": 6,
            "symbol-partition": "main",
            "symbol": "btcusdt",
            "state": "online",
            "value-precision": 8,
            "min-order-amt": 0.0001,
            "max-order-amt": 1000,
            "min-order-value": 5,
            "limit-order-min-order-amt": 0.0001,
            "limit-order-max-order-amt": 1000,
            "sell-market-min-order-amt": 0.0001,
            "sell-market-max-order-amt": 100,
            "buy-market-max-order-value": 1000000,
            "leverage-ratio": 5,
            "super-margin-leverage-ratio": 3,
            "funding-leverage-ratio": 3,
            "api-trading": "enabled"
        }
        ]
        """
        res = dict()
        for detail in symbol_details:
            res[detail['symbol'].upper()] = {
                "base_currency": detail['base-currency'],
                "quote_currency": detail['quote-currency'],
                "price_precision": detail['price-precision'],
                "size_precision": detail['amount-precision'],
                "symbol": detail['symbol'].upper(),
                "tick_size": math.pow(10, -detail['price-precision']),

                # 交易对 限价单 和 市价买单 最小下单金额 ，以计价币种为单位
                "min_order_value": detail['min-order-value'],
                # 交易对限价单最小下单量
                "min_limit_order_size": detail['limit-order-min-order-amt'],
            }
        return res

    def format_ticker(self, ticker):
        tick = ticker['tick']
        return {
            'ask_price': float(tick['ask'][0]),
            'bid_price': float(tick['bid'][0]),
            'ask_size': float(tick['ask'][1]),
            'bid_size': float(tick['bid'][1]),
            'timestamp': float(ticker['ts']),  # ms
            'symbol': ticker['ch'].split('.')[1].upper()
        }

    def format_kline(self, data):
        return pd.DataFrame(data).rename(columns={'id': 'timestamp', 'amount': 'volume'})

    def format_balance(self, balance):
        res = dict()
        for b in balance:
            currency = b['currency']
            if currency not in res:
                res[currency] = {
                    "currency": currency,
                    "frozen": 0,
                    "free": 0,
                    "total": 0
                }
            if b['type'] == 'trade':
                res[currency]['free'] += float(b['balance'])
            else:
                res[currency]['frozen'] += float(b['balance'])
            res[currency]['total'] += float(b['balance'])
        return res

    def format_order(self, order):
        """
        {'id': 180286878676697, 'symbol': 'betheth', 'account-id': 17155432,
        'client-order-id': '1609501207', 'amount': '0.040000000000000000', 'price': '1.700000000000000000',
        'created-at': 1609501207342, 'type': 'sell-limit', 'field-amount': '0.0',
        'field-cash-amount': '0.0', 'field-fees': '0.0', 'finished-at': 0,
        'source': 'spot-api', 'state': 'submitted', 'canceled-at': 0}

        field-amount 等包含 ‘field’ 的字段， 应该是火币 GET /v1/order/orders/{order-id} 接口返回结果拼写错误；
                     GET /v1/order/openOrders 返回的是 filled-amount；
                    所以将所有的 field 统一成 filled
        """
        order_id = order['id']
        order = self.dict_value_to_float(order)
        order = {k.replace('field', 'filled'): v for k, v in order.items()}
        return {
            'symbol': order['symbol'].upper(),
            'order_id': order_id,
            'status': 'closed' if order.get('finished-at', 0) - order['created-at'] >= 0 else 'open',
            'filled_size': order['filled-amount'],
            'side': order['type'].split('-')[0],
            'average_price': order['filled-cash-amount'] / order['filled-amount'] if order['filled-amount'] else 0,

            'client_order_id': order['client-order-id'],
            'order_price': order['price'],
            'order_size': order['amount'],
            'created_at': order['created-at'],  # ms
            'order_type': order['type'].split('-')[1],

        }

    def format_active_orders(self, orders):
        return [self.format_order(order) for order in orders]

    def format_active_place_order_res(self, res):
        if res:
            return self.get_order(order_id=res)
