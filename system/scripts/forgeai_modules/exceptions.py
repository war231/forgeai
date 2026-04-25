#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ForgeAI 统一异常类层次结构

提供结构化的异常类型，便于：
- 精确捕获和处理特定类型的错误
- 提供用户友好的错误信息
- 支持错误链追踪

异常层次：
    ForgeAIError (基类)
    ├── ConfigurationError
    │   ├── MissingConfigError
    │   └── InvalidConfigError
    ├── APIError
    │   ├── AuthenticationError
    │   ├── RateLimitError
    │   ├── APIConnectionError
    │   └── APIResponseError
    ├── DatabaseError
    │   ├── DatabaseConnectionError
    │   └── DatabaseQueryError
    ├── ValidationError
    │   ├── InputValidationError
    │   └── PathSecurityError
    ├── TokenExceededError
    └── ExtractionError
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List


class ForgeAIError(Exception):
    """
    ForgeAI 异常基类

    所有 ForgeAI 特定异常都继承此类。

    Attributes:
        message: 用户友好的错误信息
        detail: 技术细节（可选）
        suggestion: 修复建议（可选）
        cause: 原始异常（可选）
    """

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.suggestion = suggestion
        self.cause = cause

    def __str__(self) -> str:
        parts = [self.message]
        if self.detail:
            parts.append(f"详情: {self.detail}")
        if self.suggestion:
            parts.append(f"建议: {self.suggestion}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 API 响应"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "detail": self.detail,
            "suggestion": self.suggestion,
        }


# ============================================
# 配置相关异常
# ============================================

class ConfigurationError(ForgeAIError):
    """配置相关错误基类"""
    pass


class MissingConfigError(ConfigurationError):
    """缺少必需的配置项"""

    def __init__(
        self,
        config_key: str,
        message: Optional[str] = None,
        **kwargs
    ):
        self.config_key = config_key
        if message is None:
            message = f"缺少必需的配置项: {config_key}"
        super().__init__(
            message=message,
            suggestion=f"请在 .env 文件中设置 {config_key}=<value>",
            **kwargs
        )


class InvalidConfigError(ConfigurationError):
    """配置值无效"""

    def __init__(
        self,
        config_key: str,
        config_value: Any,
        expected_type: str,
        message: Optional[str] = None,
        **kwargs
    ):
        self.config_key = config_key
        self.config_value = config_value
        self.expected_type = expected_type

        if message is None:
            message = f"配置项 {config_key} 的值无效: 期望 {expected_type}，实际为 {type(config_value).__name__}"
        super().__init__(
            message=message,
            suggestion=f"请将 {config_key} 设置为 {expected_type} 类型",
            **kwargs
        )


# ============================================
# API 相关异常
# ============================================

class APIError(ForgeAIError):
    """API 调用相关错误基类"""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["provider"] = self.provider
        result["status_code"] = self.status_code
        return result


class AuthenticationError(APIError):
    """API 认证失败"""

    def __init__(self, provider: str, **kwargs):
        message = f"{provider} API 认证失败"
        super().__init__(
            message=message,
            provider=provider,
            suggestion="请检查 API Key 是否正确",
            **kwargs
        )


class RateLimitError(APIError):
    """API 速率限制"""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        self.retry_after = retry_after
        message = f"{provider} API 达到速率限制"
        suggestion = "请稍后重试"
        if retry_after:
            suggestion = f"请在 {retry_after} 秒后重试"
        super().__init__(
            message=message,
            provider=provider,
            suggestion=suggestion,
            **kwargs
        )


class APIConnectionError(APIError):
    """API 连接失败"""

    def __init__(
        self,
        provider: str,
        base_url: Optional[str] = None,
        **kwargs
    ):
        self.base_url = base_url
        message = f"无法连接到 {provider} API"
        if base_url:
            message += f" ({base_url})"
        super().__init__(
            message=message,
            provider=provider,
            suggestion="请检查网络连接和 API 端点配置",
            **kwargs
        )


class APIResponseError(APIError):
    """API 响应异常"""

    def __init__(
        self,
        provider: str,
        status_code: int,
        response_body: Optional[str] = None,
        **kwargs
    ):
        self.response_body = response_body
        message = f"{provider} API 返回错误状态码: {status_code}"
        super().__init__(
            message=message,
            provider=provider,
            status_code=status_code,
            detail=response_body[:200] if response_body else None,
            suggestion="请检查 API 文档或联系服务提供商",
            **kwargs
        )


# ============================================
# 数据库相关异常
# ============================================

