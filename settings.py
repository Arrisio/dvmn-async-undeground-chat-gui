from pydantic import BaseSettings, FilePath


class Settings(BaseSettings):
    CHAT_TOKEN: str
    HOST: str = "minechat.dvmn.org"
    READ_PORT: int = 5000
    SEND_PORT: int = 5050
    HISTORY_PATH: FilePath = "minechat.history"
    USER_NAME: str = "anonymous"

    LOG_LEVEL = "DEBUG"
    READ_TIMEOUT = 120
    WATCHDOG_TIMEOUT = 120
    PING_PONG_INTERVAL = 60
    CONNECTION_TTIMEOUT=5
    RECONNET_TTIMEOUT=5

    class Config:
        env_file = ".env"
