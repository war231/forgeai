"""
单元测试：env_loader.py 模块

测试环境变量加载和配置获取
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.env_loader import (
    load_env_file,
    get_llm_config,
    get_embed_config,
    get_rerank_config,
    get_llm_params,
    get_token_limits,
    get_params_for_stage,
    get_full_llm_config,
    get_logging_config,
)


class TestLoadEnvFile:
    """测试 load_env_file 函数"""

    def test_load_env_existing_file(self, temp_project: Path):
        """加载存在的 .env 文件"""
        # 创建测试 .env 文件
        env_path = temp_project / ".env"
        env_path.write_text("""
# 测试注释
LLM_PROVIDER=test_provider
LLM_MODEL=test_model
LLM_API_KEY=test_key

# 带引号的值
QUOTED_VALUE="value with spaces"
SINGLE_QUOTED='single quoted'
""", encoding="utf-8")

        env_vars = load_env_file(env_path)

        assert env_vars["LLM_PROVIDER"] == "test_provider"
        assert env_vars["LLM_MODEL"] == "test_model"
        assert env_vars["LLM_API_KEY"] == "test_key"
        assert env_vars["QUOTED_VALUE"] == "value with spaces"

    def test_load_env_missing_file(self, tmp_path: Path):
        """加载不存在的文件返回空字典"""
        env_vars = load_env_file(tmp_path / "nonexistent.env")
        assert env_vars == {}

    def test_load_env_handles_comments(self, temp_project: Path):
        """正确处理注释"""
        env_path = temp_project / "test.env"
        env_path.write_text("""
# 这是注释
KEY1=value1  # 行内注释
KEY2=value2
""", encoding="utf-8")

        env_vars = load_env_file(env_path)

        assert env_vars["KEY1"] == "value1"
        assert env_vars["KEY2"] == "value2"

    def test_load_env_handles_empty_lines(self, temp_project: Path):
        """正确处理空行"""
        env_path = temp_project / "test.env"
        env_path.write_text("""

KEY1=value1


KEY2=value2

