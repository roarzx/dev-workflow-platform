import asyncio
import functools
from typing import Callable, TypeVar

T = TypeVar("T")


def async_retry(max_retries: int = 3, base_delay: float = 1.0, backoff: float = 2.0):
    """异步重试装饰器，指数退避"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (backoff ** attempt)
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
