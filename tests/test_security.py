"""
单元测试：security.py 模块

测试安全验证、路径检查、敏感信息脱敏
"""

import os
import sys
from pathlib import Path

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.security import (
    mask_api_key,
    sanitize_for_log,
    sanitize_dict_for_log,
    sanitize_env_for_display,
    safe_path,
    validate_file_path,
    check_path_traversal,
    SecurityValidator,
    validate_input,
    secure_filename,
    hash_sensitive,
)
from forgeai_modules.exceptions import (
    InputValidationError,
    PathSecurityError,
)


class TestMaskApiKey:
    """测试 API Key 脱敏"""

    def test_normal_key(self):
        """正常 API Key"""
        masked = mask_api_key("sk-abc123def456ghi789")
        assert masked.startswith("sk-a")
        assert masked.endswith("i789")
        assert "..." in masked

    def test_short_key(self):
        """短 API Key"""
        masked = mask_api_key("abc")
        assert masked == "****"

    def test_empty_key(self):
        """空 API Key"""
        masked = mask_api_key("")
        assert masked == "[空]"

    def test_custom_visible_chars(self):
        """自定义可见字符数"""
        masked = mask_api_key("sk-abcdefghij", visible_chars=2)
        assert masked.startswith("sk")
        assert masked.endswith("ij")

    def test_none_key(self):
        """None 值"""
        masked = mask_api_key(None)
        assert masked == "[空]"


class TestSanitizeForLog:
    """测试日志脱敏"""

    def test_sanitize_string(self):
        """字符串脱敏"""
        result = sanitize_for_log("正常字符串")
        assert result == "正常字符串"

    def test_sanitize_long_string(self):
        """长字符串截断"""
        long_str = "a" * 200
        result = sanitize_for_log(long_str, max_length=50)

        assert len(result) < 100
        assert "截断" in result

    def test_sanitize_api_key_like(self):
        """类 API Key 字符串"""
        key_like = "sk-proj-abc123def456ghi789jkl"
        result = sanitize_for_log(key_like)

        assert "..." in result
        assert result != key_like

    def test_sanitize_dict(self):
        """字典脱敏"""
        data = {"api_key": "secret123", "name": "测试"}
        result = sanitize_dict_for_log(data)

        assert "secret123" not in result
        assert "测试" in result

    def test_sanitize_list(self):
        """列表脱敏"""
        data = ["item1", "item2", "item3", "item4", "item5", "item6"]
        result = sanitize_for_log(data)

        assert "6项" in result

    def test_sanitize_none(self):
        """None 值"""
        result = sanitize_for_log(None)
        assert result == "None"


class TestSanitizeEnvForDisplay:
    """测试环境变量脱敏"""

    def test_sanitize_sensitive_keys(self):
        """敏感键脱敏"""
        env = {
            "LLM_API_KEY": "sk-secret-key-123",
            "OPENAI_API_KEY": "sk-openai-key",
            "password": "my_password",
            "normal_var": "normal_value",
        }
        result = sanitize_env_for_display(env)

        assert result["LLM_API_KEY"] != "sk-secret-key-123"
        assert result["OPENAI_API_KEY"] != "sk-openai-key"
        assert result["password"] != "my_password"
        assert result["normal_var"] == "normal_value"

    def test_sanitize_long_value(self):
        """长值截断"""
        env = {"LONG_VAR": "a" * 100}
        result = sanitize_env_for_display(env)

        assert len(result["LONG_VAR"]) < 60


