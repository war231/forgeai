#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量加载器

支持从 .env 文件加载配置，兼容 ForgeAI 的配置格式：
- LLM_PROVIDER: LLM 服务商标识（kimi/openai/deepseek等，用于针对性处理）
- LLM_BASE_URL: LLM API 端点 URL
- LLM_MODEL: 模型名称
- LLM_API_KEY: API 密钥
- LLM_TEMPERATURE: 默认温度参数
- LLM_TOP_P: 默认核采样参数
- LLM_MAX_TOKENS: 默认最大输出 tokens
- LLM_TEMPERATURE_OUTLINE: 大纲环节温度（严谨）
- LLM_TEMPERATURE_WRITING: 正文环节温度（发散）
- LLM_TEMPERATURE_REVIEW: 审查环节温度（严谨）
- EMBED_BASE_URL: Embedding 模型端点
- EMBED_MODEL: Embedding 模型名称
- EMBED_API_KEY: Embedding API 密钥
- RERANK_BASE_URL: Reranker 模型端点
- RERANK_MODEL: Reranker 模型名称
- RERANK_API_KEY: Reranker API 密钥
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

# 延迟导入 logger 以避免循环导入
_logger = None

def _get_logger():
    """延迟获取 logger"""
    global _logger
    if _logger is None:
        from .logger import get_logger
        _logger = get_logger(__name__)
    return _logger


def load_env_file(env_path: Optional[Path] = None) -> Dict[str, str]:
    """
    加载 .env 文件
    
    Args:
        env_path: .env 文件路径，默认为当前目录或项目根目录
    
    Returns:
        环境变量字典
    """
    if env_path is None:
        # 尝试多个可能的位置
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).parent.parent.parent.parent.parent / ".env",  # 项目根目录
        ]
        for candidate in candidates:
            if candidate.exists():
                env_path = candidate
                break
    
    if env_path is None or not env_path.exists():
        return {}
    
    env_vars = {}
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith("#"):
                    continue
                
                # 解析 KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除行内注释（# 后的内容）
                    if "#" in value:
                        value = value.split("#")[0].strip()
                    
                    # 移除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
    except Exception as e:
        logger = _get_logger()
        logger.warning("加载 .env 文件失败: %s", e)
    
    return env_vars


def get_llm_config() -> Dict[str, Any]:
    """
    获取 LLM 配置（自动从 .env 或环境变量读取）
    
    Returns:
        {
            "provider": "kimi",  # 服务商标识（用于针对性处理）
            "model": "Kimi-K2.5",
            "api_key": "pk-xxx",
            "base_url": "https://modelservice.jdcloud.com/coding/openai/v1"
        }
    """
    # 先加载 .env 文件
    env_vars = load_env_file()
    
    # 优先从环境变量读取，其次从 .env 文件读取
    llm_provider = os.getenv("LLM_PROVIDER") or env_vars.get("LLM_PROVIDER") or "openai"
    llm_base_url = os.getenv("LLM_BASE_URL") or env_vars.get("LLM_BASE_URL")
    llm_model = os.getenv("LLM_MODEL") or env_vars.get("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY") or env_vars.get("LLM_API_KEY")
    
    # 如果没有配置，使用默认值
    if not llm_base_url:
        llm_base_url = "https://api.openai.com/v1"
    if not llm_model:
        llm_model = "gpt-3.5-turbo"
    
    return {
        "provider": llm_provider,  # 服务商标识（kimi/openai/deepseek等）
        "model": llm_model,
        "api_key": llm_api_key,
        "base_url": llm_base_url,
    }


def get_embed_config() -> Dict[str, Any]:
    """
    获取 Embedding 配置
    
    Returns:
        {
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "Qwen/Qwen3-Embedding-8B",
            "api_key": "sk-xxx"
        }
    """
    env_vars = load_env_file()
    
    embed_base_url = os.getenv("EMBED_BASE_URL") or env_vars.get("EMBED_BASE_URL")
    embed_model = os.getenv("EMBED_MODEL") or env_vars.get("EMBED_MODEL")
    embed_api_key = os.getenv("EMBED_API_KEY") or env_vars.get("EMBED_API_KEY")
    
    return {
        "base_url": embed_base_url,
        "model": embed_model,
        "api_key": embed_api_key,
    }


def get_rerank_config() -> Dict[str, Any]:
    """
    获取 Reranker 配置
    
    Returns:
        {
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "Qwen/Qwen3-Reranker-8B",
            "api_key": "sk-xxx"
        }
    """
    env_vars = load_env_file()
    
    rerank_base_url = os.getenv("RERANK_BASE_URL") or env_vars.get("RERANK_BASE_URL")
    rerank_model = os.getenv("RERANK_MODEL") or env_vars.get("RERANK_MODEL")
    rerank_api_key = os.getenv("RERANK_API_KEY") or env_vars.get("RERANK_API_KEY")
    
    return {
        "base_url": rerank_base_url,
        "model": rerank_model,
        "api_key": rerank_api_key,
    }


