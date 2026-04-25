#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 驱动的实体/关系提取模块

使用 LLM 从小说文本中提取：
1. 角色实体（姓名、类型、层级、属性、描述）
2. 角色关系（from/to、类型、描述、章节）
3. 状态变化（实体、字段、旧值→新值、章节）
"""

from __future__ import annotations

import json
import re
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .config import ForgeAIConfig, get_config
from .cloud_llm_client import CloudLLMManager
from .state_manager import StateManager
from .index_manager import IndexManager


@dataclass
class ExtractedEntity:
    """提取的实体"""
    id: str
    name: str
    type: str = "character"  # character/location/item/faction
    tier: str = "secondary"  # core/important/secondary/decorative
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "tier": self.tier,
            "aliases": self.aliases,
            "attributes": self.attributes,
            "description": self.description,
        }


@dataclass
class ExtractedRelationship:
    """提取的关系"""
    from_entity: str
    to_entity: str
    type: str = "related"  # friend/enemy/mentor/family/lover/rival/subordinate/related
    description: str = ""
    chapter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "type": self.type,
            "description": self.description,
            "chapter": self.chapter,
        }


@dataclass
class ExtractedStateChange:
    """提取的状态变化"""
    entity_id: str
    field: str
    old_value: str
    new_value: str
    reason: str
    chapter: int
    change_type: str = "other"  # power/relationship/location/item/emotion/other

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "chapter": self.chapter,
            "change_type": self.change_type,
        }


@dataclass
class ExtractionResult:
    """提取结果"""
    entities: List[ExtractedEntity] = field(default_factory=list)
    relationships: List[ExtractedRelationship] = field(default_factory=list)
    state_changes: List[ExtractedStateChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "state_changes": [s.to_dict() for s in self.state_changes],
        }


class LLMEntityExtractor:
    """LLM 驱动的实体/关系提取器"""

    EXTRACT_PROMPT = """你是一位专业的小说分析师，请从以下章节文本中提取角色信息、角色关系和状态变化。

## 章节文本
{text}

## 提取要求

### 1. 角色（entities）
提取所有出场的角色，对每个角色提供：
- id: 角色ID（用拼音首字母或英文名，如 litian）
- name: 角色名
- type: 实体类型（character/location/item/faction）
- tier: 重要性层级
  - core: 主角、核心角色（每章必出或高频出场）
  - important: 重要配角（多章出场，推动剧情）
  - secondary: 次要配角（偶尔出场）
  - decorative: 装饰角色（路人、一次性角色）
- aliases: 别名/外号列表
- attributes: 属性字典（如修为、性格、外貌等已知信息）
- description: 简短描述

### 2. 关系（relationships）
提取角色之间的关系：
- from_entity: 关系发起方ID
- to_entity: 关系对象ID
- type: 关系类型（friend/enemy/mentor/family/lover/rival/subordinate/related）
- description: 关系描述
- chapter: 关系建立/变化的章节号（{chapter}）

### 3. 状态变化（state_changes）
提取角色在本章中的状态变化：
- entity_id: 角色ID
- field: 变化字段（如 power.realm 修为、location 位置、relationship.关系对象 关系等）
- old_value: 旧值（如果可推断）
- new_value: 新值
- reason: 变化原因
- chapter: 章节号（{chapter}）
- change_type: 变化类型（power/relationship/location/item/emotion/other）

