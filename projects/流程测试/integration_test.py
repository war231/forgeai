#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""集成测试脚本 - 检查全流程"""
import sys
import os
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
import json
import sqlite3
import sys
from pathlib import Path

root = Path("projects/流程测试")
issues = []

print("=" * 60)
print("ForgeAI 集成测试报告")
print("=" * 60)

# 1. 项目结构检查
print("\n[1] 项目结构检查")
required_dirs = [".forgeai", "1-边界", "2-设定", "3-大纲", "4-正文", "5-审查"]
for d in required_dirs:
    if (root / d).is_dir():
        print(f"  ✓ {d}/")
    else:
        print(f"  ✗ {d}/ MISSING")
        issues.append(f"缺少目录: {d}")

# 2. 数据一致性检查
print("\n[2] 数据一致性: state.json ↔ index.db")
state = json.loads((root / ".forgeai/state.json").read_text(encoding="utf-8"))
state_entities = list(state.get("entities", {}).keys())
state_rels = state.get("relationships", [])

conn = sqlite3.connect(str(root / ".forgeai/index.db"))
conn.row_factory = sqlite3.Row
db_entities = [dict(r) for r in conn.execute("SELECT id, name, tier FROM entities").fetchall()]
db_rels = [dict(r) for r in conn.execute("SELECT from_entity, to_entity, type, description FROM relationships").fetchall()]
conn.close()

print(f"  state.json: {len(state_entities)} entities, {len(state_rels)} relationships")
print(f"  index.db:   {len(db_entities)} entities, {len(db_rels)} relationships")

state_ids = set(state_entities)
db_ids = set(e["id"] for e in db_entities)
only_in_state = state_ids - db_ids
only_in_db = db_ids - state_ids
if only_in_state or only_in_db:
    print(f"  ✗ INCONSISTENCY: only_in_state={only_in_state}, only_in_db={only_in_db}")
    issues.append(f"数据不一致: state={only_in_state}, db={only_in_db}")
else:
    print(f"  ✓ state.json 和 index.db 实体一致")

# 关系数量一致
if len(state_rels) == len(db_rels):
    print(f"  ✓ 关系数量一致 ({len(state_rels)})")
else:
    print(f"  ✗ 关系数量不一致: state={len(state_rels)}, db={len(db_rels)}")
    issues.append(f"关系数量不一致: state={len(state_rels)}, db={len(db_rels)}")

# 3. 实体详情
print("\n[3] 实体详情")
for eid in sorted(state_ids):
    edata = state["entities"][eid]
    db_ent = next((e for e in db_entities if e["id"] == eid), None)
    db_tier = db_ent["tier"] if db_ent else "?"
    state_tier = edata.get("tier", "?")
    match = "✓" if state_tier == db_tier else "✗"
    print(f"  {match} {eid}: name={edata.get('name')}, tier={state_tier} (db: {db_tier})")
    if state_tier != db_tier:
        issues.append(f"实体 {eid} tier 不一致: state={state_tier}, db={db_tier}")

# 4. 关系详情
print("\n[4] 关系详情")
for i, rel in enumerate(state_rels):
    print(f"  {rel['from_entity']} --[{rel['type']}]--> {rel['to_entity']}: {rel.get('description', '')}")

# 5. Stats 命令一致性
print("\n[5] stats 命令测试")
from forgeai_modules.config import get_config
from forgeai_modules.index_manager import IndexManager
from forgeai_modules.rag_adapter import RAGAdapter

config = get_config(root)
im = IndexManager(config)
stats = im.get_stats()
print(f"  index.stats: entities={stats['entities']}, relationships={stats['relationships']}")
if stats["entities"] == len(state_entities):
    print(f"  ✓ stats 实体数与 state.json 一致")
else:
    print(f"  ✗ stats 实体数不一致: stats={stats['entities']}, state={len(state_entities)}")
    issues.append(f"stats 实体数不一致")

# 6. 角色模板生成测试
print("\n[6] 角色模板生成测试")
from forgeai_modules.relationship_visualizer import RelationshipVisualizer
viz = RelationshipVisualizer(config)
for eid in ["chenxiao", "suyan"]:
    template = viz.generate_character_template(eid)
    has_name = "陈潇" in template or "苏颜" in template
    has_rel = "青梅竹马" in template or "师徒" in template
    has_mermaid = "mermaid" in template
    status = "✓" if has_name and has_rel and has_mermaid else "✗"
    print(f"  {status} {eid}: name={has_name}, rel={has_rel}, mermaid={has_mermaid}")
    if not (has_name and has_rel and has_mermaid):
        issues.append(f"角色模板 {eid} 生成不完整")

# 7. OOC 检查测试
print("\n[7] OOC 检查测试")
ooc_result = viz.check_ooc("chenxiao", "陈潇慌张地跑过来")
if "issues" in ooc_result:
    print(f"  ✓ OOC 检查正常运行, 发现 {ooc_result['total_issues']} 个问题")
else:
    print(f"  ✗ OOC 检查异常: {ooc_result}")
    issues.append("OOC 检查异常")

# 8. Growth 成长分析测试
print("\n[8] Growth 成长分析测试")
from forgeai_modules.growth_analyzer import GrowthAnalyzer
analyzer = GrowthAnalyzer(config)
# 先添加一些状态变化
from forgeai_modules.state_manager import StateManager
sm = StateManager(config)
s = sm.load()
s.setdefault("state_changes", []).append({
    "entity_id": "chenxiao",
    "field": "power.realm",
    "old_value": "练气1层",
    "new_value": "练气3层",
    "reason": "修炼突破",
    "chapter": 5,
    "change_type": "power",
})
sm.save(s)

analysis = analyzer.analyze_entity_growth("chenxiao")
if analysis:
    print(f"  ✓ Growth 分析成功: velocity={analysis.velocity}, trajectory={analysis.trajectory}")
    print(f"    milestones: {len(analysis.timeline.milestones)}, pattern={analysis.growth_pattern}")
else:
    print(f"  ✗ Growth 分析失败")
    issues.append("Growth 分析失败")

# 9. 关系图生成测试
print("\n[9] 关系图生成测试")
mermaid = viz.generate_mermaid_graph()
has_graph = "graph LR" in mermaid
has_entities = "chenxiao" in mermaid
if has_graph and has_entities:
    print(f"  ✓ Mermaid 关系图生成成功")
else:
    print(f"  ✗ Mermaid 关系图生成失败")
    issues.append("Mermaid 关系图生成失败")

# 10. 关系演变追踪测试
print("\n[10] 关系演变追踪测试")
evo = viz.generate_evolution_mermaid("chenxiao")
has_timeline = "timeline" in evo
if has_timeline:
    print(f"  ✓ 关系演变追踪生成成功")
else:
    print(f"  ✗ 关系演变追踪生成失败")
    issues.append("关系演变追踪生成失败")

# 汇总
print("\n" + "=" * 60)
if issues:
    print(f"发现问题: {len(issues)} 个")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("所有集成测试通过！")
print("=" * 60)
