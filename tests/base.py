# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio

from functools import wraps
from typing import Any, Callable


def async_test(fn: Callable[..., Any]) -> Callable[..., Any]:

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fn(*args, **kwargs))

    return wrapper
