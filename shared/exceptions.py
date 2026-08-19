# -*- coding: utf-8 -*-
"""
统一异常层：ChelingError 基类 + waybill 异常体系（迁移兼容）。

从 waybill-sync/src/core/exceptions.py 迁移，原 WaybillError 基类改为
继承统一基类 ChelingError，其余继承链保持不变。
"""


class ChelingError(Exception):
    """cheling Monorepo 统一异常基类。"""

    def __init__(self, message: str, code: int = 0):
        self.message = message
        self.code = code
        super().__init__(self.message)


class WaybillError(ChelingError):
    """运单系统基础异常（迁移兼容）。"""

    def __init__(self, message: str, code: int = 0):
        super().__init__(message, code)


class AuthError(WaybillError):
    """认证失败。"""


class TokenError(AuthError):
    """token 获取或刷新失败。"""


class APIError(WaybillError):
    """外部 API 调用失败。"""


class WeComError(APIError):
    """企业微信 API 调用失败。"""


class ValidationError(WaybillError):
    """数据校验失败。"""


__all__ = [
    "ChelingError", "WaybillError", "AuthError",
    "TokenError", "APIError", "WeComError", "ValidationError",
]