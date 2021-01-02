from Logger import logger
from TradeSystem import TradeSystem
from Utils import utils

if __name__ == '__main__':
    logger.start()
    mm_system = TradeSystem()
    mm_system.start()
    mm_system.join()
    utils.immediate_send_all_info()
    logger.stop()
