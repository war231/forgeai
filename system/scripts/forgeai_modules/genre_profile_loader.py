#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题材配置加载器

加载 genre-profiles.md 和 reading-power-taxonomy.md
为章节生成器提供题材相关的配置参数
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig


@dataclass
class GenreProfile:
    """题材配置"""
    name: str
    display_name: str
    preferred_hooks: List[str] = field(default_factory=list)
    preferred_patterns: List[str] = field(default_factory=list)
    density_per_chapter: str = "medium"  # high/medium/low
    min_micropayoff: int = 1
    strand_quest_max: int = 5
    strand_fire_gap_max: int = 12
    stagnation_threshold: int = 4
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "preferred_hooks": self.preferred_hooks,
            "preferred_patterns": self.preferred_patterns,
            "density_per_chapter": self.density_per_chapter,
            "min_micropayoff": self.min_micropayoff,
            "strand_quest_max": self.strand_quest_max,
            "strand_fire_gap_max": self.strand_fire_gap_max,
            "stagnation_threshold": self.stagnation_threshold,
        }


@dataclass
class HookType:
    """钩子类型"""
    name: str
    driver: str  # 驱动力
    applicable_genres: List[str] = field(default_factory=list)


@dataclass
class CoolPointPattern:
    """爽点模式"""
    name: str
    structure: str  # 结构描述
    phases: Dict[str, str] = field(default_factory=dict)  # 铺垫/兑现/余波


@dataclass
class MicroPayoff:
    """微兑现"""
    name: str
    example: str


@dataclass
class ReadingPowerTaxonomy:
    """追读力分类标准"""
    hook_types: Dict[str, HookType] = field(default_factory=dict)
    cool_point_patterns: Dict[str, CoolPointPattern] = field(default_factory=dict)
    micro_payoffs: Dict[str, MicroPayoff] = field(default_factory=dict)
    hard_constraints: Dict[str, str] = field(default_factory=dict)


# 内置题材配置
BUILTIN_PROFILES = {
    "shuangwen": GenreProfile(
        name="shuangwen",
        display_name="爽文/系统流",
        preferred_hooks=["渴望钩", "危机钩", "情绪钩"],
        preferred_patterns=["装逼打脸", "扮猪吃虎", "越级反杀", "迪化误解"],
        density_per_chapter="high",
        min_micropayoff=2,
        strand_quest_max=5,
        strand_fire_gap_max=15,
        stagnation_threshold=3,
    ),
    "xianxia": GenreProfile(
        name="xianxia",
        display_name="修仙/仙侠",
        preferred_hooks=["渴望钩", "危机钩", "悬念钩"],
        preferred_patterns=["越级反杀", "扮猪吃虎", "身份掉马"],
        density_per_chapter="medium",
        min_micropayoff=1,
        strand_quest_max=5,
        strand_fire_gap_max=12,
        stagnation_threshold=4,
    ),
    "urban-power": GenreProfile(
        name="urban-power",
        display_name="都市异能",
        preferred_hooks=["情绪钩", "渴望钩", "危机钩"],
        preferred_patterns=["装逼打脸", "打脸权威", "迪化误解"],
        density_per_chapter="high",
        min_micropayoff=2,
        strand_quest_max=4,
        strand_fire_gap_max=10,
        stagnation_threshold=3,
    ),
    "ancient-romance": GenreProfile(
        name="ancient-romance",
        display_name="古言/宫斗",
        preferred_hooks=["情绪钩", "选择钩", "悬念钩"],
        preferred_patterns=["甜蜜超预期", "反派翻车", "身份掉马"],
        density_per_chapter="medium",
        min_micropayoff=1,
        strand_quest_max=5,
        strand_fire_gap_max=8,
        stagnation_threshold=4,
    ),
    "mystery": GenreProfile(
        name="mystery",
        display_name="悬疑/规则怪谈",
        preferred_hooks=["悬念钩", "危机钩", "选择钩"],
        preferred_patterns=["越级反杀", "反派翻车"],
        density_per_chapter="low",
        min_micropayoff=1,
        strand_quest_max=6,
        strand_fire_gap_max=15,
        stagnation_threshold=4,
    ),
    "scifi": GenreProfile(
        name="scifi",
        display_name="科幻/末世",
        preferred_hooks=["危机钩", "渴望钩", "悬念钩"],
        preferred_patterns=["越级反杀", "扮猪吃虎", "打脸权威"],
        density_per_chapter="medium",
        min_micropayoff=1,
        strand_quest_max=5,
        strand_fire_gap_max=12,
        stagnation_threshold=4,
    ),
    "daily": GenreProfile(
        name="daily",
        display_name="日常/轻松",
        preferred_hooks=["情绪钩", "渴望钩"],
        preferred_patterns=["甜蜜超预期", "迪化误解"],
        density_per_chapter="low",
        min_micropayoff=1,
        strand_quest_max=3,
        strand_fire_gap_max=8,
        stagnation_threshold=5,
    ),
}

