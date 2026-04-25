#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全验证模块

提供输入验证、路径安全检查、敏感信息脱敏等功能。

功能：
1. 输入验证 - 验证字符串、数字、路径等输入
2. 路径安全检查 - 防止路径遍历攻击
3. 敏感信息脱敏 - API Key、密码等脱敏处理
4. 文件安全检查 - 文件类型、大小限制

用法：
    from forgeai_modules.security import (
        validate_input,
        safe_path,
        sanitize_for_log,
        SecurityValidator,
    )
"""

from __future__ import annotations

import os
import re
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Callable

from .exceptions import (
    InputValidationError,
    PathSecurityError,
)


# ============================================
# 敏感信息脱敏
# ============================================

# 敏感字段名模式
SENSITIVE_FIELD_PATTERNS = [
    r"api[_-]?key",
    r"secret",
    r"password",
    r"token",
    r"auth",
    r"credential",
    r"private[_-]?key",
]

# 编译正则表达式
_SENSITIVE_PATTERN = re.compile(
    "|".join(SENSITIVE_FIELD_PATTERNS),
    re.IGNORECASE
)


def mask_api_key(key: str, visible_chars: int = 4) -> str:
    """
    脱敏 API Key

    Args:
        key: 原始 API Key
        visible_chars: 可见字符数（前后各显示）

    Returns:
        脱敏后的字符串

    示例:
        >>> mask_api_key("sk-abc123def456")
        'sk-a...f456'
    """
    if not key:
        return "[空]"

    if len(key) <= visible_chars * 2:
        return "****"

    return f"{key[:visible_chars]}...{key[-visible_chars:]}"


def sanitize_for_log(data: Any, max_length: int = 100) -> str:
    """
    为日志输出脱敏数据

    Args:
        data: 要脱敏的数据
        max_length: 最大长度限制

    Returns:
        脱敏后的字符串
    """
    if data is None:
        return "None"

    if isinstance(data, str):
        # 检查是否像 API Key
        if _SENSITIVE_PATTERN.search(data) or (
            len(data) > 20 and
            any(c.isdigit() for c in data) and
            any(c.isalpha() for c in data) and
            " " not in data
        ):
            return mask_api_key(data)

        # 截断长字符串
        if len(data) > max_length:
            return f"{data[:max_length]}...[截断]"

        return data

    if isinstance(data, dict):
        return sanitize_dict_for_log(data, max_length)

    if isinstance(data, list):
        if len(data) > 5:
            return f"[{len(data)}项]"
        return str([sanitize_for_log(item, max_length) for item in data])

    return str(data)[:max_length]


def sanitize_dict_for_log(
    data: Dict[str, Any],
    max_length: int = 100
) -> str:
    """
    为日志输出脱敏字典

    Args:
        data: 要脱敏的字典
        max_length: 单个值的最大长度

    Returns:
        脱敏后的字符串表示
    """
    sanitized = {}
    for key, value in data.items():
        # 检查键名是否敏感
        if _SENSITIVE_PATTERN.search(key):
            sanitized[key] = mask_api_key(str(value)) if value else "[空]"
        else:
            sanitized[key] = sanitize_for_log(value, max_length)

    return str(sanitized)


def sanitize_env_for_display(env_vars: Dict[str, str]) -> Dict[str, str]:
    """
    脱敏环境变量用于显示

    Args:
        env_vars: 环境变量字典

    Returns:
        脱敏后的字典
    """
    result = {}
    for key, value in env_vars.items():
        # 包含 KEY、SECRET、PASSWORD、TOKEN 的字段需要脱敏
        if _SENSITIVE_PATTERN.search(key):
            result[key] = mask_api_key(value) if value else "[未设置]"
        else:
            # 其他字段截断显示
            result[key] = value[:50] + "..." if len(value) > 50 else value

    return result


# ============================================
# 路径安全检查
# ============================================

def safe_path(
    base_dir: Union[str, Path],
    user_path: Union[str, Path],
    allow_absolute: bool = False
) -> Path:
    """
    安全路径解析，防止路径遍历攻击

    Args:
        base_dir: 基础目录
        user_path: 用户提供的路径
        allow_absolute: 是否允许绝对路径

    Returns:
        解析后的安全路径

    Raises:
        PathSecurityError: 检测到路径遍历攻击

    示例:
        >>> safe_path("/project", "data/file.txt")
        Path("/project/data/file.txt")

        >>> safe_path("/project", "../etc/passwd")  # 抛出 PathSecurityError
    """
    base_dir = Path(base_dir).resolve()
    user_path = Path(user_path)

    # 检查是否为绝对路径
    if user_path.is_absolute() and not allow_absolute:
        raise PathSecurityError(
            path=str(user_path),
            base_dir=str(base_dir)
        )

    # 解析完整路径
    full_path = (base_dir / user_path).resolve()

    # 检查是否在基础目录内
    try:
        full_path.relative_to(base_dir)
    except ValueError:
        raise PathSecurityError(
            path=str(user_path),
            base_dir=str(base_dir)
        )

    return full_path


def validate_file_path(
    file_path: Union[str, Path],
    must_exist: bool = True,
    allowed_extensions: Optional[List[str]] = None,
    max_size_mb: Optional[float] = None
) -> Path:
    """
    验证文件路径安全性

    Args:
        file_path: 文件路径
        must_exist: 文件是否必须存在
        allowed_extensions: 允许的文件扩展名列表
        max_size_mb: 最大文件大小（MB）

    Returns:
        验证后的路径

    Raises:
        InputValidationError: 验证失败
    """
    path = Path(file_path)

    # 检查文件是否存在
    if must_exist and not path.exists():
        raise InputValidationError(
            field="file_path",
            value=str(file_path),
            reason="文件不存在"
        )

    # 检查扩展名
    if allowed_extensions:
        ext = path.suffix.lower()
        if ext not in [e.lower() for e in allowed_extensions]:
            raise InputValidationError(
                field="file_path",
                value=str(file_path),
                reason=f"不允许的文件类型: {ext}，允许: {allowed_extensions}"
            )

    # 检查文件大小
    if max_size_mb and path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise InputValidationError(
                field="file_path",
                value=str(file_path),
                reason=f"文件过大: {size_mb:.2f}MB > {max_size_mb}MB"
            )

    return path


def check_path_traversal(path: str) -> bool:
    """
    检查路径是否包含遍历字符

    Args:
        path: 要检查的路径

    Returns:
        True 如果路径安全，False 如果包含遍历字符
    """
    # 检查危险模式
    dangerous_patterns = ["../", "..\\", "~/", "/etc/", "/proc/", "/sys/"]

    for pattern in dangerous_patterns:
        if pattern in path:
            return False

    return True


# ============================================
# 输入验证
# ============================================

class SecurityValidator:
    """安全验证器"""

    # 章节号范围
    CHAPTER_MIN = 1
    CHAPTER_MAX = 99999

    # 字符串长度限制
    STRING_MAX_LENGTH = 1000000  # 1M 字符
    QUERY_MAX_LENGTH = 10000

    # 文件扩展名白名单
    ALLOWED_TEXT_EXTENSIONS = [".txt", ".md", ".json", ".csv"]
    ALLOWED_DATA_EXTENSIONS = [".json", ".db", ".sqlite"]

    @classmethod
    def validate_chapter_number(cls, chapter: int) -> int:
        """
        验证章节号

        Args:
            chapter: 章节号

        Returns:
            验证后的章节号

        Raises:
            InputValidationError: 章节号无效
        """
        if not isinstance(chapter, int):
            try:
                chapter = int(chapter)
            except (ValueError, TypeError):
                raise InputValidationError(
                    field="chapter",
                    value=chapter,
                    reason="章节号必须是整数"
                )

        if chapter < cls.CHAPTER_MIN or chapter > cls.CHAPTER_MAX:
            raise InputValidationError(
                field="chapter",
                value=chapter,
                reason=f"章节号必须在 {cls.CHAPTER_MIN} 到 {cls.CHAPTER_MAX} 之间"
            )

        return chapter

    @classmethod
    def validate_string(
        cls,
        value: str,
        field_name: str = "value",
        max_length: Optional[int] = None,
        min_length: int = 0,
        allow_empty: bool = True,
        pattern: Optional[str] = None
    ) -> str:
        """
        验证字符串输入

        Args:
            value: 字符串值
            field_name: 字段名（用于错误信息）
            max_length: 最大长度
            min_length: 最小长度
            allow_empty: 是否允许空字符串
            pattern: 正则表达式模式

        Returns:
            验证后的字符串

        Raises:
            InputValidationError: 验证失败
        """
        if not isinstance(value, str):
            raise InputValidationError(
                field=field_name,
                value=value,
                reason=f"必须是字符串类型，实际为 {type(value).__name__}"
            )

        if not allow_empty and not value.strip():
            raise InputValidationError(
                field=field_name,
                value="[空字符串]",
                reason="不能为空"
            )

        if min_length > 0 and len(value) < min_length:
            raise InputValidationError(
                field=field_name,
                value=f"[{len(value)}字符]",
                reason=f"长度不能少于 {min_length} 个字符"
            )

        max_len = max_length or cls.STRING_MAX_LENGTH
        if len(value) > max_len:
            raise InputValidationError(
                field=field_name,
                value=f"[{len(value)}字符]",
                reason=f"长度不能超过 {max_len} 个字符"
            )

        if pattern and not re.match(pattern, value):
            raise InputValidationError(
                field=field_name,
                value=value[:50],
                reason=f"格式不正确"
            )

        return value

    @classmethod
    def validate_query(cls, query: str) -> str:
        """
        验证搜索查询

        Args:
            query: 搜索查询字符串

        Returns:
            验证后的查询字符串
        """
        return cls.validate_string(
            query,
            field_name="query",
            max_length=cls.QUERY_MAX_LENGTH,
            min_length=1,
            allow_empty=False
        )

    @classmethod
    def validate_integer(
        cls,
        value: Any,
        field_name: str = "value",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> int:
        """
        验证整数输入

        Args:
            value: 输入值
            field_name: 字段名
            min_value: 最小值
            max_value: 最大值

        Returns:
            验证后的整数
        """
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise InputValidationError(
                    field=field_name,
                    value=value,
                    reason="必须是整数"
                )

        if min_value is not None and value < min_value:
            raise InputValidationError(
                field=field_name,
                value=value,
                reason=f"不能小于 {min_value}"
            )

        if max_value is not None and value > max_value:
            raise InputValidationError(
                field=field_name,
                value=value,
                reason=f"不能大于 {max_value}"
            )

        return value

    @classmethod
    def validate_file_for_indexing(
        cls,
        file_path: Union[str, Path],
        max_size_mb: float = 10.0
    ) -> Path:
        """
        验证用于索引的文件

        Args:
            file_path: 文件路径
            max_size_mb: 最大文件大小

        Returns:
            验证后的路径
        """
        return validate_file_path(
            file_path,
            must_exist=True,
            allowed_extensions=cls.ALLOWED_TEXT_EXTENSIONS,
            max_size_mb=max_size_mb
        )

    @classmethod
    def validate_json_data(
        cls,
        data: Any,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        验证 JSON 数据结构

        Args:
            data: JSON 数据
            max_depth: 最大嵌套深度

        Returns:
            验证后的数据

        Raises:
            InputValidationError: 数据无效
        """
        def check_depth(obj: Any, current_depth: int) -> None:
            if current_depth > max_depth:
                raise InputValidationError(
                    field="json_data",
                    value="[嵌套过深]",
                    reason=f"JSON 嵌套深度不能超过 {max_depth}"
                )

            if isinstance(obj, dict):
                for v in obj.values():
                    check_depth(v, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, current_depth + 1)

        if not isinstance(data, dict):
            raise InputValidationError(
                field="json_data",
                value=type(data).__name__,
                reason="必须是字典类型"
            )

        check_depth(data, 0)
        return data


