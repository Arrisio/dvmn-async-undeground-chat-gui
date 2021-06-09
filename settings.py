import logging
import sys
from typing import Optional

from pydantic import BaseSettings, FilePath


class ChatRuntimeSettings(BaseSettings):
    CHAT_TOKEN: Optional[str] = None
    USER_NAME: str = "anonymous"

    HOST: str = "minechat.dvmn.org"
    READ_PORT: int = 5000
    SEND_PORT: int = 5050
    HISTORY_PATH: FilePath = "minechat.history"

    READ_TIMEOUT = 120
    WATCHDOG_TIMEOUT = 120
    PING_PONG_INTERVAL = 60
    CONNECTION_TIMEOUT = 5
    RECONNECT_TIMEOUT = 5

    LOG_LEVEL = "DEBUG"

    class Config:
        env_file = ".env"


class RegistrationSettings(BaseSettings):
    HOST: str = "minechat.dvmn.org"
    SEND_PORT: int = 5050

    class Config:
        env_file = ".env"


class WatchdogFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return int(record.created)


def configure_watchdog_logger():
    watchdog_logger = logging.getLogger("watchdog_logger")
    watchdog_logger.propagate = False

    watchdog_log_handler = logging.StreamHandler(stream=sys.stdout)
    watchdog_log_handler.setFormatter(WatchdogFormatter("[%(asctime)s] %(message)s"))
    watchdog_logger.addHandler(watchdog_log_handler)
