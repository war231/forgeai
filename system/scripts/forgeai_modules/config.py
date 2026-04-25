#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

管理 ForgeAI 项目的配置：
- 项目根目录解析
- API 配置（Embedding / LLM）
- 运行模式（标准 / 降级）
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


DEFAULT_CONFIG = {
    "version": "1.0.0",
    # LLM 行为参数（API 配置在 .env 中）
    "llm_params": {
        "temperature": 0.7,          # 默认温度
        "top_p": 0.9,                # 核采样
        "max_tokens": 4096,          # 最大输出 tokens
        "retry_attempts": 3,         # 重试次数
        "timeout": 60,               # 请求超时（秒）
        # 环节特定温度
        "temperature_outline": 0.4,  # 大纲：严谨
        "temperature_writing": 1.0,  # 正文：发散
        "temperature_review": 0.3,   # 审查：严谨
    },
    # Embedding 参数（API 配置在 .env 中）
    "embedding_params": {
        "batch_size": 32,            # 批处理大小
        "dimension": 1536,           # 向量维度
    },
    # Rerank 参数
    "rerank_params": {
        "top_n": 5,                  # 重排后保留数
    },
    "rag": {
        "chunk_size": 500,           # 字符数
        "chunk_overlap": 100,
        "top_k": 10,                 # 召回数量
        "bm25_weight": 0.3,          # BM25 权重
        "vector_weight": 0.7,        # 向量权重
        # RAG 检索缓存配置
        "cache_enabled": True,
        "cache_ttl": 300,            # 5分钟
        "cache_max_size": 1000,      # 最大缓存条目数
    },
    "humanize": {
        # 实体提取缓存配置
        "entity_cache": {
            "enabled": True,
            "ttl": 300,  # 5分钟
        },
        "max_rounds": 3,             # 进化竞争最大轮数
        "score_threshold": 0.6,      # "更像人"的阈值
        "challenger_count": 2,       # 每轮生成挑战者数量
    },
    "index": {
        "auto_index": True,          # 写完章节后自动索引
        "track_entities": True,      # 自动追踪实体
        "track_reading_power": True, # 追踪追读力
    },
}


class ForgeAIConfig:
    """ForgeAI 配置管理器"""

    def __init__(self, project_root: Optional[Path | str] = None):
        self._project_root: Optional[Path] = None
        self._config: Dict[str, Any] = {}
        self._degraded_mode: bool = False
        self._degraded_reason: str = ""

        if project_root:
            self.set_project_root(project_root)

    def set_project_root(self, root: Path | str) -> None:
        """设置项目根目录"""
        root = Path(root).resolve()
        # 向上查找包含 .forgeai/ 的目录
        if (root / ".forgeai").is_dir():
            self._project_root = root
        elif (root / ".novelkit").is_dir():
            # 兼容旧版项目结构
            self._project_root = root
        else:
            self._project_root = root
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self._project_root:
            self._config = DEFAULT_CONFIG.copy()
            return

        config_path = self._project_root / ".forgeai" / "config.json"
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                self._config = self._deep_merge(DEFAULT_CONFIG.copy(), user_config)
            except (json.JSONDecodeError, OSError):
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """深度合并字典"""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                base[k] = ForgeAIConfig._deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    def save_config(self) -> None:
        """保存配置到文件"""
        if not self._project_root:
            return
        config_dir = self._project_root / ".forgeai"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    @property
    def project_root(self) -> Optional[Path]:
        return self._project_root

    @property
    def forgeai_dir(self) -> Optional[Path]:
        if not self._project_root:
            return None
        d = self._project_root / ".forgeai"
        if d.is_dir():
            return d
        # 兼容旧版项目结构
        d2 = self._project_root / ".novelkit"
        if d2.is_dir():
            return d2
        return None

    @property
    def state_path(self) -> Optional[Path]:
        if not self._project_root:
            return None
        return self._project_root / ".forgeai" / "state.json"

    @property
    def index_db_path(self) -> Optional[Path]:
        if not self._project_root:
            return None
        return self._project_root / ".forgeai" / "index.db"

    @property
    def vector_db_path(self) -> Optional[Path]:
        if not self._project_root:
            return None
        return self._project_root / ".forgeai" / "vectors.db"

    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值，支持点号路径：'embedding.provider'"""
        keys = key_path.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any) -> None:
        """设置配置值"""
        keys = key_path.split(".")
        val = self._config
        for k in keys[:-1]:
            if k not in val or not isinstance(val[k], dict):
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value

    @property
    def degraded_mode(self) -> bool:
        return self._degraded_mode

    @property
    def degraded_reason(self) -> str:
        return self._degraded_reason

    def set_degraded(self, reason: str) -> None:
        """进入降级模式"""
        self._degraded_mode = True
        self._degraded_reason = reason

    def get_api_key(self, purpose: str = "embedding") -> Optional[str]:
        """获取 API Key"""
        env_var = self.get(f"{purpose}.api_key_env", f"{purpose.upper()}_API_KEY")
        key = os.environ.get(env_var, "")
        return key if key else None

    def get_base_url(self, purpose: str = "embedding") -> Optional[str]:
        """获取 API Base URL"""
        url = self.get(f"{purpose}.base_url")
        return url

    def to_dict(self) -> Dict[str, Any]:
        return self._config.copy()


# 全局单例
_config_instance: Optional[ForgeAIConfig] = None


def get_config(project_root: Optional[Path | str] = None) -> ForgeAIConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None or project_root is not None:
        _config_instance = ForgeAIConfig(project_root)
    return _config_instance


def reset_config() -> None:
    """重置全局配置（主要用于测试）"""
    global _config_instance
    _config_instance = None
