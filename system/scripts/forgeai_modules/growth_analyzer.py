#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色成长曲线分析器

功能：
1. 提取角色状态变化
2. 构建成长时间线
3. 计算成长速度和轨迹
4. 生成成长报告（Markdown）
5. 绘制成长曲线图（可选matplotlib）
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .config import get_config, ForgeAIConfig
from .state_manager import StateManager

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    MATPLOTLIB_AVAILABLE = True
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
except ImportError:
    MATPLOTLIB_AVAILABLE = False


@dataclass
class GrowthMilestone:
    """成长里程碑"""
    chapter: int
    event_type: str  # breakthrough/acquire/realize/relationship
    description: str
    importance: str  # critical/high/medium/low
    old_value: Optional[str] = None
    new_value: Optional[str] = None


@dataclass
class GrowthTimeline:
    """成长时间线"""
    entity_id: str
    milestones: List[GrowthMilestone] = field(default_factory=list)
    total_changes: int = 0
    chapters_active: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "total_changes": self.total_changes,
            "chapters_active": self.chapters_active,
            "milestones": [
                {
                    "chapter": m.chapter,
                    "event_type": m.event_type,
                    "description": m.description,
                    "importance": m.importance,
                    "old_value": m.old_value,
                    "new_value": m.new_value,
                }
                for m in self.milestones
            ]
        }


@dataclass
class GrowthAnalysis:
    """成长分析结果"""
    entity_id: str
    timeline: GrowthTimeline
    velocity: float  # 成长速度（变化次数/章节数）
    trajectory: str  # linear/exponential/logarithmic/irregular
    current_level: str
    first_appearance: int
    last_appearance: int
    growth_pattern: str  # rapid/steady/slow
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "velocity": self.velocity,
            "trajectory": self.trajectory,
            "current_level": self.current_level,
            "first_appearance": self.first_appearance,
            "last_appearance": self.last_appearance,
            "growth_pattern": self.growth_pattern,
            "recommendations": self.recommendations,
            "timeline": self.timeline.to_dict(),
        }


