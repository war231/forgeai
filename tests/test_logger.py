#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志模块测试"""

import pytest
import logging
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from forgeai_modules.logger import (
    ColoredFormatter, setup_logging, get_logger,
    set_log_level, log_function_call, get_logging_status,
    _loggers, _initialized
)


class TestColoredFormatter:
    """彩色格式化器测试"""

    def test_format_basic(self):
        """基本格式化"""
        formatter = ColoredFormatter("[%(levelname)s] %(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="测试消息",
            args=(), exc_info=None
        )

        result = formatter.format(record)

        assert "INFO" in result
        assert "测试消息" in result

    def test_format_with_color(self):
        """带颜色格式化（非 Windows）"""
        formatter = ColoredFormatter("[%(levelname)s] %(message)s")
        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="", lineno=0, msg="错误消息",
            args=(), exc_info=None
        )

        with patch('sys.platform', 'linux'):
            result = formatter.format(record)
            # ERROR 应该有红色 ANSI 代码
            assert "ERROR" in result


class TestSetupLogging:
    """日志配置测试"""

    def test_setup_basic(self, temp_project):
        """基本配置"""
        setup_logging(level="INFO")

        logger = logging.getLogger("forgeai")
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_debug_level(self, temp_project):
        """调试级别"""
        setup_logging(level="DEBUG")

        logger = logging.getLogger("forgeai")
        assert logger.level == logging.DEBUG

    def test_setup_with_file(self, temp_project):
        """带文件日志"""
        log_file = temp_project / ".forgeai" / "logs" / "test.log"

        setup_logging(level="INFO", log_file=str(log_file))

        logger = logging.getLogger("forgeai")
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0

    def test_setup_custom_format(self, temp_project):
        """自定义格式"""
        setup_logging(level="INFO", format_string="%(message)s")

        logger = logging.getLogger("forgeai")
        assert logger.handlers[0].formatter._fmt == "%(message)s"


class TestGetLogger:
    """获取日志器测试"""

    def test_get_logger_basic(self):
        """基本获取"""
        logger = get_logger("test_module")

        assert logger is not None
        assert "test_module" in logger.name

    def test_get_logger_cached(self):
        """缓存日志器"""
        logger1 = get_logger("cached_test")
        logger2 = get_logger("cached_test")

        assert logger1 is logger2

    def test_get_logger_namespace(self):
        """命名空间规范化"""
        logger = get_logger("some.module.name")

        assert logger.name.startswith("forgeai")


class TestSetLogLevel:
    """设置日志级别测试"""

    def test_set_level_debug(self):
        """设置为调试级别"""
        set_log_level("DEBUG")

        logger = logging.getLogger("forgeai")
        assert logger.level == logging.DEBUG

    def test_set_level_warning(self):
        """设置为警告级别"""
        set_log_level("WARNING")

        logger = logging.getLogger("forgeai")
        assert logger.level == logging.WARNING


class TestLogFunctionCall:
    """函数调用日志装饰器测试"""

    def test_decorator_basic(self):
        """基本装饰器"""
        @log_function_call
        def add(a, b):
            return a + b

        result = add(1, 2)

        assert result == 3

    def test_decorator_with_exception(self):
        """异常处理"""
        @log_function_call
        def raise_error():
            raise ValueError("测试错误")

        with pytest.raises(ValueError):
            raise_error()


class TestGetLoggingStatus:
    """日志状态测试"""

    def test_status_basic(self):
        """基本状态"""
        setup_logging(level="INFO")
        status = get_logging_status()

        assert "initialized" in status
        assert "level" in status
        assert "handlers" in status

    def test_status_with_file(self, temp_project):
        """带文件日志状态"""
        log_file = temp_project / ".forgeai" / "logs" / "status.log"
        setup_logging(level="INFO", log_file=str(log_file))

        status = get_logging_status()

        file_handlers = [h for h in status["handlers"] if h["type"] == "FileHandler"]
        assert len(file_handlers) > 0


class TestLoggerOutput:
    """日志输出测试"""

    def test_info_output(self, caplog):
        """信息输出"""
        setup_logging(level="DEBUG")
        logger = get_logger("output_test")

        with caplog.at_level(logging.INFO):
            logger.info("测试信息")

        assert "测试信息" in caplog.text

    def test_warning_output(self, caplog):
        """警告输出"""
        setup_logging(level="DEBUG")
        logger = get_logger("warning_test")

        with caplog.at_level(logging.WARNING):
            logger.warning("测试警告")

        assert "测试警告" in caplog.text

    def test_error_output(self, caplog):
        """错误输出"""
        setup_logging(level="DEBUG")
        logger = get_logger("error_test")

        with caplog.at_level(logging.ERROR):
            logger.error("测试错误")

        assert "测试错误" in caplog.text

    def test_debug_output(self, caplog):
        """调试输出"""
        setup_logging(level="DEBUG")
        logger = get_logger("debug_test")

        with caplog.at_level(logging.DEBUG):
            logger.debug("测试调试")

        assert "测试调试" in caplog.text
