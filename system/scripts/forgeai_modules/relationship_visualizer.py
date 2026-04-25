#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关系网络可视化模块

生成 Mermaid 格式的关系图，支持：
1. 全角色关系网
2. 指定角色的关系子图
3. 关系演变追踪
4. 角色设定模板自动生成
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

from .config import ForgeAIConfig, get_config
from .state_manager import StateManager
from .index_manager import IndexManager


# 关系类型到 Mermaid 线型的映射
RELATIONSHIP_STYLES = {
    "friend": "-->",
    "enemy": "--x",
    "mentor": "--|指导|-->",
    "family": "===",
    "lover": "...>",
    "rival": "--|竞争|-->",
    "subordinate": "--|服从|-->",
    "related": "-->",
}

# 关系类型到中文标签
RELATIONSHIP_LABELS = {
    "friend": "朋友",
    "enemy": "敌人",
    "mentor": "师徒",
    "family": "家人",
    "lover": "恋人",
    "rival": "对手",
    "subordinate": "上下级",
    "related": "关联",
}

# 层级到颜色的映射
TIER_COLORS = {
    "core": "#FF6B6B",
    "important": "#4ECDC4",
    "secondary": "#45B7D1",
    "decorative": "#96CEB4",
}


class RelationshipVisualizer:
    """关系网络可视化器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.state_manager = StateManager(self.config)
        self.index_manager = IndexManager(self.config)

    def generate_mermaid_graph(self, entity_id: Optional[str] = None,
                                tier_filter: Optional[str] = None,
                                max_depth: int = 2) -> str:
        """生成 Mermaid 关系图

        Args:
            entity_id: 指定角色ID（None=全图）
            tier_filter: 层级过滤（None=全部）
            max_depth: 关系深度（仅 entity_id 指定时有效）

        Returns:
            Mermaid 格式的关系图
        """
        state = self.state_manager.load()
        entities = state.get("entities", {})
        relationships = state.get("relationships", [])

        # 也从 index.db 获取
        try:
            idx_stats = self.index_manager.get_stats()
            if idx_stats.get("relationships", 0) > 0:
                # 补充 index.db 中的关系
                idx_rels = self._get_all_index_relationships()
                existing_keys = {
                    (r.get("from_entity"), r.get("to_entity"), r.get("type"))
                    for r in relationships
                }
                for r in idx_rels:
                    key = (r.get("from_entity"), r.get("to_entity"), r.get("type"))
                    if key not in existing_keys:
                        relationships.append(r)
                        existing_keys.add(key)
        except Exception:
            pass

        if not relationships:
            return "```mermaid\ngraph LR\n    A[暂无关系数据]\\n```"

        # 确定显示的实体集合
        if entity_id:
            visible_entities = self._get_connected_entities(
                entity_id, relationships, max_depth
            )
        else:
            visible_entities = set(entities.keys())
            # 也加入关系中出现但不在 entities 中的 ID
            for r in relationships:
                visible_entities.add(r.get("from_entity", ""))
                visible_entities.add(r.get("to_entity", ""))

        # 层级过滤
        if tier_filter:
            visible_entities = {
                eid for eid in visible_entities
                if entities.get(eid, {}).get("tier", "decorative") == tier_filter
            }

        # 过滤关系
        visible_rels = [
            r for r in relationships
            if r.get("from_entity", "") in visible_entities
            and r.get("to_entity", "") in visible_entities
        ]

        # 生成 Mermaid
        lines = ["```mermaid", "graph LR"]

        # 实体节点
        for eid in sorted(visible_entities):
            entity_data = entities.get(eid, {})
            name = entity_data.get("name", eid)
            tier = entity_data.get("tier", "decorative")
            etype = entity_data.get("type", "character")
            color = TIER_COLORS.get(tier, "#96CEB4")

            # Mermaid 节点ID 不能有特殊字符
            node_id = self._safe_id(eid)
            label = f"{name}\\n({etype})"
            lines.append(f"    {node_id}[\"{label}\"]")
            lines.append(f"    style {node_id} fill:{color},color:#fff")

        # 关系边
        seen_edges = set()
        for r in visible_rels:
            from_id = self._safe_id(r.get("from_entity", ""))
            to_id = self._safe_id(r.get("to_entity", ""))
            rel_type = r.get("type", "related")
            desc = r.get("description", "")

            edge_key = (from_id, to_id, rel_type)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            label = RELATIONSHIP_LABELS.get(rel_type, rel_type)
            if desc and len(desc) <= 20:
                label = desc

            lines.append(f"    {from_id} -->|\"{label}\"| {to_id}")

        lines.append("```")

        # 添加图例
        lines.append("")
        lines.append("### 图例")
        for tier, color in TIER_COLORS.items():
            lines.append(f"- ![{tier}](https://via.placeholder.com/15/{color[1:]}/{color[1:]}.png) {tier}")
        for rtype, rlabel in RELATIONSHIP_LABELS.items():
            lines.append(f"- `--|{rlabel}|-->` = {rlabel}")

        return "\n".join(lines)

    def generate_evolution_mermaid(self, entity_id: str,
                                    from_chapter: int = 0,
                                    to_chapter: int = 999) -> str:
        """生成关系演变图（按章节追踪关系变化）

        Args:
            entity_id: 角色 ID
            from_chapter: 起始章节
            to_chapter: 结束章节

        Returns:
            Mermaid 时序图
        """
        state = self.state_manager.load()
        entities = state.get("entities", {})
        state_changes = state.get("state_changes", [])
        relationships = state.get("relationships", [])

        entity_name = entities.get(entity_id, {}).get("name", entity_id)

        lines = ["```mermaid", "timeline", f"    title {entity_name} 关系演变"]

        # 获取相关的关系变化
        rel_changes = [
            r for r in relationships
            if (r.get("from_entity") == entity_id or r.get("to_entity") == entity_id)
            and from_chapter <= r.get("chapter", 0) <= to_chapter
        ]

        # 获取状态变化
        entity_state_changes = [
            s for s in state_changes
            if (s.get("entity_id") == entity_id or s.get("entity") == entity_id)
            and from_chapter <= s.get("chapter", 0) <= to_chapter
        ]

        # 按章节分组
        chapter_events = defaultdict(list)
        for r in rel_changes:
            ch = r.get("chapter", 0)
            other = r.get("to_entity") if r.get("from_entity") == entity_id else r.get("from_entity")
            other_name = entities.get(other, {}).get("name", other)
            rel_label = RELATIONSHIP_LABELS.get(r.get("type", ""), r.get("type", ""))
            desc = r.get("description", "")
            chapter_events[ch].append(f"与{other_name}建立{rel_label}关系" + (f"：{desc}" if desc else ""))

        for s in entity_state_changes:
            ch = s.get("chapter", 0)
            field = s.get("field", "")
            old_val = s.get("old_value", "")
            new_val = s.get("new_value", "")
            chapter_events[ch].append(f"{field}: {old_val} → {new_val}")

        if not chapter_events:
            lines.append("    暂无数据")
        else:
            for ch in sorted(chapter_events.keys()):
                lines.append(f"    第{ch}章")
                for event in chapter_events[ch][:5]:
                    lines.append(f"        : {event}")

        lines.append("```")
        return "\n".join(lines)

    def generate_character_template(self, entity_id: str) -> str:
        """生成角色设定模板（Markdown）

        Args:
            entity_id: 角色 ID

        Returns:
            Markdown 格式的角色设定
        """
        state = self.state_manager.load()
        entities = state.get("entities", {})
        relationships = state.get("relationships", [])

        entity_data = entities.get(entity_id, {})
        if not entity_data:
            return f"# 角色设定：{entity_id}\n\n⚠️ 未找到角色数据"

        name = entity_data.get("name", entity_id)
        tier = entity_data.get("tier", "secondary")
        etype = entity_data.get("type", "character")
        aliases = entity_data.get("aliases", [])
        attributes = entity_data.get("attributes", {})
        description = entity_data.get("description", "")

        # 获取关系
        entity_rels = [
            r for r in relationships
            if r.get("from_entity") == entity_id or r.get("to_entity") == entity_id
        ]

        # 获取出场记录
        appearances = []
        try:
            appearances = self.index_manager.get_entity_appearances(entity_id, limit=20)
        except Exception:
            pass

        # 获取状态变化
        state_changes = [
            s for s in state.get("state_changes", [])
            if s.get("entity_id") == entity_id or s.get("entity") == entity_id
        ]

        lines = [
            f"# {name} 角色设定",
            "",
            f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 基本信息",
            "",
            f"| 属性 | 值 |",
            f"|------|-----|",
            f"| 姓名 | {name} |",
            f"| ID | {entity_id} |",
            f"| 类型 | {etype} |",
            f"| 层级 | {tier} |",
            f"| 别名 | {', '.join(aliases) if aliases else '无'} |",
            f"| 简介 | {description or '待补充'} |",
            "",
        ]

        # 属性详情
        if attributes:
            lines.extend(["## 属性详情", "", "| 属性 | 值 |", "|------|-----|"])
            for key, val in attributes.items():
                lines.append(f"| {key} | {val} |")
            lines.append("")

        # 关系网络
        if entity_rels:
            lines.extend(["## 关系网络", "", "| 对象 | 关系 | 描述 | 章节 |", "|------|------|------|------|"])
            for r in entity_rels:
                other = r.get("to_entity") if r.get("from_entity") == entity_id else r.get("from_entity")
                other_name = entities.get(other, {}).get("name", other)
                rel_label = RELATIONSHIP_LABELS.get(r.get("type", ""), r.get("type", ""))
                desc = r.get("description", "")
                ch = r.get("chapter", 0)
                lines.append(f"| {other_name} | {rel_label} | {desc} | 第{ch}章 |")
            lines.append("")

        # 状态变化
        if state_changes:
            lines.extend([
                "## 成长/状态变化",
                "",
                "| 章节 | 字段 | 旧值 | 新值 | 原因 |",
                "|------|------|------|------|------|",
            ])
            for s in sorted(state_changes, key=lambda x: x.get("chapter", 0)):
                lines.append(
                    f"| 第{s.get('chapter', 0)}章 | {s.get('field', '')} | "
                    f"{s.get('old_value', '')} | {s.get('new_value', '')} | {s.get('reason', '')} |"
                )
            lines.append("")

        # 出场记录
        if appearances:
            lines.extend(["## 出场记录", "", "| 章节 | 场景 | 角色 |", "|------|------|------|"])
            for a in appearances[:20]:
                lines.append(
                    f"| 第{a.get('chapter', 0)}章 | 场景{a.get('scene_index', 0)} | {a.get('role', '')} |"
                )
            lines.append("")

        # 关系图
        lines.extend(["## 关系图", "", self.generate_mermaid_graph(entity_id)])

        return "\n".join(lines)

    def generate_all_character_templates(self, output_dir: Path) -> Dict[str, str]:
        """为所有角色生成设定模板

        Args:
            output_dir: 输出目录

        Returns:
            {entity_id: 输出文件路径} 字典
        """
        state = self.state_manager.load()
        entities = state.get("entities", {})

        results = {}
        for eid, edata in entities.items():
            if edata.get("type") == "character":
                template = self.generate_character_template(eid)
                name = edata.get("name", eid)
                safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
                output_path = output_dir / f"{safe_name}.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(template, encoding="utf-8")
                results[eid] = str(output_path)

        return results

    def check_ooc(self, entity_id: str, chapter_text: str) -> Dict[str, Any]:
        """基于角色设定检查 OOC（Out of Character）

        Args:
            entity_id: 角色 ID
            chapter_text: 章节文本

        Returns:
            OOC 检查结果
        """
        state = self.state_manager.load()
        entities = state.get("entities", {})
        entity_data = entities.get(entity_id, {})

        if not entity_data:
            return {"error": f"未找到角色: {entity_id}"}

        name = entity_data.get("name", entity_id)
        attributes = entity_data.get("attributes", {})
        description = entity_data.get("description", "")

        # 基于规则的 OOC 检查
        issues = []

        # 1. 检查位置一致性
        current_location = attributes.get("位置", attributes.get("location", ""))
        if current_location and name in chapter_text:
            # 检查文本中是否提到了不该在的位置
            location_keywords = [current_location]
            for keyword in location_keywords:
                # 简单检查：如果角色出现但不在已知位置
                pass  # 需要更复杂的 NLP 处理

        # 2. 检查修为/能力一致性
        current_power = attributes.get("修为", attributes.get("境界", ""))
        if current_power:
            # 检查是否有低于当前修为的描述
            downgrade_patterns = [
                f"{name}.*实力倒退",
                f"{name}.*修为下降",
                f"{name}.*境界跌落",
            ]
            for pattern in downgrade_patterns:
                if re.search(pattern, chapter_text):
                    issues.append({
                        "type": "power_regression",
                        "severity": "error",
                        "description": f"{name}的修为出现倒退描述，当前修为：{current_power}",
                    })

        # 3. 检查性格一致性
        personality = attributes.get("性格", "")
        if personality:
            # 基于性格关键词的反向检查
            personality_keywords = {
                "沉稳": ["慌张", "惊慌失措", "手忙脚乱"],
                "冷酷": ["温柔", "关怀", "心软"],
                "善良": ["残忍", "狠毒", "冷血"],
                "聪明": ["愚蠢", "犯傻", "糊涂"],
                "勇敢": ["胆怯", "退缩", "畏惧"],
            }
            for trait, contradictions in personality_keywords.items():
                if trait in personality:
                    for contra in contradictions:
                        if f"{name}" in chapter_text and contra in chapter_text:
                            # 找到角色名和矛盾词的上下文
                            context_start = max(0, chapter_text.find(name) - 20)
                            context_end = min(len(chapter_text), chapter_text.find(name) + 50)
                            context = chapter_text[context_start:context_end]
                            if contra in context:
                                issues.append({
                                    "type": "personality_contradiction",
                                    "severity": "warning",
                                    "description": f"{name}性格设定为'{trait}'，但出现矛盾描述：'{context}'",
                                })

        # 4. 检查关系一致性
        relationships = state.get("relationships", [])
        entity_rels = [
            r for r in relationships
            if r.get("from_entity") == entity_id or r.get("to_entity") == entity_id
        ]
        for rel in entity_rels:
            other = rel.get("to_entity") if rel.get("from_entity") == entity_id else rel.get("from_entity")
            other_name = entities.get(other, {}).get("name", other)
            rel_type = rel.get("type", "")
            rel_desc = rel.get("description", "")

            # 检查敌人关系中出现亲密行为
            if rel_type == "enemy" and name in chapter_text and other_name in chapter_text:
                intimate_patterns = ["拥抱", "亲吻", "牵手", "微笑着看着"]
                for pattern in intimate_patterns:
                    if pattern in chapter_text:
                        # 检查是否是同一上下文
                        name_pos = chapter_text.find(name)
                        other_pos = chapter_text.find(other_name)
                        pattern_pos = chapter_text.find(pattern)
                        if (name_pos >= 0 and other_pos >= 0 and pattern_pos >= 0
                                and abs(name_pos - other_pos) < 100
                                and abs(pattern_pos - max(name_pos, other_pos)) < 50):
                            issues.append({
                                "type": "relationship_contradiction",
                                "severity": "error",
                                "description": f"{name}与{other_name}是敌人关系({rel_desc})，但出现亲密行为'{pattern}'",
                            })

        return {
            "entity_id": entity_id,
            "entity_name": name,
            "issues": issues,
            "total_issues": len(issues),
            "checked_attributes": list(attributes.keys()),
        }

    def _get_connected_entities(self, entity_id: str, relationships: List[Dict],
                                 max_depth: int) -> Set[str]:
        """获取与指定实体相连的所有实体"""
        connected = {entity_id}
        frontier = {entity_id}

        for _ in range(max_depth):
            new_frontier = set()
            for r in relationships:
                fe = r.get("from_entity", "")
                te = r.get("to_entity", "")
                if fe in frontier and te not in connected:
                    new_frontier.add(te)
                if te in frontier and fe not in connected:
                    new_frontier.add(fe)
            connected.update(new_frontier)
            frontier = new_frontier
            if not frontier:
                break

        return connected

    def _get_all_index_relationships(self) -> List[Dict]:
        """从 index.db 获取所有关系"""
        try:
            conn = self.index_manager._connect()
            rows = conn.execute("SELECT * FROM relationships").fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _safe_id(self, eid: str) -> str:
        """将实体 ID 转为安全的 Mermaid 节点 ID"""
        return re.sub(r'[^a-zA-Z0-9_]', '_', eid)
