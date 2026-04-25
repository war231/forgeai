#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文提取器

从项目文件中提取创作上下文：
- 前文回顾（最近N章摘要）
- 活跃实体状态
- 未回收伏笔
- 追读力趋势
- 当前节奏分布
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .state_manager import StateManager
from .index_manager import IndexManager
from .rag_adapter import RAGAdapter


class ContextExtractor:
    """上下文提取器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.state_manager = StateManager(self.config)
        self.index_manager = IndexManager(self.config)
        self.rag_adapter = RAGAdapter(self.config)

    def extract_full_context(self, current_chapter: int,
                              query: str = "") -> Dict[str, Any]:
        """提取完整创作上下文"""
        state = self.state_manager.load()
        progress = state.get("progress", {})

        return {
            "project": state.get("project", {}),
            "progress": progress,
            "previous_chapters": self._get_previous_chapters(current_chapter),
            "active_entities": self._get_active_entities(current_chapter),
            "active_foreshadowing": self._get_active_foreshadowing(state),
            "overdue_foreshadowing": self.state_manager.get_overdue_foreshadowing(current_chapter),
            "strand_balance": self._get_strand_balance(state),
            "reading_power_trend": self._get_reading_power_trend(),
            "narrative_debt": state.get("reading_power", {}).get("debt", 0.0),
            "recent_state_changes": self._get_recent_changes(state, current_chapter),
            "relationships_snapshot": self._get_relationships_snapshot(current_chapter),
        }

    async def extract_with_rag(self, current_chapter: int,
                                query: str = "", top_k: int = 5) -> Dict[str, Any]:
        """带 RAG 的上下文提取"""
        base_context = self.extract_full_context(current_chapter, query)

        # RAG 检索相关内容
        rag_context = await self.rag_adapter.extract_context(current_chapter, query, top_k)
        base_context["rag_results"] = rag_context.get("relevant_chunks", [])
        base_context["rag_degraded"] = rag_context.get("degraded_mode", False)

        return base_context

    def _get_previous_chapters(self, current_chapter: int,
                                lookback: int = 5) -> List[Dict[str, Any]]:
        """获取最近N章摘要"""
        chapters = []
        for ch_num in range(max(1, current_chapter - lookback), current_chapter):
            meta = self.index_manager.get_chapter(ch_num)
            if meta:
                chapters.append(meta)
        return chapters

    def _get_active_entities(self, current_chapter: int,
                              lookback: int = 10) -> List[Dict[str, Any]]:
        """获取活跃实体（最近N章出场过的）"""
        entities = self.state_manager.get_entities()
        active = []
        for eid, edata in entities.items():
            last = edata.get("last_appearance", 0)
            if current_chapter - last <= lookback:
                tier = edata.get("tier", "decorative")
                active.append({
                    "id": eid,
                    "name": edata.get("name", ""),
                    "tier": tier,
                    "last_appearance": last,
                    "type": edata.get("type", "character"),
                })
        # 按 tier 排序：core > important > secondary > decorative
        tier_order = {"core": 0, "important": 1, "secondary": 2, "decorative": 3}
        active.sort(key=lambda x: tier_order.get(x["tier"], 99))
        return active

    def _get_active_foreshadowing(self, state: Dict) -> List[Dict]:
        """获取活跃伏笔"""
        return state.get("foreshadowing", {}).get("active", [])

    def _get_strand_balance(self, state: Dict) -> Dict[str, Any]:
        """获取节奏平衡"""
        strands = state.get("strands", {})
        quest = len(strands.get("quest", []))
        fire = len(strands.get("fire", []))
        constellation = len(strands.get("constellation", []))
        total = quest + fire + constellation

        if total == 0:
            return {"quest_ratio": 0.6, "fire_ratio": 0.2, "constellation_ratio": 0.2,
                    "total": 0, "balanced": True}

        quest_ratio = quest / total
        fire_ratio = fire / total
        constellation_ratio = constellation / total

        # 目标比例：Quest 60%, Fire 20%, Constellation 20%
        balanced = abs(quest_ratio - 0.6) < 0.15 and abs(fire_ratio - 0.2) < 0.1

        return {
            "quest_count": quest,
            "fire_count": fire,
            "constellation_count": constellation,
            "quest_ratio": round(quest_ratio, 2),
            "fire_ratio": round(fire_ratio, 2),
            "constellation_ratio": round(constellation_ratio, 2),
            "target_ratio": "60/20/20",
            "balanced": balanced,
            "total": total,
        }

    def _get_reading_power_trend(self, last_n: int = 10) -> List[Dict]:
        """获取追读力趋势"""
        return self.index_manager.get_reading_power_trend(last_n)

    def _get_recent_changes(self, state: Dict,
                             current_chapter: int,
                             lookback: int = 5) -> List[Dict]:
        """获取最近的状态变化"""
        changes = state.get("state_changes", [])
        return [c for c in changes
                if c.get("chapter", 0) >= current_chapter - lookback]

    def _get_relationships_snapshot(self, current_chapter: int) -> List[Dict]:
        """获取关系快照"""
        state = self.state_manager.load()
        rels = state.get("relationships", [])
        # 只保留最近章节相关的关系
        return [r for r in rels
                if r.get("chapter", 0) >= max(1, current_chapter - 20)]

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """将上下文格式化为 prompt 文本"""
        lines = ["## 创作上下文\n"]

        # 项目信息
        proj = context.get("project", {})
        lines.append(f"**项目**: {proj.get('name', '未命名')}")
        lines.append(f"**题材**: {proj.get('genre', '未设定')}")
        lines.append(f"**模式**: {proj.get('mode', 'standard')}")

        # 进度
        progress = context.get("progress", {})
        lines.append(f"\n**当前进度**: 第{progress.get('current_chapter', 0)}章 "
                      f"/ 共{progress.get('total_chapters', '?')}章")
        lines.append(f"**阶段**: {progress.get('phase', 'init')}")
        lines.append(f"**总字数**: {progress.get('word_count', 0)}")

        # 活跃实体
        entities = context.get("active_entities", [])
        if entities:
            lines.append("\n### 活跃角色")
            for e in entities[:15]:
                lines.append(f"- {e['name']} ({e['tier']}) - 上次出场: 第{e['last_appearance']}章")

        # 伏笔
        active_fs = context.get("active_foreshadowing", [])
        if active_fs:
            lines.append("\n### 未回收伏笔")
            for fs in active_fs[:10]:
                lines.append(f"- [{fs.get('id')}] {fs.get('description', '')} "
                              f"(第{fs.get('chapter_planted', '?')}章埋设)")

        overdue = context.get("overdue_foreshadowing", [])
        if overdue:
            lines.append(f"\n⚠️ **超期伏笔**: {len(overdue)}个伏笔超过30章未回收")

        # 追读力
        debt = context.get("narrative_debt", 0.0)
        if debt > 0:
            lines.append(f"\n⚠️ **叙事债务**: {debt:.1f} (需要偿还)")

        # 节奏平衡
        balance = context.get("strand_balance", {})
        if not balance.get("balanced", True):
            lines.append(f"\n⚠️ **节奏失衡**: Quest/Fire/Constellation = "
                          f"{balance.get('quest_ratio', 0):.0%}/"
                          f"{balance.get('fire_ratio', 0):.0%}/"
                          f"{balance.get('constellation_ratio', 0):.0%} "
                          f"(目标: 60%/20%/20%)")

        return "\n".join(lines)