## 输出格式
请严格按以下 JSON 格式输出，不要输出其他内容：
```json
{{
  "entities": [
    {{
      "id": "litian",
      "name": "李天",
      "type": "character",
      "tier": "core",
      "aliases": ["小李子"],
      "attributes": {{"修为": "筑基初期", "性格": "沉稳"}},
      "description": "男主角，筑基初期修士"
    }}
  ],
  "relationships": [
    {{
      "from_entity": "litian",
      "to_entity": "linxueer",
      "type": "lover",
      "description": "李天暗恋林雪儿",
      "chapter": {chapter}
    }}
  ],
  "state_changes": [
    {{
      "entity_id": "litian",
      "field": "power.realm",
      "old_value": "练气9层",
      "new_value": "筑基初期",
      "reason": "突破筑基",
      "chapter": {chapter},
      "change_type": "power"
    }}
  ]
}}
```"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.llm = CloudLLMManager()
        self.state_manager = StateManager(self.config)
        self.index_manager = IndexManager(self.config)

    async def extract_from_chapter(self, text: str, chapter: int) -> ExtractionResult:
        """从章节文本中提取实体、关系和状态变化"""
        prompt = self.EXTRACT_PROMPT.format(text=text[:8000], chapter=chapter)

        try:
            response = await self.llm.chat_completion_async(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3000,
            )
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            return self._parse_response(content, chapter)
        except Exception as e:
            # LLM 提取失败时返回空结果
            return ExtractionResult()

    def extract_from_chapter_sync(self, text: str, chapter: int) -> ExtractionResult:
        """同步版本"""
        return asyncio.run(self.extract_from_chapter(text, chapter))

    def _parse_response(self, response: str, chapter: int) -> ExtractionResult:
        """解析 LLM 响应"""
        data = self._extract_json(response)
        if not data:
            return ExtractionResult()

        result = ExtractionResult()

        # 解析实体
        for e in data.get("entities", []):
            try:
                result.entities.append(ExtractedEntity(
                    id=e.get("id", e.get("name", "")),
                    name=e.get("name", ""),
                    type=e.get("type", "character"),
                    tier=e.get("tier", "secondary"),
                    aliases=e.get("aliases", []),
                    attributes=e.get("attributes", {}),
                    description=e.get("description", ""),
                ))
            except Exception:
                continue

        # 解析关系
        for r in data.get("relationships", []):
            try:
                result.relationships.append(ExtractedRelationship(
                    from_entity=r.get("from_entity", ""),
                    to_entity=r.get("to_entity", ""),
                    type=r.get("type", "related"),
                    description=r.get("description", ""),
                    chapter=r.get("chapter", chapter),
                ))
            except Exception:
                continue

        # 解析状态变化
        for s in data.get("state_changes", []):
            try:
                result.state_changes.append(ExtractedStateChange(
                    entity_id=s.get("entity_id", ""),
                    field=s.get("field", ""),
                    old_value=s.get("old_value", ""),
                    new_value=s.get("new_value", ""),
                    reason=s.get("reason", ""),
                    chapter=s.get("chapter", chapter),
                    change_type=s.get("change_type", "other"),
                ))
            except Exception:
                continue

        return result

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从 LLM 响应中提取 JSON"""
        # 策略1：从代码块中提取
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 策略2：找最外层花括号
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                # 尝试修复
                fixed = self._try_fix_json(text[start:end + 1])
                if fixed:
                    return fixed

        return None

    def _try_fix_json(self, json_str: str) -> Optional[Dict]:
        """尝试修复 JSON"""
        # 移除注释
        json_str = re.sub(r'//.*?\n', '\n', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        # 修复尾逗号
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def save_to_state(self, result: ExtractionResult) -> Dict[str, int]:
        """将提取结果保存到 state.json 和 index.db"""
        stats = {"entities": 0, "relationships": 0, "state_changes": 0}

        # 保存实体
        for entity in result.entities:
            # 保存到 state
            self.state_manager.upsert_entity(entity.id, {
                "name": entity.name,
                "type": entity.type,
                "tier": entity.tier,
                "aliases": entity.aliases,
                "attributes": entity.attributes,
                "description": entity.description,
            })
            # 保存到 index
            try:
                self.index_manager.upsert_entity(
                    entity_id=entity.id,
                    name=entity.name,
                    type_=entity.type,
                    tier=entity.tier,
                    aliases=entity.aliases,
                    attributes=entity.attributes,
                    description=entity.description,
                )
            except Exception:
                pass
            stats["entities"] += 1

        # 保存关系
        for rel in result.relationships:
            # 保存到 state
            self.state_manager.add_relationship(
                from_entity=rel.from_entity,
                to_entity=rel.to_entity,
                rel_type=rel.type,
                description=rel.description,
                chapter=rel.chapter,
            )
            # 保存到 index
            try:
                self.index_manager.add_relationship(
                    from_entity=rel.from_entity,
                    to_entity=rel.to_entity,
                    type_=rel.type,
                    description=rel.description,
                    chapter=rel.chapter,
                )
            except Exception:
                pass
            stats["relationships"] += 1

        # 保存状态变化
        for change in result.state_changes:
            self.state_manager.record_state_change(
                entity_id=change.entity_id,
                field=change.field,
                old_value=change.old_value,
                new_value=change.new_value,
                reason=change.reason,
                chapter=change.chapter,
            )
            stats["state_changes"] += 1

        return stats
