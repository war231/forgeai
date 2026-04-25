"""
测试 CLI Formatter 模块
"""

import pytest
from io import StringIO
from forgeai_modules.cli_formatter import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    print_panel,
    print_header,
    print_step,
    print_list,
    print_dict,
    create_progress,
)


def test_print_success(capsys):
    """测试成功消息打印"""
    print_success("操作成功")
    captured = capsys.readouterr()
    assert "操作成功" in captured.out


def test_print_error(capsys):
    """测试错误消息打印"""
    print_error("操作失败", "请检查配置")
    captured = capsys.readouterr()
    assert "操作失败" in captured.out
    assert "建议" in captured.out


def test_print_warning(capsys):
    """测试警告消息打印"""
    print_warning("这是一个警告")
    captured = capsys.readouterr()
    assert "警告" in captured.out


def test_print_info(capsys):
    """测试信息消息打印"""
    print_info("这是一条信息")
    captured = capsys.readouterr()
    assert "信息" in captured.out


def test_print_table(capsys):
    """测试表格打印"""
    data = [
        {"名称": "项目A", "状态": "完成"},
        {"名称": "项目B", "状态": "进行中"},
    ]
    print_table(data, ["名称", "状态"], title="项目列表")
    captured = capsys.readouterr()
    assert "项目列表" in captured.out
    assert "项目A" in captured.out
    assert "项目B" in captured.out


def test_print_panel(capsys):
    """测试面板打印"""
    print_panel("面板内容", title="面板标题")
    captured = capsys.readouterr()
    assert "面板内容" in captured.out


def test_print_header(capsys):
    """测试标题头打印"""
    print_header("测试标题")
    captured = capsys.readouterr()
    assert "测试标题" in captured.out


def test_print_step(capsys):
    """测试步骤打印"""
    print_step(1, 3, "第一步")
    captured = capsys.readouterr()
    assert "[1/3]" in captured.out
    assert "第一步" in captured.out


def test_print_list(capsys):
    """测试列表打印"""
    print_list(["项目1", "项目2", "项目3"], title="项目列表")
    captured = capsys.readouterr()
    assert "项目列表" in captured.out
    assert "项目1" in captured.out


def test_print_dict(capsys):
    """测试字典打印"""
    print_dict({"版本": "v1.1", "状态": "稳定"}, title="项目信息")
    captured = capsys.readouterr()
    assert "项目信息" in captured.out
    assert "版本" in captured.out
    assert "v1.1" in captured.out


def test_create_progress():
    """测试进度条创建"""
    progress = create_progress("处理中")
    assert progress is not None
    assert hasattr(progress, 'add_task')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
