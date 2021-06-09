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