# 内置追读力分类标准
BUILTIN_TAXONOMY = ReadingPowerTaxonomy(
    hook_types={
        "危机钩": HookType("危机钩", "危险逼近，读者担心", ["爽文", "悬疑"]),
        "悬念钩": HookType("悬念钩", "信息缺口，读者好奇", ["悬疑", "日常"]),
        "情绪钩": HookType("情绪钩", "强情绪触发（愤怒/心疼/心动）", ["言情", "爽文"]),
        "选择钩": HookType("选择钩", "两难抉择，想知道选择", ["悬疑", "言情"]),
        "渴望钩": HookType("渴望钩", "好事将至，读者期待", ["爽文", "言情"]),
    },
    cool_point_patterns={
        "装逼打脸": CoolPointPattern("装逼打脸", "嘲讽→反转→震惊", {
            "铺垫": "建立嘲讽场景，主角被轻视",
            "兑现": "主角展现实力，反转打脸",
            "余波": "震惊反应，收获认可",
        }),
        "扮猪吃虎": CoolPointPattern("扮猪吃虎", "示弱→暴露→碾压", {
            "铺垫": "主角隐藏实力，示弱低调",
            "兑现": "关键时刻暴露实力，碾压对手",
            "余波": "震惊反应，收获敬畏",
        }),
        "越级反杀": CoolPointPattern("越级反杀", "差距→策略→逆转", {
            "铺垫": "建立实力差距，危机感",
            "兑现": "使用策略/底牌，逆转局势",
            "余波": "收获战利品，实力提升",
        }),
        "打脸权威": CoolPointPattern("打脸权威", "权威→挑战→成功", {
            "铺垫": "权威人物质疑/打压主角",
            "兑现": "主角挑战权威并成功",
            "余波": "权威崩塌，主角地位提升",
        }),
        "反派翻车": CoolPointPattern("反派翻车", "得意→反杀→落幕", {
            "铺垫": "反派得意洋洋，算计主角",
            "兑现": "主角反击，反派自食其果",
            "余波": "反派落幕，收获正义",
        }),
        "甜蜜超预期": CoolPointPattern("甜蜜超预期", "期待→超预期→升华", {
            "铺垫": "建立期待，小期待",
            "兑现": "结果远超预期，惊喜",
            "余波": "关系升华，甜蜜回味",
        }),
        "迪化误解": CoolPointPattern("迪化误解", "随意行为+信息差+脑补+读者优越", {
            "铺垫": "主角随意行为，他人误解",
            "兑现": "他人脑补过度，自我攻略",
            "余波": "读者优越感，喜剧效果",
        }),
        "身份掉马": CoolPointPattern("身份掉马", "长期隐藏+触发事件+揭露+群体反应", {
            "铺垫": "长期隐藏身份，伏笔埋设",
            "兑现": "触发事件揭露身份",
            "余波": "群体震惊反应，地位巨变",
        }),
    },
    micro_payoffs={
        "信息兑现": MicroPayoff("信息兑现", "原来那把钥匙的真正用途是..."),
        "关系兑现": MicroPayoff("关系兑现", "她第一次主动握住了他的手"),
        "能力兑现": MicroPayoff("能力兑现", "他终于掌握了这门功法的精髓"),
        "资源兑现": MicroPayoff("资源兑现", "储物袋里竟然还藏着一颗聚气丹"),
        "认可兑现": MicroPayoff("认可兑现", "在场所有人看他的眼神都变了"),
        "情绪兑现": MicroPayoff("情绪兑现", "他终于说出了压在心底的那句话"),
        "线索兑现": MicroPayoff("线索兑现", "三年前的那件事，终于有了眉目"),
    },
    hard_constraints={
        "HARD-001": "可读性底线 - 看不懂'发生了什么'",
        "HARD-002": "承诺违背 - 上章钩子完全无回应",
        "HARD-003": "节奏灾难 - 连续N章无推进",
        "HARD-004": "冲突真空 - 整章无问题/目标/代价",
    },
)


