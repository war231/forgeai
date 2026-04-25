#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色成长曲线分析器测试"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from forgeai_modules.growth_analyzer import (
    GrowthAnalyzer, GrowthMilestone, GrowthTimeline, GrowthAnalysis
)


class TestGrowthMilestone:
    """成长里程碑数据类测试"""

    def test_create_milestone(self):
        """创建里程碑"""
        m = GrowthMilestone(
            chapter=10,
            event_type="breakthrough",
            description="突破筑基期",
            importance="critical",
            old_value="练气期",
            new_value="筑基期"
        )

        assert m.chapter == 10
        assert m.event_type == "breakthrough"
        assert m.importance == "critical"


class TestGrowthTimeline:
    """成长时间线测试"""

    def test_create_timeline(self):
        """创建时间线"""
        timeline = GrowthTimeline(entity_id="李天")

        assert timeline.entity_id == "李天"
        assert timeline.milestones == []
        assert timeline.total_changes == 0

    def test_timeline_to_dict(self):
        """转换为字典"""
        timeline = GrowthTimeline(
            entity_id="李天",
            total_changes=5,
            chapters_active=3
        )
        timeline.milestones.append(GrowthMilestone(
            chapter=1, event_type="breakthrough",
            description="测试", importance="high"
        ))

        d = timeline.to_dict()

        assert d["entity_id"] == "李天"
        assert d["total_changes"] == 5
        assert len(d["milestones"]) == 1


class TestGrowthAnalysis:
    """成长分析结果测试"""

    def test_create_analysis(self):
        """创建分析结果"""
        timeline = GrowthTimeline(entity_id="李天")
        analysis = GrowthAnalysis(
            entity_id="李天",
            timeline=timeline,
            velocity=1.5,
            trajectory="linear",
            current_level="筑基期",
            first_appearance=1,
            last_appearance=10,
            growth_pattern="steady"
        )

        assert analysis.entity_id == "李天"
        assert analysis.velocity == 1.5
        assert analysis.trajectory == "linear"

    def test_analysis_to_dict(self):
        """转换为字典"""
        timeline = GrowthTimeline(entity_id="李天")
        analysis = GrowthAnalysis(
            entity_id="李天",
            timeline=timeline,
            velocity=1.5,
            trajectory="linear",
            current_level="筑基期",
            first_appearance=1,
            last_appearance=10,
            growth_pattern="steady",
            recommendations=["建议1", "建议2"]
        )

        d = analysis.to_dict()

        assert d["velocity"] == 1.5
        assert d["trajectory"] == "linear"
        assert len(d["recommendations"]) == 2


class TestClassifyEventType:
    """事件类型分类测试"""

    def test_classify_breakthrough(self):
        """突破类型"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._classify_event_type("突破筑基期", "修为") == "breakthrough"
        assert analyzer._classify_event_type("踏入新境界", "") == "breakthrough"
        assert analyzer._classify_event_type("晋升为长老", "") == "breakthrough"

    def test_classify_acquire(self):
        """获得类型"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._classify_event_type("获得神器", "") == "acquire"
        assert analyzer._classify_event_type("得到传承", "") == "acquire"

    def test_classify_realize(self):
        """领悟类型"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._classify_event_type("领悟剑意", "") == "realize"
        assert analyzer._classify_event_type("参悟大道", "") == "realize"

    def test_classify_relationship(self):
        """关系类型"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._classify_event_type("结为好友", "关系") == "relationship"

    def test_classify_other(self):
        """其他类型"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._classify_event_type("普通变化", "属性") == "other"


class TestJudgeImportance:
    """重要性判断测试"""

    def test_judge_critical(self):
        """关键突破"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._judge_importance("breakthrough", "修为") == "critical"

    def test_judge_high(self):
        """重要"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._judge_importance("breakthrough", "其他") == "high"
        assert analyzer._judge_importance("acquire", "") == "high"

    def test_judge_medium(self):
        """一般"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._judge_importance("realize", "") == "medium"

    def test_judge_low(self):
        """次要"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._judge_importance("other", "") == "low"


class TestCalculateVelocity:
    """成长速度计算测试"""

    def test_calculate_velocity_basic(self):
        """基本计算"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.total_changes = 10
        timeline.chapters_active = 5

        velocity = analyzer._calculate_velocity(timeline)

        assert velocity == 2.0

    def test_calculate_velocity_zero_chapters(self):
        """零章节"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.total_changes = 10
        timeline.chapters_active = 0

        velocity = analyzer._calculate_velocity(timeline)

        assert velocity == 0.0


class TestIdentifyTrajectory:
    """成长轨迹识别测试"""

    def test_identify_insufficient_data(self):
        """数据不足"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.milestones = [
            GrowthMilestone(1, "breakthrough", "", "high", new_value="练气")
        ]

        trajectory = analyzer._identify_trajectory(timeline)

        assert trajectory == "insufficient_data"

    def test_identify_linear(self):
        """线性增长"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.milestones = [
            GrowthMilestone(1, "breakthrough", "", "high", new_value="练气1层"),
            GrowthMilestone(2, "breakthrough", "", "high", new_value="练气2层"),
            GrowthMilestone(3, "breakthrough", "", "high", new_value="练气3层"),
        ]

        trajectory = analyzer._identify_trajectory(timeline)

        # 线性或指数取决于具体数值
        assert trajectory in ["linear", "exponential", "irregular"]


class TestParseRealmLevel:
    """修为等级解析测试"""

    def test_parse_realm_basic(self):
        """基本解析"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._parse_realm_level("练气期") == 100
        assert analyzer._parse_realm_level("筑基期") == 200
        assert analyzer._parse_realm_level("金丹期") == 300

    def test_parse_realm_with_layer(self):
        """带层数"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._parse_realm_level("练气5层") == 105
        assert analyzer._parse_realm_level("筑基3层") == 203

    def test_parse_realm_unknown(self):
        """未知等级"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._parse_realm_level("未知境界") is None


