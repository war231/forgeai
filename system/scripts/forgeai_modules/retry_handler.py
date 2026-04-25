#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试处理器

提供统一的重试机制,支持:
1. 指数退避
2. 自定义重试条件
3. 错误分类
4. 重试日志
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, List, Type
from enum import Enum
from functools import wraps

from .logger import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """错误分类"""
    TRANSIENT = "transient"  # 临时错误(可重试)
    PERMANENT = "permanent"  # 永久错误(不可重试)
    RATE_LIMIT = "rate_limit"  # 限流错误(需等待)
    NETWORK = "network"  # 网络错误(可重试)
    VALIDATION = "validation"  # 验证错误(不可重试)
    UNKNOWN = "unknown"  # 未知错误


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0  # 基础延迟(秒)
    max_delay: float = 60.0  # 最大延迟(秒)
    exponential_base: float = 2.0  # 指数基数
    jitter: bool = True  # 是否添加随机抖动
    
    # 可重试的错误类型
    retryable_errors: List[Type[Exception]] = field(default_factory=lambda: [
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    ])
    
    # 可重试的错误消息关键词
    retryable_keywords: List[str] = field(default_factory=lambda: [
        "rate limit",
        "timeout",
        "connection",
        "network",
        "temporarily",
        "overloaded",
    ])


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    total_time: float = 0.0
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "result": self.result if self.success else None,
            "error": str(self.error) if self.error else None,
            "attempts": self.attempts,
            "total_time": round(self.total_time, 2),
            "error_category": self.error_category.value,
        }


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误"""
        error_str = str(error).lower()
        
        # 检查限流错误
        if "rate limit" in error_str or "too many requests" in error_str:
            return ErrorCategory.RATE_LIMIT
        
        # 检查网络错误
        if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
            return ErrorCategory.NETWORK
        
        # 检查关键词
        for keyword in self.config.retryable_keywords:
            if keyword in error_str:
                return ErrorCategory.TRANSIENT
        
        # 检查错误类型
        for retryable_type in self.config.retryable_errors:
            if isinstance(error, retryable_type):
                return ErrorCategory.TRANSIENT
        
        # 默认为永久错误
        return ErrorCategory.PERMANENT
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        # 超过最大重试次数
        if attempt >= self.config.max_retries:
            return False
        
        # 分类错误
        category = self.classify_error(error)
        
        # 永久错误和验证错误不重试
        if category in [ErrorCategory.PERMANENT, ErrorCategory.VALIDATION]:
            return False
        
        return True
    
    def calculate_delay(self, attempt: int, category: ErrorCategory) -> float:
        """计算延迟时间"""
        # 限流错误使用更长延迟
        if category == ErrorCategory.RATE_LIMIT:
            base = self.config.base_delay * 2
        else:
            base = self.config.base_delay
        
        # 指数退避
        delay = base * (self.config.exponential_base ** (attempt - 1))
        
        # 限制最大延迟
        delay = min(delay, self.config.max_delay)
        
        # 添加随机抖动
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        执行函数并自动重试
        
        Args:
            func: 要执行的函数(可以是异步函数)
            *args: 函数参数
            **kwargs: 函数关键字参数
        
        Returns:
            重试结果
        """
        start_time = time.time()
        attempt = 0
        last_error = None
        error_category = ErrorCategory.UNKNOWN
        
        while attempt <= self.config.max_retries:
            attempt += 1
            
            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 成功
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt,
                    total_time=time.time() - start_time,
                )
            
            except Exception as e:
                last_error = e
                error_category = self.classify_error(e)
                
                logger.warning(
                    f"尝试 {attempt}/{self.config.max_retries + 1} 失败: {e} "
                    f"(分类: {error_category.value})"
                )
                
                # 判断是否重试
                if not self.should_retry(e, attempt):
                    break
                
                # 计算延迟
                delay = self.calculate_delay(attempt, error_category)
                logger.info(f"等待 {delay:.1f} 秒后重试...")
                
                # 等待
                await asyncio.sleep(delay)
        
        # 所有重试都失败
        return RetryResult(
            success=False,
            error=last_error,
            attempts=attempt,
            total_time=time.time() - start_time,
            error_category=error_category,
        )


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_errors: Optional[List[Type[Exception]]] = None,
):
    """
    重试装饰器
    
    用法:
        @with_retry(max_retries=3, base_delay=1.0)
        async def my_function():
            # 可能失败的代码
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
            )
            if retryable_errors:
                config.retryable_errors = retryable_errors
            
            handler = RetryHandler(config)
            result = await handler.execute_with_retry(func, *args, **kwargs)
            
            if result.success:
                return result.result
            else:
                raise result.error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
            )
            if retryable_errors:
                config.retryable_errors = retryable_errors
            
            handler = RetryHandler(config)
            
            # 同步函数包装为异步
            async def async_func(*a, **kw):
                return func(*a, **kw)
            
            result = asyncio.run(handler.execute_with_retry(async_func, *args, **kwargs))
            
            if result.success:
                return result.result
            else:
                raise result.error
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 预定义的重试配置
RETRY_CONFIGS = {
    "llm_api": RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0,
        retryable_keywords=[
            "rate limit",
            "timeout",
            "overloaded",
            "temporarily unavailable",
        ],
    ),
    "network": RetryConfig(
        max_retries=5,
        base_delay=1.0,
        max_delay=60.0,
        retryable_errors=[
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        ],
    ),
    "file_io": RetryConfig(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        retryable_keywords=[
            "file locked",
            "permission denied",
        ],
    ),
}
