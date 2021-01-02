import time

import Settings
from ApiBuilder import api_builder

from Logger import logger
from Worker import Worker
from strategies import GridTrading


class TradeSystem:
    def __init__(self, name=None):
        self.name = self.__class__.__name__ if not name else name
        self.config = Settings.configs
        self.api = api_builder.get_default_api()

        self.worker_process_command = Worker(name="ProcessCommand", callback=self.process_command)
        self.command_file_name = "Command.txt"
        self.support_command = {
            "exit": self.process_command_exit,
            "stop": self.process_command_exit
        }
        with open(self.command_file_name, 'w'): pass

        # 第一版只支持 GridTrading
        self.strategy = GridTrading.GridTrading(config=self.config, api=self.api)

    def process_command(self):
        with open(self.command_file_name) as f:
            commands = f.readline().split()
        if commands:
            with open(self.command_file_name, 'w') as f:
                pass
            if len(commands) == 1 and commands[0] in self.support_command:
                logger.info(f"({self.name}) process command: {commands[0]}")
                self.support_command[commands[0]]()
            else:
                logger.info(f"({self.name}) command error: {''.join(commands)}")
        time.sleep(5)

    def process_command_exit(self):
        self.stop()

    def start(self):
        logger.info(f"({self.name}) start")
        self.worker_process_command.start()
        self.strategy.start()

    def stop(self):
        self.strategy.stop()
        self.worker_process_command.stop()
        logger.info(f"({self.name}) stop")

    def join(self):
        self.worker_process_command.join()


if __name__ == '__main__':
    pass
