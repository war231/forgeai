#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考融入器

将样板书分析结果和题材配置融入章节创作
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .genre_profile_loader import GenreProfileLoader, GenreProfile, ReadingPowerTaxonomy


@dataclass
class BookAnalysisResult:
    """样板书分析结果"""
    # 结构数据
    chapter_count: int = 0
    total_words: int = 0
    avg_word_count: float = 0
    rhythm_ratio: Dict[str, float] = field(default_factory=dict)  # 铺垫/冲突/高潮
    
    # 爽点数据
    trophy_density: float = 0
    trophy_distribution: Dict[str, int] = field(default_factory=dict)
    high_density_chapters: List[int] = field(default_factory=list)
    
    # 文风数据
    avg_sentence_length: float = 0
    dialogue_ratio: float = 0
    opening_modes: Dict[str, int] = field(default_factory=dict)
    ending_modes: Dict[str, int] = field(default_factory=dict)
    
    # 套路数据
    main_patterns: List[str] = field(default_factory=list)
    hook_types: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookAnalysisResult":
        """从字典创建"""
        structure = data.get("structure", {})
        trophy = data.get("trophy", {})
        style = data.get("style", {})
        
        return cls(
            chapter_count=structure.get("chapter_count", 0),
            total_words=structure.get("total_words", 0),
            avg_word_count=structure.get("avg_word_count", 0),
            rhythm_ratio=structure.get("rhythm", {}),
            trophy_density=trophy.get("density", 0),
            trophy_distribution=trophy.get("distribution", {}),
            high_density_chapters=trophy.get("high_density_chapters", []),
            avg_sentence_length=style.get("avg_sentence_length", 0),
            dialogue_ratio=style.get("dialogue_ratio", 0),
            opening_modes=style.get("opening_modes", {}),
            ending_modes=style.get("ending_modes", {}),
            main_patterns=list(trophy.get("distribution", {}).keys())[:3],
            hook_types=[],
        )


@dataclass
class IntegratedContext:
    """融合后的创作上下文"""
    # 基础信息
    genre: str = ""
    chapter_num: int = 0
    
    # 题材配置
    genre_profile: Optional[GenreProfile] = None
    
    # 样板书参考
    book_analysis: Optional[BookAnalysisResult] = None
    
    # 钩子指导
    hook_guidance: Dict[str, Any] = field(default_factory=dict)
    
    # 爽点模式指导
    pattern_guidance: Dict[str, Any] = field(default_factory=dict)
    
    # 微兑现建议
    micro_payoff_suggestions: List[Dict[str, str]] = field(default_factory=list)
    
    # 节奏建议
    rhythm_suggestion: Dict[str, Any] = field(default_factory=dict)
    
    # 文风参考
    style_reference: Dict[str, Any] = field(default_factory=dict)
    
    # 创作提示词片段
    prompt_fragments: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "genre": self.genre,
            "chapter_num": self.chapter_num,
            "genre_profile": self.genre_profile.to_dict() if self.genre_profile else None,
            "book_analysis": {
                "trophy_density": self.book_analysis.trophy_density if self.book_analysis else 0,
                "main_patterns": self.book_analysis.main_patterns if self.book_analysis else [],
            },
            "hook_guidance": self.hook_guidance,
            "pattern_guidance": self.pattern_guidance,
            "micro_payoff_suggestions": self.micro_payoff_suggestions,
            "rhythm_suggestion": self.rhythm_suggestion,
            "style_reference": self.style_reference,
            "prompt_fragments": self.prompt_fragments,
        }


