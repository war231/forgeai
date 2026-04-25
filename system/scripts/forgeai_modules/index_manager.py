#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
索引管理模块

管理 SQLite index.db：
- 章节元数据索引
- 实体出场记录
- 场景索引
- 关系存储
- 追读力债务
- 审查指标
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .config import get_config, ForgeAIConfig


INDEX_SCHEMA_VERSION = "1"

SCHEMA_SQL = """
-- 章节元数据
CREATE TABLE IF NOT EXISTS chapters (
    chapter INTEGER PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    location TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    summary TEXT DEFAULT '',
    reading_power REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 实体
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'character',  -- character / location / item / faction
    tier TEXT NOT NULL DEFAULT 'decorative',  -- core / important / secondary / decorative
    aliases TEXT DEFAULT '[]',  -- JSON array
    attributes TEXT DEFAULT '{}',  -- JSON object
    first_appearance INTEGER DEFAULT 0,
    last_appearance INTEGER DEFAULT 0,
    description TEXT DEFAULT ''
);

-- 实体出场记录
CREATE TABLE IF NOT EXISTS entity_appearances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    scene_index INTEGER DEFAULT 0,
    role TEXT DEFAULT 'mentioned',  -- pov / active / mentioned / referenced
    context TEXT DEFAULT '',
    UNIQUE(entity_id, chapter, scene_index)
);

-- 场景
CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter INTEGER NOT NULL,
    scene_index INTEGER NOT NULL,
    start_offset INTEGER DEFAULT 0,
    end_offset INTEGER DEFAULT 0,
    location TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    characters TEXT DEFAULT '[]',  -- JSON array of entity ids
    mood TEXT DEFAULT '',
    UNIQUE(chapter, scene_index)
);

-- 关系
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'related',
    description TEXT DEFAULT '',
    chapter INTEGER DEFAULT 0
);

-- 状态变化
CREATE TABLE IF NOT EXISTS state_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT DEFAULT '',
    new_value TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    chapter INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT (datetime('now'))
);

-- 追读力记录
CREATE TABLE IF NOT EXISTS reading_power (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter INTEGER NOT NULL,
    score REAL DEFAULT 0.0,
    hooks TEXT DEFAULT '[]',  -- JSON array
    debt_change REAL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now'))
);

-- 叙事债务
CREATE TABLE IF NOT EXISTS narrative_debt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter INTEGER NOT NULL,
    debt_type TEXT NOT NULL,  -- foreshadowing / promise / mystery
    description TEXT NOT NULL,
    amount REAL DEFAULT 1.0,
    status TEXT DEFAULT 'active',  -- active / partially_paid / paid
    paid_chapter INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 审查指标
CREATE TABLE IF NOT EXISTS review_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter INTEGER NOT NULL,
    checker_type TEXT NOT NULL,  -- high_point / consistency / pacing / ooc / continuity / reader_pull
    score REAL DEFAULT 0.0,
    issues TEXT DEFAULT '[]',  -- JSON array
    suggestions TEXT DEFAULT '[]',  -- JSON array
    timestamp TEXT DEFAULT (datetime('now'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_appearances_entity ON entity_appearances(entity_id);
CREATE INDEX IF NOT EXISTS idx_appearances_chapter ON entity_appearances(chapter);
CREATE INDEX IF NOT EXISTS idx_scenes_chapter ON scenes(chapter);
CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_entity);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_entity);
CREATE INDEX IF NOT EXISTS idx_state_changes_entity ON state_changes(entity_id);
CREATE INDEX IF NOT EXISTS idx_reading_power_chapter ON reading_power(chapter);
CREATE INDEX IF NOT EXISTS idx_debt_status ON narrative_debt(status);
CREATE INDEX IF NOT EXISTS idx_review_chapter ON review_metrics(chapter);

-- Schema 版本
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('version', ?);
"""


