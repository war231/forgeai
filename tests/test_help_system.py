#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试帮助系统
"""

import pytest
from io import StringIO
from unittest.mock import patch

from forgeai_modules.help_system import CommandHelp, HelpSystem


class TestCommandHelp:
    """测试命令帮助"""

    def test_init(self):
        """测试初始化"""
        help_info = CommandHelp(
            name="test",
            description="Test command",
            usage="forgeai test [选项]",
            examples=["forgeai test --example"],
        )

        assert help_info.name == "test"
        assert help_info.description == "Test command"
        assert help_info.usage == "forgeai test [选项]"
        assert len(help_info.examples) == 1
        assert help_info.options == {}
        assert help_info.see_also == []

    def test_init_with_options(self):
        """测试带选项初始化"""
        help_info = CommandHelp(
            name="test",
            description="Test command",
            usage="forgeai test [选项]",
            examples=["forgeai test"],
            options={"--option": "选项说明"},
            see_also=["other"],
        )

        assert help_info.options == {"--option": "选项说明"}
        assert help_info.see_also == ["other"]

    def test_print(self, capsys):
        """测试打印帮助"""
        help_info = CommandHelp(
            name="test",
            description="Test command description",
            usage="forgeai test [选项]",
            examples=["forgeai test --example"],
            options={"--option": "选项说明"},
        )

        help_info.print()

        captured = capsys.readouterr()
        # 检查输出包含关键信息
        assert "test" in captured.out
        assert "Test command description" in captured.out


class TestHelpSystem:
    """测试帮助系统"""

    def test_commands_exist(self):
        """测试命令存在"""
        assert "init" in HelpSystem.COMMANDS
        assert "generate" in HelpSystem.COMMANDS
        assert "optimize" in HelpSystem.COMMANDS
        assert "validate" in HelpSystem.COMMANDS
        assert "status" in HelpSystem.COMMANDS
        assert "config" in HelpSystem.COMMANDS
        assert "export" in HelpSystem.COMMANDS
        assert "help" in HelpSystem.COMMANDS

    def test_command_help_structure(self):
        """测试命令帮助结构"""
        for cmd_name, cmd_help in HelpSystem.COMMANDS.items():
            assert cmd_help.name == cmd_name
            assert cmd_help.description
            assert cmd_help.usage
            assert isinstance(cmd_help.examples, list)
            assert len(cmd_help.examples) > 0

    def test_show_help_overview(self, capsys):
        """测试显示总体帮助"""
        HelpSystem.show_help()

        captured = capsys.readouterr()
        # 检查输出包含关键信息
        assert "ForgeAI" in captured.out
        assert "可用命令" in captured.out or "命令" in captured.out

    def test_show_help_specific_command(self, capsys):
        """测试显示特定命令帮助"""
        HelpSystem.show_help("generate")

        captured = capsys.readouterr()
        # 检查输出包含命令信息
        assert "generate" in captured.out

    def test_show_help_unknown_command(self, capsys):
        """测试显示未知命令帮助"""
        HelpSystem.show_help("unknown_command")

        captured = capsys.readouterr()
        # 检查输出包含错误信息
        assert "错误" in captured.out or "未知" in captured.out

    def test_show_version(self, capsys):
        """测试显示版本信息"""
        HelpSystem.show_version()

        captured = capsys.readouterr()
        # 检查输出包含版本信息
        assert "v1.1.0" in captured.out or "ForgeAI" in captured.out

    def test_show_quick_start(self, capsys):
        """测试显示快速入门"""
        HelpSystem.show_quick_start()

        captured = capsys.readouterr()
        # 检查输出包含快速入门步骤
        assert "快速入门" in captured.out or "步骤" in captured.out or "init" in captured.out


class TestCommandExamples:
    """测试命令示例"""

    def test_init_examples(self):
        """测试 init 命令示例"""
        cmd = HelpSystem.COMMANDS["init"]
        assert len(cmd.examples) >= 1
        assert all("forgeai init" in ex for ex in cmd.examples)

    def test_generate_examples(self):
        """测试 generate 命令示例"""
        cmd = HelpSystem.COMMANDS["generate"]
        assert len(cmd.examples) >= 1
        assert all("forgeai generate" in ex for ex in cmd.examples)

    def test_config_examples(self):
        """测试 config 命令示例"""
        cmd = HelpSystem.COMMANDS["config"]
        assert len(cmd.examples) >= 1
        assert all("forgeai config" in ex for ex in cmd.examples)


class TestCommandOptions:
    """测试命令选项"""

    def test_generate_options(self):
        """测试 generate 命令选项"""
        cmd = HelpSystem.COMMANDS["generate"]
        assert "--words" in cmd.options
        assert "--context" in cmd.options
        assert "--theme" in cmd.options

    def test_optimize_options(self):
        """测试 optimize 命令选项"""
        cmd = HelpSystem.COMMANDS["optimize"]
        assert "--focus" in cmd.options
        assert "--iterations" in cmd.options

    def test_export_options(self):
        """测试 export 命令选项"""
        cmd = HelpSystem.COMMANDS["export"]
        assert "--output" in cmd.options
        assert "--chapters" in cmd.options


class TestSeeAlso:
    """测试相关命令"""

    def test_generate_see_also(self):
        """测试 generate 相关命令"""
        cmd = HelpSystem.COMMANDS["generate"]
        assert "optimize" in cmd.see_also
        assert "status" in cmd.see_also

    def test_init_see_also(self):
        """测试 init 相关命令"""
        cmd = HelpSystem.COMMANDS["init"]
        assert "config" in cmd.see_also
        assert "generate" in cmd.see_also
