#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Strand Weave 节奏系统
"""

import pytest
from pathlib import Path
import sys

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.strand_tracker import StrandTracker, StrandRecord, StrandState


class TestStrandTracker:
    """测试 Strand Weave 节奏追踪器"""

    def test_init(self):
        """测试初始化"""
        tracker = StrandTracker()
        assert tracker.state.total_chapters == 0
        assert tracker.state.quest_count == 0
        assert tracker.state.fire_count == 0
        assert tracker.state.constellation_count == 0

    def test_record_quest(self):
        """测试记录主线"""
        tracker = StrandTracker()
        tracker.record(1, "quest", "主角突破筑基期", "major")

        assert tracker.state.quest_count == 1
        assert tracker.state.last_quest_chapter == 1
        assert tracker.state.total_chapters == 1

    def test_record_fire(self):
        """测试记录感情线"""
        tracker = StrandTracker()
        tracker.record(1, "fire", "女主出场", "major")

        assert tracker.state.fire_count == 1
        assert tracker.state.last_fire_chapter == 1

    def test_record_constellation(self):
        """测试记录世界观线"""
        tracker = StrandTracker()
        tracker.record(1, "constellation", "揭露世界真相", "major")

        assert tracker.state.constellation_count == 1
        assert tracker.state.last_constellation_chapter == 1

    def test_record_invalid_type(self):
        """测试无效类型"""
        tracker = StrandTracker()
        with pytest.raises(ValueError):
            tracker.record(1, "invalid", "测试")

    def test_record_batch(self):
        """测试批量记录"""
        tracker = StrandTracker()
        tracker.record_batch([
            {"chapter": 1, "strand_type": "quest", "description": "主线1"},
            {"chapter": 2, "strand_type": "quest", "description": "主线2"},
            {"chapter": 3, "strand_type": "fire", "description": "感情线1"},
            {"chapter": 5, "strand_type": "constellation", "description": "世界观1"},
        ])

        assert tracker.state.quest_count == 2
        assert tracker.state.fire_count == 1
        assert tracker.state.constellation_count == 1
        assert len(tracker.state.records) == 4

    def test_no_warning_initially(self):
        """测试初始无警告"""
        tracker = StrandTracker()
        tracker.record(1, "quest", "主线", "major")

        warnings = tracker.check_warnings(1)
        assert len(warnings) == 0

    def test_quest_warning(self):
        """测试主线缺失警告"""
        tracker = StrandTracker()
        tracker.record(1, "quest", "主线", "major")
        # 跳过5章

        warnings = tracker.check_warnings(6)
        assert len(warnings) == 1
        assert warnings[0]["type"] == "quest_missing"
        assert warnings[0]["severity"] == "critical"

    def test_fire_warning(self):
        """测试感情线缺失警告"""
        tracker = StrandTracker()
        tracker.record(1, "fire", "感情线", "major")
        # 跳过10章

        warnings = tracker.check_warnings(11)
        assert len(warnings) >= 1
        fire_warnings = [w for w in warnings if w["type"] == "fire_missing"]
        assert len(fire_warnings) == 1

    def test_constellation_warning(self):
        """测试世界观线缺失警告"""
        tracker = StrandTracker()
        tracker.record(1, "constellation", "世界观", "major")
        # 跳过15章

        warnings = tracker.check_warnings(16)
        assert len(warnings) >= 1
        constellation_warnings = [w for w in warnings if w["type"] == "constellation_missing"]
        assert len(constellation_warnings) == 1

    def test_get_ratios(self):
        """测试比例计算"""
        tracker = StrandTracker()
        tracker.record_batch([
            {"chapter": 1, "strand_type": "quest", "description": "主线"},
            {"chapter": 2, "strand_type": "quest", "description": "主线"},
            {"chapter": 3, "strand_type": "quest", "description": "主线"},
            {"chapter": 4, "strand_type": "fire", "description": "感情线"},
            {"chapter": 5, "strand_type": "constellation", "description": "世界观"},
        ])

        ratios = tracker.get_ratios()
        assert ratios["quest"] == pytest.approx(0.6, 0.1)
        assert ratios["fire"] == pytest.approx(0.2, 0.1)
        assert ratios["constellation"] == pytest.approx(0.2, 0.1)

    def test_balance_score(self):
        """测试平衡分数"""
        tracker = StrandTracker()
        # 完美平衡：60% quest, 20% fire, 20% constellation
        tracker.record_batch([
            {"chapter": i, "strand_type": "quest", "description": f"主线{i}"}
            for i in range(1, 7)
        ] + [
            {"chapter": i, "strand_type": "fire", "description": f"感情线{i}"}
            for i in range(7, 9)
        ] + [
            {"chapter": i, "strand_type": "constellation", "description": f"世界观{i}"}
            for i in range(9, 11)
        ])

        score = tracker.get_balance_score()
        assert score >= 90  # 接近完美平衡

    def test_imbalanced_score(self):
        """测试不平衡分数"""
        tracker = StrandTracker()
        # 完全不平衡：只有主线
        for i in range(1, 11):
            tracker.record(i, "quest", f"主线{i}", "minor")

        score = tracker.get_balance_score()
        assert score < 50  # 不平衡

    def test_generate_report(self):
        """测试报告生成"""
        tracker = StrandTracker()
        tracker.record_batch([
            {"chapter": 1, "strand_type": "quest", "description": "主线"},
            {"chapter": 2, "strand_type": "fire", "description": "感情线"},
            {"chapter": 3, "strand_type": "constellation", "description": "世界观"},
        ])

        report = tracker.generate_report(3)

        assert report["current_chapter"] == 3
        assert report["counts"]["quest"] == 1
        assert report["counts"]["fire"] == 1
        assert report["counts"]["constellation"] == 1
        assert "balance_score" in report
        assert len(report["warnings"]) == 0

    def test_to_markdown(self):
        """测试 Markdown 输出"""
        tracker = StrandTracker()
        tracker.record(1, "quest", "主线", "major")
        tracker.record(2, "fire", "感情线", "major")

        md = tracker.to_markdown(2)

        assert "# Strand Weave 节奏报告" in md
        assert "主线" in md
        assert "感情线" in md


class TestStrandRecord:
    """测试 StrandRecord 数据类"""

    def test_create(self):
        """测试创建记录"""
        record = StrandRecord(
            chapter=1,
            strand_type="quest",
            description="测试",
            importance="major"
        )

        assert record.chapter == 1
        assert record.strand_type == "quest"
        assert record.description == "测试"
        assert record.importance == "major"


class TestStrandState:
    """测试 StrandState 数据类"""

    def test_create(self):
        """测试创建状态"""
        state = StrandState()

        assert state.last_quest_chapter == 0
        assert state.last_fire_chapter == 0
        assert state.last_constellation_chapter == 0
        assert state.records == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
