from __future__ import annotations

import sys
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


class ErrorCode(Enum):
    PARSE_ERROR = 1


class SuccessCode(Enum):
    SUCCESS = 0


type ReturnCode = ErrorCode | SuccessCode


class WatchFsBaseException(Exception):
    code: ErrorCode
    message: str

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ParseError(WatchFsBaseException):
    code = ErrorCode.PARSE_ERROR


def handleUncaughtException(
    exctype: type[BaseException], exception: BaseException, trace: TracebackType | None
) -> None:
    oldHook(exctype, exception, trace)
    if isinstance(exception, WatchFsBaseException):
        raise SystemExit(exception.code.value)


oldHook = sys.excepthook
sys.excepthook = handleUncaughtException