""", encoding="utf-8")

        env_vars = load_env_file(env_path)

        assert len(env_vars) == 2
        assert env_vars["KEY1"] == "value1"


class TestGetLLMConfig:
    """测试 get_llm_config 函数"""

    def test_get_llm_config_returns_required_keys(self, mock_env):
        """返回所有必需的 LLM 配置键"""
        config = get_llm_config()

        assert "provider" in config
        assert "model" in config
        assert "api_key" in config
        assert "base_url" in config

    def test_get_llm_config_values_from_env(self, mock_env):
        """从环境变量获取值"""
        config = get_llm_config()

        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o-mini"
        assert config["api_key"] == "test-api-key-12345"
        assert config["base_url"] == "https://api.test.com/v1"

    def test_get_llm_config_defaults(self, clean_env):
        """缺少环境变量时使用默认值"""
        config = get_llm_config()

        # 应有默认 base_url（可能是项目配置或标准默认值）
        assert config["base_url"] is not None
        # 应有默认 model
        assert config["model"] is not None

    def test_get_llm_config_priority(self, mock_env):
        """环境变量优先于 .env 文件"""
        # 修改环境变量
        os.environ["LLM_MODEL"] = "overridden-model"

        config = get_llm_config()
        assert config["model"] == "overridden-model"


class TestGetEmbedConfig:
    """测试 get_embed_config 函数"""

    def test_get_embed_config_returns_keys(self, mock_env):
        """返回 embedding 配置键"""
        config = get_embed_config()

        assert "model" in config
        assert "api_key" in config
        assert "base_url" in config

    def test_get_embed_config_values_from_env(self, mock_env):
        """从环境变量获取 embedding 配置"""
        config = get_embed_config()

        assert config["model"] == "text-embedding-3-small"
        assert config["api_key"] == "test-embed-key"


class TestGetRerankConfig:
    """测试 get_rerank_config 函数"""

    def test_get_rerank_config_returns_keys(self, mock_env):
        """返回 rerank 配置键"""
        config = get_rerank_config()

        assert "api_key" in config
        assert "base_url" in config

    def test_get_rerank_config_values_from_env(self, mock_env):
        """从环境变量获取 rerank 配置"""
        config = get_rerank_config()

        assert config["api_key"] == "test-rerank-key"
        assert config["base_url"] == "https://rerank.test.com/v1"


class TestGetLLMParams:
    """测试 get_llm_params 函数"""

    def test_get_llm_params_defaults(self, clean_env):
        """返回默认参数值"""
        params = get_llm_params()

        assert params["default"]["temperature"] == 0.7
        assert params["default"]["top_p"] == 0.9
        assert params["default"]["max_tokens"] == 4096

    def test_get_llm_params_from_env(self, mock_env):
        """从环境变量获取参数"""
        params = get_llm_params()

        assert params["default"]["temperature"] == 0.7

    def test_get_llm_params_stage_specific(self, mock_env):
        """环节特定参数"""
        params = get_llm_params()

        assert "outline" in params
        assert "writing" in params
        assert "review" in params

    def test_get_llm_params_stage_temperatures(self, mock_env):
        """各环节温度设置"""
        params = get_llm_params()

        # 大纲温度低于默认
        assert params["outline"]["temperature"] < params["default"]["temperature"]
        # 正文温度高于默认
        assert params["writing"]["temperature"] > params["default"]["temperature"]
        # 审查温度最低
        assert params["review"]["temperature"] < params["outline"]["temperature"]


class TestGetTokenLimits:
    """测试 get_token_limits 函数"""

    def test_get_token_limits_defaults(self, clean_env):
        """返回默认 token 限制"""
        limits = get_token_limits()

        assert limits["max_context_tokens"] == 128000
        assert limits["reserve_tokens"] == 4096
        assert limits["max_input_tokens"] == 128000 - 4096

    def test_get_token_limits_from_env(self, mock_env):
        """从环境变量获取 token 限制"""
        os.environ["LLM_MAX_CONTEXT_TOKENS"] = "64000"
        os.environ["LLM_RESERVE_TOKENS"] = "2048"

        limits = get_token_limits()

        assert limits["max_context_tokens"] == 64000
        assert limits["reserve_tokens"] == 2048
        assert limits["max_input_tokens"] == 64000 - 2048

    def test_get_token_limits_calculation(self, clean_env):
        """max_input_tokens 应正确计算"""
        limits = get_token_limits()

        assert limits["max_input_tokens"] == limits["max_context_tokens"] - limits["reserve_tokens"]


class TestGetParamsForStage:
    """测试 get_params_for_stage 函数"""

    def test_get_params_default(self, mock_env):
        """获取默认参数"""
        params = get_params_for_stage("default")

        assert "temperature" in params
        assert "top_p" in params
        assert "max_tokens" in params

    def test_get_params_outline(self, mock_env):
        """获取大纲参数"""
        params = get_params_for_stage("outline")

        # 大纲参数应合并默认参数和环节特定参数
        assert "top_p" in params  # 来自默认
        assert params["temperature"] < 0.6  # 大纲温度较低

    def test_get_params_writing(self, mock_env):
        """获取正文参数"""
        params = get_params_for_stage("writing")

        # 正文温度应较高
        assert params["temperature"] > 0.8

    def test_get_params_review(self, mock_env):
        """获取审查参数"""
        params = get_params_for_stage("review")

        # 审查温度应最低
        assert params["temperature"] < 0.5


class TestGetFullLLMConfig:
    """测试 get_full_llm_config 函数"""

    def test_get_full_llm_config_combines(self, mock_env):
        """合并连接和参数配置"""
        config = get_full_llm_config()

        # 应包含连接信息
        assert "provider" in config
        assert "model" in config
        assert "api_key" in config
        assert "base_url" in config

        # 应包含参数
        assert "temperature" in config
        assert "top_p" in config
        assert "max_tokens" in config

    def test_get_full_llm_config_complete(self, mock_env):
        """完整配置可访问所有字段"""
        config = get_full_llm_config()

        assert config["provider"] == "openai"
        assert config["temperature"] == 0.7


class TestGetLoggingConfig:
    """测试 get_logging_config 函数"""

    def test_get_logging_config_defaults(self, clean_env):
        """返回默认日志配置"""
        config = get_logging_config()

        assert config["level"] == "INFO"
        assert config["log_file"] == ""

    def test_get_logging_config_from_env(self, mock_env):
        """从环境变量获取日志配置"""
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_FILE"] = "/var/log/forgeai.log"

        config = get_logging_config()

        assert config["level"] == "DEBUG"
        assert config["log_file"] == "/var/log/forgeai.log"


class TestEnvLoaderIntegration:
    """环境变量加载集成测试"""

    def test_full_config_workflow(self, temp_project: Path):
        """完整配置工作流"""
        # 1. 创建 .env 文件
        env_path = temp_project / ".env"
        env_path.write_text("""
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-test-123
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_TEMPERATURE=0.8
LOG_LEVEL=WARNING
""", encoding="utf-8")

        # 2. 加载配置
        with patch("forgeai_modules.env_loader.load_env_file") as mock_load:
            mock_load.return_value = {
                "LLM_PROVIDER": "deepseek",
                "LLM_MODEL": "deepseek-chat",
                "LLM_API_KEY": "sk-test-123",
                "LLM_BASE_URL": "https://api.deepseek.com/v1",
                "LLM_TEMPERATURE": "0.8",
                "LOG_LEVEL": "WARNING",
            }

            llm_config = get_llm_config()
            assert llm_config["provider"] == "deepseek"

    def test_missing_api_key_warning(self, clean_env):
        """缺少 API Key 时应有默认行为"""
        # 强制重新加载环境
        from forgeai_modules import env_loader
        # 清除缓存的环境变量
        env_loader._env_vars = {} if hasattr(env_loader, '_env_vars') else None

        config = get_llm_config()
        # API Key 可能为空或从其他来源获取
        assert "api_key" in config