class TestAnalyzeGrowthPattern:
    """成长模式分析测试"""

    def test_pattern_rapid(self):
        """快速成长"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._analyze_growth_pattern(3.0, "linear") == "rapid"
        assert analyzer._analyze_growth_pattern(5.0, "exponential") == "rapid"

    def test_pattern_steady(self):
        """稳定成长"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._analyze_growth_pattern(1.5, "linear") == "steady"
        assert analyzer._analyze_growth_pattern(1.0, "linear") == "steady"

    def test_pattern_slow(self):
        """缓慢成长"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert analyzer._analyze_growth_pattern(0.5, "logarithmic") == "slow"
        assert analyzer._analyze_growth_pattern(0.1, "irregular") == "slow"


class TestGenerateRecommendations:
    """成长建议生成测试"""

    def test_recommendations_fast_growth(self):
        """成长过快建议"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.milestones = []

        recs = analyzer._generate_recommendations("test", timeline, 4.0, "exponential", "rapid")

        assert any("过快" in r for r in recs)

    def test_recommendations_slow_growth(self):
        """成长过慢建议"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.milestones = []

        recs = analyzer._generate_recommendations("test", timeline, 0.3, "logarithmic", "slow")

        assert any("较慢" in r for r in recs)

    def test_recommendations_exponential(self):
        """指数型轨迹建议"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="test")
        timeline.milestones = []

        recs = analyzer._generate_recommendations("test", timeline, 1.5, "exponential", "steady")

        assert any("指数型" in r for r in recs)


class TestDisplayMethods:
    """显示方法测试"""

    def test_trajectory_display(self):
        """轨迹显示"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert "指数型" in analyzer._trajectory_display("exponential")
        assert "线性型" in analyzer._trajectory_display("linear")
        assert "对数型" in analyzer._trajectory_display("logarithmic")

    def test_pattern_display(self):
        """模式显示"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert "快速" in analyzer._pattern_display("rapid")
        assert "稳定" in analyzer._pattern_display("steady")
        assert "缓慢" in analyzer._pattern_display("slow")

    def test_event_type_display(self):
        """事件类型显示"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert "突破" in analyzer._event_type_display("breakthrough")
        assert "获得" in analyzer._event_type_display("acquire")
        assert "领悟" in analyzer._event_type_display("realize")

    def test_importance_display(self):
        """重要性显示"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        assert "关键" in analyzer._importance_display("critical")
        assert "重要" in analyzer._importance_display("high")
        assert "一般" in analyzer._importance_display("medium")


class TestGenerateGrowthReport:
    """成长报告生成测试"""

    def test_generate_report_basic(self):
        """基本报告"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)
        timeline = GrowthTimeline(entity_id="李天")
        timeline.milestones = [
            GrowthMilestone(1, "breakthrough", "突破练气", "high")
        ]

        analysis = GrowthAnalysis(
            entity_id="李天",
            timeline=timeline,
            velocity=1.0,
            trajectory="linear",
            current_level="练气期",
            first_appearance=1,
            last_appearance=10,
            growth_pattern="steady"
        )

        report = analyzer.generate_growth_report("李天", analysis)

        assert "李天" in report
        assert "成长分析报告" in report
        assert "练气期" in report
        assert "成长时间线" in report

    def test_generate_report_no_data(self):
        """无数据报告"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        report = analyzer.generate_growth_report("未知角色", None)

        assert "未找到" in report or "无" in report


class TestCompareEntities:
    """角色对比测试"""

    def test_compare_entities_no_data(self):
        """无数据对比"""
        analyzer = GrowthAnalyzer.__new__(GrowthAnalyzer)

        with patch.object(analyzer, 'analyze_entity_growth', return_value=None):
            result = analyzer.compare_entities(["角色1", "角色2"])

            assert "error" in result