class GenreProfileLoader:
    """题材配置加载器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self._profiles: Dict[str, GenreProfile] = {}
        self._taxonomy: Optional[ReadingPowerTaxonomy] = None
        self._loaded = False
    
    def load(self) -> None:
        """加载配置"""
        if self._loaded:
            return
        
        # 加载内置配置
        self._profiles = BUILTIN_PROFILES.copy()
        self._taxonomy = BUILTIN_TAXONOMY
        
        # 尝试从文件加载自定义配置
        self._load_from_files()
        
        self._loaded = True
    
    def _load_from_files(self) -> None:
        """从文件加载自定义配置"""
        # 查找配置文件
        references_dir = self._find_references_dir()
        if not references_dir:
            return
        
        # 加载 genre-profiles.md
        genre_file = references_dir / "genre-profiles.md"
        if genre_file.exists():
            self._parse_genre_profiles(genre_file.read_text(encoding="utf-8"))
        
        # 加载 reading-power-taxonomy.md
        taxonomy_file = references_dir / "reading-power-taxonomy.md"
        if taxonomy_file.exists():
            self._parse_reading_power_taxonomy(taxonomy_file.read_text(encoding="utf-8"))
    
    def _find_references_dir(self) -> Optional[Path]:
        """查找 references 目录"""
        # 1. 项目目录下的 system/references/
        if self.config.project_root:
            path = self.config.project_root.parent / "system" / "references"
            if path.is_dir():
                return path
        
        # 2. ForgeAI 安装目录下的 system/references/
        forgeai_root = Path(__file__).parent.parent.parent
        path = forgeai_root / "references"
        if path.is_dir():
            return path
        
        return None
    
    def _parse_genre_profiles(self, content: str) -> None:
        """解析 genre-profiles.md"""
        # 简化实现：只解析内置配置中已有的
        # 完整实现需要解析 YAML 块
        pass
    
    def _parse_reading_power_taxonomy(self, content: str) -> None:
        """解析 reading-power-taxonomy.md"""
        # 简化实现：使用内置配置
        pass
    
    def get_profile(self, genre: str) -> Optional[GenreProfile]:
        """获取题材配置
        
        Args:
            genre: 题材名称，支持复合题材如 "修仙+系统流"
        
        Returns:
            题材配置对象
        """
        if not self._loaded:
            self.load()
        
        # 处理复合题材
        if "+" in genre:
            return self._merge_profiles(genre)
        
        return self._profiles.get(genre)
    
    def _merge_profiles(self, compound_genre: str) -> GenreProfile:
        """合并复合题材配置
        
        主辅比例 7:3
        """
        parts = [p.strip() for p in compound_genre.split("+")]
        if len(parts) != 2:
            # 只支持两个题材组合
            return self._profiles.get(parts[0], list(self._profiles.values())[0])
        
        main = self._profiles.get(parts[0])
        sub = self._profiles.get(parts[1])
        
        if not main:
            main = list(self._profiles.values())[0]
        if not sub:
            sub = main
        
        # 合并配置 (7:3 比例)
        merged = GenreProfile(
            name=compound_genre,
            display_name=f"{main.display_name}+{sub.display_name}",
            preferred_hooks=main.preferred_hooks[:],  # 主题材钩子
            preferred_patterns=main.preferred_patterns[:2] + sub.preferred_patterns[:1],  # 7:3
            density_per_chapter=main.density_per_chapter,
            min_micropayoff=main.min_micropayoff,
            strand_quest_max=main.strand_quest_max,
            strand_fire_gap_max=min(main.strand_fire_gap_max, sub.strand_fire_gap_max),
            stagnation_threshold=min(main.stagnation_threshold, sub.stagnation_threshold),
        )
        
        # 添加副题材的钩子
        for hook in sub.preferred_hooks:
            if hook not in merged.preferred_hooks:
                merged.preferred_hooks.append(hook)
        
        return merged
    
    def get_taxonomy(self) -> ReadingPowerTaxonomy:
        """获取追读力分类标准"""
        if not self._loaded:
            self.load()
        return self._taxonomy
    
    def list_profiles(self) -> List[str]:
        """列出所有可用题材"""
        if not self._loaded:
            self.load()
        return list(self._profiles.keys())
    
    def get_hook_guidance(self, genre: str, chapter_type: str = "normal") -> Dict[str, Any]:
        """获取钩子指导
        
        Args:
            genre: 题材名称
            chapter_type: 章节类型 (normal/climax/transition)
        
        Returns:
            钩子指导信息
        """
        profile = self.get_profile(genre)
        if not profile:
            profile = list(self._profiles.values())[0]
        
        taxonomy = self.get_taxonomy()
        
        # 根据章节类型选择钩子强度
        strength_map = {
            "climax": "strong",
            "normal": "medium",
            "transition": "weak",
        }
        strength = strength_map.get(chapter_type, "medium")
        
        # 推荐钩子
        recommended_hooks = []
        for hook_name in profile.preferred_hooks[:3]:
            hook = taxonomy.hook_types.get(hook_name)
            if hook:
                recommended_hooks.append({
                    "name": hook.name,
                    "driver": hook.driver,
                    "strength": strength,
                    "position": "章末" if hook_name in ["危机钩", "选择钩", "渴望钩"] else "章内",
                })
        
        return {
            "recommended_hooks": recommended_hooks,
            "strength": strength,
            "chapter_type": chapter_type,
        }
    
    def get_pattern_guidance(self, genre: str) -> Dict[str, Any]:
        """获取爽点模式指导"""
        profile = self.get_profile(genre)
        if not profile:
            profile = list(self._profiles.values())[0]
        
        taxonomy = self.get_taxonomy()
        
        # 推荐爽点模式
        recommended_patterns = []
        for pattern_name in profile.preferred_patterns:
            pattern = taxonomy.cool_point_patterns.get(pattern_name)
            if pattern:
                recommended_patterns.append({
                    "name": pattern.name,
                    "structure": pattern.structure,
                    "phases": pattern.phases,
                })
        
        # 爽点密度建议
        density_map = {
            "high": {"min": 2, "target": 3},
            "medium": {"min": 1, "target": 2},
            "low": {"min": 0, "target": 1},
        }
        density = density_map.get(profile.density_per_chapter, {"min": 1, "target": 2})
        
        return {
            "recommended_patterns": recommended_patterns,
            "density": density,
            "min_micropayoff": profile.min_micropayoff,
        }
    
    def get_micro_payoff_suggestions(self, genre: str) -> List[Dict[str, str]]:
        """获取微兑现建议"""
        profile = self.get_profile(genre)
        if not profile:
            profile = list(self._profiles.values())[0]
        
        taxonomy = self.get_taxonomy()
        
        # 根据题材选择微兑现类型
        genre_payoff_map = {
            "shuangwen": ["能力兑现", "资源兑现", "认可兑现"],
            "xianxia": ["能力兑现", "资源兑现", "线索兑现"],
            "urban-power": ["能力兑现", "认可兑现", "情绪兑现"],
            "ancient-romance": ["关系兑现", "情绪兑现", "认可兑现"],
            "mystery": ["信息兑现", "线索兑现"],
            "scifi": ["能力兑现", "资源兑现", "信息兑现"],
            "daily": ["关系兑现", "情绪兑现"],
        }
        
        preferred = genre_payoff_map.get(profile.name, ["关系兑现", "情绪兑现"])
        
        suggestions = []
        for payoff_name in preferred:
            payoff = taxonomy.micro_payoffs.get(payoff_name)
            if payoff:
                suggestions.append({
                    "name": payoff.name,
                    "example": payoff.example,
                })
        
        return suggestions


# 便捷函数
def load_genre_profile(genre: str, config: Optional[ForgeAIConfig] = None) -> Optional[GenreProfile]:
    """加载题材配置"""
    loader = GenreProfileLoader(config)
    return loader.get_profile(genre)


def get_genre_loader(config: Optional[ForgeAIConfig] = None) -> GenreProfileLoader:
    """获取题材配置加载器"""
    return GenreProfileLoader(config)
