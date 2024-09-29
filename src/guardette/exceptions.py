class GuardetteException(Exception):
    pass


class AuthException(GuardetteException):
    pass


class MatchNotFoundException(GuardetteException):
    pass


class ConfigurationException(GuardetteException):
    pass


class AuthHandlerAuthException(GuardetteException):
    pass


class HttpMethodNotSupportedException(GuardetteException):
    pass

class ProxyClientTimeoutException(GuardetteException):
    pass

class TransformationException(GuardetteException):
    pass
