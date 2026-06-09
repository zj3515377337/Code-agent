"""LLM 调用重试工具：指数退避，处理限流和临时故障。"""
import time
import logging
from functools import wraps
from typing import Callable, TypeVar

logger = logging.getLogger("code_agent.retry")

T = TypeVar("T")


def retry_on_api_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
) -> Callable:
    """
    装饰器：LLM API 调用失败时自动重试。

    指数退避：1s → 2s → 4s
    适用于限流 (429)、超时、网络抖动等临时故障。
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"API 调用失败 (尝试 {attempt + 1}/{max_retries + 1})，"
                            f"{delay:.1f}s 后重试: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"API 调用在 {max_retries + 1} 次尝试后仍然失败: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator
