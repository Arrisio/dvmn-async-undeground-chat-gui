from socket import gaierror


class ParseServerResponseException(Exception):
    pass


class WatchdogException(Exception):
    pass


class AuthException(Exception):
    pass


CONNECTION_EXCEPTIONS = (ConnectionError, gaierror, WatchdogException)