def get_llm_params() -> Dict[str, Any]:
    """
    获取 LLM 创作参数配置
    
    Returns:
        {
            "default": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096},
            "outline": {"temperature": 0.4},  # 大纲：严谨
            "writing": {"temperature": 1.0},  # 正文：发散
            "review": {"temperature": 0.3},   # 审查：严谨
        }
    """
    env_vars = load_env_file()
    
    # 全局默认参数
    default_temperature = float(os.getenv("LLM_TEMPERATURE") or env_vars.get("LLM_TEMPERATURE") or "0.7")
    default_top_p = float(os.getenv("LLM_TOP_P") or env_vars.get("LLM_TOP_P") or "0.9")
    default_max_output_tokens = int(os.getenv("LLM_MAX_OUTPUT_TOKENS") or env_vars.get("LLM_MAX_OUTPUT_TOKENS") or "4096")
    
    # 环节特定参数
    outline_temperature = float(os.getenv("LLM_TEMPERATURE_OUTLINE") or env_vars.get("LLM_TEMPERATURE_OUTLINE") or "0.4")
    writing_temperature = float(os.getenv("LLM_TEMPERATURE_WRITING") or env_vars.get("LLM_TEMPERATURE_WRITING") or "1.0")
    review_temperature = float(os.getenv("LLM_TEMPERATURE_REVIEW") or env_vars.get("LLM_TEMPERATURE_REVIEW") or "0.3")
    
    return {
        "default": {
            "temperature": default_temperature,
            "top_p": default_top_p,
            "max_tokens": default_max_output_tokens,
        },
        "outline": {
            "temperature": outline_temperature,
        },
        "writing": {
            "temperature": writing_temperature,
        },
        "review": {
            "temperature": review_temperature,
        },
    }


def get_token_limits() -> Dict[str, int]:
    """
    获取 Token 限制配置
    
    Returns:
        {
            "max_context_tokens": 128000,  # 最大上下文长度
            "reserve_tokens": 4096,        # 预留 tokens
            "max_input_tokens": 123584,    # 最大输入 tokens（max_context - reserve）
        }
    """
    env_vars = load_env_file()
    
    max_context_tokens = int(os.getenv("LLM_MAX_CONTEXT_TOKENS") or env_vars.get("LLM_MAX_CONTEXT_TOKENS") or "128000")
    reserve_tokens = int(os.getenv("LLM_RESERVE_TOKENS") or env_vars.get("LLM_RESERVE_TOKENS") or "4096")
    
    return {
        "max_context_tokens": max_context_tokens,
        "reserve_tokens": reserve_tokens,
        "max_input_tokens": max_context_tokens - reserve_tokens,
    }


def get_params_for_stage(stage: str = "default") -> Dict[str, Any]:
    """
    获取特定创作环节的参数
    
    Args:
        stage: 创作环节（default/outline/writing/review）
    
    Returns:
        {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096}
    """
    params = get_llm_params()
    
    if stage == "default":
        return params["default"]
    
    # 合并默认参数和环节特定参数
    stage_params = params["default"].copy()
    stage_params.update(params.get(stage, {}))
    
    return stage_params


def get_full_llm_config() -> Dict[str, Any]:
    """
    获取完整的 LLM 配置（合并连接和参数）

    Returns:
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-xxx",
            "base_url": "https://api.openai.com/v1",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 4096,
        }
    """
    llm_config = get_llm_config()
    llm_params = get_llm_params()

    return {
        **llm_config,
        **llm_params["default"],
    }


def get_logging_config() -> Dict[str, Any]:
    """
    获取日志配置

    Returns:
        {
            "level": "INFO",
            "log_file": ".forgeai/logs/forgeai.log"
        }
    """
    env_vars = load_env_file()

    log_level = os.getenv("LOG_LEVEL") or env_vars.get("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE") or env_vars.get("LOG_FILE", "")

    return {
        "level": log_level,
        "log_file": log_file,
    }


def print_config_status():
    """打印配置状态"""
    llm_config = get_llm_config()
    embed_config = get_embed_config()
    rerank_config = get_rerank_config()
    llm_params = get_llm_params()
    token_limits = get_token_limits()
    
    print("=" * 60)
    print("ForgeAI 配置状态")
    print("=" * 60)
    
    print("\n[创作大模型]")
    print(f"  Provider: {llm_config['provider']}")
    print(f"  Base URL: {llm_config['base_url']}")
    print(f"  Model: {llm_config['model']}")
    print(f"  API Key: {'[OK] 已配置' if llm_config['api_key'] else '[FAIL] 未配置'}")
    
    print("\n[Token 限制配置]")
    print(f"  最大上下文: {token_limits['max_context_tokens']:,} tokens")
    print(f"  预留空间: {token_limits['reserve_tokens']:,} tokens")
    print(f"  最大输入: {token_limits['max_input_tokens']:,} tokens")
    
    print("\n[创作参数配置]")
    print(f"  默认温度: {llm_params['default']['temperature']}")
    print(f"  默认Top-P: {llm_params['default']['top_p']}")
    print(f"  默认Max Tokens: {llm_params['default']['max_tokens']}")
    print(f"  大纲温度: {llm_params['outline']['temperature']} (严谨)")
    print(f"  正文温度: {llm_params['writing']['temperature']} (发散)")
    print(f"  审查温度: {llm_params['review']['temperature']} (严谨)")
    
    print("\n[Embedding 模型]")
    print(f"  Base URL: {embed_config['base_url']}")
    print(f"  Model: {embed_config['model']}")
    print(f"  API Key: {'[OK] 已配置' if embed_config['api_key'] else '[FAIL] 未配置'}")
    
    print("\n[Reranker 模型]")
    print(f"  Base URL: {rerank_config['base_url']}")
    print(f"  Model: {rerank_config['model']}")
    print(f"  API Key: {'[OK] 已配置' if rerank_config['api_key'] else '[FAIL] 未配置'}")
    
    print("=" * 60)


if __name__ == "__main__":
    print_config_status()
