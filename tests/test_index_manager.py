"""
单元测试：index_manager.py 模块

测试 SQLite 索引管理功能：
- 数据库初始化
- 章节元数据 CRUD
- 实体管理
- 关系管理
- 追读力记录
- 审查指标
- 统计信息
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.index_manager import IndexManager
from forgeai_modules.config import ForgeAIConfig


@pytest.fixture
def index_mgr(temp_project: Path) -> IndexManager:
    """创建索引管理器并初始化数据库"""
    config = ForgeAIConfig(temp_project)
    mgr = IndexManager(config)
    mgr.init_db()
    return mgr


class TestDatabaseInit:
    """测试数据库初始化"""

    def test_init_db_creates_file(self, temp_project: Path):
        """初始化后数据库文件存在"""
        config = ForgeAIConfig(temp_project)
        mgr = IndexManager(config)
        mgr.init_db()

        assert config.index_db_path is not None
        assert config.index_db_path.exists()

    def test_init_db_idempotent(self, index_mgr: IndexManager):
        """重复初始化不报错"""
        index_mgr.init_db()  # 应该不抛异常


class TestChapterOperations:
    """测试章节操作"""

    def test_upsert_and_get_chapter(self, index_mgr: IndexManager):
        """插入并获取章节"""
        index_mgr.upsert_chapter(1, title="第一章", word_count=3000)
        ch = index_mgr.get_chapter(1)

        assert ch is not None
        assert ch["chapter"] == 1
        assert ch["title"] == "第一章"
        assert ch["word_count"] == 3000

    def test_upsert_updates_existing(self, index_mgr: IndexManager):
        """更新已存在的章节"""
        index_mgr.upsert_chapter(1, title="旧标题", word_count=1000)
        index_mgr.upsert_chapter(1, title="新标题", word_count=2000)

        ch = index_mgr.get_chapter(1)
        assert ch["title"] == "新标题"
        assert ch["word_count"] == 2000

    def test_get_nonexistent_chapter(self, index_mgr: IndexManager):
        """获取不存在的章节返回 None"""
        result = index_mgr.get_chapter(999)
        assert result is None

    def test_get_all_chapters(self, index_mgr: IndexManager):
        """获取所有章节"""
        for i in range(1, 4):
            index_mgr.upsert_chapter(i, title=f"第{i}章", word_count=1000 * i)

        chapters = index_mgr.get_all_chapters()
        assert len(chapters) == 3
        assert chapters[0]["chapter"] == 1

    def test_chapter_with_summary(self, index_mgr: IndexManager):
        """章节包含摘要"""
        index_mgr.upsert_chapter(1, title="测试", summary="这是摘要", reading_power=0.85)
        ch = index_mgr.get_chapter(1)

        assert ch["summary"] == "这是摘要"
        assert ch["reading_power"] == 0.85


class TestEntityOperations:
    """测试实体操作"""

    def test_upsert_and_get_entity(self, index_mgr: IndexManager):
        """插入并获取实体"""
        index_mgr.upsert_entity("char1", "李明", type_="character", tier="core")
        entity = index_mgr.get_entity("char1")

        assert entity is not None
        assert entity["name"] == "李明"
        assert entity["type"] == "character"
        assert entity["tier"] == "core"

    def test_entity_aliases_json(self, index_mgr: IndexManager):
        """实体别名 JSON 解析"""
        index_mgr.upsert_entity("char1", "李明", aliases=["小明", "阿明"])
        entity = index_mgr.get_entity("char1")

        assert entity["aliases"] == ["小明", "阿明"]

    def test_entity_attributes_json(self, index_mgr: IndexManager):
        """实体属性 JSON 解析"""
        index_mgr.upsert_entity("char1", "李明", attributes={"power": "筑基"})
        entity = index_mgr.get_entity("char1")

        assert entity["attributes"] == {"power": "筑基"}

    def test_get_nonexistent_entity(self, index_mgr: IndexManager):
        """获取不存在的实体返回 None"""
        result = index_mgr.get_entity("nonexistent")
        assert result is None

    def test_search_entities(self, index_mgr: IndexManager):
        """模糊搜索实体"""
        index_mgr.upsert_entity("char1", "李明", type_="character")
        index_mgr.upsert_entity("loc1", "青云宗", type_="location")
        index_mgr.upsert_entity("char2", "李雪", type_="character")

        results = index_mgr.search_entities("李")
        assert len(results) == 2

        results = index_mgr.search_entities("李", type_="character")
        assert len(results) == 2

    def test_record_appearance(self, index_mgr: IndexManager):
        """记录实体出场"""
        index_mgr.upsert_entity("char1", "李明", type_="character")
        index_mgr.record_appearance("char1", chapter=1, role="pov")
        index_mgr.record_appearance("char1", chapter=3, role="active")

        appearances = index_mgr.get_entity_appearances("char1")
        assert len(appearances) == 2

    def test_record_appearance_updates_last(self, index_mgr: IndexManager):
        """出场记录更新 last_appearance"""
        index_mgr.upsert_entity("char1", "李明", first_appearance=1)
        index_mgr.record_appearance("char1", chapter=5)
        index_mgr.record_appearance("char1", chapter=10)

        entity = index_mgr.get_entity("char1")
        assert entity["last_appearance"] == 10


class TestRelationshipOperations:
    """测试关系操作"""

    def test_add_and_get_relationships(self, index_mgr: IndexManager):
        """添加并获取关系"""
        index_mgr.upsert_entity("char1", "李明")
        index_mgr.upsert_entity("char2", "林雪")

        index_mgr.add_relationship("char1", "char2", type_="friend", description="师姐弟", chapter=1)

        rels = index_mgr.get_relationships("char1")
        assert len(rels) == 1
        assert rels[0]["type"] == "friend"

    def test_relationships_bidirectional(self, index_mgr: IndexManager):
        """关系可双向查询"""
        index_mgr.upsert_entity("char1", "李明")
        index_mgr.upsert_entity("char2", "林雪")

        index_mgr.add_relationship("char1", "char2", type_="friend")

        # 从任一端查询都能找到
        rels_from = index_mgr.get_relationships("char1")
        rels_to = index_mgr.get_relationships("char2")
        assert len(rels_from) == 1
        assert len(rels_to) == 1


class TestReadingPowerOperations:
    """测试追读力操作"""

    def test_record_reading_power(self, index_mgr: IndexManager):
        """记录追读力"""
        index_mgr.record_reading_power(1, score=0.8, hooks=["悬念"], debt_change=0.1)

        trend = index_mgr.get_reading_power_trend()
        assert len(trend) == 1
        assert trend[0]["score"] == 0.8

    def test_reading_power_trend_order(self, index_mgr: IndexManager):
        """追读力趋势按章节排序"""
        for i in range(1, 4):
            index_mgr.record_reading_power(i, score=0.5 + i * 0.1)

        trend = index_mgr.get_reading_power_trend()
        assert len(trend) == 3
        assert trend[0]["chapter"] == 1
        assert trend[2]["chapter"] == 3

    def test_reading_power_hooks_json(self, index_mgr: IndexManager):
        """追读力钩子 JSON 解析"""
        index_mgr.record_reading_power(1, score=0.8, hooks=["悬念", "冲突"])

        trend = index_mgr.get_reading_power_trend()
        assert trend[0]["hooks"] == ["悬念", "冲突"]


class TestReviewMetrics:
    """测试审查指标"""

    def test_record_and_get_review_metric(self, index_mgr: IndexManager):
        """记录并获取审查指标"""
        index_mgr.record_review_metric(
            1, checker_type="consistency", score=0.9,
            issues=["角色名不一致"], suggestions=["统一角色名"]
        )

        metrics = index_mgr.get_review_metrics(1)
        assert len(metrics) == 1
        assert metrics[0]["checker_type"] == "consistency"
        assert metrics[0]["issues"] == ["角色名不一致"]

    def test_multiple_review_metrics(self, index_mgr: IndexManager):
        """同一章节多个审查维度"""
        for checker in ["consistency", "pacing", "ooc"]:
            index_mgr.record_review_metric(1, checker_type=checker, score=0.8)

        metrics = index_mgr.get_review_metrics(1)
        assert len(metrics) == 3


class TestStats:
    """测试统计信息"""

    def test_empty_stats(self, index_mgr: IndexManager):
        """空数据库统计"""
        stats = index_mgr.get_stats()

        assert stats["chapters"] == 0
        assert stats["entities"] == 0
        assert stats["relationships"] == 0

    def test_stats_with_data(self, index_mgr: IndexManager):
        """有数据时的统计"""
        index_mgr.upsert_chapter(1, word_count=3000)
        index_mgr.upsert_chapter(2, word_count=2500)
        index_mgr.upsert_entity("char1", "李明")

        stats = index_mgr.get_stats()
        assert stats["chapters"] == 2
        assert stats["entities"] == 1


class TestReset:
    """测试重置"""

    def test_reset_clears_data(self, index_mgr: IndexManager):
        """重置后数据清空"""
        index_mgr.upsert_chapter(1, word_count=3000)
        assert index_mgr.get_stats()["chapters"] == 1

        index_mgr.reset()
        assert index_mgr.get_stats()["chapters"] == 0
