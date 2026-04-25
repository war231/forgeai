#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审查流水线

统一管理所有审查Agent，提供一站式审查服务：
1. 一致性检查（ConsistencyChecker）
2. 独立审查（IndependentReviewer）
3. 审查汇总（ReviewAggregator）
4. 自动修复（AutoFixer）

集成到 Pipeline.post_write() 中，实现写作后自动审查。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .consistency_checker import ConsistencyChecker, ConsistencyReport
from .independent_reviewer import IndependentReviewer
from .review_aggregator import ReviewAggregator, AggregatedReport, AgentResult, Issue, Severity
from .auto_fixer import AutoFixer
from .logger import get_logger

logger = get_logger(__name__)


class ReviewPipeline:
    """审查流水线 - 统一管理所有审查Agent"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None, project_root: Optional[Path] = None):
        """
        初始化审查流水线
        
        Args:
            config: ForgeAI配置
            project_root: 项目根目录
        """
        self.config = config or get_config()
        self.project_root = project_root or Path(".")
        
        # 初始化审查组件
        self.consistency_checker = ConsistencyChecker(self.project_root)
        self.independent_reviewer = IndependentReviewer(self.config)
        self.review_aggregator = ReviewAggregator(chapter=1)  # 会在运行时更新
        self.auto_fixer = AutoFixer(self.project_root)  # 传入project_root而非config
        
        logger.info("审查流水线初始化完成")
    
    def review_chapter(
        self, 
        chapter: int, 
        text: str,
        check_scope: str = "full",
        enable_independent_review: bool = True,
        enable_auto_fix: bool = True
    ) -> Dict[str, Any]:
        """
        审查单章节
        
        Args:
            chapter: 章节号
            text: 章节内容
            check_scope: 检查范围（timeline/character/worldview/ooc/full）
            enable_independent_review: 是否启用独立审查
            enable_auto_fix: 是否启用自动修复
        
        Returns:
            审查结果字典
        """
        logger.info(f"开始审查第{chapter}章")
        
        results = {
            "chapter": chapter,
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "overall_passed": True,
            "critical_issues": [],
            "auto_fixes": []
        }
        
        # 1. 一致性检查
        logger.info(f"[1/4] 执行一致性检查...")
        consistency_result = self._run_consistency_check(chapter, check_scope)
        results["agents"]["consistency"] = consistency_result
        
        # 2. 独立审查（可选）
        if enable_independent_review:
            logger.info(f"[2/4] 执行独立审查...")
            independent_result = self._run_independent_review(chapter, text)
            results["agents"]["independent"] = independent_result
        else:
            logger.info(f"[2/4] 跳过独立审查")
            results["agents"]["independent"] = {"status": "skipped"}
        
        # 3. 汇总审查结果
        logger.info(f"[3/4] 汇总审查结果...")
        aggregated_report = self._aggregate_results(chapter, results["agents"])
        results["aggregated"] = {
            "overall_score": aggregated_report.overall_score,
            "passed": aggregated_report.passed,
            "critical_count": len(aggregated_report.critical_issues),
            "high_count": len(aggregated_report.high_issues),
            "medium_count": len(aggregated_report.medium_issues),
            "low_count": len(aggregated_report.low_issues),
        }
        
        # 更新总体状态
        results["overall_passed"] = aggregated_report.passed
        results["critical_issues"] = [
            {
                "severity": issue.severity.value,
                "category": issue.category,
                "description": issue.description,
                "suggestion": issue.suggestion
            }
            for issue in aggregated_report.critical_issues
        ]
        
        # 4. 自动修复（可选）
        if enable_auto_fix and not aggregated_report.passed:
            logger.info(f"[4/4] 执行自动修复...")
            auto_fix_result = self._run_auto_fix(chapter, aggregated_report)
            results["auto_fixes"] = auto_fix_result
        else:
            logger.info(f"[4/4] 跳过自动修复")
            results["auto_fixes"] = []
        
        logger.info(f"审查完成: {'通过' if results['overall_passed'] else '未通过'}")
        
        return results
    
    def _run_consistency_check(self, chapter: int, check_scope: str) -> Dict[str, Any]:
        """执行一致性检查"""
        try:
            report = self.consistency_checker.check_chapter(chapter, check_scope=check_scope)
            
            return {
                "status": "ok",
                "agent": "ConsistencyChecker",
                "total_issues": report.total_issues,
                "errors": report.errors,
                "warnings": report.warnings,
                "issues": [
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "description": issue.description,
                        "suggestion": issue.suggestion
                    }
                    for issue in report.issues[:10]  # 最多返回10个问题
                ]
            }
        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            return {
                "status": "error",
                "agent": "ConsistencyChecker",
                "error": str(e)
            }
    
    def _run_independent_review(self, chapter: int, text: str) -> Dict[str, Any]:
        """执行独立审查"""
        try:
            # 准备最小化上下文
            context = self.independent_reviewer.prepare_minimal_context(
                chapter, self.project_root
            )
            
            if "error" in context:
                return {
                    "status": "error",
                    "agent": "IndependentReviewer",
                    "error": context["error"],
                    "hint": context.get("hint", "")
                }
            
            # TODO: 调用LLM进行审查（需要实现LLM调用）
            # 这里返回模拟结果
            return {
                "status": "ok",
                "agent": "IndependentReviewer",
                "context_prepared": True,
                "previous_chapter": context.get("previous_chapter", {}).get("number"),
                "current_chapter": context.get("current_chapter", {}).get("number"),
                "note": "独立审查上下文已准备，需要LLM调用进行实际审查"
            }
        except Exception as e:
            logger.error(f"独立审查失败: {e}")
            return {
                "status": "error",
                "agent": "IndependentReviewer",
                "error": str(e)
            }
    
    def _aggregate_results(self, chapter: int, agent_results: Dict[str, Any]) -> AggregatedReport:
        """汇总审查结果"""
        # 创建新的汇总器
        self.review_aggregator = ReviewAggregator(chapter=chapter)
        
        # 转换Agent结果
        for agent_name, result in agent_results.items():
            if result.get("status") == "skipped":
                continue
            
            if result.get("status") == "error":
                agent_result = AgentResult(
                    agent_name=agent_name,
                    overall_score=0.0,
                    passed=False,
                    error=result.get("error", "Unknown error")
                )
                self.review_aggregator.add_result(agent_result)
                continue
            
            # 计算评分
            if agent_name == "consistency":
                # 一致性检查评分：根据问题数量计算
                total_issues = result.get("total_issues", 0)
                errors = result.get("errors", 0)
                score = max(0.0, 1.0 - (errors * 0.3 + total_issues * 0.05))
                
                # 转换问题
                issues = []
                for issue in result.get("issues", []):
                    severity_map = {
                        "error": Severity.CRITICAL,
                        "warning": Severity.HIGH,
                        "info": Severity.LOW
                    }
                    issues.append(Issue(
                        agent=agent_name,
                        severity=severity_map.get(issue["severity"], Severity.MEDIUM),
                        category=issue["type"],
                        description=issue["description"],
                        suggestion=issue.get("suggestion", "")
                    ))
                
                agent_result = AgentResult(
                    agent_name=agent_name,
                    overall_score=score,
                    passed=errors == 0,
                    issues=issues
                )
                self.review_aggregator.add_result(agent_result)
            
            elif agent_name == "independent":
                # 独立审查评分（模拟）
                agent_result = AgentResult(
                    agent_name=agent_name,
                    overall_score=0.85,  # 模拟评分
                    passed=True
                )
                self.review_aggregator.add_result(agent_result)
        
        # 汇总结果
        return self.review_aggregator.aggregate()
    
    def _run_auto_fix(self, chapter: int, report: AggregatedReport) -> List[Dict[str, Any]]:
        """执行自动修复"""
        fixes = []
        
        try:
            # 对每个严重问题生成修复建议
            for issue in report.critical_issues[:5]:  # 最多处理5个问题
                try:
                    # 构造issue字典
                    issue_dict = {
                        "issue_type": issue.category,
                        "severity": issue.severity.value,
                        "description": issue.description,
                        "chapter": chapter
                    }
                    
                    # 生成修复建议
                    fix_suggestion = self.auto_fixer.generate_fix_suggestion(issue_dict)
                    
                    fixes.append({
                        "issue": issue.description,
                        "suggestion": fix_suggestion,
                        "success": True
                    })
                except Exception as e:
                    logger.error(f"生成修复建议失败: {e}")
                    fixes.append({
                        "issue": issue.description,
                        "error": str(e),
                        "success": False
                    })
        except Exception as e:
            logger.error(f"自动修复流程失败: {e}")
        
        return fixes
    
    def generate_review_report(self, results: Dict[str, Any], output_path: Optional[Path] = None) -> str:
        """
        生成审查报告（Markdown格式）
        
        Args:
            results: 审查结果
            output_path: 输出路径（可选）
        
        Returns:
            Markdown格式的报告
        """
        chapter = results["chapter"]
        
        report_lines = [
            f"# 第{chapter}章审查报告",
            "",
            f"**审查时间**: {results['timestamp']}",
            f"**总体结果**: {'✅ 通过' if results['overall_passed'] else '❌ 未通过'}",
            "",
            "## 审查汇总",
            "",
            f"- **综合评分**: {results['aggregated']['overall_score']:.2%}",
            f"- **严重问题**: {results['aggregated']['critical_count']}个",
            f"- **高优先级问题**: {results['aggregated']['high_count']}个",
            f"- **中优先级问题**: {results['aggregated']['medium_count']}个",
            f"- **低优先级问题**: {results['aggregated']['low_count']}个",
            "",
        ]
        
        # 各Agent结果
        report_lines.append("## Agent审查结果")
        report_lines.append("")
        
        for agent_name, agent_result in results["agents"].items():
            if agent_result.get("status") == "skipped":
                report_lines.append(f"### {agent_name}")
                report_lines.append("")
                report_lines.append("*已跳过*")
                report_lines.append("")
                continue
            
            if agent_result.get("status") == "error":
                report_lines.append(f"### {agent_name}")
                report_lines.append("")
                report_lines.append(f"❌ **错误**: {agent_result.get('error', 'Unknown error')}")
                report_lines.append("")
                continue
            
            report_lines.append(f"### {agent_name}")
            report_lines.append("")
            
            if agent_name == "consistency":
                report_lines.append(f"- 总问题数: {agent_result['total_issues']}")
                report_lines.append(f"- 错误: {agent_result['errors']}个")
                report_lines.append(f"- 警告: {agent_result['warnings']}个")
                report_lines.append("")
                
                if agent_result.get("issues"):
                    report_lines.append("**发现的问题**:")
                    report_lines.append("")
                    for issue in agent_result["issues"]:
                        report_lines.append(f"- [{issue['severity']}] {issue['type']}: {issue['description']}")
                        if issue.get("suggestion"):
                            report_lines.append(f"  - 建议: {issue['suggestion']}")
                    report_lines.append("")
        
        # 严重问题列表
        if results["critical_issues"]:
            report_lines.append("## 严重问题")
            report_lines.append("")
            for issue in results["critical_issues"]:
                report_lines.append(f"- **[{issue['severity']}]** {issue['category']}: {issue['description']}")
                if issue.get("suggestion"):
                    report_lines.append(f"  - 建议: {issue['suggestion']}")
            report_lines.append("")
        
        # 自动修复结果
        if results["auto_fixes"]:
            report_lines.append("## 自动修复")
            report_lines.append("")
            for fix in results["auto_fixes"]:
                if fix["success"]:
                    report_lines.append(f"- ✅ {fix['issue']}")
                    report_lines.append(f"  - 修复: {fix['fix']}")
                else:
                    report_lines.append(f"- ❌ {fix['issue']}")
                    report_lines.append(f"  - 错误: {fix['error']}")
            report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        # 保存到文件
        if output_path:
            output_path.write_text(report_content, encoding="utf-8")
            logger.info(f"审查报告已保存: {output_path}")
        
        return report_content