class DatabaseError(ForgeAIError):
    """数据库相关错误基类"""

    def __init__(
        self,
        message: str,
        db_path: Optional[str] = None,
        **kwargs
    ):
        self.db_path = db_path
        super().__init__(message, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """数据库连接失败"""

    def __init__(self, db_path: str, **kwargs):
        message = f"无法连接到数据库: {db_path}"
        super().__init__(
            message=message,
            db_path=db_path,
            suggestion="请检查文件路径和权限",
            **kwargs
        )


class DatabaseQueryError(DatabaseError):
    """数据库查询错误"""

    def __init__(
        self,
        query: Optional[str] = None,
        db_path: Optional[str] = None,
        **kwargs
    ):
        self.query = query
        message = "数据库查询执行失败"
        super().__init__(
            message=message,
            db_path=db_path,
            detail=query[:100] if query else None,
            suggestion="请检查查询语法或数据库状态",
            **kwargs
        )


# ============================================
# 验证相关异常
# ============================================

class ValidationError(ForgeAIError):
    """验证相关错误基类"""
    pass


class InputValidationError(ValidationError):
    """输入验证失败"""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        **kwargs
    ):
        self.field = field
        self.value = value
        self.reason = reason

        message = f"输入验证失败: {field} - {reason}"
        super().__init__(
            message=message,
            suggestion="请检查输入值是否符合要求",
            **kwargs
        )


class PathSecurityError(ValidationError):
    """路径安全错误（路径遍历攻击检测）"""

    def __init__(
        self,
        path: str,
        base_dir: str,
        **kwargs
    ):
        self.path = path
        self.base_dir = base_dir

        message = f"检测到潜在的路径遍历攻击: {path}"
        super().__init__(
            message=message,
            detail=f"基础目录: {base_dir}",
            suggestion="请使用合法的文件路径",
            **kwargs
        )


# ============================================
# Token 相关异常
# ============================================

class TokenExceededError(ForgeAIError):
    """Token 超出限制"""

    def __init__(
        self,
        current_tokens: int,
        max_tokens: int,
        **kwargs
    ):
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens

        message = f"Token 数量超出限制: {current_tokens} > {max_tokens}"
        super().__init__(
            message=message,
            suggestion="请减少输入内容或启用自动截断",
            **kwargs
        )


# ============================================
# 提取相关异常
# ============================================

class ExtractionError(ForgeAIError):
    """信息提取失败"""

    def __init__(
        self,
        extraction_type: str,
        reason: str,
        **kwargs
    ):
        self.extraction_type = extraction_type

        message = f"{extraction_type} 提取失败: {reason}"
        super().__init__(
            message=message,
            suggestion="请检查输入内容格式",
            **kwargs
        )


# ============================================
# 辅助函数
# ============================================

def wrap_exception(
    original: Exception,
    wrapper_class: type,
    message: Optional[str] = None,
    **kwargs
) -> ForgeAIError:
    """
    将原始异常包装为 ForgeAI 异常

    Args:
        original: 原始异常
        wrapper_class: 目标异常类
        message: 自定义消息（可选）

    Returns:
        包装后的 ForgeAI 异常

    示例:
        try:
            response = requests.get(url)
        except requests.ConnectionError as e:
            raise wrap_exception(e, APIConnectionError, provider="openai")
    """
    import inspect

    if message is None:
        message = str(original)

    # 检查包装类是否接受 message 参数
    sig = inspect.signature(wrapper_class.__init__)
    accepts_message = 'message' in sig.parameters

    # 准备通用参数
    common_kwargs = {
        'detail': f"原始错误: {type(original).__name__}: {original}",
        'cause': original,
    }

    # 如果类接受 message 参数，则传递
    if accepts_message:
        common_kwargs['message'] = message

    # 合并用户提供的参数
    common_kwargs.update(kwargs)

    return wrapper_class(**common_kwargs)


def is_recoverable(error: Exception) -> bool:
    """
    判断错误是否可恢复

    Args:
        error: 异常实例

    Returns:
        True 如果错误可恢复（可重试）
    """
    # 速率限制可恢复
    if isinstance(error, RateLimitError):
        return True

    # 连接错误可恢复
    if isinstance(error, (APIConnectionError, DatabaseConnectionError)):
        return True

    # 配置错误不可恢复
    if isinstance(error, ConfigurationError):
        return False

    # 安全错误不可恢复
    if isinstance(error, PathSecurityError):
        return False

    return False


def get_retry_delay(error: Exception) -> Optional[float]:
    """
    获取重试延迟时间

    Args:
        error: 异常实例

    Returns:
        重试延迟秒数，如果不应该重试则返回 None
    """
    if not is_recoverable(error):
        return None

    if isinstance(error, RateLimitError):
        return float(error.retry_after) if error.retry_after else 60.0

    if isinstance(error, (APIConnectionError, DatabaseConnectionError)):
        return 5.0  # 默认 5 秒后重试

    return None


# ============================================
# 异常处理装饰器
# ============================================

def safe_call(default=None, log_errors: bool = True):
    """
    安全调用装饰器，捕获异常并返回默认值

    Args:
        default: 发生异常时返回的默认值
        log_errors: 是否记录错误日志

    示例:
        @safe_call(default=[])
        def get_items():
            return api.fetch_items()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ForgeAIError as e:
                if log_errors:
                    from .logger import get_logger
                    logger = get_logger(func.__module__)
                    logger.warning("%s: %s", type(e).__name__, e.message)
                return default
            except Exception as e:
                if log_errors:
                    from .logger import get_logger
                    logger = get_logger(func.__module__)
                    logger.error("Unexpected error in %s: %s", func.__name__, e)
                return default
        return wrapper
    return decorator