class ReferenceIntegrator:
    """参考融入器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.profile_loader = GenreProfileLoader(self.config)
    
    def integrate(self, 
                  genre: str,
                  chapter_num: int,
                  book_analysis: Optional[BookAnalysisResult] = None,
                  chapter_type: str = "normal") -> IntegratedContext:
        """
        融合参考数据
        
        Args:
            genre: 题材名称
            chapter_num: 章节号
            book_analysis: 样板书分析结果
            chapter_type: 章节类型 (normal/climax/transition)
        
        Returns:
            融合后的创作上下文
        """
        context = IntegratedContext(
            genre=genre,
            chapter_num=chapter_num,
            book_analysis=book_analysis,
        )
        
        # 1. 加载题材配置
        context.genre_profile = self.profile_loader.get_profile(genre)
        
        # 2. 获取钩子指导
        context.hook_guidance = self.profile_loader.get_hook_guidance(genre, chapter_type)
        
        # 3. 获取爽点模式指导
        context.pattern_guidance = self.profile_loader.get_pattern_guidance(genre)
        
        # 4. 获取微兑现建议
        context.micro_payoff_suggestions = self.profile_loader.get_micro_payoff_suggestions(genre)
        
        # 5. 计算节奏建议
        context.rhythm_suggestion = self._calculate_rhythm_suggestion(
            chapter_num, context.genre_profile, book_analysis
        )
        
        # 6. 提取文风参考
        context.style_reference = self._extract_style_reference(book_analysis)
        
        # 7. 生成创作提示词片段
        context.prompt_fragments = self._generate_prompt_fragments(context)
        
        return context
    
    def _calculate_rhythm_suggestion(self,
                                     chapter_num: int,
                                     profile: Optional[GenreProfile],
                                     book_analysis: Optional[BookAnalysisResult]) -> Dict[str, Any]:
        """计算节奏建议"""
        suggestion = {
            "target_word_count": 3000,  # 默认目标字数
            "rhythm_ratio": {"铺垫": 30, "冲突": 40, "高潮": 30},
            "strand_balance": {"Quest": 60, "Fire": 20, "Constellation": 20},
        }
        
        if profile:
            # 根据题材调整字数
            density_map = {
                "high": 2500,  # 爽点密度高，章长短
                "medium": 3000,
                "low": 3500,   # 爽点密度低，章长长
            }
            suggestion["target_word_count"] = density_map.get(
                profile.density_per_chapter, 3000
            )
            
            # Strand 平衡
            suggestion["strand_balance"] = {
                "Quest": 60,
                "Fire": 20,
                "Constellation": 20,
            }
        
        if book_analysis:
            # 参考样板书的节奏
            if book_analysis.rhythm_ratio:
                suggestion["rhythm_ratio"] = book_analysis.rhythm_ratio
            
            # 参考样板书的字数
            if book_analysis.avg_word_count > 0:
                suggestion["target_word_count"] = int(book_analysis.avg_word_count)
        
        return suggestion
    
    def _extract_style_reference(self, 
                                 book_analysis: Optional[BookAnalysisResult]) -> Dict[str, Any]:
        """提取文风参考"""
        reference = {
            "avg_sentence_length": 25,
            "dialogue_ratio": 30,
            "preferred_opening": "场景切入",
            "preferred_ending": "悬念钩子",
        }
        
        if not book_analysis:
            return reference
        
        # 句长
        if book_analysis.avg_sentence_length > 0:
            reference["avg_sentence_length"] = book_analysis.avg_sentence_length
        
        # 对白密度
        if book_analysis.dialogue_ratio > 0:
            reference["dialogue_ratio"] = book_analysis.dialogue_ratio
        
        # 开头模式
        if book_analysis.opening_modes:
            preferred = max(book_analysis.opening_modes.items(), key=lambda x: x[1])
            reference["preferred_opening"] = preferred[0]
        
        # 结尾模式
        if book_analysis.ending_modes:
            preferred = max(book_analysis.ending_modes.items(), key=lambda x: x[1])
            reference["preferred_ending"] = preferred[0]
        
        return reference
    
    def _generate_prompt_fragments(self, context: IntegratedContext) -> List[str]:
        """生成创作提示词片段"""
        fragments = []
        
        # 1. 题材风格
        if context.genre_profile:
            fragments.append(f"题材风格: {context.genre_profile.display_name}")
            
            # 钩子偏好
            hooks = context.genre_profile.preferred_hooks[:3]
            if hooks:
                fragments.append(f"推荐钩子类型: {', '.join(hooks)}")
            
            # 爽点模式
            patterns = context.genre_profile.preferred_patterns[:3]
            if patterns:
                fragments.append(f"推荐爽点模式: {', '.join(patterns)}")
        
        # 2. 爽点密度
        if context.pattern_guidance:
            density = context.pattern_guidance.get("density", {})
            min_count = density.get("min", 1)
            target_count = density.get("target", 2)
            fragments.append(f"爽点密度: {min_count}-{target_count} 个/章")
        
        # 3. 微兑现
        if context.micro_payoff_suggestions:
            payoff_names = [p["name"] for p in context.micro_payoff_suggestions[:3]]
            fragments.append(f"微兑现类型: {', '.join(payoff_names)}")
        
        # 4. 节奏建议
        if context.rhythm_suggestion:
            ratio = context.rhythm_suggestion.get("rhythm_ratio", {})
            if ratio:
                fragments.append(
                    f"节奏比例: 铺垫{ratio.get('铺垫', 30)}% / "
                    f"冲突{ratio.get('冲突', 40)}% / "
                    f"高潮{ratio.get('高潮', 30)}%"
                )
            
            word_count = context.rhythm_suggestion.get("target_word_count", 3000)
            fragments.append(f"目标字数: {word_count} 字")
        
        # 5. 文风参考
        if context.style_reference:
            sentence_len = context.style_reference.get("avg_sentence_length", 25)
            dialogue_ratio = context.style_reference.get("dialogue_ratio", 30)
            fragments.append(f"文风参考: 句长{sentence_len:.0f}字, 对白密度{dialogue_ratio:.0f}%")
            
            opening = context.style_reference.get("preferred_opening", "场景切入")
            ending = context.style_reference.get("preferred_ending", "悬念钩子")
            fragments.append(f"开头模式: {opening}, 结尾模式: {ending}")
        
        # 6. 样板书参考
        if context.book_analysis:
            if context.book_analysis.trophy_density > 0:
                fragments.append(
                    f"样板书参考: 爽点密度{context.book_analysis.trophy_density:.1f}个/章"
                )
            
            if context.book_analysis.main_patterns:
                fragments.append(
                    f"样板书主要套路: {', '.join(context.book_analysis.main_patterns)}"
                )
        
        return fragments
    
    def format_context_for_prompt(self, context: IntegratedContext) -> str:
        """将融合上下文格式化为提示词"""
        lines = ["## 创作指导\n"]
        
        # 添加提示词片段
        for fragment in context.prompt_fragments:
            lines.append(f"- {fragment}")
        
        lines.append("")
        
        # 添加钩子指导
        if context.hook_guidance:
            lines.append("### 钩子设计")
            hooks = context.hook_guidance.get("recommended_hooks", [])
            for hook in hooks[:3]:
                lines.append(f"- {hook['name']} ({hook['position']}, 强度: {hook['strength']})")
                lines.append(f"  驱动力: {hook['driver']}")
            lines.append("")
        
        # 添加爽点模式指导
        if context.pattern_guidance:
            lines.append("### 爽点设计")
            patterns = context.pattern_guidance.get("recommended_patterns", [])
            for pattern in patterns[:2]:
                lines.append(f"- {pattern['name']}: {pattern['structure']}")
                phases = pattern.get("phases", {})
                for phase_name, phase_desc in phases.items():
                    lines.append(f"  - {phase_name}: {phase_desc}")
            lines.append("")
        
        # 添加微兑现建议
        if context.micro_payoff_suggestions:
            lines.append("### 微兑现建议")
            for payoff in context.micro_payoff_suggestions[:3]:
                lines.append(f"- {payoff['name']}: {payoff['example']}")
            lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def integrate_references(genre: str,
                        chapter_num: int,
                        book_analysis: Optional[Dict[str, Any]] = None,
                        config: Optional[ForgeAIConfig] = None) -> IntegratedContext:
    """融合参考数据"""
    integrator = ReferenceIntegrator(config)
    
    analysis = None
    if book_analysis:
        analysis = BookAnalysisResult.from_dict(book_analysis)
    
    return integrator.integrate(genre, chapter_num, analysis)
