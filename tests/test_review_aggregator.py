#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试审查汇总器
"""

import pytest
from pathlib import Path
import sys

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.review_aggregator import (
    ReviewAggregator, AgentResult, Issue, AggregatedReport, Severity
)


class TestIssue:
    """测试 Issue 数据类"""

    def test_create(self):
        """测试创建问题"""
        issue = Issue(
            agent="consistency-checker",
            severity=Severity.HIGH,
            category="power_conflict",
            description="主角筑基期使用金丹技能",
            location="第3段",
            suggestion="替换为筑基期技能"
        )

        assert issue.agent == "consistency-checker"
        assert issue.severity == Severity.HIGH
        assert issue.category == "power_conflict"

    def test_severity_values(self):
        """测试严重程度枚举"""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"


class TestAgentResult:
    """测试 AgentResult 数据类"""

    def test_create(self):
        """测试创建结果"""
        result = AgentResult(
            agent_name="consistency-checker",
            overall_score=85.0,
            passed=True,
            issues=[],
            execution_time=1.5
        )

        assert result.agent_name == "consistency-checker"
        assert result.overall_score == 85.0
        assert result.passed is True
        assert result.issues == []

    def test_with_issues(self):
        """测试带问题的结果"""
        issues = [
            Issue("test", Severity.MEDIUM, "test", "测试问题")
        ]
        result = AgentResult(
            agent_name="test-agent",
            overall_score=70.0,
            passed=False,
            issues=issues
        )

        assert len(result.issues) == 1


class TestReviewAggregator:
    """测试审查汇总器"""

    def test_init(self):
        """测试初始化"""
        aggregator = ReviewAggregator(chapter=1)
        assert aggregator.chapter == 1
        assert len(aggregator.results) == 0

    def test_add_result(self):
        """测试添加结果"""
        aggregator = ReviewAggregator(chapter=1)
        result = AgentResult(
            agent_name="consistency-checker",
            overall_score=90.0,
            passed=True
        )
        aggregator.add_result(result)

        assert len(aggregator.results) == 1

    def test_add_result_from_dict(self):
        """测试从字典添加结果"""
        aggregator = ReviewAggregator(chapter=1)
        data = {
            "agent": "test-agent",
            "overall_score": 85,
            "pass": True,
            "issues": [
                {
                    "severity": "medium",
                    "category": "test",
                    "description": "测试问题"
                }
            ]
        }
        aggregator.add_result_from_dict(data)

        assert len(aggregator.results) == 1
        assert aggregator.results[0].agent_name == "test-agent"
        assert len(aggregator.results[0].issues) == 1

    def test_calculate_overall_score_single(self):
        """测试单个 Agent 评分"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult("agent1", 80.0, True))

        score = aggregator.calculate_overall_score()
        assert score == 80.0

    def test_calculate_overall_score_multiple(self):
        """测试多个 Agent 加权评分"""
        aggregator = ReviewAggregator(chapter=1)
        # 默认权重都是1.0
        aggregator.add_result(AgentResult("consistency-checker", 90.0, True))
        aggregator.add_result(AgentResult("ooc-checker", 80.0, True))

        score = aggregator.calculate_overall_score()
        assert score == 85.0  # (90 + 80) / 2

    def test_classify_issues(self):
        """测试问题分类"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult(
            "agent1", 70.0, False,
            issues=[
                Issue("agent1", Severity.CRITICAL, "cat1", "critical问题"),
                Issue("agent1", Severity.HIGH, "cat2", "high问题"),
                Issue("agent1", Severity.MEDIUM, "cat3", "medium问题"),
                Issue("agent1", Severity.LOW, "cat4", "low问题"),
            ]
        ))

        classified = aggregator.classify_issues()

        assert len(classified["critical"]) == 1
        assert len(classified["high"]) == 1
        assert len(classified["medium"]) == 1
        assert len(classified["low"]) == 1

    def test_generate_auto_fix_suggestions(self):
        """测试自动修复建议生成"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult(
            "agent1", 70.0, False,
            issues=[
                Issue("agent1", Severity.CRITICAL, "cat1", "必须修复", suggestion="修复方案1"),
                Issue("agent1", Severity.HIGH, "cat2", "建议修复", suggestion="修复方案2"),
            ]
        ))

        suggestions = aggregator.generate_auto_fix_suggestions()

        assert len(suggestions) == 2
        assert suggestions[0]["priority"] == 1  # critical 优先
        assert suggestions[1]["priority"] == 2  # high 次之

    def test_aggregate(self):
        """测试汇总"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult("agent1", 90.0, True))
        aggregator.add_result(AgentResult("agent2", 80.0, True))

        report = aggregator.aggregate()

        assert report.chapter == 1
        assert report.overall_score == 85.0
        assert report.passed is True  # >= 85

    def test_aggregate_fail(self):
        """测试未通过汇总"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult("agent1", 70.0, False))

        report = aggregator.aggregate()

        assert report.overall_score == 70.0
        assert report.passed is False  # < 85

    def test_to_dict(self):
        """测试字典输出"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult("agent1", 90.0, True))

        data = aggregator.to_dict()

        assert data["chapter"] == 1
        assert data["overall_score"] == 90.0
        assert data["passed"] is True
        assert "agents" in data
        assert "issue_summary" in data

    def test_to_markdown(self):
        """测试 Markdown 输出"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult("consistency-checker", 90.0, True))

        md = aggregator.to_markdown()

        assert "# 第1章审查报告" in md
        assert "90.0/100" in md
        assert "consistency-checker" in md

    def test_markdown_with_issues(self):
        """测试带问题的 Markdown 输出"""
        aggregator = ReviewAggregator(chapter=1)
        aggregator.add_result(AgentResult(
            "consistency-checker", 70.0, False,
            issues=[
                Issue("consistency-checker", Severity.CRITICAL, "power", "战力冲突", suggestion="修复战力")
            ]
        ))

        md = aggregator.to_markdown()

        assert "Critical 问题" in md
        assert "战力冲突" in md


class TestAggregatedReport:
    """测试汇总报告数据类"""

    def test_create(self):
        """测试创建报告"""
        report = AggregatedReport(
            chapter=1,
            overall_score=90.0,
            passed=True
        )

        assert report.chapter == 1
        assert report.overall_score == 90.0
        assert report.passed is True
        assert report.critical_issues == []
        assert report.high_issues == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
