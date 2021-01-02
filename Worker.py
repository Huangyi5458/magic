
import queue
import threading
import time
import traceback

from Logger import logger
from typing import Callable, Any


class Worker:
    def __init__(self, name: str, callback: Callable, msg: str = "", period: int = 0, params: Any = None, enable=True, pause_period=1):
        self.name = name
        self.working = False
        self.pause = False
        self.pause_period = pause_period

        self._callback = callback
        self._msg = msg
        self._params = params if params else dict()
        self._period = period if period >= 0 else 0

        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._error_interval = 5
        self._enable = enable

    def _run(self):
        while self.working:
            try:
                if not self.pause:
                    self._callback(**self._params)
                else:
                    time.sleep(self.pause_period)
                time.sleep(self._period)
            except queue.Empty:
                pass
            except Exception:
                s = traceback.format_exc()
                logger.info(f"({self.name}) caught error: {s}")
                time.sleep(self._error_interval)

    def set_pause(self, info=''):
        self.pause = True
        logger.info(f"({self.name}) set_pause: {self.pause}, {info}")

    def restart(self, info=''):
        self.pause = False
        logger.info(f"({self.name}) restart set_pause: {self.pause}, {info}")
        self.start()

    def start(self):
        if not self._enable:
            self.working = True
            logger.info(f"({self.name}) {self._msg} Worker No Start, enable is {self._enable}")
            return

        if not self.working:
            self.working = True
            self._thread.start()
            logger.info(f"({self.name}) Worker started {self._msg}")

    def stop(self):
        if self.working:
            self.working = False
            # self._thread.join()
            logger.info(f"({self.name}) Worker stopped {self._msg} enable is {self._enable}")

    def join(self, timeout=None):
        self._thread.join(timeout=timeout)

