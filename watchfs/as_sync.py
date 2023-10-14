from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any


def as_sync[T](async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    @wraps(async_func)
    def sync_func(*args: Any, **kwargs: Any):
        return asyncio.run(async_func(*args, **kwargs))

    return sync_func
