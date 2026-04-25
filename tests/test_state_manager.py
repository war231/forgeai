"""
单元测试：state_manager.py 模块

测试状态管理、实体追踪、伏笔管理等功能
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.state_manager import StateManager
from forgeai_modules.config import ForgeAIConfig


class TestStateManagerInit:
    """测试 StateManager 初始化"""

    def test_init_with_config(self, temp_project: Path):
        """使用配置初始化"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)
        assert sm.config is not None

    def test_init_default_state(self, temp_project: Path):
        """初始化默认状态"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)
        state = sm.load()

        assert "version" in state
        assert "project" in state
        assert "progress" in state
        assert "entities" in state


class TestStateLoadSave:
    """测试状态加载和保存"""

    def test_load_existing_state(self, temp_project: Path):
        """加载已存在的状态文件"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)
        state = sm.load()

        assert state["project"]["name"] == "test-project"

    def test_load_creates_default(self, tmp_path: Path):
        """加载不存在的状态文件时创建默认值"""
        config = ForgeAIConfig(tmp_path)
        sm = StateManager(config)
        state = sm.load()

        assert "version" in state
        assert sm._cache is not None

    def test_save_state(self, temp_project: Path):
        """保存状态"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        state = sm.load()
        state["project"]["name"] = "modified-name"
        sm.save(state)

        # 重新加载验证
        sm2 = StateManager(config)
        loaded = sm2.load()
        assert loaded["project"]["name"] == "modified-name"

    def test_state_caching(self, temp_project: Path):
        """状态缓存"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        state1 = sm.load()
        state2 = sm.load()

        # 应返回缓存的同一对象
        assert state1 is state2


class TestProgressManagement:
    """测试进度管理"""

    def test_get_progress(self, temp_project: Path):
        """获取进度"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)
        progress = sm.get_progress()

        assert "current_chapter" in progress
        assert "phase" in progress

    def test_update_progress(self, temp_project: Path):
        """更新进度"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.update_progress(
            current_chapter=10,
            phase="write",
            word_count=5000
        )

        progress = sm.get_progress()
        assert progress["current_chapter"] == 10
        assert progress["phase"] == "write"
        assert progress["word_count"] == 5000


class TestEntityManagement:
    """测试实体管理"""

    def test_get_entities_empty(self, temp_project: Path):
        """获取空实体列表"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)
        entities = sm.get_entities()

        assert isinstance(entities, dict)

    def test_upsert_entity(self, temp_project: Path):
        """添加/更新实体"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.upsert_entity("protagonist", {
            "name": "李明",
            "type": "character",
            "tier": "core",
            "state": {"power": "筑基初期"}
        })

        entities = sm.get_entities()
        assert "protagonist" in entities
        assert entities["protagonist"]["name"] == "李明"

    def test_upsert_entity_update(self, temp_project: Path):
        """更新已存在的实体"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 添加
        sm.upsert_entity("char1", {"name": "张三", "power": "练气"})

        # 更新
        sm.upsert_entity("char1", {"name": "张三", "power": "筑基"})

        entities = sm.get_entities()
        assert entities["char1"]["power"] == "筑基"

    def test_record_state_change(self, temp_project: Path):
        """记录状态变化"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.record_state_change(
            entity_id="protagonist",
            field="power.realm",
            old_value="练气1层",
            new_value="练气2层",
            reason="修炼突破",
            chapter=5
        )

        state = sm.load()
        changes = state.get("state_changes", [])
        assert len(changes) == 1
        assert changes[0]["entity_id"] == "protagonist"
        assert changes[0]["chapter"] == 5

    def test_add_relationship(self, temp_project: Path):
        """添加实体关系"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.add_relationship(
            from_entity="李明",
            to_entity="林雪",
            rel_type="friend",
            description="师姐弟",
            chapter=1
        )

        state = sm.load()
        relationships = state.get("relationships", [])
        assert len(relationships) == 1
        assert relationships[0]["type"] == "friend"


class TestForeshadowingManagement:
    """测试伏笔管理"""

    def test_add_foreshadowing(self, temp_project: Path):
        """添加伏笔"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.add_foreshadowing(
            description="神秘玉佩",
            chapter_planted=1,
            expected_payoff=10,
            category="plot"
        )

        state = sm.load()
        active = state["foreshadowing"]["active"]
        assert len(active) == 1
        assert active[0]["description"] == "神秘玉佩"
        assert active[0]["status"] == "active"

    def test_resolve_foreshadowing(self, temp_project: Path):
        """回收伏笔"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 添加伏笔
        sm.add_foreshadowing(
            description="神秘玉佩",
            chapter_planted=1
        )

        state = sm.load()
        fs_id = state["foreshadowing"]["active"][0]["id"]

        # 回收伏笔
        sm.resolve_foreshadowing(fs_id, chapter_resolved=10)

        state = sm.load()
        assert len(state["foreshadowing"]["active"]) == 0
        assert len(state["foreshadowing"]["resolved"]) == 1

    def test_get_overdue_foreshadowing(self, temp_project: Path):
        """获取超期伏笔"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 添加超期伏笔（设置很早的章节）
        sm.add_foreshadowing(
            description="遗忘的伏笔",
            chapter_planted=1,
            expected_payoff=10
        )

        # 更新当前章节
        sm.update_progress(current_chapter=50)

        overdue = sm.get_overdue_foreshadowing(50, threshold=30)
        assert len(overdue) == 1


