import base64
import hashlib
import hmac
import json
from urllib import parse

from datetime import datetime

from Exchanges.BaseRest import BaseRest, try_n_decorator, catch_function_error_decorator, HTTP_TIMEOUT
from Logger import logger


class Rest(BaseRest):
    real_url = "https://api.huobi.pro"

    def __init__(self, *args, **kwargs):
        """
        account_type:
            spot：现货账户, margin：逐仓杠杆账户, otc：OTC 账户, point：点卡账户,
            super-margin：全仓杠杆账户, investment: C2C杠杆借出账户,
            borrow: C2C杠杆借入账户，矿池账户: minepool,
            ETF账户: etf, 抵押借贷账户: crypto-loans
        """
        super().__init__(*args, **kwargs)
        self._signature_version = 2
        self._signature_method = "HmacSHA256"
        self._signature_url = parse.urlparse(self.url).hostname.lower()

        self.account_type = kwargs.get('account_type', 'spot').lower()
        self.account_id = self.get_account_id(self.account_type)
        assert self.account_id, f"Get account id failed with {self.account_type}"

    def get_account_id(self, account_type):
        account_info = self._http_requests(method='get', path='/v1/account/accounts')
        for i in account_info:
            if i['type'].lower() == account_type: return i['id']
        logger.info(f'get_account_id failed, account_info: {account_info}, account_type: {account_type}')

    def _sign(self, path, method, params):
        params = params.copy()
        msg = "\n".join([method, self._signature_url, path, parse.urlencode(params)])
        return base64.b64encode(
            hmac.new(self._secret.encode('utf-8'), msg.encode('utf-8'), digestmod=hashlib.sha256).digest()).decode()

    @staticmethod
    def _get_headers(method):
        headers = {
            'GET': {
                "Content-type": "application/x-www-form-urlencoded"
            },
            'POST': {
                "Accept": "application/json",
                "Content-type": "application/json"
            }
        }
        return headers.get(method.upper(), dict())

    @staticmethod
    def _get_utc_time():
        """
        2017-05-11T16:22:06
        """
        return datetime.utcnow().strftime("%FT%X")

    @try_n_decorator(1)
    def _http_requests(self, path, method='GET', params=None, data=None, sign=True):
        params = params if params else dict()
        data = data if data else dict()
        method = method.upper()
        url = self.url + path
        if sign:
            params.update({
                "AccessKeyId": self._key,
                "SignatureMethod": self._signature_method,
                "SignatureVersion": self._signature_version,
                "Timestamp": self._get_utc_time()
            })
            params = {k: params[k] for k in sorted(params)}
            params.update({"Signature": self._sign(path, method, params)})
        headers = self._get_headers(method)
        if method == 'GET':
            response = self._session.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
        elif method == 'POST':
            response = self._session.post(url, params=params, data=json.dumps(data, separators=(',', ':')),
                                          headers=headers, timeout=HTTP_TIMEOUT)
        return self._handle_http_request_result(response)

    @staticmethod
    def _handle_http_request_result(resp):
        if resp.status_code // 100 == 2:
            result = resp.json()
            if 'status' in result and result['status'] == 'error':
                return resp.text
            else:
                return result['data'] if 'data' in result else result
        else:
            return resp.text

    @catch_function_error_decorator
    def get_balances(self):
        return self._http_requests(path=f"/v1/account/accounts/{self.account_id}/balance")['list']

    @catch_function_error_decorator
    def place_order(self, symbol, side, size, order_type, price=None, client_order_id=None, time_in_force=None, post_only=False, **kwargs):
        order_type = order_type.lower()
        # 当前该接口不支持市价单，市价买单需要按照金额下单；市价单容易产生滑点， 所以暂时不支持市价单。
        assert order_type != "market", "Market orders are not currently supported"
        data = {
            "account-id": self.account_id,
            "symbol": symbol.lower(),
            "type": f"{side}-{order_type}-maker" if post_only else f"{side}-{order_type}",
            "amount": size,
            "price": price
        }
        if client_order_id: data.update({'client-order-id': client_order_id})
        return self._http_requests(method='post', path='/v1/order/orders/place', data=data)

    @catch_function_error_decorator
    def get_order(self, order_id=None, client_order_id=None, symbol=None):
        return self._http_requests(path=f'/v1/order/orders/{order_id}')

    @catch_function_error_decorator
    def cancel_order(self, order_id, client_order_id=None, symbol=None):
        return self._http_requests(method='post', path=f'/v1/order/orders/{order_id}/submitcancel')

    @catch_function_error_decorator
    def get_active_orders(self, symbol):
        params = {
            'account-id': self.account_id,
            'symbol': symbol.lower(),
            'size': 500  # huobi spot max return size 500
        }
        return self._http_requests(path='/v1/order/openOrders', params=params)

    @catch_function_error_decorator
    def cancel_all(self, symbol):
        return self._http_requests(method='post', path='/v1/order/orders/batchCancelOpenOrders', data={'symbol': symbol.lower()})

    @catch_function_error_decorator
    def get_symbol_details(self):
        return self.symbol_details or self._http_requests(path='/v1/common/symbols', sign=False)

    @catch_function_error_decorator
    def get_ticker(self, symbol):
        return self._http_requests(path='/market/detail/merged', sign=False, params={'symbol': symbol.lower()})

    @catch_function_error_decorator
    def get_kline(self, symbol, period, size, *args, **kwargs):
        params = {
            'symbol': symbol.lower(),
            'period': period.lower(),
            'size': size
        }
        return self._http_requests(path='/market/history/kline', params=params, sign=False)
