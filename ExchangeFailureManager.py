import threading
import time
import traceback
import pandas as pd

from Logger import logger


def single(cls):
    cls_dict = dict()

    def wrapper(*args, **kwargs):
        if cls not in cls_dict:
            cls_dict.update({cls: cls(*args, **kwargs)})
        return cls_dict[cls]

    return wrapper


class ErrorManager(object):
    def __init__(self, error_limit, error_expired):
        self.error_limit = error_limit
        self.error_expired = error_expired
        self.error_info_df = pd.DataFrame(columns=['time', 'exchange', 'info'])

    def add_error_info(self, exchange, info):
        self.error_info_df.loc[self.error_info_df.shape[0]] = [time.time(), exchange, info]

    def delete_expired_error_info(self):
        expired_time = time.time() - self.error_expired
        self.error_info_df = self.error_info_df.loc[self.error_info_df['time'] > expired_time].reset_index(drop=True)

    def is_error_exceeds_limit(self):
        return self.error_info_df['info'].count() > self.error_limit

    def status(self):
        error_total_count = self.error_info_df['info'].count()
        status_info = f"error_total_count: {error_total_count}, error_limit: {self.error_limit}, error_expired: {self.error_expired}"
        return status_info


@single
class ExchangeFailureManager(object):
    def __init__(self):
        self.command_file = './Command.txt'

        self.thread = threading.Thread(target=self.on_timer)
        self.thread.daemon = True
        self.working = False

        self.request_error = ErrorManager(60, 60)
        self.ws_error = ErrorManager(10, 600)

        self.error_type_map = {
            'request': self.request_error,
            'ws': self.ws_error
        }
        self.exchanges = list()

    def add_error_info(self, exchange, info='error', error_type='request'):
        if error_type in self.error_type_map:
            self.error_type_map[error_type].add_error_info(exchange, info)
            logger.info('(ExchangeFailureManager) exchange: {}, error_type: {}, status: {}'.format(exchange, error_type, self.error_type_map[error_type].status()))
        else:
            logger.info('Unsupported type: {}, The types of support are: {}'.format(error_type, list(self.error_type_map.keys())))

    def on_timer(self):
        while self.working:
            try:
                self.process_failure()
                time.sleep(1)
            except Exception as e:
                s = traceback.format_exc()
                logger.info('(ExchangeFailureManager) process_failure error: {}'.format(s))
                time.sleep(10)

    def process_failure(self):
        for error_type, error_manager in self.error_type_map.items():
            error_manager.delete_expired_error_info()
            if error_manager.is_error_exceeds_limit():
                warning_info = '(ExchangeFailureManager) {} error status: {}'.format(error_type, error_manager.status())
                logger.warning(warning_info)
                self.write_command('exit')
                self.stop()
                break

    def write_command(self, command):
        logger.info('(ExchangeFailureManager) write command: {} to {}'.format(command, self.command_file))
        with open(self.command_file, 'w') as f:
            f.write(command)

    def start(self):
        self.working = True
        self.thread.start()
        logger.info("Started exchange failure manager ")

    def stop(self):
        self.working = False
        logger.info("Stopped exchange failure manager ")


exchange_failure_manager = ExchangeFailureManager()

if __name__ == '__main__':
    logger.start()

    exchange_failure_manager.start()

    for i in range(100):
        # exchange_failure_manager.add_error_info('bitmex', error_type='ws')
        time.sleep(0.1)
        exchange_failure_manager.add_error_info('bitmex')

    time.sleep(80)
    exchange_failure_manager.stop()

    logger.stop()
