#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试进度显示模块
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from forgeai_modules.progress_display import (
    ProgressTracker,
    MultiProgressTracker,
    StatusDisplay,
    ChapterProgress,
    create_spinner,
    show_progress,
    show_spinner,
)


class TestProgressTracker:
    """测试进度跟踪器"""

    def test_init(self):
        """测试初始化"""
        tracker = ProgressTracker(total=10, description="测试")
        
        assert tracker.total == 10
        assert tracker.description == "测试"
        assert tracker.current == 0
        assert tracker.progress is None

    def test_start_and_complete(self):
        """测试启动和完成"""
        tracker = ProgressTracker(total=10)
        
        tracker.start()
        assert tracker.progress is not None
        assert tracker.task_id is not None
        
        tracker.complete()
        # 进度条已停止

    def test_update(self):
        """测试更新进度"""
        tracker = ProgressTracker(total=10)
        tracker.start()
        
        tracker.update(1)
        assert tracker.current == 1
        
        tracker.update(5)
        assert tracker.current == 6
        
        tracker.complete()

    def test_update_with_description(self):
        """测试带描述更新"""
        tracker = ProgressTracker(total=10)
        tracker.start()
        
        tracker.update(1, description="新描述")
        assert tracker.current == 1
        
        tracker.complete()

    def test_context_manager(self):
        """测试上下文管理器"""
        with ProgressTracker(total=10) as tracker:
            assert tracker.progress is not None
            tracker.update(1)
            assert tracker.current == 1
        # 退出上下文后自动完成


class TestMultiProgressTracker:
    """测试多任务进度跟踪器"""

    def test_init(self):
        """测试初始化"""
        tasks = [
            {"name": "task1", "total": 10, "description": "任务1"},
            {"name": "task2", "total": 20, "description": "任务2"},
        ]
        
        tracker = MultiProgressTracker(tasks)
        
        assert len(tracker.tasks) == 2
        assert tracker.progress is None

    def test_start_and_complete(self):
        """测试启动和完成"""
        tasks = [
            {"name": "task1", "total": 10},
            {"name": "task2", "total": 20},
        ]
        
        tracker = MultiProgressTracker(tasks)
        tracker.start()
        
        assert tracker.progress is not None
        assert len(tracker.task_ids) == 2
        
        tracker.complete()

    def test_update(self):
        """测试更新任务"""
        tasks = [
            {"name": "task1", "total": 10},
            {"name": "task2", "total": 20},
        ]
        
        tracker = MultiProgressTracker(tasks)
        tracker.start()
        
        tracker.update("task1", advance=1)
        tracker.update("task2", advance=5)
        
        tracker.complete()

    def test_context_manager(self):
        """测试上下文管理器"""
        tasks = [{"name": "task1", "total": 10}]
        
        with MultiProgressTracker(tasks) as tracker:
            assert tracker.progress is not None
            tracker.update("task1", advance=1)


class TestStatusDisplay:
    """测试状态显示器"""

    def test_init(self):
        """测试初始化"""
        display = StatusDisplay("测试状态")
        
        assert display.title == "测试状态"
        assert display.status_data == {}

    def test_update(self):
        """测试更新状态"""
        display = StatusDisplay()
        
        display.update("key1", "value1")
        assert display.status_data["key1"] == "value1"
        
        display.update("key2", 123)
        assert display.status_data["key2"] == 123

    def test_display(self, capsys):
        """测试显示状态"""
        display = StatusDisplay("项目状态")
        display.update("总章节", 10)
        display.update("已完成", 5)
        
        display.display()
        
        captured = capsys.readouterr()
        # 检查输出包含状态信息
        assert "项目状态" in captured.out or "总章节" in captured.out


class TestChapterProgress:
    """测试章节进度"""

    def test_init(self):
        """测试初始化"""
        progress = ChapterProgress(total_chapters=10)
        
        assert progress.total_chapters == 10
        assert progress.completed_chapters == []
        assert progress.current_chapter is None

    def test_start_chapter(self, capsys):
        """测试开始章节"""
        progress = ChapterProgress(5)
        progress.start_chapter(1)
        
        assert progress.current_chapter == 1
        
        captured = capsys.readouterr()
        assert "章节" in captured.out

    def test_complete_chapter_success(self, capsys):
        """测试完成章节（成功）"""
        progress = ChapterProgress(5)
        progress.start_chapter(1)
        progress.complete_chapter(1, success=True)
        
        assert 1 in progress.completed_chapters
        assert progress.current_chapter is None
        
        captured = capsys.readouterr()
        assert "完成" in captured.out

    def test_complete_chapter_failure(self, capsys):
        """测试完成章节（失败）"""
        progress = ChapterProgress(5)
        progress.start_chapter(1)
        progress.complete_chapter(1, success=False)
        
        assert 1 not in progress.completed_chapters
        
        captured = capsys.readouterr()
        assert "失败" in captured.out

    def test_show_summary(self, capsys):
        """测试显示摘要"""
        progress = ChapterProgress(5)
        progress.completed_chapters = [1, 2, 3]
        
        progress.show_summary()
        
        captured = capsys.readouterr()
        assert "3/5" in captured.out or "60" in captured.out


class TestHelperFunctions:
    """测试辅助函数"""

    def test_create_spinner(self):
        """测试创建旋转加载器"""
        spinner = create_spinner("测试")
        
        assert spinner is not None

    def test_show_progress_context(self):
        """测试进度上下文管理器"""
        with show_progress("测试", 10) as tracker:
            assert tracker.progress is not None
            tracker.update(1)

    def test_show_spinner_context(self):
        """测试旋转加载器上下文管理器"""
        with show_spinner("加载中") as spinner:
            assert spinner is not None


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, capsys):
        """测试完整工作流"""
        # 创建章节进度
        progress = ChapterProgress(3)
        
        # 处理每个章节
        for i in range(1, 4):
            progress.start_chapter(i)
            time.sleep(0.05)
            progress.complete_chapter(i)
        
        # 显示摘要
        progress.show_summary()
        
        captured = capsys.readouterr()
        # 检查所有章节都完成了
        assert "3/3" in captured.out or "100" in captured.out

    def test_status_and_progress(self, capsys):
        """测试状态和进度组合"""
        # 状态显示
        status = StatusDisplay("项目状态")
        status.update("总章节", 10)
        status.update("已完成", 5)
        status.display()
        
        # 进度跟踪
        with show_progress("生成章节", 5) as tracker:
            for i in range(5):
                tracker.update(1)
        
        captured = capsys.readouterr()
        # 检查输出包含状态和进度信息
        assert len(captured.out) > 0
