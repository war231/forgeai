"""
单元测试：exceptions.py 模块

测试统一异常类层次结构
"""

import sys
from pathlib import Path

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.exceptions import (
    ForgeAIError,
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
    APIError,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APIResponseError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    ValidationError,
    InputValidationError,
    PathSecurityError,
    TokenExceededError,
    ExtractionError,
    wrap_exception,
    is_recoverable,
    get_retry_delay,
    safe_call,
)


class TestForgeAIError:
    """测试基类 ForgeAIError"""

    def test_basic_error(self):
        """基本错误创建"""
        error = ForgeAIError("发生错误")
        assert error.message == "发生错误"
        assert str(error) == "发生错误"

    def test_error_with_detail(self):
        """带详情的错误"""
        error = ForgeAIError(
            message="发生错误",
            detail="技术详情信息"
        )
        assert "技术详情信息" in str(error)

    def test_error_with_suggestion(self):
        """带建议的错误"""
        error = ForgeAIError(
            message="发生错误",
            suggestion="请尝试重新操作"
        )
        assert "请尝试重新操作" in str(error)

    def test_error_with_cause(self):
        """带原因的错误"""
        original = ValueError("原始错误")
        error = ForgeAIError(
            message="包装错误",
            cause=original
        )
        assert error.cause is original

    def test_to_dict(self):
        """转换为字典"""
        error = ForgeAIError(
            message="测试错误",
            detail="详情",
            suggestion="建议"
        )
        d = error.to_dict()

        assert d["error_type"] == "ForgeAIError"
        assert d["message"] == "测试错误"
        assert d["detail"] == "详情"
        assert d["suggestion"] == "建议"


class TestConfigurationErrors:
    """测试配置相关异常"""

    def test_missing_config_error(self):
        """缺少配置错误"""
        error = MissingConfigError("LLM_API_KEY")

        assert error.config_key == "LLM_API_KEY"
        assert "LLM_API_KEY" in error.message
        assert ".env" in error.suggestion

    def test_invalid_config_error(self):
        """无效配置错误"""
        error = InvalidConfigError(
            config_key="temperature",
            config_value="abc",
            expected_type="float"
        )

        assert error.config_key == "temperature"
        assert error.expected_type == "float"
        assert "float" in error.suggestion


class TestAPIErrors:
    """测试 API 相关异常"""

    def test_authentication_error(self):
        """认证错误"""
        error = AuthenticationError("openai")

        assert error.provider == "openai"
        assert "认证失败" in error.message

    def test_rate_limit_error(self):
        """速率限制错误"""
        error = RateLimitError("openai", retry_after=60)

        assert error.provider == "openai"
        assert error.retry_after == 60
        assert "60 秒" in error.suggestion

    def test_rate_limit_error_no_retry_after(self):
        """速率限制无重试时间"""
        error = RateLimitError("openai")

        assert error.retry_after is None
        assert "稍后重试" in error.suggestion

    def test_api_connection_error(self):
        """API 连接错误"""
        error = APIConnectionError("openai", base_url="https://api.openai.com")

        assert error.provider == "openai"
        assert error.base_url == "https://api.openai.com"
        assert "无法连接" in error.message

    def test_api_response_error(self):
        """API 响应错误"""
        error = APIResponseError(
            provider="openai",
            status_code=500,
            response_body='{"error": "Internal Server Error"}'
        )

        assert error.status_code == 500
        assert error.response_body is not None

    def test_api_error_to_dict(self):
        """API 错误转换为字典"""
        error = APIError("测试错误", provider="test", status_code=400)
        d = error.to_dict()

        assert d["provider"] == "test"
        assert d["status_code"] == 400


class TestDatabaseErrors:
    """测试数据库相关异常"""

    def test_database_connection_error(self):
        """数据库连接错误"""
        error = DatabaseConnectionError("/path/to/db.sqlite")

        assert error.db_path == "/path/to/db.sqlite"
        assert "无法连接" in error.message

    def test_database_query_error(self):
        """数据库查询错误"""
        error = DatabaseQueryError(
            query="SELECT * FROM nonexistent",
            db_path="/path/to/db.sqlite"
        )

        assert error.query == "SELECT * FROM nonexistent"


