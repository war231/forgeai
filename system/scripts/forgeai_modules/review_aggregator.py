#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审查结果汇总器

汇总所有审查 Agent 的结果，生成综合报告。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum


class Severity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"  # 必须修复
    HIGH = "high"          # 强烈建议修复
    MEDIUM = "medium"      # 建议修复
    LOW = "low"            # 可选修复
    INFO = "info"          # 提示信息


@dataclass
class Issue:
    """单个问题"""
    agent: str
    severity: Severity
    category: str
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class AgentResult:
    """单个 Agent 的审查结果"""
    agent_name: str
    overall_score: float
    passed: bool
    issues: List[Issue] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass
class AggregatedReport:
    """汇总报告"""
    chapter: int
    overall_score: float
    passed: bool
    agent_results: List[AgentResult] = field(default_factory=list)
    critical_issues: List[Issue] = field(default_factory=list)
    high_issues: List[Issue] = field(default_factory=list)
    medium_issues: List[Issue] = field(default_factory=list)
    low_issues: List[Issue] = field(default_factory=list)
    auto_fix_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ReviewAggregator:
    """
    审查结果汇总器

    功能：
    1. 汇总多个 Agent 的审查结果
    2. 按严重程度分类问题
    3. 计算综合评分
    4. 生成修复建议
    5. 输出 Markdown 报告
    """

    # Agent 权重（用于计算综合评分）
    AGENT_WEIGHTS = {
        "consistency-checker": 1.0,
        "ooc-checker": 1.0,
        "continuity-checker": 1.0,
        "reader-pull-checker": 1.0,
        "high-point-checker": 0.8,
        "pacing-checker": 0.8,
        "timeline-agent": 0.9,
    }

    # 通过阈值
    PASS_THRESHOLD = 85.0

    def __init__(self, chapter: int):
        self.chapter = chapter
        self.results: List[AgentResult] = []

    def add_result(self, result: AgentResult) -> None:
        """添加一个 Agent 的审查结果"""
        self.results.append(result)

    def add_result_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典添加结果"""
        issues = []
        for i in data.get("issues", []):
            issues.append(Issue(
                agent=data.get("agent", "unknown"),
                severity=Severity(i.get("severity", "medium")),
                category=i.get("category", "general"),
                description=i.get("description", ""),
                location=i.get("location"),
                suggestion=i.get("suggestion")
            ))

        result = AgentResult(
            agent_name=data.get("agent", "unknown"),
            overall_score=data.get("overall_score", 0),
            passed=data.get("pass", False),
            issues=issues,
            execution_time=data.get("execution_time", 0),
            error=data.get("error")
        )
        self.add_result(result)

    def calculate_overall_score(self) -> float:
        """计算加权综合评分"""
        if not self.results:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for result in self.results:
            weight = self.AGENT_WEIGHTS.get(result.agent_name, 1.0)
            weighted_sum += result.overall_score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 1)

    def classify_issues(self) -> Dict[str, List[Issue]]:
        """按严重程度分类问题"""
        classified = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": []
        }

        for result in self.results:
            for issue in result.issues:
                severity = issue.severity.value if isinstance(issue.severity, Severity) else issue.severity
                if severity in classified:
                    classified[severity].append(issue)

        return classified

    def generate_auto_fix_suggestions(self) -> List[Dict[str, Any]]:
        """生成自动修复建议"""
        suggestions = []
        classified = self.classify_issues()

        # 处理 critical 问题
        for issue in classified["critical"]:
            suggestions.append({
                "priority": 1,
                "issue": issue.description,
                "agent": issue.agent,
                "suggestion": issue.suggestion or "需要人工检查并修复",
                "auto_fixable": False
            })

        # 处理 high 问题
        for issue in classified["high"]:
            suggestions.append({
                "priority": 2,
                "issue": issue.description,
                "agent": issue.agent,
                "suggestion": issue.suggestion or "建议修复",
                "auto_fixable": True  # 部分 high 问题可自动修复
            })

        return suggestions

    def aggregate(self) -> AggregatedReport:
        """生成汇总报告"""
        classified = self.classify_issues()
        overall_score = self.calculate_overall_score()

        return AggregatedReport(
            chapter=self.chapter,
            overall_score=overall_score,
            passed=overall_score >= self.PASS_THRESHOLD,
            agent_results=self.results,
            critical_issues=classified["critical"],
            high_issues=classified["high"],
            medium_issues=classified["medium"],
            low_issues=classified["low"],
            auto_fix_suggestions=self.generate_auto_fix_suggestions()
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        report = self.aggregate()

        return {
            "chapter": report.chapter,
            "overall_score": report.overall_score,
            "passed": report.passed,
            "pass_threshold": self.PASS_THRESHOLD,
            "timestamp": report.timestamp,
            "agent_count": len(report.agent_results),
            "agents": [
                {
                    "name": r.agent_name,
                    "score": r.overall_score,
                    "passed": r.passed,
                    "issue_count": len(r.issues),
                    "error": r.error
                }
                for r in report.agent_results
            ],
            "issue_summary": {
                "critical": len(report.critical_issues),
                "high": len(report.high_issues),
                "medium": len(report.medium_issues),
                "low": len(report.low_issues)
            },
            "critical_issues": [
                {
                    "agent": i.agent,
                    "category": i.category,
                    "description": i.description,
                    "location": i.location,
                    "suggestion": i.suggestion
                }
                for i in report.critical_issues
            ],
            "high_issues": [
                {
                    "agent": i.agent,
                    "category": i.category,
                    "description": i.description,
                    "location": i.location,
                    "suggestion": i.suggestion
                }
                for i in report.high_issues
            ],
            "auto_fix_suggestions": report.auto_fix_suggestions
        }

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        report = self.aggregate()

        lines = [
            f"# 第{self.chapter}章审查报告",
            "",
            f"**综合评分**: {report.overall_score}/100",
            f"**状态**: {'✅ 通过' if report.passed else '❌ 需要修复'}",
            f"**时间**: {report.timestamp}",
            "",
            "---",
            "",
            "## Agent 评分汇总",
            "",
            "| Agent | 评分 | 状态 | 问题数 |",
            "|-------|------|------|--------|",
        ]

        for r in report.agent_results:
            status = "✅" if r.passed else "❌"
            lines.append(f"| {r.agent_name} | {r.overall_score} | {status} | {len(r.issues)} |")

        lines.extend([
            "",
            "---",
            "",
            "## 问题统计",
            "",
            f"| 严重程度 | 数量 |",
            f"|----------|------|",
            f"| 🔴 Critical | {len(report.critical_issues)} |",
            f"| 🟠 High | {len(report.high_issues)} |",
            f"| 🟡 Medium | {len(report.medium_issues)} |",
            f"| 🟢 Low | {len(report.low_issues)} |",
        ])

        if report.critical_issues:
            lines.extend([
                "",
                "## 🔴 Critical 问题（必须修复）",
                "",
            ])
            for i, issue in enumerate(report.critical_issues, 1):
                lines.append(f"### {i}. {issue.description}")
                if issue.location:
                    lines.append(f"- **位置**: {issue.location}")
                if issue.suggestion:
                    lines.append(f"- **建议**: {issue.suggestion}")
                lines.append("")

        if report.high_issues:
            lines.extend([
                "",
                "## 🟠 High 问题（强烈建议修复）",
                "",
            ])
            for i, issue in enumerate(report.high_issues, 1):
                lines.append(f"### {i}. {issue.description}")
                if issue.location:
                    lines.append(f"- **位置**: {issue.location}")
                if issue.suggestion:
                    lines.append(f"- **建议**: {issue.suggestion}")
                lines.append("")

        if report.auto_fix_suggestions:
            lines.extend([
                "",
                "## 🔧 修复建议",
                "",
            ])
            for s in report.auto_fix_suggestions[:5]:  # 最多显示5条
                priority_icon = "🔴" if s["priority"] == 1 else "🟠"
                lines.append(f"{priority_icon} **{s['issue']}**")
                lines.append(f"   - 建议: {s['suggestion']}")
                lines.append("")

        return "\n".join(lines)

    def save(self, filepath: Path) -> None:
        """保存报告"""
        data = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_markdown(self, filepath: Path) -> None:
        """保存 Markdown 报告"""
        content = self.to_markdown()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
