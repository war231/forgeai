#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重试处理器
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

from forgeai_modules.retry_handler import (
    ErrorCategory,
    RetryConfig,
    RetryResult,
    RetryHandler,
    with_retry,
    RETRY_CONFIGS,
)


class TestErrorCategory:
    """测试错误分类枚举"""

    def test_values(self):
        """测试枚举值"""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestRetryConfig:
    """测试重试配置"""

    def test_defaults(self):
        """测试默认值"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert ConnectionError in config.retryable_errors

    def test_custom_values(self):
        """测试自定义值"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestRetryResult:
    """测试重试结果"""

    def test_defaults(self):
        """测试默认值"""
        result = RetryResult(success=True)

        assert result.success is True
        assert result.result is None
        assert result.error is None
        assert result.attempts == 0
        assert result.total_time == 0.0
        assert result.error_category == ErrorCategory.UNKNOWN

    def test_to_dict(self):
        """测试转换为字典"""
        result = RetryResult(
            success=True,
            result="test_value",
            attempts=3,
            total_time=5.5,
            error_category=ErrorCategory.NETWORK,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["result"] == "test_value"
        assert data["attempts"] == 3
        assert data["total_time"] == 5.5
        assert data["error_category"] == "network"

    def test_to_dict_with_error(self):
        """测试带错误的字典"""
        result = RetryResult(
            success=False,
            error=ValueError("test error"),
            error_category=ErrorCategory.PERMANENT,
        )

        data = result.to_dict()

        assert data["success"] is False
        assert data["result"] is None
        assert data["error"] == "test error"
        assert data["error_category"] == "permanent"


class TestRetryHandler:
    """测试重试处理器"""

    def test_init_default(self):
        """测试默认初始化"""
        handler = RetryHandler()
        assert handler.config is not None

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = RetryConfig(max_retries=5)
        handler = RetryHandler(config)
        assert handler.config.max_retries == 5

    def test_classify_error_rate_limit(self):
        """测试分类限流错误"""
        handler = RetryHandler()

        error = Exception("rate limit exceeded")
        category = handler.classify_error(error)

        assert category == ErrorCategory.RATE_LIMIT

    def test_classify_error_network(self):
        """测试分类网络错误"""
        handler = RetryHandler()

        error = ConnectionError("connection failed")
        category = handler.classify_error(error)

        assert category == ErrorCategory.NETWORK

    def test_classify_error_timeout(self):
        """测试分类超时错误"""
        handler = RetryHandler()

        error = TimeoutError("request timed out")
        category = handler.classify_error(error)

        assert category == ErrorCategory.NETWORK

    def test_classify_error_permanent(self):
        """测试分类永久错误"""
        handler = RetryHandler()

        error = ValueError("invalid value")
        category = handler.classify_error(error)

        assert category == ErrorCategory.PERMANENT

    def test_classify_error_transient_keywords(self):
        """测试临时错误关键词"""
        handler = RetryHandler()

        error = Exception("temporarily unavailable")
        category = handler.classify_error(error)

        assert category == ErrorCategory.TRANSIENT

    def test_should_retry_within_limit(self):
        """测试重试次数限制内"""
        handler = RetryHandler()

        error = ConnectionError("connection failed")

        assert handler.should_retry(error, 1) is True
        assert handler.should_retry(error, 2) is True
        assert handler.should_retry(error, 3) is False  # 达到最大重试

    def test_should_retry_permanent_error(self):
        """测试永久错误不重试"""
        handler = RetryHandler()

        error = ValueError("invalid value")
        assert handler.should_retry(error, 1) is False

    def test_calculate_delay_exponential(self):
        """测试指数退避"""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # 不测试抖动，只测试指数增长
        delay1 = handler.calculate_delay(1, ErrorCategory.TRANSIENT)
        delay2 = handler.calculate_delay(2, ErrorCategory.TRANSIENT)
        delay3 = handler.calculate_delay(3, ErrorCategory.TRANSIENT)

        # 延迟应该增加
        assert delay1 >= 0.5  # base * 2^0 = 1, 但有抖动
        assert delay2 > delay1
        assert delay3 > delay2

    def test_calculate_delay_rate_limit(self):
        """测试限流错误延迟加倍"""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        delay_transient = handler.calculate_delay(1, ErrorCategory.TRANSIENT)
        delay_rate_limit = handler.calculate_delay(1, ErrorCategory.RATE_LIMIT)

        # 限流错误延迟应该更长
        assert delay_rate_limit > delay_transient

    def test_calculate_delay_max_limit(self):
        """测试最大延迟限制"""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=10.0,
            max_delay=30.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        delay = handler.calculate_delay(10, ErrorCategory.TRANSIENT)

        # 不应该超过最大延迟
        assert delay <= config.max_delay * 1.5  # 考虑抖动

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_try(self):
        """测试首次成功"""
        handler = RetryHandler()

        async def success_func():
            return "success"

        result = await handler.execute_with_retry(success_func)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self):
        """测试重试后成功"""
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)

        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("connection failed")
            return "success"

        result = await handler.execute_with_retry(fail_then_succeed)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_retries_exceeded(self):
        """测试超过最大重试"""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)

        async def always_fail():
            raise ConnectionError("always fails")

        result = await handler.execute_with_retry(always_fail)

        assert result.success is False
        # With max_retries=2, we get: attempt=1 (initial), attempt=2 (1st retry)
        # should_retry returns False when attempt >= max_retries (2 >= 2)
        assert result.attempts == 2  # 初始 + 1次重试 (因为 should_retry 在 attempt=2 时返回 False)
        assert result.error_category == ErrorCategory.NETWORK

    @pytest.mark.asyncio
    async def test_execute_with_retry_sync_function(self):
        """测试同步函数"""
        handler = RetryHandler()

        def sync_func():
            return "sync_success"

        result = await handler.execute_with_retry(sync_func)

        assert result.success is True
        assert result.result == "sync_success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_permanent_error_no_retry(self):
        """测试永久错误不重试"""
        config = RetryConfig(max_retries=3)
        handler = RetryHandler(config)

        call_count = 0

        async def permanent_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("invalid value")

        result = await handler.execute_with_retry(permanent_fail)

        assert result.success is False
        assert call_count == 1  # 只调用一次，不重试


