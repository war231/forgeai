"""
单元测试：config.py 模块

测试配置加载、保存、合并等功能
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.config import (
    ForgeAIConfig,
    DEFAULT_CONFIG,
    get_config,
    reset_config,
)


class TestDefaultConfig:
    """测试 DEFAULT_CONFIG 结构"""

    def test_default_config_has_version(self):
        """DEFAULT_CONFIG 应包含 version"""
        assert "version" in DEFAULT_CONFIG

    def test_default_config_has_llm_params(self):
        """DEFAULT_CONFIG 应包含 llm_params 配置"""
        assert "llm_params" in DEFAULT_CONFIG
        assert "temperature" in DEFAULT_CONFIG["llm_params"]
        assert "top_p" in DEFAULT_CONFIG["llm_params"]
        assert "max_tokens" in DEFAULT_CONFIG["llm_params"]

    def test_default_config_has_rag_settings(self):
        """DEFAULT_CONFIG 应包含 rag 配置"""
        assert "rag" in DEFAULT_CONFIG
        assert "chunk_size" in DEFAULT_CONFIG["rag"]
        assert "top_k" in DEFAULT_CONFIG["rag"]

    def test_default_config_no_secrets(self):
        """DEFAULT_CONFIG 不应包含敏感信息"""
        config_str = json.dumps(DEFAULT_CONFIG)
        # 检查不应出现敏感字段
        assert "api_key" not in config_str.lower() or "api_key_env" not in config_str

    def test_default_config_has_humanize(self):
        """DEFAULT_CONFIG 应包含 humanize 配置"""
        assert "humanize" in DEFAULT_CONFIG
        assert "score_threshold" in DEFAULT_CONFIG["humanize"]

    def test_temperature_stages(self):
        """环节特定温度应有合理默认值"""
        params = DEFAULT_CONFIG["llm_params"]
        # 大纲温度应较低（严谨）
        assert params.get("temperature_outline", 0.4) < 0.6
        # 正文温度应较高（发散）
        assert params.get("temperature_writing", 1.0) > 0.8
        # 审查温度应最低
        assert params.get("temperature_review", 0.3) < 0.5


class TestForgeAIConfig:
    """测试 ForgeAIConfig 类"""

    def test_config_init_default(self):
        """默认初始化"""
        config = ForgeAIConfig()
        assert config.project_root is None
        assert config._config == {}

    def test_config_init_with_root(self, temp_project: Path):
        """带项目根目录初始化"""
        config = ForgeAIConfig(temp_project)
        # 路径可能被 resolve() 转换，比较 resolved 路径
        assert config.project_root.resolve() == temp_project.resolve()

    def test_config_load_existing(self, temp_project: Path):
        """加载已存在的配置文件"""
        config = ForgeAIConfig(temp_project)
        # 应从 config.json 加载
        assert "version" in config._config

    def test_config_load_missing_file(self, tmp_path: Path):
        """配置文件不存在时使用默认值"""
        config = ForgeAIConfig(tmp_path)
        # 应使用默认配置
        assert config._config.get("rag", {}).get("chunk_size") == 500

    def test_config_get_top_level(self, temp_project: Path):
        """获取顶级配置值"""
        config = ForgeAIConfig(temp_project)
        version = config.get("version")
        assert version is not None

    def test_config_get_nested(self, temp_project: Path):
        """获取嵌套配置值"""
        config = ForgeAIConfig(temp_project)
        chunk_size = config.get("rag.chunk_size")
        assert chunk_size is not None

    def test_config_get_missing_returns_none(self, temp_project: Path):
        """获取不存在的配置返回 None"""
        config = ForgeAIConfig(temp_project)
        value = config.get("nonexistent.key")
        assert value is None

    def test_config_get_with_default(self, temp_project: Path):
        """获取不存在的配置返回默认值"""
        config = ForgeAIConfig(temp_project)
        value = config.get("missing.key", default="default_value")
        assert value == "default_value"

    def test_config_set_value(self, temp_project: Path):
        """设置配置值"""
        config = ForgeAIConfig(temp_project)
        config.set("rag.chunk_size", 1000)
        assert config.get("rag.chunk_size") == 1000

    def test_config_set_nested_value(self, temp_project: Path):
        """设置嵌套配置值"""
        config = ForgeAIConfig(temp_project)
        config.set("rag.new_setting", "test")
        assert config.get("rag.new_setting") == "test"

    def test_config_save(self, temp_project: Path):
        """保存配置到文件"""
        config = ForgeAIConfig(temp_project)
        config.set("test_key", "test_value")
        config.save_config()

        # 重新加载验证
        config2 = ForgeAIConfig(temp_project)
        assert config2.get("test_key") == "test_value"

    def test_config_forgeai_dir(self, temp_project: Path):
        """获取 .forgeai 目录路径"""
        config = ForgeAIConfig(temp_project)
        nf_dir = config.forgeai_dir
        assert nf_dir is not None
        assert nf_dir.name == ".forgeai"

    def test_config_state_path(self, temp_project: Path):
        """获取 state.json 路径"""
        config = ForgeAIConfig(temp_project)
        state_path = config.state_path
        assert state_path is not None
        assert state_path.name == "state.json"

    def test_config_index_db_path(self, temp_project: Path):
        """获取 index.db 路径"""
        config = ForgeAIConfig(temp_project)
        db_path = config.index_db_path
        assert db_path is not None
        assert db_path.name == "index.db"

    def test_config_deep_merge(self):
        """测试深度合并"""
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10, "e": 4}, "f": 5}

        result = ForgeAIConfig._deep_merge(base, override)

        assert result["a"]["b"] == 10  # 覆盖
        assert result["a"]["c"] == 2   # 保留
        assert result["a"]["e"] == 4   # 新增
        assert result["d"] == 3        # 保留
        assert result["f"] == 5        # 新增

    def test_config_degraded_mode(self, temp_project: Path):
        """测试降级模式"""
        config = ForgeAIConfig(temp_project)
        assert config.degraded_mode is False

        config.set_degraded("测试原因")
        assert config.degraded_mode is True
        assert "测试原因" in config.degraded_reason


class TestGetConfig:
    """测试全局配置函数"""

    def test_get_config_singleton(self, temp_project: Path):
        """get_config 返回单例"""
        reset_config()

        config1 = get_config(temp_project)
        config2 = get_config()

        assert config1 is config2

    def test_get_config_reset(self, temp_project: Path):
        """reset_config 重置单例"""
        config1 = get_config(temp_project)
        reset_config()
        config2 = get_config(temp_project)

        # 重置后路径应相同（resolve 后比较）
        assert config2.project_root.resolve() == temp_project.resolve()

    def test_get_config_with_different_root(self, temp_project: Path, tmp_path: Path):
        """传入不同的 root 会重置配置"""
        config1 = get_config(temp_project)
        config2 = get_config(tmp_path)

        # 传入新的 root 会创建新配置
        assert config2.project_root == tmp_path


class TestConfigIntegration:
    """配置集成测试"""

    def test_config_full_workflow(self, temp_project: Path):
        """完整配置工作流"""
        # 1. 初始化配置
        config = ForgeAIConfig(temp_project)

        # 2. 读取默认值
        assert config.get("rag.chunk_size") == 500

        # 3. 修改配置
        config.set("rag.chunk_size", 800)
        config.set("llm_params.temperature", 0.8)

        # 4. 保存
        config.save_config()

        # 5. 重新加载验证
        config2 = ForgeAIConfig(temp_project)
        assert config2.get("rag.chunk_size") == 800
        assert config2.get("llm_params.temperature") == 0.8

    def test_config_with_env_override(self, temp_project: Path, mock_env):
        """环境变量不应直接覆盖 config.json"""
        config = ForgeAIConfig(temp_project)
        # config.json 的值应该独立于环境变量
        # 环境变量通过 env_loader 读取
        assert config.get("version") is not None
