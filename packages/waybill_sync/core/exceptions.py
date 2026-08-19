"""Custom exception hierarchy"""


class WaybillError(Exception):
    """Base exception for waybill system."""
    def __init__(self, message: str, code: int = 0):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthError(WaybillError):
    """Authentication failure."""
    pass


class TokenError(AuthError):
    """Token acquisition or refresh failed."""
    pass


class APIError(WaybillError):
    """External API call failed."""
    pass


class WeComError(APIError):
    """WeCom API call failed."""
    pass


class ValidationError(WaybillError):
    """Data validation failed."""
    pass
