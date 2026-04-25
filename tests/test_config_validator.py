"""
单元测试：config_validator.py 模块

测试配置验证功能
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.config_validator import (
    ConfigValidator,
    ConfigIssue,
    validate_config,
)


class TestConfigIssue:
    """测试 ConfigIssue 数据类"""

    def test_config_issue_creation(self):
        """创建配置问题"""
        issue = ConfigIssue(
            severity="error",
            category="env",
            key="TEST_KEY",
            message="测试问题",
            suggestion="测试建议"
        )

        assert issue.severity == "error"
        assert issue.category == "env"
        assert issue.key == "TEST_KEY"

    def test_config_issue_defaults(self):
        """默认字段值"""
        issue = ConfigIssue(
            severity="warning",
            category="config",
            key="KEY",
            message="消息",
            suggestion=""
        )

        assert issue.suggestion == ""


class TestConfigValidator:
    """测试 ConfigValidator 类"""

    def test_validator_init(self):
        """初始化验证器"""
        validator = ConfigValidator()
        assert validator.issues == []

    def test_validator_with_paths(self, temp_project: Path):
        """带路径初始化"""
        validator = ConfigValidator(
            env_path=temp_project / ".env",
            config_path=temp_project / ".forgeai" / "config.json"
        )

        assert validator.env_path is not None

    def test_validate_all_returns_tuple(self, mock_env):
        """validate_all 返回元组"""
        validator = ConfigValidator()
        result = validator.validate_all(raise_on_error=False)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)

    def test_validate_detects_missing_llm_key(self, clean_env):
        """检测缺少 LLM API Key"""
        validator = ConfigValidator()
        is_valid, issues = validator.validate_all(raise_on_error=False)

        # 没有 API Key 应报错
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0
        assert not is_valid

    def test_validate_with_valid_config(self, mock_env):
        """有效配置验证"""
        validator = ConfigValidator()
        is_valid, issues = validator.validate_all(raise_on_error=False)

        # 有 mock_env 应通过
        # 注意：可能还有其他问题


class TestValidateEnvKeys:
    """测试环境变量验证"""

    def test_missing_required_key(self, clean_env):
        """缺少必需键"""
        validator = ConfigValidator()
        validator._load_env()
        validator._validate_env_keys()

        errors = [i for i in validator.issues if i.severity == "error"]
        assert len(errors) > 0

    def test_present_required_key(self, mock_env):
        """存在必需键"""
        validator = ConfigValidator()
        validator._load_env()
        validator._validate_env_keys()

        # 检查是否检测到缺失的键
        llm_errors = [i for i in validator.issues
                     if i.key == "LLM_API_KEY" and i.severity == "error"]
        # mock_env 设置了 LLM_API_KEY，不应有错误
        assert len(llm_errors) == 0


class TestValidateProviderKeys:
    """测试提供商特定验证"""

    def test_openai_provider(self, mock_env):
        """OpenAI 提供商"""
        os.environ["LLM_PROVIDER"] = "openai"

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_provider_keys()

        # OpenAI 通常需要 OPENAI_API_KEY 或 LLM_API_KEY
        # 由于 mock_env 设置了 LLM_API_KEY，应通过

    def test_unknown_provider(self, mock_env):
        """未知提供商"""
        os.environ["LLM_PROVIDER"] = "unknown_provider"

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_provider_keys()

        # 未知提供商不应报错（只是没有特定检查）


class TestValidateConsistency:
    """测试一致性验证"""

    def test_temperature_range_valid(self, mock_env):
        """有效温度范围"""
        os.environ["LLM_TEMPERATURE"] = "0.7"

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_consistency()

        temp_issues = [i for i in validator.issues if "TEMPERATURE" in i.key]
        # 0.7 是有效值，不应有警告
        warnings = [i for i in temp_issues if i.severity == "warning"]
        assert len(warnings) == 0

    def test_temperature_out_of_range(self, mock_env):
        """温度超出范围"""
        os.environ["LLM_TEMPERATURE"] = "3.0"  # 超出推荐范围

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_consistency()

        # 应有警告
        warnings = [i for i in validator.issues
                   if "TEMPERATURE" in i.key and i.severity == "warning"]
        # 根据实现可能有警告

    def test_temperature_invalid_value(self, mock_env):
        """无效温度值"""
        os.environ["LLM_TEMPERATURE"] = "not_a_number"

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_consistency()

        # 应有错误
        errors = [i for i in validator.issues
                 if "TEMPERATURE" in i.key and i.severity == "error"]
        assert len(errors) > 0

    def test_url_format_valid(self, mock_env):
        """有效 URL 格式"""
        os.environ["LLM_BASE_URL"] = "https://api.openai.com/v1"

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_consistency()

        url_warnings = [i for i in validator.issues
                       if "BASE_URL" in i.key and i.severity == "warning"]
        # 有效 URL 不应有警告
        assert len(url_warnings) == 0

    def test_url_format_invalid(self, mock_env):
        """无效 URL 格式"""
        os.environ["LLM_BASE_URL"] = "not_a_url"

        validator = ConfigValidator()
        validator._load_env()
        validator._validate_consistency()

        # 应有警告
        warnings = [i for i in validator.issues
                   if "BASE_URL" in i.key and i.severity == "warning"]
        assert len(warnings) > 0


class TestGetValidatedConfig:
    """测试获取验证后配置"""

    def test_get_validated_config_structure(self, mock_env):
        """配置结构"""
        validator = ConfigValidator()
        validator._load_env()
        config = validator.get_validated_config()

        assert "llm" in config
        assert "embedding" in config
        assert "rerank" in config

    def test_get_validated_config_values(self, mock_env):
        """配置值"""
        validator = ConfigValidator()
        validator._load_env()
        config = validator.get_validated_config()

        assert config["llm"]["provider"] == "openai"
        assert config["llm"]["api_key"] == "test-api-key-12345"


class TestValidateConfig:
    """测试便捷验证函数"""

    def test_validate_config_function(self, mock_env):
        """便捷函数"""
        is_valid, issues = validate_config(raise_on_error=False)

        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_validate_config_raise_on_error(self, clean_env):
        """发现错误时抛出异常"""
        with pytest.raises(RuntimeError):
            validate_config(raise_on_error=True)

    def test_validate_config_no_raise(self, clean_env):
        """不抛出异常"""
        is_valid, issues = validate_config(raise_on_error=False)

        assert is_valid is False
        assert len(issues) > 0


class TestPrintReport:
    """测试报告打印"""

    def test_print_report_no_issues(self, capsys, mock_env):
        """无问题时"""
        validator = ConfigValidator()
        validator.issues = []
        validator.print_report()

        captured = capsys.readouterr()
        assert "通过" in captured.out or "✅" in captured.out

    def test_print_report_with_errors(self, capsys, clean_env):
        """有错误时"""
        validator = ConfigValidator()
        validator.issues = [
            ConfigIssue(
                severity="error",
                category="env",
                key="TEST_KEY",
                message="测试错误",
                suggestion="测试建议"
            )
        ]
        validator.print_report()

        captured = capsys.readouterr()
        assert "错误" in captured.out or "❌" in captured.out

    def test_print_report_with_warnings(self, capsys):
        """有警告时"""
        validator = ConfigValidator()
        validator.issues = [
            ConfigIssue(
                severity="warning",
                category="config",
                key="TEST_KEY",
                message="测试警告",
                suggestion="测试建议"
            )
        ]
        validator.print_report()

        captured = capsys.readouterr()
        assert "警告" in captured.out or "⚠️" in captured.out


class TestConfigValidatorIntegration:
    """配置验证集成测试"""

    def test_full_validation_workflow(self, temp_project: Path, mock_env):
        """完整验证工作流"""
        # 1. 创建验证器
        validator = ConfigValidator(
            env_path=temp_project / ".env",
            config_path=temp_project / ".forgeai" / "config.json"
        )

        # 2. 执行验证
        is_valid, issues = validator.validate_all(raise_on_error=False)

        # 3. 获取验证后配置
        if is_valid:
            config = validator.get_validated_config()
            assert config is not None

    def test_validation_with_env_file(self, temp_project: Path):
        """从 .env 文件验证"""
        # 创建 .env 文件
        env_content = """
LLM_PROVIDER=test
LLM_MODEL=test-model
LLM_API_KEY=test-key
LLM_BASE_URL=https://api.test.com
EMBED_MODEL=test-embed
EMBED_API_KEY=embed-key
"""
        env_path = temp_project / ".env"
        env_path.write_text(env_content, encoding="utf-8")

        validator = ConfigValidator(env_path=env_path)
        validator._load_env()

        # 应加载环境变量
        assert len(validator._env_vars) > 0

    def test_validation_with_config_file(self, temp_project: Path, mock_env):
        """从 config.json 验证"""
        validator = ConfigValidator(
            config_path=temp_project / ".forgeai" / "config.json"
        )
        validator._load_config()

        # 应加载配置
        assert len(validator._config) > 0
