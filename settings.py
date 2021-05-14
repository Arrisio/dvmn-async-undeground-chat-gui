import sys
from typing import  Optional

from pydantic import BaseSettings, FilePath


class Settings(BaseSettings):
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


def get_loguru_config(log_level=Settings().LOG_LEVEL):
    return {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "<level>{level: <8} {time:HH:mm:ss}</level>|<cyan>{name:<12}</cyan>:<cyan>{function:<24}</cyan>:<cyan>{line}</cyan> - <level>{message:>32}</level> |{extra}",
                "filter": lambda rec: "logger_name" not in rec["extra"],
                "level": log_level,
            },
            {
                "sink": sys.stdout,
                "format": "[{time:X}] {message}",
                "filter": lambda rec: rec["extra"].get("logger_name") == "watchdog_logger",
            },
        ],
    }