class TestWithRetryDecorator:
    """测试重试装饰器"""

    @pytest.mark.asyncio
    async def test_with_retry_async_success(self):
        """测试异步函数成功"""

        @with_retry(max_retries=3, base_delay=0.01)
        async def my_function():
            return "success"

        result = await my_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_retry_async_with_retries(self):
        """测试异步函数重试"""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def my_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("fail")
            return "success"

        result = await my_function()
        assert result == "success"
        assert call_count == 2

    def test_with_retry_sync_success(self):
        """测试同步函数成功"""

        @with_retry(max_retries=3, base_delay=0.01)
        def my_function():
            return "success"

        result = my_function()
        assert result == "success"

    def test_with_retry_sync_with_retries(self):
        """测试同步函数重试"""
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01)
        def my_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("fail")
            return "success"

        result = my_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_exceed_max(self):
        """测试超过最大重试抛出异常"""

        @with_retry(max_retries=1, base_delay=0.01)
        async def always_fail():
            raise ConnectionError("always fails")

        with pytest.raises(ConnectionError):
            await always_fail()

    def test_with_retry_custom_errors(self):
        """测试自定义可重试错误"""
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01, retryable_errors=[ValueError])
        def my_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "success"

        result = my_function()
        assert result == "success"


class TestRetryConfigs:
    """测试预定义重试配置"""

    def test_llm_api_config(self):
        """测试LLM API配置"""
        config = RETRY_CONFIGS["llm_api"]

        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert "rate limit" in config.retryable_keywords

    def test_network_config(self):
        """测试网络配置"""
        config = RETRY_CONFIGS["network"]

        assert config.max_retries == 5
        assert ConnectionError in config.retryable_errors
        assert TimeoutError in config.retryable_errors

    def test_file_io_config(self):
        """测试文件IO配置"""
        config = RETRY_CONFIGS["file_io"]

        assert config.max_retries == 2
        assert "file locked" in config.retryable_keywords
