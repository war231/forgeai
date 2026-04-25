"""
单元测试：pipeline.py 模块

测试自动流水线功能：
- 写作后流水线（post_write）
- 写前检查（pre_write_check）
- 智能上下文组装（smart_context）
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.pipeline import Pipeline
from forgeai_modules.config import ForgeAIConfig
from forgeai_modules.state_manager import StateManager
from forgeai_modules.index_manager import IndexManager


@pytest.fixture
def pipeline(temp_project: Path) -> Pipeline:
    """创建流水线实例"""
    config = ForgeAIConfig(temp_project)
    # 初始化数据库
    im = IndexManager(config)
    im.init_db()
    return Pipeline(config)


class TestPreWriteCheck:
    """测试写前检查"""

    def test_pre_check_no_alerts(self, pipeline: Pipeline):
        """无问题时检查结果正常"""
        result = pipeline.pre_write_check(next_chapter=1)

        assert "alerts" in result
        assert "next_chapter" in result
        assert result["next_chapter"] == 1
        assert result["alert_count"] == 0

    def test_pre_check_overdue_foreshadowing(self, pipeline: Pipeline):
        """超期伏笔产生提醒"""
        sm = pipeline.state_manager
        sm.add_foreshadowing("神秘玉佩", chapter_planted=1, expected_payoff=10)
        sm.update_progress(current_chapter=50)

        result = pipeline.pre_write_check(next_chapter=50)

        overdue_alerts = [a for a in result["alerts"] if a["type"] == "overdue_foreshadowing"]
        assert len(overdue_alerts) > 0

    def test_pre_check_too_many_foreshadowing(self, pipeline: Pipeline):
        """活跃伏笔过多产生提醒"""
        sm = pipeline.state_manager
        for i in range(20):
            sm.add_foreshadowing(f"伏笔{i}", chapter_planted=1)
        sm.update_progress(current_chapter=5)

        result = pipeline.pre_write_check(next_chapter=5)

        fs_alerts = [a for a in result["alerts"] if a["type"] == "too_many_foreshadowing"]
        assert len(fs_alerts) > 0

    def test_pre_check_high_narrative_debt(self, pipeline: Pipeline):
        """叙事债务过高产生提醒"""
        sm = pipeline.state_manager
        state = sm.load()
        state["reading_power"] = {"debt": 8.0, "history": []}
        sm.save(state)

        result = pipeline.pre_write_check(next_chapter=10)

        debt_alerts = [a for a in result["alerts"] if a["type"] == "narrative_debt"]
        assert len(debt_alerts) > 0

    def test_pre_check_reading_power_decline(self, pipeline: Pipeline):
        """追读力连续下降产生提醒"""
        sm = pipeline.state_manager
        state = sm.load()
        state["reading_power"] = {
            "debt": 0.0,
            "history": [
                {"chapter": 1, "score": 0.9},
                {"chapter": 2, "score": 0.7},
                {"chapter": 3, "score": 0.5},
            ]
        }
        sm.save(state)

        result = pipeline.pre_write_check(next_chapter=4)

        decline_alerts = [a for a in result["alerts"] if a["type"] == "reading_power_decline"]
        assert len(decline_alerts) > 0


class TestSmartContext:
    """测试智能上下文组装"""

    def test_smart_context_basic(self, pipeline: Pipeline):
        """基本上下文组装"""
        result = pipeline.smart_context(chapter=1)

        assert "chapter" in result
        assert "formatted" in result
        assert result["chapter"] == 1
        assert isinstance(result["formatted"], str)

    def test_smart_context_within_budget(self, pipeline: Pipeline):
        """上下文不超过预算"""
        result = pipeline.smart_context(chapter=1, max_chars=500)

        assert result["total_chars"] <= 600  # 允许少量溢出

    def test_smart_context_with_entities(self, pipeline: Pipeline):
        """有实体时包含角色信息"""
        sm = pipeline.state_manager
        sm.upsert_entity("protagonist", {
            "name": "李明", "tier": "core", "last_appearance": 1, "type": "character"
        })

        result = pipeline.smart_context(chapter=2)
        assert "活跃角色" in result["formatted"] or result["sections"] >= 1


class TestPostWrite:
    """测试写作后流水线"""

    @pytest.mark.asyncio
    async def test_post_write_returns_results(self, pipeline: Pipeline):
        """写作后流水线返回结果"""
        # Mock RAG 适配器的 index_chapter 方法
        pipeline.rag_adapter.index_chapter = MagicMock(return_value=5)
        pipeline.entity_extractor.save_extraction = MagicMock(return_value={
            "entities": 1, "relationships": 0, "state_changes": 0, "foreshadowing": 0, "scenes": 1
        })
        pipeline.entity_extractor.extract_from_text = MagicMock(return_value=MagicMock())

        result = await pipeline.post_write(
            chapter=1,
            text="这是测试文本，李明站在山顶。",
            score_ai=True,
        )

        assert "chapter" in result
        assert "steps" in result
        assert result["chapter"] == 1

    @pytest.mark.asyncio
    async def test_post_write_index_step(self, pipeline: Pipeline):
        """写作后流水线包含索引步骤"""
        pipeline.rag_adapter.index_chapter = MagicMock(return_value=3)
        pipeline.entity_extractor.save_extraction = MagicMock(return_value={
            "entities": 0, "relationships": 0, "state_changes": 0, "foreshadowing": 0, "scenes": 0
        })
        pipeline.entity_extractor.extract_from_text = MagicMock(return_value=MagicMock())

        result = await pipeline.post_write(chapter=1, text="测试文本")

        assert "index" in result["steps"]

    @pytest.mark.asyncio
    async def test_post_write_score_step(self, pipeline: Pipeline):
        """写作后流水线包含评分步骤"""
        pipeline.rag_adapter.index_chapter = MagicMock(return_value=1)
        pipeline.entity_extractor.save_extraction = MagicMock(return_value={
            "entities": 0, "relationships": 0, "state_changes": 0, "foreshadowing": 0, "scenes": 0
        })
        pipeline.entity_extractor.extract_from_text = MagicMock(return_value=MagicMock())

        result = await pipeline.post_write(chapter=1, text="测试文本", score_ai=True)

        assert "score" in result["steps"]

    @pytest.mark.asyncio
    async def test_post_write_no_score(self, pipeline: Pipeline):
        """跳过评分时无 score 步骤"""
        pipeline.rag_adapter.index_chapter = MagicMock(return_value=1)
        pipeline.entity_extractor.save_extraction = MagicMock(return_value={
            "entities": 0, "relationships": 0, "state_changes": 0, "foreshadowing": 0, "scenes": 0
        })
        pipeline.entity_extractor.extract_from_text = MagicMock(return_value=MagicMock())

        result = await pipeline.post_write(chapter=1, text="测试文本", score_ai=False)

        assert "score" not in result["steps"]


class TestBuildCoreSettings:
    """测试核心设定构建"""

    def test_build_core_settings_with_name(self, pipeline: Pipeline):
        """有项目名时包含项目信息"""
        sm = pipeline.state_manager
        state = sm.load()
        state["project"]["name"] = "测试小说"
        state["project"]["genre"] = "玄幻"
        sm.save(state)

        result = pipeline._build_core_settings(sm.load())
        assert "测试小说" in result

    def test_build_core_settings_empty(self, pipeline: Pipeline):
        """无项目名时返回空或基本信息"""
        sm = pipeline.state_manager
        state = sm.load()
        state["project"] = {}
        sm.save(state)

        result = pipeline._build_core_settings(sm.load())
        # 至少不应抛异常
        assert isinstance(result, str)


class TestGetActiveEntities:
    """测试活跃实体获取"""

    def test_get_active_entities(self, pipeline: Pipeline):
        """获取活跃实体"""
        entities = {
            "char1": {"name": "李明", "tier": "core", "last_appearance": 5, "type": "character"},
            "char2": {"name": "老王", "tier": "decorative", "last_appearance": 1, "type": "character"},
        }

        active = pipeline._get_active_entities(entities, chapter=10, lookback=10)

        # char1 在 lookback 范围内，char2 超出
        assert len(active) >= 1
        assert any(e["name"] == "李明" for e in active)

    def test_active_entities_sorted_by_tier(self, pipeline: Pipeline):
        """活跃实体按 tier 排序"""
        entities = {
            "char1": {"name": "配角", "tier": "secondary", "last_appearance": 5, "type": "character"},
            "char2": {"name": "主角", "tier": "core", "last_appearance": 5, "type": "character"},
        }

        active = pipeline._get_active_entities(entities, chapter=5)
        assert active[0]["tier"] == "core"
