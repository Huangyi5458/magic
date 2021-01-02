import logging
import os
import queue
import threading
import time

import Settings
from logging import handlers
from Utils import utils


class MyLogger(logging.Logger):
    def __init__(self, name, level='INFO', fmt=None, interval=1, backup_count=10, when='D'):
        super().__init__(name)
        self.setLevel(level.upper())

        self._interval = interval
        self._backup_count = backup_count
        self._when = when
        self._fmt = '[%(asctime)s] - %(levelname)s: %(message)s' if not fmt else fmt
        self.log_dir = "./Logs"
        self.file_name = f"{self.log_dir}/{name}.log"
        self.working = False

        self._que = queue.Queue()
        self._level_callback = {
            logging.INFO: super().info,
            logging.WARNING: super().warning,
            logging.DEBUG: super().debug,
            logging.CRITICAL: super().critical,
            logging.ERROR: super().error
        }
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True

        self._initialize()

    def run(self):
        while self.working or not self._que.empty():
            try:
                level, msg = self._que.get(timeout=1)
            except queue.Empty:
                continue
            if level in self._level_callback:
                self._level_callback[level](msg)

    def set_log_name(self, name, clear_handlers=True):
        if clear_handlers:
            self._sh.close()
            self._th.close()
            self.removeHandler(self._th)
            self.removeHandler(self._sh)
        self._initialize(f"{self.log_dir}/{name}.log")

    def _initialize(self, name=None):
        if not os.path.exists(self.log_dir): os.mkdir(self.log_dir)
        fmt = logging.Formatter(self._fmt)
        fmt.default_msec_format = '%s.%03d'
        self._th = handlers.TimedRotatingFileHandler(filename=name or self.file_name,
                                                    interval=self._interval,
                                                    when=self._when,
                                                    backupCount=self._backup_count,
                                                    encoding='utf-8')
        self._th.setFormatter(fmt=fmt)
        self._sh = logging.StreamHandler()
        self._sh.setFormatter(fmt)
        self.addHandler(self._sh)
        self.addHandler(self._th)
        self.setLevel(self.level)

    def warning(self, msg, *args, **kwargs):
        self.put(logging.WARNING, msg)
        utils.send(msg)

    def debug(self, msg, *args, **kwargs):
        self.put(logging.DEBUG, msg)

    def error(self, msg, *args, **kwargs):
        self.put(logging.ERROR, msg)

    def put(self, level, msg):
        if self.working:
            msg = f"({threading.current_thread().ident}) {msg}"
            self._que.put((level, msg))

    def info(self, msg, *args, **kwargs):
        for item in args:
            msg += f" {item}"
        self.put(logging.INFO, msg)

    def stop(self):
        self.working = False
        self._thread.join()
        super().info("Logger Stopped")

    def start(self):
        self.working = True
        self._thread.start()
        self.info('Logger Started')


logger = MyLogger(name='mm', level=Settings.configs.get('log_level', 'INFO'))

if __name__ == '__main__':
    logger.start()
    for i in range(100):
        logger.info('info')
        logger.info('info')
        time.sleep(0.5)
    logger.stop()
    utils.immediate_send_all_info()