class IndexManager:
    """索引管理器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()

    @property
    def db_path(self) -> Optional[Path]:
        return self.config.index_db_path

    def _connect(self) -> sqlite3.Connection:
        """获取数据库连接"""
        path = self.db_path
        if not path:
            raise RuntimeError("项目根目录未设置，无法定位 index.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self) -> None:
        """初始化数据库"""
        conn = self._connect()
        try:
            conn.executescript(SCHEMA_SQL.replace("?", f"'{INDEX_SCHEMA_VERSION}'"))
            conn.commit()
        finally:
            conn.close()

    # ---- 章节操作 ----

    def upsert_chapter(self, chapter: int, title: str = "", location: str = "",
                       word_count: int = 0, summary: str = "",
                       reading_power: float = 0.0) -> None:
        """插入或更新章节"""
        conn = self._connect()
        try:
            conn.execute("""
                INSERT INTO chapters (chapter, title, location, word_count, summary, reading_power)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chapter) DO UPDATE SET
                    title=excluded.title, location=excluded.location,
                    word_count=excluded.word_count, summary=excluded.summary,
                    reading_power=excluded.reading_power, updated_at=datetime('now')
            """, (chapter, title, location, word_count, summary, reading_power))
            conn.commit()
        finally:
            conn.close()

    def get_chapter(self, chapter: int) -> Optional[Dict[str, Any]]:
        """获取章节信息"""
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM chapters WHERE chapter = ?", (chapter,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_chapters(self) -> List[Dict[str, Any]]:
        """获取所有章节"""
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM chapters ORDER BY chapter").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---- 实体操作 ----

    def upsert_entity(self, entity_id: str, name: str, type_: str = "character",
                      tier: str = "decorative", aliases: List[str] = None,
                      attributes: Dict = None, first_appearance: int = 0,
                      description: str = "") -> None:
        """插入或更新实体"""
        conn = self._connect()
        try:
            conn.execute("""
                INSERT INTO entities (id, name, type, tier, aliases, attributes,
                                       first_appearance, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, type=excluded.type, tier=excluded.tier,
                    aliases=excluded.aliases, attributes=excluded.attributes,
                    description=excluded.description
            """, (entity_id, name, type_, tier,
                  json.dumps(aliases or [], ensure_ascii=False),
                  json.dumps(attributes or {}, ensure_ascii=False),
                  first_appearance, description))
            conn.commit()
        finally:
            conn.close()

    def record_appearance(self, entity_id: str, chapter: int,
                          scene_index: int = 0, role: str = "mentioned",
                          context: str = "") -> None:
        """记录实体出场"""
        conn = self._connect()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO entity_appearances
                    (entity_id, chapter, scene_index, role, context)
                VALUES (?, ?, ?, ?, ?)
            """, (entity_id, chapter, scene_index, role, context))
            conn.execute("""
                UPDATE entities SET last_appearance = ?
                WHERE id = ? AND last_appearance < ?
            """, (chapter, entity_id, chapter))
            conn.commit()
        finally:
            conn.close()

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """获取实体"""
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
            if row:
                d = dict(row)
                d["aliases"] = json.loads(d.get("aliases", "[]"))
                d["attributes"] = json.loads(d.get("attributes", "{}"))
                return d
            return None
        finally:
            conn.close()

    def search_entities(self, query: str, type_: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索实体（名称/别名模糊匹配）"""
        conn = self._connect()
        try:
            sql = "SELECT * FROM entities WHERE name LIKE ?"
            params: list = [f"%{query}%"]
            if type_:
                sql += " AND type = ?"
                params.append(type_)
            rows = conn.execute(sql, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["aliases"] = json.loads(d.get("aliases", "[]"))
                d["attributes"] = json.loads(d.get("attributes", "{}"))
                results.append(d)
            return results
        finally:
            conn.close()

    def get_entity_appearances(self, entity_id: str,
                                limit: int = 20) -> List[Dict[str, Any]]:
        """获取实体出场记录"""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM entity_appearances WHERE entity_id = ? ORDER BY chapter DESC LIMIT ?",
                (entity_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---- 关系操作 ----

    def add_relationship(self, from_entity: str, to_entity: str,
                         type_: str = "related", description: str = "",
                         chapter: int = 0) -> None:
        """添加关系"""
        conn = self._connect()
        try:
            conn.execute("""
                INSERT INTO relationships (from_entity, to_entity, type, description, chapter)
                VALUES (?, ?, ?, ?, ?)
            """, (from_entity, to_entity, type_, description, chapter))
            conn.commit()
        finally:
            conn.close()

    def get_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """获取实体的所有关系"""
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT * FROM relationships
                WHERE from_entity = ? OR to_entity = ?
                ORDER BY chapter
            """, (entity_id, entity_id)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---- 追读力操作 ----

    def record_reading_power(self, chapter: int, score: float,
                              hooks: List[str] = None,
                              debt_change: float = 0.0,
                              notes: str = "") -> None:
        """记录追读力"""
        conn = self._connect()
        try:
            conn.execute("""
                INSERT INTO reading_power (chapter, score, hooks, debt_change, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (chapter, score,
                  json.dumps(hooks or [], ensure_ascii=False),
                  debt_change, notes))
            conn.commit()
        finally:
            conn.close()

    def get_reading_power_trend(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """获取追读力趋势"""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM reading_power ORDER BY chapter DESC LIMIT ?", (last_n,)
            ).fetchall()
            results = []
            for r in reversed(list(rows)):
                d = dict(r)
                d["hooks"] = json.loads(d.get("hooks", "[]"))
                results.append(d)
            return results
        finally:
            conn.close()

    # ---- 审查指标 ----

    def record_review_metric(self, chapter: int, checker_type: str,
                              score: float, issues: List[str] = None,
                              suggestions: List[str] = None) -> None:
        """记录审查指标"""
        conn = self._connect()
        try:
            conn.execute("""
                INSERT INTO review_metrics (chapter, checker_type, score, issues, suggestions)
                VALUES (?, ?, ?, ?, ?)
            """, (chapter, checker_type, score,
                  json.dumps(issues or [], ensure_ascii=False),
                  json.dumps(suggestions or [], ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()

    def get_review_metrics(self, chapter: int) -> List[Dict[str, Any]]:
        """获取章节的审查指标"""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM review_metrics WHERE chapter = ?", (chapter,)
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["issues"] = json.loads(d.get("issues", "[]"))
                d["suggestions"] = json.loads(d.get("suggestions", "[]"))
                results.append(d)
            return results
        finally:
            conn.close()

    # ---- 统计 ----

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计"""
        conn = self._connect()
        try:
            chapters = conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
            entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            relationships = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
            appearances = conn.execute("SELECT COUNT(*) FROM entity_appearances").fetchone()[0]
            active_debt = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM narrative_debt WHERE status = 'active'"
            ).fetchone()[0]
            return {
                "chapters": chapters,
                "entities": entities,
                "relationships": relationships,
                "appearances": appearances,
                "active_debt": active_debt,
            }
        finally:
            conn.close()

    def reset(self) -> None:
        """重置索引（删除并重建）"""
        path = self.db_path
        if path and path.is_file():
            path.unlink()
        self.init_db()