# ============================================
# 便捷函数
# ============================================

def validate_input(value: Any, field_name: str = "value", **kwargs) -> Any:
    """
    便捷验证函数

    根据值类型自动选择验证方法
    """
    if isinstance(value, int):
        return SecurityValidator.validate_integer(value, field_name)
    elif isinstance(value, str):
        return SecurityValidator.validate_string(value, field_name, **kwargs)
    elif isinstance(value, dict):
        return SecurityValidator.validate_json_data(value)
    else:
        return value


def secure_filename(filename: str) -> str:
    """
    安全文件名处理

    移除或替换危险字符

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    # 只保留字母、数字、中文、下划线、连字符和点
    safe_chars = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', filename)

    # 移除连续的下划线
    safe_chars = re.sub(r'_+', '_', safe_chars)

    # 移除首尾的下划线和点
    safe_chars = safe_chars.strip('_.')

    # 确保不为空
    if not safe_chars:
        safe_chars = "unnamed"

    return safe_chars


def hash_sensitive(value: str, salt: str = "") -> str:
    """
    对敏感信息进行哈希处理

    Args:
        value: 敏感信息
        salt: 盐值

    Returns:
        哈希值
    """
    combined = f"{salt}{value}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()[:16]


# ============================================
# 模块测试
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("安全验证模块测试")
    print("=" * 60)

    # 测试 API Key 脱敏
    print("\n[API Key 脱敏测试]")
    test_keys = [
        "sk-abc123def456ghi789",
        "pk-short",
        "",
        "a",
    ]
    for key in test_keys:
        print(f"  {key!r} → {mask_api_key(key)}")

    # 测试路径安全
    print("\n[路径安全测试]")
    test_paths = [
        ("data/file.txt", True),
        ("../etc/passwd", False),
        ("data/../../../etc/passwd", False),
        ("data/./file.txt", True),
    ]
    for path, expected_safe in test_paths:
        try:
            result = safe_path("/project", path)
            print(f"  {path} → ✅ 安全: {result}")
        except PathSecurityError as e:
            print(f"  {path} → ❌ 危险: {e.message}")

    # 测试输入验证
    print("\n[输入验证测试]")
    validator = SecurityValidator()

    # 章节号验证
    test_chapters = [1, 100, 0, -1, 1000000]
    for ch in test_chapters:
        try:
            validator.validate_chapter_number(ch)
            print(f"  章节 {ch} → ✅ 有效")
        except InputValidationError as e:
            print(f"  章节 {ch} → ❌ 无效: {e.message}")

    # 测试敏感信息脱敏
    print("\n[敏感信息脱敏测试]")
    test_data = {
        "LLM_API_KEY": "sk-super-secret-key-12345",
        "user_name": "张三",
        "password": "my_password",
        "normal_field": "正常数据",
    }
    print(f"  原始: {test_data}")
    print(f"  脱敏: {sanitize_env_for_display(test_data)}")

    print("\n" + "=" * 60)
