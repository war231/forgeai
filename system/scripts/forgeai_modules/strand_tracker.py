#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strand Weave 节奏系统

追踪三条故事线的平衡：
- Quest (主线): 主剧情推进，占比约60%
- Fire (感情线): 关系变化，占比约20%
- Constellation (世界观): 世界展开，占比约20%

当某条线长期缺失时发出警告。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .config import get_config, ForgeAIConfig


@dataclass
class StrandRecord:
    """单条故事线记录"""
    chapter: int
    strand_type: str  # quest, fire, constellation
    description: str
    importance: str  # major, minor, mention
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StrandState:
    """故事线状态"""
    last_quest_chapter: int = 0
    last_fire_chapter: int = 0
    last_constellation_chapter: int = 0
    quest_count: int = 0
    fire_count: int = 0
    constellation_count: int = 0
    total_chapters: int = 0
    records: List[StrandRecord] = field(default_factory=list)


class StrandTracker:
    """
    Strand Weave 节奏追踪器

    功能：
    1. 记录每章出现的故事线类型
    2. 计算三条线的分布比例
    3. 检测长期缺失的线并发出警告
    4. 生成节奏报告
    """

    # 目标比例
    TARGET_RATIOS = {
        "quest": 0.60,        # 主线占60%
        "fire": 0.20,         # 感情线占20%
        "constellation": 0.20 # 世界观占20%
    }

    # 警告阈值（连续N章未出现）
    WARNING_THRESHOLDS = {
        "quest": 5,           # Quest连续5章
        "fire": 10,           # Fire >10章未出现
        "constellation": 15   # Constellation >15章未出现
    }

    # 线的中文显示名
    STRAND_NAMES = {
        "quest": "主线",
        "fire": "感情线",
        "constellation": "世界观"
    }

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.state = StrandState()

    def record(
        self,
        chapter: int,
        strand_type: str,
        description: str,
        importance: str = "minor"
    ) -> None:
        """
        记录一条故事线

        Args:
            chapter: 章节号
            strand_type: 类型 (quest/fire/constellation)
            description: 描述
            importance: 重要程度 (major/minor/mention)
        """
        if strand_type not in self.TARGET_RATIOS:
            raise ValueError(f"Unknown strand type: {strand_type}")

        record = StrandRecord(
            chapter=chapter,
            strand_type=strand_type,
            description=description,
            importance=importance
        )

        self.state.records.append(record)
        self.state.total_chapters = max(self.state.total_chapters, chapter)

        # 更新状态
        if strand_type == "quest":
            self.state.last_quest_chapter = chapter
            self.state.quest_count += 1
        elif strand_type == "fire":
            self.state.last_fire_chapter = chapter
            self.state.fire_count += 1
        elif strand_type == "constellation":
            self.state.last_constellation_chapter = chapter
            self.state.constellation_count += 1

    def record_batch(self, records: List[Dict[str, Any]]) -> None:
        """批量记录"""
        for r in records:
            self.record(
                chapter=r["chapter"],
                strand_type=r["strand_type"],
                description=r.get("description", ""),
                importance=r.get("importance", "minor")
            )

    def check_warnings(self, current_chapter: int) -> List[Dict[str, Any]]:
        """
        检查是否需要发出警告

        Returns:
            警告列表，每个警告包含类型、缺失章数、建议
        """
        warnings = []

        # Quest 警告
        quest_gap = current_chapter - self.state.last_quest_chapter
        if quest_gap >= self.WARNING_THRESHOLDS["quest"]:
            warnings.append({
                "type": "quest_missing",
                "severity": "critical",
                "message": f"主线已连续{quest_gap}章未推进",
                "gap": quest_gap,
                "threshold": self.WARNING_THRESHOLDS["quest"],
                "suggestion": "建议在接下来1-2章内安排主线剧情推进"
            })

        # Fire 警告
        fire_gap = current_chapter - self.state.last_fire_chapter
        if fire_gap >= self.WARNING_THRESHOLDS["fire"]:
            warnings.append({
                "type": "fire_missing",
                "severity": "warning",
                "message": f"感情线已{fire_gap}章未出现",
                "gap": fire_gap,
                "threshold": self.WARNING_THRESHOLDS["fire"],
                "suggestion": "建议安排感情线互动，避免读者遗忘角色关系"
            })

        # Constellation 警告
        constellation_gap = current_chapter - self.state.last_constellation_chapter
        if constellation_gap >= self.WARNING_THRESHOLDS["constellation"]:
            warnings.append({
                "type": "constellation_missing",
                "severity": "info",
                "message": f"世界观线已{constellation_gap}章未展开",
                "gap": constellation_gap,
                "threshold": self.WARNING_THRESHOLDS["constellation"],
                "suggestion": "建议适当展开世界观设定，增加故事深度"
            })

        return warnings

    def get_ratios(self) -> Dict[str, float]:
        """计算当前比例"""
        total = self.state.quest_count + self.state.fire_count + self.state.constellation_count
        if total == 0:
            return {k: 0.0 for k in self.TARGET_RATIOS}

        return {
            "quest": self.state.quest_count / total,
            "fire": self.state.fire_count / total,
            "constellation": self.state.constellation_count / total
        }

    def get_balance_score(self) -> float:
        """
        计算平衡分数 (0-100)

        分数越高表示三条线越平衡
        """
        ratios = self.get_ratios()

        # 计算与目标的偏差
        deviations = []
        for strand_type, target in self.TARGET_RATIOS.items():
            actual = ratios.get(strand_type, 0)
            deviation = abs(actual - target)
            deviations.append(deviation)

        # 平均偏差
        avg_deviation = sum(deviations) / len(deviations)

        # 转换为分数 (偏差越小分数越高)
        score = max(0, 100 - avg_deviation * 200)

        return round(score, 1)

    def generate_report(self, current_chapter: int) -> Dict[str, Any]:
        """生成完整报告"""
        ratios = self.get_ratios()
        warnings = self.check_warnings(current_chapter)
        balance_score = self.get_balance_score()

        return {
            "current_chapter": current_chapter,
            "total_chapters_tracked": self.state.total_chapters,
            "counts": {
                "quest": self.state.quest_count,
                "fire": self.state.fire_count,
                "constellation": self.state.constellation_count
            },
            "ratios": ratios,
            "target_ratios": self.TARGET_RATIOS,
            "last_appearance": {
                "quest": self.state.last_quest_chapter,
                "fire": self.state.last_fire_chapter,
                "constellation": self.state.last_constellation_chapter
            },
            "gaps": {
                "quest": current_chapter - self.state.last_quest_chapter,
                "fire": current_chapter - self.state.last_fire_chapter,
                "constellation": current_chapter - self.state.last_constellation_chapter
            },
            "warnings": warnings,
            "balance_score": balance_score,
            "status": "balanced" if balance_score >= 70 else "imbalanced"
        }

    def to_markdown(self, current_chapter: int) -> str:
        """生成 Markdown 格式报告"""
        report = self.generate_report(current_chapter)

        lines = [
            "# Strand Weave 节奏报告",
            "",
            f"**当前章节**: {current_chapter}",
            f"**平衡分数**: {report['balance_score']}/100",
            f"**状态**: {'✅ 平衡' if report['status'] == 'balanced' else '⚠️ 需要调整'}",
            "",
            "## 三线分布",
            "",
            "| 故事线 | 出现次数 | 实际比例 | 目标比例 | 差距 |",
            "|--------|----------|----------|----------|------|",
        ]

        for strand_type in ["quest", "fire", "constellation"]:
            name = self.STRAND_NAMES[strand_type]
            count = report["counts"][strand_type]
            actual = report["ratios"][strand_type]
            target = report["target_ratios"][strand_type]
            diff = actual - target
            diff_str = f"+{diff:.1%}" if diff > 0 else f"{diff:.1%}"
            lines.append(f"| {name} | {count} | {actual:.1%} | {target:.1%} | {diff_str} |")

        lines.extend([
            "",
            "## 缺口分析",
            "",
            "| 故事线 | 上次出现 | 缺失章数 | 阈值 | 状态 |",
            "|--------|----------|----------|------|------|",
        ])

        for strand_type in ["quest", "fire", "constellation"]:
            name = self.STRAND_NAMES[strand_type]
            last = report["last_appearance"][strand_type]
            gap = report["gaps"][strand_type]
            threshold = self.WARNING_THRESHOLDS[strand_type]
            status = "⚠️ 警告" if gap >= threshold else "✅ 正常"
            lines.append(f"| {name} | 第{last}章 | {gap}章 | {threshold}章 | {status} |")

        if report["warnings"]:
            lines.extend([
                "",
                "## 警告",
                "",
            ])
            for w in report["warnings"]:
                severity_icon = {
                    "critical": "🔴",
                    "warning": "🟡",
                    "info": "🔵"
                }.get(w["severity"], "⚪")
                lines.append(f"### {severity_icon} {w['message']}")
                lines.append(f"")
                lines.append(f"**建议**: {w['suggestion']}")
                lines.append(f"")

        return "\n".join(lines)

    def save(self, filepath: Path) -> None:
        """保存状态"""
        data = {
            "last_quest_chapter": self.state.last_quest_chapter,
            "last_fire_chapter": self.state.last_fire_chapter,
            "last_constellation_chapter": self.state.last_constellation_chapter,
            "quest_count": self.state.quest_count,
            "fire_count": self.state.fire_count,
            "constellation_count": self.state.constellation_count,
            "total_chapters": self.state.total_chapters,
            "records": [
                {
                    "chapter": r.chapter,
                    "strand_type": r.strand_type,
                    "description": r.description,
                    "importance": r.importance,
                    "timestamp": r.timestamp
                }
                for r in self.state.records
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, filepath: Path) -> None:
        """加载状态"""
        if not filepath.exists():
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.state = StrandState(
            last_quest_chapter=data.get("last_quest_chapter", 0),
            last_fire_chapter=data.get("last_fire_chapter", 0),
            last_constellation_chapter=data.get("last_constellation_chapter", 0),
            quest_count=data.get("quest_count", 0),
            fire_count=data.get("fire_count", 0),
            constellation_count=data.get("constellation_count", 0),
            total_chapters=data.get("total_chapters", 0),
            records=[
                StrandRecord(
                    chapter=r["chapter"],
                    strand_type=r["strand_type"],
                    description=r["description"],
                    importance=r["importance"],
                    timestamp=r.get("timestamp", "")
                )
                for r in data.get("records", [])
            ]
        )
