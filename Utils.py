import json
import time
import threading
import traceback
import requests

from datetime import datetime

from Settings import ROBOT_URL, configs

RATE_LIMIT = ([0] * 15, threading.Lock())
TIMEOUT = 5


class Utils:
    # MakerWarning
    TIMEOUT = 5

    def __init__(self):
        self.remote_server = None
        self.send_warning_period = 120
        self.send_warning_last_time = 0
        self.warnings = list()
        self.thread_send_warning = threading.Thread(target=self.worker)
        self.thread_send_warning.daemon = True
        self.thread_send_warning.start()

        self._configs = configs.copy()
        self.name = self._configs.get('name', "")

    def send(self, warning, label="MarketMaker"):
        c_time = datetime.now().strftime("%F %X")
        warning = f"({label}@ {self.name}@ {c_time}) {warning}"
        self.warnings.append(warning)

    def worker(self):
        from Logger import logger
        self.logger = logger
        while True:
            try:
                cur_time = time.time()
                if self.warnings and (cur_time - self.send_warning_last_time > self.send_warning_period):
                    warnings = '\n===============\n'.join(self.warnings)
                    self.warnings = list()
                    self._send(warnings)
                    self.send_warning_last_time = cur_time
                else:
                    time.sleep(1)
            except Exception as e:
                s = traceback.format_exc()
                self.logger.info(f"send info error: {s}")
                time.sleep(10)

    def _send(self, warning, msgtype='text', atMobiles=None, isAtAll=True, title='======'):
        with RATE_LIMIT[1]:
            pre, cur = RATE_LIMIT[0].pop(0), time.time()
            if cur - pre < 60: time.sleep(pre + 60 - cur)
            RATE_LIMIT[0].append(time.time())
            if atMobiles is None: atMobiles = list()
            data = {
                "msgtype": msgtype,
                "at": {"atMobiles": atMobiles, "isAtAll": isAtAll}
            }

            if msgtype == 'markdown':
                data.update(self.markdown_info(warning, title))
            else:
                data.update(self.text_info(warning))

            header = {"Content-Type": "application/json; charset=utf-8"}
            response = requests.post(ROBOT_URL, timeout=self.TIMEOUT, data=json.dumps(data), headers=header).json()

    def text_info(self, warning):
        return {"text": {"content": warning}}

    def markdown_info(self, warning, title):
        return {"markdown": {
            "title": title,
            "text": warning}}

    def get_now_time(self):
        return datetime.now().strftime('%F %H:%M')

    def immediate_send_all_info(self):
        if self.warnings:
            warnings = '\n===============\n'.join(self.warnings)
            self._send(warnings)


utils = Utils()

if __name__ == '__main__':
    utils.send('test_1')
    time.sleep(2)
    for i in range(15):
        utils.send(f'test_{i*2}')
    time.sleep(600)
