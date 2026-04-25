#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证模块

在启动时验证配置的完整性和一致性：
- 检查必需的环境变量
- 验证配置文件结构
- 检测配置冲突

用法:
    from forgeai_modules.config_validator import validate_config, ConfigValidator

    # 快速验证
    is_valid, issues = validate_config(raise_on_error=False)

    # 详细验证
    validator = ConfigValidator()
    is_valid, issues = validator.validate_all()
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConfigIssue:
    """配置问题"""
    severity: str  # "error" | "warning" | "info"
    category: str  # "env" | "config" | "consistency"
    key: str       # 相关的配置键
    message: str   # 问题描述
    suggestion: str  # 修复建议


class ConfigValidator:
    """配置验证器"""

    # 必需的环境变量
    REQUIRED_ENV_KEYS = {
        "llm": ["LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY"],
        "embedding": ["EMBED_MODEL", "EMBED_API_KEY"],
    }

    # 可选的环境变量
    OPTIONAL_ENV_KEYS = {
        "llm": ["LLM_BASE_URL", "LLM_TEMPERATURE", "LLM_TOP_P", "LLM_MAX_TOKENS",
                "LLM_MAX_CONTEXT_TOKENS", "LLM_RESERVE_TOKENS",
                "LLM_TEMPERATURE_OUTLINE", "LLM_TEMPERATURE_WRITING", "LLM_TEMPERATURE_REVIEW"],
        "embedding": ["EMBED_BASE_URL", "EMBED_DIMENSION"],
        "rerank": ["RERANK_PROVIDER", "RERANK_MODEL", "RERANK_API_KEY", "RERANK_BASE_URL"],
        "logging": ["LOG_LEVEL", "LOG_FILE"],
    }

    # 提供商特定的环境变量
    PROVIDER_ENV_KEYS = {
        "openai": ["OPENAI_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "qwen": ["DASHSCOPE_API_KEY"],
        "ernie": ["ERNIE_API_KEY", "ERNIE_SECRET_KEY"],
        "claude": ["ANTHROPIC_API_KEY"],
        "kimi": [],  # 使用 LLM_API_KEY
    }

    def __init__(
        self,
        env_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        project_root: Optional[Path] = None
    ):
        """
        初始化配置验证器

        Args:
            env_path: .env 文件路径
            config_path: config.json 文件路径
            project_root: 项目根目录
        """
        self.env_path = env_path
        self.config_path = config_path
        self.project_root = project_root
        self.issues: List[ConfigIssue] = []
        self._env_vars: Dict[str, str] = {}
        self._config: Dict[str, Any] = {}

    def validate_all(self, raise_on_error: bool = False) -> Tuple[bool, List[ConfigIssue]]:
        """
        执行所有验证

        Args:
            raise_on_error: 发现错误时是否抛出异常

        Returns:
            (是否有效, 问题列表)
        """
        self.issues = []

        # 加载配置
        self._load_env()
        self._load_config()

        # 执行验证
        self._validate_env_keys()
        self._validate_provider_keys()
        self._validate_config_structure()
        self._validate_consistency()

        # 分类问题
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]

        # 记录结果
        if errors:
            logger.error("配置验证发现 %d 个错误", len(errors))
        if warnings:
            logger.warning("配置验证发现 %d 个警告", len(warnings))
        if not self.issues:
            logger.info("配置验证通过")

        # 抛出异常（可选）
        if errors and raise_on_error:
            msg = "\n".join(f"  - {i.message}" for i in errors)
            raise RuntimeError(f"配置错误:\n{msg}")

        return len(errors) == 0, self.issues

    def _load_env(self) -> None:
        """加载环境变量"""
        # 从 .env 文件加载
        if self.env_path and self.env_path.exists():
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            # 移除行内注释
                            if "#" in value:
                                value = value.split("#")[0].strip()
                            self._env_vars[key] = value
                logger.debug("从 %s 加载了 %d 个环境变量", self.env_path, len(self._env_vars))
            except (OSError, IOError) as e:
                self.issues.append(ConfigIssue(
                    severity="warning",
                    category="env",
                    key=".env",
                    message=f"无法读取 .env 文件: {e}",
                    suggestion="检查文件权限"
                ))

        # 从系统环境变量加载（优先级更高）
        for key in os.environ:
            if key.startswith(("LLM_", "EMBED_", "RERANK_", "LOG_", "OPENAI_", "DEEPSEEK_",
                              "DASHSCOPE_", "ERNIE_", "ANTHROPIC_")):
                self._env_vars[key] = os.environ[key]

    def _load_config(self) -> None:
        """加载配置文件"""
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.debug("从 %s 加载配置", self.config_path)
            except json.JSONDecodeError as e:
                self.issues.append(ConfigIssue(
                    severity="error",
                    category="config",
                    key="config.json",
                    message=f"配置文件 JSON 格式错误: {e}",
                    suggestion="检查 JSON 语法"
                ))
            except (OSError, IOError) as e:
                self.issues.append(ConfigIssue(
                    severity="warning",
                    category="config",
                    key="config.json",
                    message=f"无法读取配置文件: {e}",
                    suggestion="检查文件权限"
                ))

    def _validate_env_keys(self) -> None:
        """验证必需的环境变量"""
        for category, keys in self.REQUIRED_ENV_KEYS.items():
            for key in keys:
                value = self._env_vars.get(key) or os.environ.get(key)
                if not value:
                    self.issues.append(ConfigIssue(
                        severity="error",
                        category="env",
                        key=key,
                        message=f"缺少必需的环境变量: {key}",
                        suggestion=f"在 .env 文件中添加 {key}=<value>"
                    ))

    def _validate_provider_keys(self) -> None:
        """验证提供商特定的环境变量"""
        provider = self._env_vars.get("LLM_PROVIDER", "").lower()

        if provider in self.PROVIDER_ENV_KEYS:
            required = self.PROVIDER_ENV_KEYS[provider]
            for key in required:
                # 检查是否已有 LLM_API_KEY 或提供商特定 key
                has_key = (
                    self._env_vars.get(key) or
                    self._env_vars.get("LLM_API_KEY") or
                    os.environ.get(key)
                )
                if not has_key:
                    self.issues.append(ConfigIssue(
                        severity="warning",
                        category="env",
                        key=key,
                        message=f"提供商 {provider} 通常需要 {key}",
                        suggestion=f"添加 {key} 或确保 LLM_API_KEY 已设置"
                    ))

    def _validate_config_structure(self) -> None:
        """验证配置文件结构"""
        if not self._config:
            # 配置文件不存在，使用默认值
            self.issues.append(ConfigIssue(
                severity="info",
                category="config",
                key="config.json",
                message="配置文件不存在或为空，将使用默认值",
                suggestion="运行 forgeai init 创建配置文件"
            ))
            return

        # 检查必需的配置节
        recommended_sections = ["rag", "llm_params"]
        for section in recommended_sections:
            if section not in self._config:
                self.issues.append(ConfigIssue(
                    severity="warning",
                    category="config",
                    key=section,
                    message=f"配置缺少 {section} 节",
                    suggestion=f"添加 {section} 配置节或运行 forgeai init"
                ))

    def _validate_consistency(self) -> None:
        """验证配置一致性"""
        # 检查温度参数范围
        temp_keys = ["LLM_TEMPERATURE", "LLM_TEMPERATURE_OUTLINE",
                     "LLM_TEMPERATURE_WRITING", "LLM_TEMPERATURE_REVIEW"]
        for key in temp_keys:
            value = self._env_vars.get(key)
            if value:
                try:
                    temp = float(value)
                    if not 0 <= temp <= 2:
                        self.issues.append(ConfigIssue(
                            severity="warning",
                            category="env",
                            key=key,
                            message=f"{key}={temp} 超出推荐范围 [0, 2]",
                            suggestion="将温度设置为 0-2 之间的值"
                        ))
                except ValueError:
                    self.issues.append(ConfigIssue(
                        severity="error",
                        category="env",
                        key=key,
                        message=f"{key}={value} 不是有效的数字",
                        suggestion="设置 {key} 为数字，如 0.7"
                    ))

        # 检查 Base URL 格式
        url_keys = ["LLM_BASE_URL", "EMBED_BASE_URL", "RERANK_BASE_URL"]
        for key in url_keys:
            value = self._env_vars.get(key)
            if value and not value.startswith(("http://", "https://")):
                self.issues.append(ConfigIssue(
                    severity="warning",
                    category="env",
                    key=key,
                    message=f"{key}={value} 不是有效的 URL",
                    suggestion="URL 应以 http:// 或 https:// 开头"
                ))

    def get_validated_config(self) -> Dict[str, Any]:
        """
        获取验证后的配置

        Returns:
            合并了环境变量和配置文件的配置字典
        """
        return {
            "llm": {
                "provider": self._env_vars.get("LLM_PROVIDER", "openai"),
                "model": self._env_vars.get("LLM_MODEL", "gpt-3.5-turbo"),
                "api_key": self._env_vars.get("LLM_API_KEY", ""),
                "base_url": self._env_vars.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            },
            "embedding": {
                "model": self._env_vars.get("EMBED_MODEL", "text-embedding-3-small"),
                "api_key": self._env_vars.get("EMBED_API_KEY", ""),
                "base_url": self._env_vars.get("EMBED_BASE_URL", "https://api.openai.com/v1"),
                "dimension": int(self._env_vars.get("EMBED_DIMENSION", "1536")),
            },
            "rerank": {
                "provider": self._env_vars.get("RERANK_PROVIDER", ""),
                "model": self._env_vars.get("RERANK_MODEL", ""),
                "api_key": self._env_vars.get("RERANK_API_KEY", ""),
                "base_url": self._env_vars.get("RERANK_BASE_URL", ""),
            },
            "llm_params": self._config.get("llm_params", {}),
            "rag": self._config.get("rag", {}),
            "file": self._config,
        }

    def print_report(self) -> None:
        """打印验证报告"""
        print("\n" + "=" * 60)
        print("配置验证报告")
        print("=" * 60)

        if not self.issues:
            print("\n✅ 配置验证通过，无问题")
            return

        # 按严重程度分组
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        infos = [i for i in self.issues if i.severity == "info"]

        if errors:
            print(f"\n❌ 错误 ({len(errors)}):")
            for issue in errors:
                print(f"   [{issue.key}] {issue.message}")
                print(f"   建议: {issue.suggestion}")

        if warnings:
            print(f"\n⚠️  警告 ({len(warnings)}):")
            for issue in warnings:
                print(f"   [{issue.key}] {issue.message}")
                print(f"   建议: {issue.suggestion}")

        if infos:
            print(f"\nℹ️  信息 ({len(infos)}):")
            for issue in infos:
                print(f"   [{issue.key}] {issue.message}")

        print("\n" + "=" * 60)


def validate_config(
    raise_on_error: bool = False,
    env_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
    project_root: Optional[Path] = None
) -> Tuple[bool, List[ConfigIssue]]:
    """
    快速验证配置

    Args:
        raise_on_error: 发现错误时是否抛出异常
        env_path: .env 文件路径
        config_path: config.json 文件路径
        project_root: 项目根目录

    Returns:
        (是否有效, 问题列表)

    示例:
        is_valid, issues = validate_config()
        if not is_valid:
            for issue in issues:
                print(f"{issue.severity}: {issue.message}")
    """
    validator = ConfigValidator(
        env_path=env_path,
        config_path=config_path,
        project_root=project_root
    )
    return validator.validate_all(raise_on_error=raise_on_error)


if __name__ == "__main__":
    # 测试配置验证
    print("=" * 60)
    print("配置验证器测试")
    print("=" * 60)

    validator = ConfigValidator()
    is_valid, issues = validator.validate_all(raise_on_error=False)
    validator.print_report()

    print(f"\n验证结果: {'通过' if is_valid else '失败'}")
