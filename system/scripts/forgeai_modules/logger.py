#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志模块

提供统一的日志接口，支持：
- 控制台彩色输出
- 可选文件日志
- 日志级别配置
- 模块化日志器

用法:
    from forgeai_modules.logger import get_logger
    logger = get_logger(__name__)
    logger.info("处理开始")
    logger.warning("配置缺失，使用默认值")
    logger.error("API 调用失败")
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# 日志器缓存
_loggers: dict = {}

# 是否已初始化
_initialized: bool = False


class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # Windows 兼容：检查是否支持 ANSI 颜色
        if sys.platform == "win32":
            # Windows Terminal 或启用了 ANSI 的终端
            if not os.environ.get("WT_SESSION") and not os.environ.get("TERM"):
                # 不支持颜色，直接返回
                return super().format(record)

        color = self.COLORS.get(record.levelname, "")
        if color:
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    配置 forgeai 根日志器

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 可选的日志文件路径
        format_string: 自定义格式字符串

    示例:
        setup_logging(level="DEBUG", log_file=".forgeai/logs/forgeai.log")
    """
    global _initialized

    root_logger = logging.getLogger("forgeai")

    # 设置日志级别
    level_value = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(level_value)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 默认格式
    if format_string is None:
        format_string = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter(format_string, datefmt="%H:%M:%S"))
    root_logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError):
            # 无法创建日志文件，仅使用控制台
            root_logger.warning("无法创建日志文件: %s", log_file)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    获取模块日志器

    Args:
        name: 模块名（通常传入 __name__）

    Returns:
        配置好的日志器实例

    示例:
        logger = get_logger(__name__)
        logger.info("处理开始")
    """
    global _initialized

    # 规范化名称到 forgeai 命名空间
    if not name.startswith("forgeai"):
        # 提取模块名
        if "." in name:
            module_name = name.split(".")[-1]
        else:
            module_name = name
        name = f"forgeai.{module_name}"

    # 使用缓存的日志器
    if name not in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger

        # 首次获取日志器时自动初始化（如果尚未初始化）
        if not _initialized:
            # 从环境变量读取配置
            log_level = os.environ.get("LOG_LEVEL", "INFO")
            log_file = os.environ.get("LOG_FILE", "")
            setup_logging(level=log_level, log_file=log_file if log_file else None)

    return _loggers[name]


def set_log_level(level: str) -> None:
    """
    动态设置日志级别

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger("forgeai")
    level_value = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(level_value)


def log_function_call(func):
    """
    函数调用日志装饰器

    用于调试时记录函数进入和退出

    示例:
        @log_function_call
        def process_text(text: str) -> str:
            return text.upper()
    """
    logger = get_logger(func.__module__)

    def wrapper(*args, **kwargs):
        logger.debug("进入 %s()", func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.debug("退出 %s()", func.__name__)
            return result
        except Exception as e:
            logger.error("%s() 发生错误: %s", func.__name__, e)
            raise

    return wrapper


def get_logging_status() -> dict:
    """
    获取日志系统状态

    Returns:
        包含日志配置信息的字典
    """
    root_logger = logging.getLogger("forgeai")

    handlers_info = []
    for handler in root_logger.handlers:
        handler_info = {
            "type": type(handler).__name__,
            "level": logging.getLevelName(handler.level),
        }
        if isinstance(handler, logging.FileHandler):
            handler_info["file"] = handler.baseFilename
        handlers_info.append(handler_info)

    return {
        "initialized": _initialized,
        "level": logging.getLevelName(root_logger.level),
        "handlers": handlers_info,
        "loggers": list(_loggers.keys()),
    }


if __name__ == "__main__":
    # 测试日志模块
    print("=" * 60)
    print("日志模块测试")
    print("=" * 60)

    # 设置调试级别
    setup_logging(level="DEBUG")

    logger = get_logger("test")
    logger.debug("这是一条调试消息")
    logger.info("这是一条信息消息")
    logger.warning("这是一条警告消息")
    logger.error("这是一条错误消息")

    # 显示状态
    print("\n日志系统状态:")
    import json
    print(json.dumps(get_logging_status(), indent=2, ensure_ascii=False))
