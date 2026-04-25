#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理器

提供友好的错误提示和诊断建议
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

from .logger import get_logger
from .cli_formatter import console, print_error as cli_print_error, print_warning, print_list, print_panel

logger = get_logger(__name__)


class ErrorType(Enum):
    """错误类型"""
    # 配置错误
    CONFIG_MISSING = "config_missing"
    CONFIG_INVALID = "config_invalid"
    API_KEY_MISSING = "api_key_missing"
    
    # 网络错误
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    
    # 文件错误
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION = "file_permission"
    FILE_FORMAT = "file_format"
    
    # 数据错误
    DATA_INVALID = "data_invalid"
    DATA_MISSING = "data_missing"
    DATA_CORRUPTED = "data_corrupted"
    
    # LLM错误
    LLM_API_ERROR = "llm_api_error"
    LLM_RESPONSE_ERROR = "llm_response_error"
    LLM_QUOTA_EXCEEDED = "llm_quota_exceeded"
    
    # 生成错误
    GENERATION_FAILED = "generation_failed"
    OPTIMIZATION_FAILED = "optimization_failed"
    VALIDATION_FAILED = "validation_failed"
    
    # 系统错误
    UNKNOWN = "unknown"


@dataclass
class ErrorSuggestion:
    """错误建议"""
    title: str
    description: str
    actions: List[str]
    priority: int = 0  # 0=高优先级, 1=中优先级, 2=低优先级


@dataclass
class ForgeAIError:
    """ForgeAI错误"""
    error_type: ErrorType
    message: str
    original_error: Optional[Exception] = None
    context: Dict[str, Any] = None
    suggestions: List[ErrorSuggestion] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.suggestions is None:
            self.suggestions = []
    
    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "original_error": str(self.original_error) if self.original_error else None,
            "context": self.context,
            "suggestions": [
                {
                    "title": s.title,
                    "description": s.description,
                    "actions": s.actions,
                    "priority": s.priority,
                }
                for s in self.suggestions
            ],
        }
    
    def __str__(self) -> str:
        """传统字符串输出（向后兼容）"""
        lines = [
            f"\n{'='*60}",
            f"❌ 错误: {self.message}",
            f"{'='*60}",
        ]
        
        if self.suggestions:
            lines.append("\n💡 解决建议:\n")
            for i, suggestion in enumerate(sorted(self.suggestions, key=lambda x: x.priority), 1):
                lines.append(f"{i}. {suggestion.title}")
                lines.append(f"   {suggestion.description}")
                for action in suggestion.actions:
                    lines.append(f"   • {action}")
                lines.append("")
        
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)
    
    def print_friendly(self) -> None:
        """使用彩色格式打印错误信息"""
        # 打印错误消息
        cli_print_error(self.message)
        
        # 打印建议
        if self.suggestions:
            console.print("\n💡 解决建议:\n", style="bold yellow")
            
            for i, suggestion in enumerate(sorted(self.suggestions, key=lambda x: x.priority), 1):
                # 建议标题
                console.print(f"  {i}. {suggestion.title}", style="bold cyan")
                # 建议描述
                console.print(f"     {suggestion.description}", style="dim white")
                # 操作步骤
                for action in suggestion.actions:
                    console.print(f"       • {action}", style="white")
                console.print()  # 空行


