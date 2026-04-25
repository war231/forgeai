#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审查反馈循环

根据审查结果自动修正章节问题
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .cloud_llm_client import CloudLLMClient
from .review_pipeline import ReviewPipeline
from .auto_fixer import AutoFixer
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class FeedbackRound:
    """反馈轮次"""
    round_num: int
    issues_before: List[Dict[str, Any]] = field(default_factory=list)
    issues_after: List[Dict[str, Any]] = field(default_factory=list)
    auto_fixes: List[Dict[str, Any]] = field(default_factory=list)
    manual_fixes: List[str] = field(default_factory=list)
    content_before: str = ""
    content_after: str = ""


@dataclass
class FeedbackResult:
    """反馈结果"""
    chapter_num: int
    rounds: List[FeedbackRound] = field(default_factory=list)
    final_content: str = ""
    final_issues: List[Dict[str, Any]] = field(default_factory=list)
    total_fixes: int = 0
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_num": self.chapter_num,
            "rounds": [
                {
                    "round_num": r.round_num,
                    "issues_before": len(r.issues_before),
                    "issues_after": len(r.issues_after),
                    "auto_fixes": len(r.auto_fixes),
                    "manual_fixes": len(r.manual_fixes),
                }
                for r in self.rounds
            ],
            "final_issues_count": len(self.final_issues),
            "total_fixes": self.total_fixes,
            "success": self.success,
        }


class ReviewFeedbackLoop:
    """审查反馈循环"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.llm_client = CloudLLMClient(self.config)
        self.review_pipeline = ReviewPipeline(self.config)
        self.auto_fixer = AutoFixer(self.config)
    
    async def apply_feedback(self,
                            chapter_num: int,
                            content: str,
                            max_rounds: int = 2,
                            critical_only: bool = False) -> FeedbackResult:
        """
        应用审查反馈
        
        Args:
            chapter_num: 章节号
            content: 章节内容
            max_rounds: 最大反馈轮次
            critical_only: 是否只处理严重问题
        
        Returns:
            反馈结果
        """
        result = FeedbackResult(chapter_num=chapter_num)
        current_content = content
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"反馈循环第 {round_num} 轮...")
            
            # 创建反馈轮次
            feedback_round = FeedbackRound(round_num=round_num)
            feedback_round.content_before = current_content
            
            # Step 1: 审查章节
            logger.info(f"  审查章节...")
            review_result = self.review_pipeline.review_chapter(
                chapter=chapter_num,
                text=current_content,
                check_scope="full",
                enable_independent_review=True,
                enable_auto_fix=False,
            )
            
            # 提取问题
            issues = review_result.get("critical_issues", [])
            
            if critical_only:
                # 只处理严重问题
                issues = [i for i in issues if i.get("severity") == "critical"]
            
            feedback_round.issues_before = issues
            
            logger.info(f"  发现 {len(issues)} 个问题")
            
            # 检查是否还有问题
            if not issues:
                logger.info(f"  无问题，停止反馈循环")
                feedback_round.content_after = current_content
                result.rounds.append(feedback_round)
                break
            
            # Step 2: 自动修复
            logger.info(f"  尝试自动修复...")
            auto_fixes = []
            
            for issue in issues[:3]:  # 最多修复3个问题
                try:
                    fix_result = self.auto_fixer.fix_issue(
                        current_content, issue
                    )
                    if fix_result.get("success"):
                        current_content = fix_result.get("content", current_content)
                        auto_fixes.append({
                            "issue": issue.get("description", ""),
                            "fix": fix_result.get("description", ""),
                        })
                        logger.info(f"    修复: {issue.get('description', '')[:50]}")
                except Exception as e:
                    logger.warning(f"    自动修复失败: {e}")
            
            feedback_round.auto_fixes = auto_fixes
            
            # Step 3: 手动修复（LLM）
            remaining_issues = [i for i in issues if i not in [f.get("issue") for f in auto_fixes]]
            
            if remaining_issues:
                logger.info(f"  调用 LLM 修复剩余问题...")
                
                fix_prompt = self._build_fix_prompt(current_content, remaining_issues)
                
                response = await self.llm_client.chat_completion_async(
                    messages=[{"role": "user", "content": fix_prompt}],
                    temperature=0.7,
                    max_tokens=4000,
                )
                
                fixed_content = response.get("content", "")
                fixed_content = self._clean_content(fixed_content)
                
                if len(fixed_content) > 100:  # 确保内容有效
                    current_content = fixed_content
                    feedback_round.manual_fixes.append("LLM修复")
            
            # Step 4: 重新审查
            logger.info(f"  重新审查...")
            re_review = self.review_pipeline.review_chapter(
                chapter=chapter_num,
                text=current_content,
                check_scope="quick",
                enable_independent_review=False,
                enable_auto_fix=False,
            )
            
            feedback_round.issues_after = re_review.get("critical_issues", [])
            feedback_round.content_after = current_content
            
            logger.info(f"  剩余问题: {len(feedback_round.issues_after)}")
            
            result.rounds.append(feedback_round)
            
            # 检查是否有改进
            if len(feedback_round.issues_after) >= len(feedback_round.issues_before):
                logger.info(f"  无改进，停止反馈循环")
                break
        
        # 计算总体修复数
        if result.rounds:
            result.final_content = result.rounds[-1].content_after
            result.final_issues = result.rounds[-1].issues_after
            
            for r in result.rounds:
                result.total_fixes += len(r.auto_fixes) + len(r.manual_fixes)
        
        logger.info(f"反馈循环完成: 总修复 {result.total_fixes} 个问题")
        
        return result
    
    def _build_fix_prompt(self,
                         content: str,
                         issues: List[Dict[str, Any]]) -> str:
        """构建修复提示词"""
        lines = [
            "# 任务: 修复章节问题",
            "",
            "## 发现的问题",
            "",
        ]
        
        for i, issue in enumerate(issues[:5], 1):
            lines.append(f"{i}. [{issue.get('severity', 'unknown')}] {issue.get('description', '')}")
            if issue.get('suggestion'):
                lines.append(f"   建议: {issue.get('suggestion')}")
        
        lines.extend([
            "",
            "## 修复要求",
            "",
            "1. 针对每个问题进行修复",
            "2. 保持原文的核心情节和人物性格",
            "3. 保持叙事风格一致",
            "4. 确保修复后逻辑通顺",
            "",
            "## 原文",
            "---",
            content[:3000],
            "---" if len(content) > 3000 else "",
            "",
            "请输出修复后的章节内容:",
        ])
        
        return "\n".join(lines)
    
    def _clean_content(self, content: str) -> str:
        """清理内容"""
        lines = content.split("\n")
        if lines and lines[0].startswith("#"):
            lines = lines[1:]
        
        content = "\n".join(lines)
        content = content.replace("```", "")
        
        return content.strip()


# 便捷函数
async def apply_review_feedback(chapter_num: int,
                               content: str,
                               max_rounds: int = 2,
                               config: Optional[ForgeAIConfig] = None) -> FeedbackResult:
    """应用审查反馈"""
    loop = ReviewFeedbackLoop(config)
    return await loop.apply_feedback(chapter_num, content, max_rounds)
