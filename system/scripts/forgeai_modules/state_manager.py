#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理模块

管理 state.json 的读写：
- 实体状态（角色/地点/物品/势力）
- 创作进度（当前章节/阶段）
- 伏笔追踪
- Strand 节奏追踪
- 追读力记录
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import filelock

from .config import get_config, ForgeAIConfig


class StateManager:
    """状态管理器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self._cache: Optional[Dict[str, Any]] = None

    @property
    def state_path(self) -> Optional[Path]:
        return self.config.state_path

    def _default_state(self) -> Dict[str, Any]:
        """默认状态结构"""
        return {
            "version": "1.0.0",
            "project": {
                "name": "",
                "genre": "",
                "mode": "standard",  # standard / flexible / reference
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            "progress": {
                "phase": "init",  # init / analyze / define / ideation / outline / write / review
                "current_chapter": 0,
                "total_chapters": 0,
                "current_volume": 1,
                "total_volumes": 0,
                "word_count": 0,
            },
            "entities": {},       # id -> EntityState dict
            "relationships": [],  # Relationship dicts
            "state_changes": [],  # StateChange dicts
            "foreshadowing": {
                "active": [],     # 未回收的伏笔
                "resolved": [],   # 已回收的伏笔
            },
            "strands": {
                "quest": [],      # 主线任务（60%）
                "fire": [],       # 爽点爆发（20%）
                "constellation": [],  # 情感/世界观（20%）
            },
            "reading_power": {
                "history": [],    # 每章追读力记录
                "current_hooks": [],  # 当前活跃钩子
                "debt": 0.0,     # 叙事债务
            },
            "timeline": {
                "current_anchor": "",  # 当前时间锚点（如：末世第100天）
                "anchors": [],  # 时间锚点列表 [{"chapter": 1, "anchor": "末世第1天", "event": "末世降临"}]
                "countdowns": [],  # 倒计时列表 [{"name": "物资耗尽", "current_value": "D-5", "initial_value": "D-10"}]
                "time_units": "天",  # 时间单位（天/小时/年）
                "warnings": [],  # 时间线警告
            },
            "review_history": [],  # 审查记录
        }

    def load(self) -> Dict[str, Any]:
        """加载状态"""
        if self._cache is not None:
            return self._cache

        path = self.state_path
        if path and path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                return self._cache
            except (json.JSONDecodeError, OSError):
                pass

        self._cache = self._default_state()
        return self._cache

    def save(self, state: Optional[Dict[str, Any]] = None) -> None:
        """保存状态（带文件锁 + 自动分片归档）"""
        if state is not None:
            self._cache = state

        if self._cache is None:
            return

        self._cache["project"]["updated_at"] = datetime.now().isoformat()

        # 自动分片：当 state_changes 或 reading_power.history 超过阈值时归档
        self._auto_archive()

        path = self.state_path
        if not path:
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = str(path) + ".lock"

        with filelock.FileLock(lock_path, timeout=10):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def get_progress(self) -> Dict[str, Any]:
        """获取创作进度"""
        state = self.load()
        return state.get("progress", {})

    def update_progress(self, **kwargs) -> None:
        """更新创作进度"""
        state = self.load()
        progress = state.get("progress", {})
        progress.update(kwargs)
        state["progress"] = progress
        self.save(state)

    # ==================== 时间线管理 ====================

    def get_timeline(self) -> Dict[str, Any]:
        """获取时间线状态"""
        state = self.load()
        return state.get("timeline", {})

    def update_timeline(self, **kwargs) -> None:
        """更新时间线状态"""
        state = self.load()
        timeline = state.get("timeline", {})
        timeline.update(kwargs)
        state["timeline"] = timeline
        self.save(state)

    def add_timeline_anchor(self, chapter: int, anchor: str, event: str) -> None:
        """添加时间锚点"""
        state = self.load()
        timeline = state.get("timeline", {})
        anchors = timeline.get("anchors", [])
        
        # 检查是否已存在
        for existing in anchors:
            if existing.get("chapter") == chapter:
                existing["anchor"] = anchor
                existing["event"] = event
                break
        else:
            anchors.append({
                "chapter": chapter,
                "anchor": anchor,
                "event": event
            })
        
        # 按章节排序
        anchors.sort(key=lambda x: x.get("chapter", 0))
        
        timeline["anchors"] = anchors
        timeline["current_anchor"] = anchor
        state["timeline"] = timeline
        self.save(state)

    def add_countdown(self, name: str, initial_value: str) -> None:
        """添加倒计时"""
        state = self.load()
        timeline = state.get("timeline", {})
        countdowns = timeline.get("countdowns", [])
        
        # 检查是否已存在
        for existing in countdowns:
            if existing.get("name") == name:
                existing["initial_value"] = initial_value
                existing["current_value"] = initial_value
                existing["status"] = "active"
                break
        else:
            countdowns.append({
                "name": name,
                "initial_value": initial_value,
                "current_value": initial_value,
                "status": "active"
            })
        
        timeline["countdowns"] = countdowns
        state["timeline"] = timeline
        self.save(state)

    def get_entities(self) -> Dict[str, Any]:
        """获取所有实体"""
        state = self.load()
        return state.get("entities", {})

    def upsert_entity(self, entity_id: str, entity_data: Dict[str, Any]) -> None:
        """插入或更新实体"""
        state = self.load()
        entities = state.get("entities", {})
        entities[entity_id] = entity_data
        state["entities"] = entities
        self.save(state)

    def record_state_change(self, entity_id: str, field: str,
                            old_value: Any, new_value: Any, reason: str,
                            chapter: int) -> None:
        """记录实体状态变化"""
        state = self.load()
        change = {
            "entity_id": entity_id,
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
            "chapter": chapter,
            "timestamp": datetime.now().isoformat(),
        }
        state.setdefault("state_changes", []).append(change)
        self.save(state)

    def add_relationship(self, from_entity: str, to_entity: str,
                         rel_type: str, description: str, chapter: int) -> None:
        """添加实体关系"""
        state = self.load()
        rel = {
            "from_entity": from_entity,
            "to_entity": to_entity,
            "type": rel_type,
            "description": description,
            "chapter": chapter,
        }
        state.setdefault("relationships", []).append(rel)
        self.save(state)

    def add_foreshadowing(self, description: str, chapter_planted: int,
                          expected_payoff: int = 0,
                          category: str = "plot") -> None:
        """添加伏笔"""
        state = self.load()
        fs = {
            "id": f"fs_{len(state.get('foreshadowing', {}).get('active', [])) + 1}",
            "description": description,
            "chapter_planted": chapter_planted,
            "expected_payoff": expected_payoff,
            "category": category,  # plot / character / world / emotion
            "status": "active",
        }
        state.setdefault("foreshadowing", {}).setdefault("active", []).append(fs)
        self.save(state)

    def resolve_foreshadowing(self, fs_id: str, chapter_resolved: int) -> None:
        """回收伏笔"""
        state = self.load()
        active = state.get("foreshadowing", {}).get("active", [])
        for i, fs in enumerate(active):
            if fs.get("id") == fs_id:
                fs["status"] = "resolved"
                fs["chapter_resolved"] = chapter_resolved
                state.setdefault("foreshadowing", {}).setdefault("resolved", []).append(fs)
                active.pop(i)
                break
        self.save(state)

    def add_reading_power(self, chapter: int, score: float,
                          hooks: List[str], debt_change: float = 0.0,
                          notes: str = "") -> None:
        """记录追读力"""
        state = self.load()
        rp = {
            "chapter": chapter,
            "score": score,  # 0.0 ~ 1.0
            "hooks": hooks,
            "debt_change": debt_change,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        state.setdefault("reading_power", {}).setdefault("history", []).append(rp)
        # 更新累计债务
        current_debt = state.get("reading_power", {}).get("debt", 0.0)
        state["reading_power"]["debt"] = current_debt + debt_change
        self.save(state)

    def get_overdue_foreshadowing(self, current_chapter: int, threshold: int = 30) -> List[Dict]:
        """获取超期未回收的伏笔"""
        state = self.load()
        active = state.get("foreshadowing", {}).get("active", [])
        overdue = []
        for fs in active:
            expected = fs.get("expected_payoff", 0)
            if expected > 0 and current_chapter - fs.get("chapter_planted", 0) > threshold:
                overdue.append(fs)
        return overdue

    def get_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        state = self.load()
        entities = state.get("entities", {})
        active_fs = state.get("foreshadowing", {}).get("active", [])
        rp_history = state.get("reading_power", {}).get("history", [])

        return {
            "project": state.get("project", {}),
            "progress": state.get("progress", {}),
            "entity_count": len(entities),
            "active_foreshadowing": len(active_fs),
            "overdue_foreshadowing": len(self.get_overdue_foreshadowing(
                state.get("progress", {}).get("current_chapter", 0)
            )),
            "avg_reading_power": (
                sum(r.get("score", 0) for r in rp_history) / len(rp_history)
                if rp_history else 0
            ),
            "narrative_debt": state.get("reading_power", {}).get("debt", 0.0),
            "total_relationships": len(state.get("relationships", [])),
        }

    # ---- 分片归档 ----

    def _auto_archive(self) -> None:
        """自动分片归档：大列表超过阈值时，将旧数据归档到按卷文件"""
        if not self._cache or not self.state_path:
            return

        ARCHIVE_THRESHOLD = 200  # 超过200条触发归档

        # 归档 state_changes
        changes = self._cache.get("state_changes", [])
        if len(changes) > ARCHIVE_THRESHOLD:
            self._archive_list("state_changes", changes, ARCHIVE_THRESHOLD)

        # 归档 reading_power.history
        rp = self._cache.get("reading_power", {})
        history = rp.get("history", [])
        if len(history) > ARCHIVE_THRESHOLD:
            self._archive_list("reading_power.history", history, ARCHIVE_THRESHOLD)

        # 归档 review_history
        reviews = self._cache.get("review_history", [])
        if len(reviews) > ARCHIVE_THRESHOLD:
            self._archive_list("review_history", reviews, ARCHIVE_THRESHOLD)

    def _archive_list(self, key_path: str, items: list, threshold: int) -> None:
        """将列表的旧数据归档到按卷文件"""
        if not self.state_path:
            return

        # 保留最近 threshold 条
        to_archive = items[:-threshold]
        to_keep = items[-threshold:]

        if not to_archive:
            return

        # 确定归档的卷号范围
        chapters = [item.get("chapter", 0) for item in to_archive if isinstance(item, dict)]
        if not chapters:
            return

        min_ch = min(chapters)
        max_ch = max(chapters)
        # 每卷约50章
        for vol_start in range(1, max_ch + 1, 50):
            vol_end = vol_start + 49
            vol_items = [
                item for item in to_archive
                if isinstance(item, dict) and vol_start <= item.get("chapter", 0) <= vol_end
            ]
            if not vol_items:
                continue

            # 写入归档文件
            archive_dir = self.state_path.parent / "archives"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"state_vol{vol_start // 50 + 1}.json"

            # 读取已有归档，追加
            existing = []
            if archive_path.is_file():
                try:
                    with open(archive_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, OSError):
                    existing = []

            # 按主键去重
            existing_ids = set()
            for item in existing:
                item_id = json.dumps(item, sort_keys=True, ensure_ascii=False)
                existing_ids.add(item_id)

            for item in vol_items:
                item_id = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if item_id not in existing_ids:
                    existing.append(item)

            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)

        # 更新缓存，只保留最近的数据
        self._set_nested(self._cache, key_path, to_keep)

    def _set_nested(self, d: dict, key_path: str, value: Any) -> None:
        """设置嵌套字典值"""
        keys = key_path.split(".")
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value

    def load_archived(self, volume: int = 0) -> Dict[str, Any]:
        """加载归档数据"""
        if not self.state_path:
            return {}

        archive_dir = self.state_path.parent / "archives"
        if not archive_dir.is_dir():
            return {}

        result = {}
        for path in sorted(archive_dir.glob("state_vol*.json")):
            if volume > 0:
                vol_num = int(path.stem.replace("state_vol", ""))
                if vol_num != volume:
                    continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result[path.name] = {
                    "count": len(data) if isinstance(data, list) else 0,
                    "chapters": list(set(
                        item.get("chapter", 0) for item in data
                        if isinstance(item, dict)
                    ))[:10],
                }
            except (json.JSONDecodeError, OSError):
                pass
        return result