class ErrorHandler:
    """错误处理器"""
    
    # 错误模式匹配
    ERROR_PATTERNS = {
        ErrorType.API_KEY_MISSING: [
            "api key",
            "api_key",
            "apikey",
            "authentication",
            "unauthorized",
        ],
        ErrorType.RATE_LIMIT: [
            "rate limit",
            "too many requests",
            "429",
        ],
        ErrorType.TIMEOUT: [
            "timeout",
            "timed out",
        ],
        ErrorType.NETWORK_ERROR: [
            "connection",
            "network",
            "dns",
            "socket",
        ],
        ErrorType.FILE_NOT_FOUND: [
            "no such file",
            "file not found",
            "does not exist",
        ],
        ErrorType.FILE_PERMISSION: [
            "permission denied",
            "access denied",
            "forbidden",
        ],
        ErrorType.LLM_QUOTA_EXCEEDED: [
            "quota",
            "limit exceeded",
            "insufficient quota",
        ],
    }
    
    # 错误建议库
    SUGGESTIONS_DB: Dict[ErrorType, List[ErrorSuggestion]] = {
        ErrorType.API_KEY_MISSING: [
            ErrorSuggestion(
                title="配置API密钥",
                description="需要配置LLM API密钥才能使用生成功能",
                actions=[
                    "在 .env 文件中添加 API_KEY=your_key",
                    "或设置环境变量: export API_KEY=your_key",
                    "或使用 forgeai config set api_key your_key",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="获取API密钥",
                description="如果还没有API密钥,需要先申请",
                actions=[
                    "访问 LLM 提供商官网注册账号",
                    "在控制台创建 API 密钥",
                    "确保密钥有足够的配额",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.RATE_LIMIT: [
            ErrorSuggestion(
                title="等待后重试",
                description="API调用频率超限,需要等待一段时间",
                actions=[
                    "等待 60 秒后重试",
                    "减少并发请求数量",
                    "使用 forgeai config set rate_limit_delay 2.0 增加延迟",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="升级套餐",
                description="如果频繁遇到限流,考虑升级API套餐",
                actions=[
                    "检查当前API套餐限制",
                    "升级到更高配额的套餐",
                    "或使用多个API密钥轮换",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.NETWORK_ERROR: [
            ErrorSuggestion(
                title="检查网络连接",
                description="无法连接到API服务器",
                actions=[
                    "检查网络连接是否正常",
                    "尝试访问其他网站确认网络",
                    "检查防火墙设置",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="使用代理",
                description="如果网络受限,可以配置代理",
                actions=[
                    "设置 HTTP_PROXY 环境变量",
                    "或在配置文件中设置 proxy",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.FILE_NOT_FOUND: [
            ErrorSuggestion(
                title="检查文件路径",
                description="指定的文件不存在",
                actions=[
                    "确认文件路径是否正确",
                    "使用绝对路径而非相对路径",
                    "检查文件名拼写",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="创建文件",
                description="如果文件应该存在但不存在",
                actions=[
                    "运行 forgeai init 初始化项目",
                    "检查是否在正确的项目目录",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.FILE_PERMISSION: [
            ErrorSuggestion(
                title="检查文件权限",
                description="没有权限访问文件",
                actions=[
                    "检查文件读写权限",
                    "在 Linux/Mac 使用 chmod 修改权限",
                    "在 Windows 检查文件属性",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="关闭占用程序",
                description="文件可能被其他程序占用",
                actions=[
                    "关闭可能占用文件的程序",
                    "重启编辑器或IDE",
                    "使用文件解锁工具",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.LLM_QUOTA_EXCEEDED: [
            ErrorSuggestion(
                title="检查配额",
                description="API配额已用完",
                actions=[
                    "登录API控制台查看配额使用情况",
                    "等待配额重置(通常按月)",
                    "购买额外配额",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="优化使用",
                description="减少不必要的API调用",
                actions=[
                    "使用缓存减少重复调用",
                    "批量处理请求",
                    "降低生成温度减少token消耗",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.GENERATION_FAILED: [
            ErrorSuggestion(
                title="检查输入数据",
                description="生成失败可能是输入数据问题",
                actions=[
                    "检查章节号是否正确",
                    "确认项目状态文件存在",
                    "验证上下文数据完整性",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="简化请求",
                description="复杂的请求可能导致生成失败",
                actions=[
                    "减少上下文长度",
                    "简化主题指导",
                    "降低目标字数",
                ],
                priority=1,
            ),
        ],
        
        ErrorType.DATA_INVALID: [
            ErrorSuggestion(
                title="验证数据格式",
                description="数据格式不正确",
                actions=[
                    "检查 JSON 文件格式是否正确",
                    "使用 JSON 验证工具",
                    "查看错误日志获取详细信息",
                ],
                priority=0,
            ),
            ErrorSuggestion(
                title="恢复数据",
                description="如果数据损坏,尝试恢复",
                actions=[
                    "从备份恢复数据",
                    "重新生成损坏的数据",
                    "运行 forgeai init 重新初始化",
                ],
                priority=1,
            ),
        ],
    }
    
    @classmethod
    def classify_error(cls, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorType:
        """分类错误"""
        error_str = str(error).lower()
        
        # 匹配错误模式
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in error_str:
                    return error_type
        
        # 根据异常类型判断
        if isinstance(error, FileNotFoundError):
            return ErrorType.FILE_NOT_FOUND
        elif isinstance(error, PermissionError):
            return ErrorType.FILE_PERMISSION
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorType.NETWORK_ERROR
        elif isinstance(error, ValueError):
            return ErrorType.DATA_INVALID
        elif isinstance(error, KeyError):
            return ErrorType.DATA_MISSING
        
        return ErrorType.UNKNOWN
    
    @classmethod
    def create_error(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        custom_message: Optional[str] = None,
    ) -> ForgeAIError:
        """创建友好的错误对象"""
        error_type = cls.classify_error(error, context)
        
        # 获取建议
        suggestions = cls.SUGGESTIONS_DB.get(error_type, [])
        
        # 生成错误消息
        if custom_message:
            message = custom_message
        else:
            message = cls._generate_message(error_type, error, context)
        
        return ForgeAIError(
            error_type=error_type,
            message=message,
            original_error=error,
            context=context or {},
            suggestions=suggestions,
        )
    
    @classmethod
    def _generate_message(
        cls,
        error_type: ErrorType,
        error: Exception,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """生成错误消息"""
        base_messages = {
            ErrorType.API_KEY_MISSING: "API密钥未配置",
            ErrorType.RATE_LIMIT: "API调用频率超限",
            ErrorType.TIMEOUT: "请求超时",
            ErrorType.NETWORK_ERROR: "网络连接失败",
            ErrorType.FILE_NOT_FOUND: "文件不存在",
            ErrorType.FILE_PERMISSION: "文件权限不足",
            ErrorType.LLM_QUOTA_EXCEEDED: "API配额已用完",
            ErrorType.GENERATION_FAILED: "内容生成失败",
            ErrorType.DATA_INVALID: "数据格式无效",
            ErrorType.UNKNOWN: "未知错误",
        }
        
        message = base_messages.get(error_type, "操作失败")
        
        # 添加上下文信息
        if context:
            if "file" in context:
                message += f" (文件: {context['file']})"
            if "chapter" in context:
                message += f" (章节: {context['chapter']})"
            if "api" in context:
                message += f" (API: {context['api']})"
        
        # 添加原始错误信息
        if str(error):
            message += f"\n详细信息: {str(error)}"
        
        return message
    
    @classmethod
    def handle_error(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        raise_exception: bool = False,
        use_color: bool = True,
    ) -> Optional[ForgeAIError]:
        """
        处理错误
        
        Args:
            error: 原始异常
            context: 错误上下文
            raise_exception: 是否抛出异常
            use_color: 是否使用彩色输出（默认True）
        
        Returns:
            ForgeAIError对象
        """
        forge_error = cls.create_error(error, context)
        
        # 记录日志
        logger.error(
            f"错误类型: {forge_error.error_type.value}, "
            f"消息: {forge_error.message}",
            exc_info=error,
        )
        
        # 打印友好提示
        if use_color:
            forge_error.print_friendly()
        else:
            print(str(forge_error))
        
        if raise_exception:
            raise forge_error
        
        return forge_error


def handle_errors(context: Optional[Dict[str, Any]] = None):
    """
    错误处理装饰器
    
    用法:
        @handle_errors(context={"operation": "generate"})
        async def my_function():
            # 可能失败的代码
            pass
    """
    def decorator(func):
        import functools
        import asyncio
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.handle_error(e, context)
                return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.handle_error(e, context)
                return None
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
