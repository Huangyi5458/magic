from Worker import Worker
from .Base import Base
from Exchanges.BaseExchangeApi import BaseExchangeApi

from Logger import logger


class GridTrading(Base):
    def __init__(self, config, api: BaseExchangeApi):
        super().__init__()
        self.name = self.__class__.__name__
        self.api = api
        self.config = config
        self._initialize_config(self.config)

        self.worker_trade = Worker(name=self.name, callback=self.trade, msg='worker_trade', period=self.trade_loop_period)
        self._reset_active_orders()

        self.current_sell_price = None
        self.current_buy_price = None

    def _reset_active_orders(self):
        # 第一版只挂两个单， 看看后面能不能再优化
        self.active_orders = {
            'buy': dict(),
            'sell': dict()
        }

    def _initialize_config(self, config):
        self.symbol = self.config['symbol']
        self.base_currency = self.config['base_currency']
        self.quote_currency = self.config['quote_currency']
        self.ma_kline_period = self.config['ma_kline_period']
        self.ma_kline_size = self.config['ma_kline_size']
        self.max_num_active_order = self.config['max_num_active_order']
        self.trade_loop_period = self.config['trade_loop_period']
        self.spread_rate = self.config['spread_rate']
        self.reorder_rate = self.config['reorder_rate']

        self.ma_kline_source = self.config.get('ma_kline_source', 'close')

    def update_active_orders(self):
        orders = self.api.get_active_orders(symbol=self.symbol)
        if len(orders) > self.max_num_active_order:
            logger.warning(f"({self.name}) active orders {orders} exceed the limit {self.max_num_active_order}")
            self.api.cancel_all(symbol=self.symbol)
            return False

        for order in orders:
            if order['side'] == 'sell' and abs(1 - self.current_sell_price / order['order_price']) >= self.reorder_rate:
                self.api.cancel_order(order_id=order['order_id'])
            elif order['side'] == 'buy' and abs(1 - self.current_buy_price / order['order_price']) >= self.reorder_rate:
                self.api.cancel_order(order_id=order['order_id'])
            else:
                logger.info(f"({self.name}) active order: {order}")
                self.active_orders[order['side']] = order
        return True

    def update_current_price(self):
        ma = self.api.get_ma(symbol=self.symbol, period=self.ma_kline_period, size=self.ma_kline_size, source=self.ma_kline_source)
        self.current_sell_price = ma * (1 + self.spread_rate)
        self.current_buy_price = ma * (1 - self.spread_rate)
        data = {
            "current_sell_price": self.current_sell_price,
            "current_buy_price": self.current_buy_price,
            "MA": ma
        }
        logger.info(f'({self.name}) current prices: {data}')

    def place_orders(self):
        balances = self.api.get_balances()
        base_balance = balances[self.base_currency]
        quote_balance = balances[self.quote_currency]
        for side, order in self.active_orders.items():
            if not order:
                self.api.place_order(**self.gen_order_info(side, base_balance['free'], quote_balance['free']))
        logger.info(f"({self.name}) current balances: {base_balance} {quote_balance}")

    def gen_order_info(self, side, base_balance, quote_balance):
        if side == 'buy':
            price = self.current_buy_price
            size = quote_balance / price
        else:
            price = self.current_sell_price
            size = base_balance
        return dict(
            symbol=self.symbol,
            side=side,
            size=size,
            order_type='limit',
            price=price,
        )

    def trade(self):
        self._reset_active_orders()
        self.update_current_price()
        if self.update_active_orders():
            self.place_orders()
        logger.info(f"({self.name}) {'*'*50}")

    def start(self):
        logger.info(f'({self.name}) Starting')
        self.worker_trade.start()
        logger.info(f'({self.name}) Started')

    def stop(self):
        logger.info(f"({self.name}) Stopping")
        self.worker_trade.stop()
        self.api.cancel_all(self.symbol)
        logger.info(f"({self.name}) Stopped")