class GrowthAnalyzer:
    """角色成长曲线分析器"""
    
    # 修为等级映射（用于数值化）
    REALM_MAPPING = {
        "练气": 1,
        "筑基": 2,
        "金丹": 3,
        "元婴": 4,
        "化神": 5,
        "炼虚": 6,
        "合体": 7,
        "大乘": 8,
        "渡劫": 9,
        "仙人": 10,
    }
    
    # 突破关键词
    BREAKTHROUGH_KEYWORDS = ["突破", "踏入", "晋升", "达到", "修炼到", "领悟"]
    ACQUIRE_KEYWORDS = ["获得", "得到", "夺取", "炼化", "融合"]
    REALIZE_KEYWORDS = ["领悟", "参悟", "理解", "掌握"]
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.state_manager = StateManager(self.config)
    
    def analyze_entity_growth(self, entity_id: str) -> Optional[GrowthAnalysis]:
        """
        分析单个角色的成长曲线
        
        Args:
            entity_id: 实体ID（角色名）
        
        Returns:
            GrowthAnalysis 或 None
        """
        # 1. 获取实体信息
        entities = self.state_manager.get_entities()
        entity_data = entities.get(entity_id)
        if not entity_data:
            return None
        
        # 2. 提取所有状态变化
        state_changes = self.state_manager.load().get("state_changes", [])
        entity_changes = [
            change for change in state_changes
            if change.get("entity_id") == entity_id or change.get("entity") == entity_id
        ]
        
        if not entity_changes:
            # 无状态变化，返回基本信息
            return GrowthAnalysis(
                entity_id=entity_id,
                timeline=GrowthTimeline(entity_id=entity_id),
                velocity=0.0,
                trajectory="none",
                current_level="未知",
                first_appearance=entity_data.get("first_appearance", 1),
                last_appearance=entity_data.get("last_appearance", 1),
                growth_pattern="无变化",
                recommendations=["该角色暂无成长记录"],
            )
        
        # 3. 构建成长时间线
        timeline = self._build_growth_timeline(entity_id, entity_changes)
        
        # 4. 计算成长速度
        velocity = self._calculate_velocity(timeline)
        
        # 5. 识别成长轨迹
        trajectory = self._identify_trajectory(timeline)
        
        # 6. 获取当前等级
        current_level = self._extract_current_level(entity_changes)
        
        # 7. 分析成长模式
        growth_pattern = self._analyze_growth_pattern(velocity, trajectory)
        
        # 8. 生成建议
        recommendations = self._generate_recommendations(
            entity_id, timeline, velocity, trajectory, growth_pattern
        )
        
        # 9. 获取出场信息
        first_appearance = entity_data.get("first_appearance", entity_changes[0].get("chapter", 1))
        last_appearance = entity_data.get("last_appearance", entity_changes[-1].get("chapter", 1))
        
        return GrowthAnalysis(
            entity_id=entity_id,
            timeline=timeline,
            velocity=velocity,
            trajectory=trajectory,
            current_level=current_level,
            first_appearance=first_appearance,
            last_appearance=last_appearance,
            growth_pattern=growth_pattern,
            recommendations=recommendations,
        )
    
    def _build_growth_timeline(self, entity_id: str, 
                                changes: List[Dict]) -> GrowthTimeline:
        """构建成长时间线"""
        timeline = GrowthTimeline(entity_id=entity_id)
        timeline.total_changes = len(changes)
        
        # 按章节排序
        changes_sorted = sorted(changes, key=lambda x: x.get("chapter", 0))
        
        # 提取章节集合
        chapters = set()
        
        for change in changes_sorted:
            chapter = change.get("chapter", 0)
            chapters.add(chapter)
            
            # 解析变化类型
            reason = change.get("reason", "")
            field = change.get("field", "")
            old_value = change.get("old_value", "")
            new_value = change.get("new_value", "")
            
            # 判断事件类型
            event_type = self._classify_event_type(reason, field)
            importance = self._judge_importance(event_type, field)
            
            milestone = GrowthMilestone(
                chapter=chapter,
                event_type=event_type,
                description=reason or f"{field}: {old_value} → {new_value}",
                importance=importance,
                old_value=old_value,
                new_value=new_value,
            )
            
            timeline.milestones.append(milestone)
        
        timeline.chapters_active = len(chapters)
        
        return timeline
    
    def _classify_event_type(self, reason: str, field: str) -> str:
        """分类事件类型"""
        reason_lower = reason.lower()
        
        if any(kw in reason_lower for kw in self.BREAKTHROUGH_KEYWORDS):
            return "breakthrough"
        elif any(kw in reason_lower for kw in self.ACQUIRE_KEYWORDS):
            return "acquire"
        elif any(kw in reason_lower for kw in self.REALIZE_KEYWORDS):
            return "realize"
        elif "关系" in field or "关系" in reason_lower:
            return "relationship"
        else:
            return "other"
    
    def _judge_importance(self, event_type: str, field: str) -> str:
        """判断事件重要性"""
        if event_type == "breakthrough":
            if "修为" in field:
                return "critical"
            return "high"
        elif event_type == "acquire":
            return "high"
        elif event_type == "realize":
            return "medium"
        else:
            return "low"
    
    def _calculate_velocity(self, timeline: GrowthTimeline) -> float:
        """计算成长速度（变化次数/活跃章节数）"""
        if timeline.chapters_active == 0:
            return 0.0
        
        return timeline.total_changes / timeline.chapters_active
    
    def _identify_trajectory(self, timeline: GrowthTimeline) -> str:
        """识别成长轨迹"""
        if len(timeline.milestones) < 3:
            return "insufficient_data"
        
        # 提取修为等级序列（简化版）
        levels = []
        for milestone in timeline.milestones:
            if milestone.event_type == "breakthrough" and milestone.new_value:
                # 尝试提取修为等级
                level = self._parse_realm_level(milestone.new_value)
                if level is not None:
                    levels.append(level)
        
        if len(levels) < 3:
            return "irregular"
        
        # 简单判断：线性/指数/对数
        # 这里使用简化算法，实际可用更复杂的模型
        diffs = [levels[i+1] - levels[i] for i in range(len(levels)-1)]
        
        if all(d > 0 for d in diffs):
            if max(diffs) > min(diffs) * 2:
                return "exponential"  # 加速增长
            elif max(diffs) < min(diffs) * 0.5:
                return "logarithmic"  # 减速增长
            else:
                return "linear"  # 线性增长
        else:
            return "irregular"  # 不规则
    
    def _parse_realm_level(self, value: str) -> Optional[int]:
        """解析修为等级为数值"""
        for realm, level in self.REALM_MAPPING.items():
            if realm in value:
                # 尝试提取层数
                match = re.search(r'(\d+)层?', value)
                if match:
                    layer = int(match.group(1))
                    return level * 100 + layer
                return level * 100
        return None
    
    def _extract_current_level(self, changes: List[Dict]) -> str:
        """提取当前等级"""
        # 从最新的突破记录中提取
        for change in reversed(changes):
            field = change.get("field", "")
            if "修为" in field or "境界" in field:
                new_value = change.get("new_value", "")
                if new_value:
                    return new_value
        
        return "未知"
    
    def _analyze_growth_pattern(self, velocity: float, trajectory: str) -> str:
        """分析成长模式"""
        if velocity >= 2.0:
            return "rapid"  # 快速成长
        elif velocity >= 1.0:
            return "steady"  # 稳定成长
        else:
            return "slow"  # 缓慢成长
    
    def _generate_recommendations(self, entity_id: str, 
                                   timeline: GrowthTimeline,
                                   velocity: float,
                                   trajectory: str,
                                   growth_pattern: str) -> List[str]:
        """生成成长建议"""
        recommendations = []
        
        # 基于速度的建议
        if velocity > 3.0:
            recommendations.append("⚠️ 成长速度过快，建议增加瓶颈期，避免主角光环过强")
        elif velocity < 0.5:
            recommendations.append("💡 成长速度较慢，建议增加成长机会，保持读者兴趣")
        
        # 基于轨迹的建议
        if trajectory == "exponential":
            recommendations.append("📈 成长轨迹呈指数型，初期快速成长，预计后期将放缓，建议提前规划")
        elif trajectory == "linear":
            recommendations.append("📊 成长轨迹呈线性，节奏稳定，建议保持")
        elif trajectory == "logarithmic":
            recommendations.append("📉 成长轨迹呈对数型，后期成长放缓，建议增加新的成长路径")
        
        # 基于里程碑的建议
        critical_count = sum(1 for m in timeline.milestones if m.importance == "critical")
        if critical_count > timeline.total_changes * 0.3:
            recommendations.append(f"🔥 关键突破次数较多（{critical_count}次），建议合理安排节奏")
        
        # 默认建议
        if not recommendations:
            recommendations.append("✅ 成长曲线合理，继续保持")
        
        return recommendations
    
    def generate_growth_report(self, entity_id: str, 
                               analysis: Optional[GrowthAnalysis] = None) -> str:
        """
        生成成长报告（Markdown格式）
        
        Args:
            entity_id: 实体ID
            analysis: 成长分析结果（可选，如不提供则自动分析）
        
        Returns:
            Markdown格式的报告
        """
        if analysis is None:
            analysis = self.analyze_entity_growth(entity_id)
        
        if analysis is None:
            return f"# {entity_id} 成长分析报告\n\n未找到该角色的数据。"
        
        # 构建报告
        report_lines = [
            f"# {entity_id} 成长分析报告",
            "",
            "## 基本信息",
            "",
            f"- **角色名**: {entity_id}",
            f"- **首次出场**: 第{analysis.first_appearance}章",
            f"- **最后出场**: 第{analysis.last_appearance}章",
            f"- **当前等级**: {analysis.current_level}",
            f"- **出场章节数**: {analysis.timeline.chapters_active}章",
            "",
            "## 成长指标",
            "",
            f"- **成长速度**: {analysis.velocity:.2f} 次/章",
            f"- **成长轨迹**: {self._trajectory_display(analysis.trajectory)}",
            f"- **成长模式**: {self._pattern_display(analysis.growth_pattern)}",
            f"- **总变化次数**: {analysis.timeline.total_changes}次",
            "",
            "## 成长时间线",
            "",
            "| 章节 | 事件类型 | 描述 | 重要性 |",
            "|------|---------|------|--------|",
        ]
        
        for milestone in analysis.timeline.milestones:
            event_display = self._event_type_display(milestone.event_type)
            importance_display = self._importance_display(milestone.importance)
            report_lines.append(
                f"| {milestone.chapter} | {event_display} | {milestone.description} | {importance_display} |"
            )
        
        # 添加建议
        if analysis.recommendations:
            report_lines.extend([
                "",
                "## 成长建议",
                "",
            ])
            for rec in analysis.recommendations:
                report_lines.append(f"- {rec}")
        
        # 添加可视化说明（如果matplotlib不可用）
        if not MATPLOTLIB_AVAILABLE:
            report_lines.extend([
                "",
                "## 可视化",
                "",
                "⚠️ 未安装matplotlib，无法生成成长曲线图。",
                "请执行：`pip install matplotlib`",
            ])
        
        return "\n".join(report_lines)
    
    def _trajectory_display(self, trajectory: str) -> str:
        """轨迹显示名称"""
        mapping = {
            "exponential": "指数型（初期快速）",
            "linear": "线性型（稳定增长）",
            "logarithmic": "对数型（后期放缓）",
            "irregular": "不规则",
            "insufficient_data": "数据不足",
            "none": "无成长",
        }
        return mapping.get(trajectory, trajectory)
    
    def _pattern_display(self, pattern: str) -> str:
        """模式显示名称"""
        mapping = {
            "rapid": "快速成长",
            "steady": "稳定成长",
            "slow": "缓慢成长",
        }
        return mapping.get(pattern, pattern)
    
    def _event_type_display(self, event_type: str) -> str:
        """事件类型显示名称"""
        mapping = {
            "breakthrough": "🌟 突破",
            "acquire": "📦 获得",
            "realize": "💡 领悟",
            "relationship": "🤝 关系",
            "other": "📌 其他",
        }
        return mapping.get(event_type, event_type)
    
    def _importance_display(self, importance: str) -> str:
        """重要性显示"""
        mapping = {
            "critical": "🔴 关键",
            "high": "🟡 重要",
            "medium": "🟢 一般",
            "low": "⚪ 次要",
        }
        return mapping.get(importance, importance)
    
    def plot_growth_curve(self, entity_id: str,
                         output_file: Optional[str] = None,
                         analysis: Optional[GrowthAnalysis] = None) -> Optional[str]:
        """
        绘制成长曲线图
        
        Args:
            entity_id: 实体ID
            output_file: 输出文件路径（可选）
            analysis: 成长分析结果（可选）
        
        Returns:
            输出文件路径，失败返回None
        """
        if not MATPLOTLIB_AVAILABLE:
            print("警告：未安装matplotlib，无法绘制成长曲线")
            return None
        
        if analysis is None:
            analysis = self.analyze_entity_growth(entity_id)
        
        if analysis is None or not analysis.timeline.milestones:
            print(f"警告：{entity_id} 无成长数据")
            return None
        
        # 提取数据
        chapters = [m.chapter for m in analysis.timeline.milestones]
        
        # 尝试提取修为等级（数值化）
        levels = []
        for m in analysis.timeline.milestones:
            if m.event_type == "breakthrough" and m.new_value:
                level = self._parse_realm_level(m.new_value)
                levels.append(level if level is not None else 0)
            else:
                levels.append(0)
        
        # 绘图
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(chapters, levels, marker='o', linewidth=2, markersize=8)
        ax.set_xlabel('章节', fontsize=12)
        ax.set_ylabel('修为等级', fontsize=12)
        ax.set_title(f'{entity_id} 成长曲线', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 标注关键节点
        for i, m in enumerate(analysis.timeline.milestones):
            if m.importance == "critical":
                ax.annotate(m.description[:10] + "...", 
                           xy=(chapters[i], levels[i]),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8)
        
        plt.tight_layout()
        
        # 保存或显示
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            return output_file
        else:
            plt.show()
            plt.close()
            return None
    
    def compare_entities(self, entity_ids: List[str]) -> Dict[str, Any]:
        """
        对比多个角色的成长
        
        Args:
            entity_ids: 实体ID列表
        
        Returns:
            对比结果
        """
        analyses = {}
        for entity_id in entity_ids:
            analysis = self.analyze_entity_growth(entity_id)
            if analysis:
                analyses[entity_id] = analysis
        
        if not analyses:
            return {"error": "未找到任何角色的成长数据"}
        
        # 对比分析
        comparison = {
            "entities": entity_ids,
            "velocity_comparison": {},
            "trajectory_comparison": {},
            "summary": {},
        }
        
        # 速度对比
        velocities = {eid: a.velocity for eid, a in analyses.items()}
        comparison["velocity_comparison"] = {
            "fastest": max(velocities.items(), key=lambda x: x[1])[0],
            "slowest": min(velocities.items(), key=lambda x: x[1])[0],
            "average": sum(velocities.values()) / len(velocities),
            "details": velocities,
        }
        
        # 轨迹对比
        trajectories = {eid: a.trajectory for eid, a in analyses.items()}
        comparison["trajectory_comparison"] = trajectories
        
        # 摘要
        comparison["summary"] = {
            eid: {
                "current_level": a.current_level,
                "velocity": a.velocity,
                "pattern": a.growth_pattern,
                "total_changes": a.timeline.total_changes,
            }
            for eid, a in analyses.items()
        }
        
        return comparison