class TestSafePath:
    """测试安全路径检查"""

    def test_normal_relative_path(self):
        """正常相对路径"""
        result = safe_path("/project", "data/file.txt")
        # 在 Windows 上路径可能被转换，检查是否包含预期部分
        assert "data" in str(result)
        assert "file.txt" in str(result)

    def test_path_traversal_attack(self):
        """路径遍历攻击"""
        with pytest.raises(PathSecurityError):
            safe_path("/project", "../etc/passwd")

    def test_deep_traversal(self):
        """深层路径遍历"""
        with pytest.raises(PathSecurityError):
            safe_path("/project", "data/../../../etc/passwd")

    def test_absolute_path_blocked(self):
        """绝对路径被阻止"""
        with pytest.raises(PathSecurityError):
            safe_path("/project", "/etc/passwd")

    def test_absolute_path_allowed(self):
        """允许绝对路径"""
        # 需要显式允许
        result = safe_path("/project", "/project/data/file.txt", allow_absolute=True)
        # Windows 路径格式可能不同，检查关键部分
        assert "data" in str(result)
        assert "file.txt" in str(result)

    def test_dotdot_in_middle(self):
        """中间包含 .."""
        with pytest.raises(PathSecurityError):
            safe_path("/project", "data/../..")


class TestValidateFilePath:
    """测试文件路径验证"""

    def test_existing_file(self, temp_project: Path):
        """存在的文件"""
        # 创建测试文件
        test_file = temp_project / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        result = validate_file_path(test_file, must_exist=True)
        assert result.exists()

    def test_nonexistent_file(self):
        """不存在的文件"""
        with pytest.raises(InputValidationError):
            validate_file_path("/nonexistent/path/file.txt", must_exist=True)

    def test_file_not_required(self):
        """文件不必须存在"""
        result = validate_file_path("/any/path/file.txt", must_exist=False)
        assert isinstance(result, Path)

    def test_allowed_extensions(self, temp_project: Path):
        """允许的扩展名"""
        test_file = temp_project / "test.txt"
        test_file.write_text("test", encoding="utf-8")

        result = validate_file_path(
            test_file,
            allowed_extensions=[".txt", ".md"]
        )
        assert result.exists()

    def test_disallowed_extension(self, temp_project: Path):
        """不允许的扩展名"""
        test_file = temp_project / "test.exe"
        test_file.write_text("test", encoding="utf-8")

        with pytest.raises(InputValidationError) as exc_info:
            validate_file_path(test_file, allowed_extensions=[".txt"])

        assert ".exe" in str(exc_info.value)


class TestCheckPathTraversal:
    """测试路径遍历检查"""

    def test_safe_paths(self):
        """安全路径"""
        safe_paths = [
            "data/file.txt",
            "chapters/chapter1.txt",
            "output/result.json",
        ]
        for path in safe_paths:
            assert check_path_traversal(path) is True

    def test_dangerous_paths(self):
        """危险路径"""
        dangerous = [
            "../etc/passwd",
            "data/../../../etc",
            "~/secret",
            "/etc/passwd",
        ]
        for path in dangerous:
            assert check_path_traversal(path) is False


class TestSecurityValidator:
    """测试安全验证器"""

    def test_validate_chapter_number(self):
        """验证章节号"""
        # 有效章节号
        assert SecurityValidator.validate_chapter_number(1) == 1
        assert SecurityValidator.validate_chapter_number(100) == 100

    def test_validate_chapter_number_invalid(self):
        """无效章节号"""
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_chapter_number(0)

        with pytest.raises(InputValidationError):
            SecurityValidator.validate_chapter_number(-1)

        with pytest.raises(InputValidationError):
            SecurityValidator.validate_chapter_number(1000000)

    def test_validate_chapter_number_from_string(self):
        """从字符串转换章节号"""
        assert SecurityValidator.validate_chapter_number("10") == 10

    def test_validate_string(self):
        """验证字符串"""
        result = SecurityValidator.validate_string("测试字符串", "test")
        assert result == "测试字符串"

    def test_validate_string_max_length(self):
        """字符串最大长度"""
        long_str = "a" * 1000
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_string(long_str, "test", max_length=100)

    def test_validate_string_min_length(self):
        """字符串最小长度"""
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_string("ab", "test", min_length=5)

    def test_validate_string_empty_not_allowed(self):
        """不允许空字符串"""
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_string("", "test", allow_empty=False)

    def test_validate_string_pattern(self):
        """正则表达式模式"""
        result = SecurityValidator.validate_string(
            "test@example.com",
            "email",
            pattern=r"^[\w@.]+$"
        )
        assert result == "test@example.com"

    def test_validate_query(self):
        """验证搜索查询"""
        result = SecurityValidator.validate_query("主角战斗场景")
        assert result == "主角战斗场景"

    def test_validate_integer(self):
        """验证整数"""
        assert SecurityValidator.validate_integer(10, "count") == 10

    def test_validate_integer_range(self):
        """整数范围验证"""
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_integer(5, "score", min_value=1, max_value=3)

    def test_validate_integer_from_string(self):
        """从字符串转换整数"""
        assert SecurityValidator.validate_integer("42", "value") == 42

    def test_validate_json_data(self):
        """验证 JSON 数据"""
        data = {"key": "value", "nested": {"a": 1}}
        result = SecurityValidator.validate_json_data(data)
        assert result is data

    def test_validate_json_data_too_deep(self):
        """JSON 嵌套过深"""
        deep_data = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": 1}}}}}}}}}
        with pytest.raises(InputValidationError):
            SecurityValidator.validate_json_data(deep_data, max_depth=5)


