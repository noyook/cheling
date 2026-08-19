# -*- coding: utf-8 -*-
"""shared.exceptions 单元测试：异常层级与捕获语义。"""

import pytest

from shared.exceptions import (
    APIError,
    AuthError,
    ChelingError,
    TokenError,
    ValidationError,
    WaybillError,
    WeComError,
)


def test_hierarchy_chain():
    assert issubclass(WaybillError, ChelingError)
    assert issubclass(AuthError, WaybillError)
    assert issubclass(TokenError, AuthError)
    assert issubclass(APIError, WaybillError)
    assert issubclass(WeComError, APIError)
    assert issubclass(ValidationError, WaybillError)


def test_all_under_cheling_error():
    for exc in (WaybillError, AuthError, TokenError, APIError, WeComError,
                ValidationError):
        assert issubclass(exc, ChelingError)


def test_base_catch_covers_all():
    for exc_cls in (AuthError, TokenError, APIError, WeComError,
                    ValidationError):
        with pytest.raises(ChelingError):
            raise exc_cls("test")


def test_exceptions_carry_message():
    err = WaybillError("数据错误")
    assert str(err) == "数据错误"