class TestReadingPowerManagement:
    """测试追读力管理"""

    def test_add_reading_power(self, temp_project: Path):
        """记录追读力"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.add_reading_power(
            chapter=1,
            score=0.8,
            hooks=["悬念钩子", "冲突钩子"],
            debt_change=0.1,
            notes="开篇悬念"
        )

        state = sm.load()
        history = state.get("reading_power", {}).get("history", [])
        assert len(history) == 1
        assert history[0]["score"] == 0.8

    def test_narrative_debt_tracking(self, temp_project: Path):
        """叙事债务追踪"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.add_reading_power(chapter=1, score=0.7, hooks=[], debt_change=0.2)
        sm.add_reading_power(chapter=2, score=0.8, hooks=[], debt_change=-0.1)

        state = sm.load()
        debt = state.get("reading_power", {}).get("debt", 0)
        assert debt == 0.1  # 0.2 - 0.1


class TestTimelineManagement:
    """测试时间线管理"""

    def test_get_timeline(self, temp_project: Path):
        """获取时间线状态"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)
        timeline = sm.get_timeline()

        # 时间线应包含基本字段
        assert isinstance(timeline, dict)

    def test_add_timeline_anchor(self, temp_project: Path):
        """添加时间锚点"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.add_timeline_anchor(
            chapter=1,
            anchor="末世第1天",
            event="末世降临"
        )

        timeline = sm.get_timeline()
        assert len(timeline["anchors"]) == 1
        assert timeline["current_anchor"] == "末世第1天"

    def test_update_timeline(self, temp_project: Path):
        """更新时间线"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.update_timeline(time_units="小时")
        timeline = sm.get_timeline()

        assert timeline["time_units"] == "小时"

    def test_add_countdown(self, temp_project: Path):
        """添加倒计时"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        sm.add_countdown("物资耗尽", "D-10")

        timeline = sm.get_timeline()
        assert len(timeline["countdowns"]) == 1
        assert timeline["countdowns"][0]["name"] == "物资耗尽"


class TestSummary:
    """测试状态摘要"""

    def test_get_summary(self, temp_project: Path):
        """获取状态摘要"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 添加一些数据
        sm.upsert_entity("char1", {"name": "角色1", "tier": "core"})
        sm.add_foreshadowing("测试伏笔", chapter_planted=1)
        sm.add_reading_power(chapter=1, score=0.8, hooks=[])

        summary = sm.get_summary()

        assert "project" in summary
        assert "progress" in summary
        assert summary["entity_count"] >= 1
        assert summary["active_foreshadowing"] >= 1


class TestArchiving:
    """测试自动归档"""

    def test_archive_large_state_changes(self, temp_project: Path):
        """大量状态变化触发归档"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 添加大量状态变化
        for i in range(250):
            sm.record_state_change(
                entity_id=f"entity_{i}",
                field="some_field",
                old_value="old",
                new_value="new",
                reason="test",
                chapter=i
            )

        state = sm.load()
        # 应该触发归档，保留最近的数据
        assert len(state.get("state_changes", [])) <= 250

    def test_archive_reading_power_history(self, temp_project: Path):
        """追读力历史归档"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 添加大量追读力记录
        for i in range(250):
            sm.add_reading_power(chapter=i, score=0.5 + i * 0.001, hooks=[])

        state = sm.load()
        # 应该有归档
        history = state.get("reading_power", {}).get("history", [])
        # 归档后保留最近的数据
        assert len(history) <= 250


class TestStateManagerIntegration:
    """状态管理集成测试"""

    def test_full_workflow(self, temp_project: Path):
        """完整工作流"""
        config = ForgeAIConfig(temp_project)
        sm = StateManager(config)

        # 1. 初始化项目
        sm.update_progress(phase="define", current_chapter=0)

        # 2. 添加实体
        sm.upsert_entity("protagonist", {
            "name": "李明",
            "type": "character",
            "tier": "core",
            "state": {"power": "练气1层", "location": "青云宗"}
        })

        # 3. 添加伏笔
        sm.add_foreshadowing("神秘玉佩", chapter_planted=1, expected_payoff=20)

        # 4. 记录章节完成
        sm.add_reading_power(chapter=1, score=0.85, hooks=["悬念"])

        # 5. 更新进度
        sm.update_progress(current_chapter=1, phase="write")

        # 6. 记录状态变化
        sm.record_state_change(
            entity_id="protagonist",
            field="state.power",
            old_value="练气1层",
            new_value="练气2层",
            reason="修炼突破",
            chapter=1
        )

        # 验证最终状态
        summary = sm.get_summary()
        assert summary["entity_count"] == 1
        assert summary["active_foreshadowing"] == 1
        assert summary["progress"]["current_chapter"] == 1