class TestValidationErrors:
    """测试验证相关异常"""

    def test_input_validation_error(self):
        """输入验证错误"""
        error = InputValidationError(
            field="chapter",
            value=-1,
            reason="章节号必须为正整数"
        )

        assert error.field == "chapter"
        assert error.value == -1
        assert error.reason == "章节号必须为正整数"

    def test_path_security_error(self):
        """路径安全错误"""
        error = PathSecurityError(
            path="../../../etc/passwd",
            base_dir="/project/data"
        )

        assert error.path == "../../../etc/passwd"
        assert error.base_dir == "/project/data"
        assert "路径遍历" in error.message


class TestTokenExceededError:
    """测试 Token 超出异常"""

    def test_token_exceeded_error(self):
        """Token 超出错误"""
        error = TokenExceededError(
            current_tokens=150000,
            max_tokens=128000
        )

        assert error.current_tokens == 150000
        assert error.max_tokens == 128000
        assert "150000" in error.message


class TestExtractionError:
    """测试提取错误"""

    def test_extraction_error(self):
        """提取错误"""
        error = ExtractionError(
            extraction_type="实体提取",
            reason="文本格式异常"
        )

        assert error.extraction_type == "实体提取"
        assert "实体提取" in error.message


class TestHelperFunctions:
    """测试辅助函数"""

    def test_wrap_exception(self):
        """异常包装"""
        original = ValueError("无效值")
        wrapped = wrap_exception(
            original,
            InputValidationError,
            field="test_field",
            value="invalid",
            reason="验证失败"
        )

        assert isinstance(wrapped, InputValidationError)
        assert wrapped.cause is original
        assert "无效值" in wrapped.detail

    def test_is_recoverable_rate_limit(self):
        """速率限制可恢复"""
        error = RateLimitError("openai")
        assert is_recoverable(error) is True

    def test_is_recoverable_connection_error(self):
        """连接错误可恢复"""
        error = APIConnectionError("openai")
        assert is_recoverable(error) is True

    def test_is_recoverable_config_error(self):
        """配置错误不可恢复"""
        error = MissingConfigError("API_KEY")
        assert is_recoverable(error) is False

    def test_is_recoverable_security_error(self):
        """安全错误不可恢复"""
        error = PathSecurityError("/etc/passwd", "/project")
        assert is_recoverable(error) is False

    def test_get_retry_delay_rate_limit(self):
        """速率限制重试延迟"""
        error = RateLimitError("openai", retry_after=30)
        delay = get_retry_delay(error)

        assert delay == 30.0

    def test_get_retry_delay_connection(self):
        """连接错误重试延迟"""
        error = APIConnectionError("openai")
        delay = get_retry_delay(error)

        assert delay == 5.0

    def test_get_retry_delay_unrecoverable(self):
        """不可恢复错误无重试延迟"""
        error = MissingConfigError("API_KEY")
        delay = get_retry_delay(error)

        assert delay is None


class TestSafeCallDecorator:
    """测试安全调用装饰器"""

    def test_safe_call_success(self):
        """正常调用"""
        @safe_call(default="default")
        def normal_function():
            return "success"

        result = normal_function()
        assert result == "success"

    def test_safe_call_exception(self):
        """异常时返回默认值"""
        @safe_call(default="default")
        def failing_function():
            raise ValueError("error")

        result = failing_function()
        assert result == "default"

    def test_safe_call_with_list_default(self):
        """列表默认值"""
        @safe_call(default=[])
        def failing_function():
            raise RuntimeError("error")

        result = failing_function()
        assert result == []

    def test_safe_call_forgeai_error(self):
        """ForgeAI 错误也返回默认值"""
        @safe_call(default=None)
        def failing_function():
            raise MissingConfigError("API_KEY")

        result = failing_function()
        assert result is None


class TestExceptionHierarchy:
    """测试异常层次结构"""

    def test_inheritance(self):
        """继承关系"""
        # 所有异常都应继承 ForgeAIError
        assert issubclass(ConfigurationError, ForgeAIError)
        assert issubclass(MissingConfigError, ConfigurationError)
        assert issubclass(APIError, ForgeAIError)
        assert issubclass(DatabaseError, ForgeAIError)
        assert issubclass(ValidationError, ForgeAIError)

    def test_catch_base_class(self):
        """捕获基类"""
        errors = [
            MissingConfigError("key"),
            AuthenticationError("provider"),
            DatabaseConnectionError("/path"),
            InputValidationError("field", "value", "reason"),
        ]

        for error in errors:
            assert isinstance(error, ForgeAIError)

    def test_catch_category(self):
        """捕获类别异常"""
        errors = [
            MissingConfigError("key1"),
            InvalidConfigError("key2", "value", "type"),
        ]

        for error in errors:
            assert isinstance(error, ConfigurationError)
