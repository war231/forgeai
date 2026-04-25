#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节优化器

支持多轮迭代优化章节内容
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .cloud_llm_client import CloudLLMClient
from .humanize_scorer import HumanizeScorer
from .review_pipeline import ReviewPipeline
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationRound:
    """优化轮次"""
    round_num: int
    original_score: float = 0.0
    optimized_score: float = 0.0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    content_before: str = ""
    content_after: str = ""


@dataclass
class OptimizationResult:
    """优化结果"""
    chapter_num: int
    rounds: List[OptimizationRound] = field(default_factory=list)
    final_content: str = ""
    final_score: float = 0.0
    total_improvement: float = 0.0
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_num": self.chapter_num,
            "rounds": [
                {
                    "round_num": r.round_num,
                    "original_score": r.original_score,
                    "optimized_score": r.optimized_score,
                    "improvement": r.optimized_score - r.original_score,
                    "issues_count": len(r.issues),
                    "fixes_count": len(r.fixes),
                }
                for r in self.rounds
            ],
            "final_score": self.final_score,
            "total_improvement": self.total_improvement,
            "success": self.success,
        }


class ChapterOptimizer:
    """章节优化器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.llm_client = CloudLLMClient(self.config)
        self.humanize_scorer = HumanizeScorer(self.config)
        self.review_pipeline = ReviewPipeline(self.config)
    
    async def optimize_chapter(self,
                               chapter_num: int,
                               content: str,
                               max_rounds: int = 3,
                               target_score: float = 0.7,
                               enable_review: bool = True) -> OptimizationResult:
        """
        优化章节
        
        Args:
            chapter_num: 章节号
            content: 章节内容
            max_rounds: 最大优化轮次
            target_score: 目标分数
            enable_review: 是否启用审查
        
        Returns:
            优化结果
        """
        result = OptimizationResult(chapter_num=chapter_num)
        current_content = content
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"优化第 {round_num} 轮...")
            
            # 创建优化轮次
            opt_round = OptimizationRound(round_num=round_num)
            opt_round.content_before = current_content
            
            # Step 1: 评分
            score_result = self.humanize_scorer.rule_based_score(current_content)
            opt_round.original_score = score_result.score
            
            logger.info(f"  当前分数: {score_result.score:.3f}")
            
            # 检查是否达到目标
            if score_result.score >= target_score:
                logger.info(f"  已达到目标分数 {target_score}")
                opt_round.optimized_score = score_result.score
                opt_round.content_after = current_content
                result.rounds.append(opt_round)
                break
            
            # Step 2: 审查（可选）
            if enable_review:
                logger.info(f"  执行审查...")
                review_result = self.review_pipeline.review_chapter(
                    chapter=chapter_num,
                    text=current_content,
                    check_scope="quick",
                    enable_independent_review=False,
                    enable_auto_fix=False,
                )
                
                # 提取问题
                issues = review_result.get("critical_issues", [])
                opt_round.issues = issues[:5]  # 最多5个问题
                
                logger.info(f"  发现 {len(issues)} 个问题")
            
            # Step 3: 生成优化提示词
            optimization_prompt = self._build_optimization_prompt(
                current_content, score_result, opt_round.issues
            )
            
            # Step 4: 调用 LLM 优化
            logger.info(f"  调用 LLM 优化...")
            response = await self.llm_client.chat_completion_async(
                messages=[{"role": "user", "content": optimization_prompt}],
                temperature=0.7,
                max_tokens=4000,
            )
            
            optimized_content = response.get("content", "")
            
            # 清理内容
            optimized_content = self._clean_content(optimized_content)
            
            # Step 5: 重新评分
            new_score_result = self.humanize_scorer.rule_based_score(optimized_content)
            opt_round.optimized_score = new_score_result.score
            opt_round.content_after = optimized_content
            
            improvement = opt_round.optimized_score - opt_round.original_score
            logger.info(f"  优化后分数: {opt_round.optimized_score:.3f} (提升 {improvement:.3f})")
            
            # 记录修复
            if improvement > 0:
                opt_round.fixes.append(f"分数提升 {improvement:.3f}")
            
            result.rounds.append(opt_round)
            
            # 更新当前内容
            current_content = optimized_content
            
            # 检查是否有改进
            if improvement <= 0:
                logger.info(f"  无改进，停止优化")
                break
        
        # 计算总体改进
        if result.rounds:
            result.final_content = result.rounds[-1].content_after
            result.final_score = result.rounds[-1].optimized_score
            
            initial_score = result.rounds[0].original_score
            result.total_improvement = result.final_score - initial_score
        
        logger.info(f"优化完成: 最终分数 {result.final_score:.3f}, 总提升 {result.total_improvement:.3f}")
        
        return result
    
    def _build_optimization_prompt(self,
                                   content: str,
                                   score_result: Any,
                                   issues: List[Dict[str, Any]]) -> str:
        """构建优化提示词"""
        lines = [
            "# 任务: 优化章节内容",
            "",
            "## 当前评分",
            f"- 分数: {score_result.score:.3f}/1.0",
            f"- AI模式数量: {len(score_result.ai_patterns)}",
            "",
        ]
        
        # AI 模式
        if score_result.ai_patterns:
            lines.append("## 检测到的AI写作模式")
            for pattern in score_result.ai_patterns[:5]:
                lines.append(f"- {pattern.get('name', '未知')}: {pattern.get('count', 0)}次")
            lines.append("")
        
        # 审查问题
        if issues:
            lines.append("## 审查发现的问题")
            for issue in issues[:5]:
                lines.append(f"- [{issue.get('severity', 'unknown')}] {issue.get('description', '')}")
            lines.append("")
        
        # 优化要求
        lines.extend([
            "## 优化要求",
            "",
            "1. 消除AI写作模式:",
            "   - 避免过度使用形容词和副词",
            "   - 避免宣传广告式语言（如'令人...的是'、'不可...的'）",
            "   - 避免夸大象征意义",
            "   - 避免模糊归因（如'有人说'、'众所周知'）",
            "",
            "2. 增强人类写作特征:",
            "   - 使用更自然的中文表达",
            "   - 加入'不完美'的人类写作特征",
            "   - 增强对话感和节奏感",
            "   - 适当使用口语化表达",
            "",
            "3. 保持内容完整性:",
            "   - 不改变核心情节",
            "   - 保持人物性格一致",
            "   - 保持叙事节奏",
            "",
            "4. 解决审查问题:",
            "   - 修复逻辑问题",
            "   - 增强冲突张力",
            "   - 优化节奏控制",
            "",
            "## 原文",
            "---",
            content[:3000],
            "---" if len(content) > 3000 else "",
            "",
            "请输出优化后的章节内容:",
        ])
        
        return "\n".join(lines)
    
    def _clean_content(self, content: str) -> str:
        """清理内容"""
        # 移除可能的标题
        lines = content.split("\n")
        if lines and lines[0].startswith("#"):
            lines = lines[1:]
        
        # 移除代码块标记
        content = "\n".join(lines)
        content = content.replace("```", "")
        
        return content.strip()


# 便捷函数
async def optimize_chapter(chapter_num: int,
                          content: str,
                          max_rounds: int = 3,
                          target_score: float = 0.7,
                          config: Optional[ForgeAIConfig] = None) -> OptimizationResult:
    """优化章节"""
    optimizer = ChapterOptimizer(config)
    return await optimizer.optimize_chapter(
        chapter_num, content, max_rounds, target_score
    )