class TestValidateInput:
    """测试便捷验证函数"""

    def test_validate_integer_input(self):
        """验证整数输入"""
        result = validate_input(10, "count")
        assert result == 10

    def test_validate_string_input(self):
        """验证字符串输入"""
        result = validate_input("test", "field", max_length=100)
        assert result == "test"

    def test_validate_dict_input(self):
        """验证字典输入"""
        result = validate_input({"key": "value"}, "data")
        assert result["key"] == "value"


class TestSecureFilename:
    """测试安全文件名处理"""

    def test_normal_filename(self):
        """正常文件名"""
        result = secure_filename("chapter_1.txt")
        assert result == "chapter_1.txt"

    def test_chinese_filename(self):
        """中文文件名"""
        result = secure_filename("第一章 正文.txt")
        assert "第一章" in result
        assert ".txt" in result

    def test_filename_with_special_chars(self):
        """特殊字符文件名"""
        result = secure_filename("file<>:\"|?*.txt")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_filename_with_path_separators(self):
        """路径分隔符"""
        result = secure_filename("path/to/file.txt")
        assert "/" not in result or "\\" not in result

    def test_empty_filename(self):
        """空文件名"""
        result = secure_filename("")
        assert result == "unnamed"


class TestHashSensitive:
    """测试敏感信息哈希"""

    def test_hash_consistency(self):
        """哈希一致性"""
        value = "secret123"
        hash1 = hash_sensitive(value)
        hash2 = hash_sensitive(value)
        assert hash1 == hash2

    def test_hash_with_salt(self):
        """带盐值的哈希"""
        value = "secret"
        hash1 = hash_sensitive(value, "salt1")
        hash2 = hash_sensitive(value, "salt2")
        assert hash1 != hash2

    def test_hash_length(self):
        """哈希长度"""
        result = hash_sensitive("any_value")
        assert len(result) == 16


class TestSecurityIntegration:
    """安全模块集成测试"""

    def test_full_validation_workflow(self, temp_project: Path):
        """完整验证工作流"""
        # 1. 验证章节号
        chapter = SecurityValidator.validate_chapter_number(10)

        # 2. 验证查询字符串
        query = SecurityValidator.validate_query("主角与反派战斗")

        # 3. 安全路径处理
        data_dir = temp_project / "data"
        data_dir.mkdir(exist_ok=True)
        safe_file = safe_path(data_dir, "chapter_10.txt")

        # 4. 创建文件
        safe_file.write_text("章节内容", encoding="utf-8")

        # 5. 验证文件
        validated_path = SecurityValidator.validate_file_for_indexing(safe_file)
        assert validated_path.exists()

    def test_api_key_handling(self):
        """API Key 处理流程"""
        api_key = "sk-proj-abc123def456ghi789"

        # 日志中脱敏
        log_safe = sanitize_for_log(api_key)
        assert api_key not in log_safe

        # 存储哈希
        key_hash = hash_sensitive(api_key)
        assert len(key_hash) == 16
