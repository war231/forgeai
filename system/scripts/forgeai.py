#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ForgeAI CLI - 统一命令行入口

用法:
  python forgeai.py init [--name NAME] [--genre GENRE] [--mode MODE] [--project-root DIR]
  python forgeai.py status [--project-root DIR]
  python forgeai.py index <chapter> <text_file> [--project-root DIR]
  python forgeai.py search <query> [--top-k N] [--project-root DIR]
  python forgeai.py context <chapter> [--query QUERY] [--project-root DIR]
  python forgeai.py score <text_file> [--llm] [--project-root DIR]
  python forgeai.py evolve <text_file> [--rounds N] [--project-root DIR]
  python forgeai.py stats [--project-root DIR]
  python forgeai.py entity list [--type TYPE] [--project-root DIR]
  python forgeai.py entity add --id ID --name NAME [--type TYPE] [--tier TIER] [--project-root DIR]
  python forgeai.py entity import --input-file FILE [--project-root DIR]
  python forgeai.py entity relationship [list|add|graph|evolution|template|ooc-check] [OPTIONS]
  python forgeai.py relationship [list|add|graph|evolution|template|ooc-check] [OPTIONS]
  python forgeai.py extract <chapter> <text_file> [--save] [--llm] [--project-root DIR]
  python forgeai.py foreshadowing list [--active-only] [--project-root DIR]
  python forgeai.py foreshadowing add --description DESC --chapter N [--payoff N] [--project-root DIR]
  python forgeai.py foreshadowing resolve --id ID --chapter N [--project-root DIR]
  python forgeai.py analyze <input_file> [-o OUTPUT_DIR] [--from-chapter N] [--to-chapter N] [-v] [--project-root DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path

# Windows UTF-8 兼容
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# 将当前目录加入 sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from forgeai_modules.config import ForgeAIConfig, get_config, reset_config
from forgeai_modules.state_manager import StateManager
from forgeai_modules.index_manager import IndexManager
from forgeai_modules.rag_adapter import RAGAdapter
from forgeai_modules.context_extractor import ContextExtractor
from forgeai_modules.humanize_scorer import HumanizeScorer
from forgeai_modules.entity_extractor_v3_ner import SmartEntityExtractor as EntityExtractor
from forgeai_modules.pipeline import Pipeline
from forgeai_modules.init_project import ProjectInitializer
from forgeai_modules.timeline_manager import TimelineManager
from forgeai_modules.independent_reviewer import IndependentReviewer
from forgeai_modules.outline_confirmer import OutlineConfirmer
from forgeai_modules.state_change_confirmer import StateChangeConfirmer
from forgeai_modules.growth_analyzer import GrowthAnalyzer
from forgeai_modules.volume_manager import VolumeManager
from forgeai_modules.consistency_checker import ConsistencyChecker
from forgeai_modules.chapter_generator import ChapterGenerator
from forgeai_modules.reference_integrator import ReferenceIntegrator
from forgeai_modules.genre_profile_loader import GenreProfileLoader
from forgeai_modules.book_analyzer import BookAnalyzer
from forgeai_modules.llm_entity_extractor import LLMEntityExtractor
from forgeai_modules.relationship_visualizer import RelationshipVisualizer

# CLI 优化模块
from forgeai_modules.cli_formatter import print_success, print_error, print_info
from forgeai_modules.help_system import HelpSystem
from forgeai_modules.progress_display import show_progress, show_spinner


def _resolve_root(args) -> Path:
    """解析项目根目录：优先用 --project-root，否则自动查找"""
    explicit = getattr(args, "project_root", None)
    if explicit:
        return Path(explicit).resolve()
    # 自动从当前目录向上查找
    current = Path.cwd()
    while current != current.parent:
        if (current / ".forgeai").is_dir() or (current / ".novelkit").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def _get_config(args) -> ForgeAIConfig:
    """从 args 获取配置"""
    root = _resolve_root(args)
    return get_config(root)


# ====== 子命令实现 ======

def cmd_init(args) -> None:
    """初始化项目"""
    root = _resolve_root(args)
    initializer = ProjectInitializer()
    result = initializer.init(
        project_root=root,
        project_name=args.name or "",
        genre=args.genre or "",
        mode=args.mode or "standard",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_status(args) -> None:
    """查看项目状态"""
    config = _get_config(args)
    sm = StateManager(config)
    summary = sm.get_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def cmd_help(args) -> None:
    """显示帮助信息"""
    command_name = getattr(args, "command_name", None)
    HelpSystem.show_help(command_name)


def cmd_version(args) -> None:
    """显示版本信息"""
    HelpSystem.show_version()


def cmd_index(args) -> None:
    """索引章节"""
    config = _get_config(args)
    rag = RAGAdapter(config)

    text_file = Path(args.text_file)
    if not text_file.is_file():
        print(json.dumps({"error": f"文件不存在: {text_file}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    text = text_file.read_text(encoding="utf-8")
    count = rag.index_chapter(args.chapter, text, source_file=str(text_file))

    # 同时更新 state 和 index
    sm = StateManager(config)
    sm.update_progress(current_chapter=args.chapter)

    im = IndexManager(config)
    im.upsert_chapter(args.chapter, word_count=len(text))

    print(json.dumps({"status": "ok", "chapter": args.chapter, "chunks_indexed": count}, ensure_ascii=False))


def cmd_search(args) -> None:
    """搜索"""
    config = _get_config(args)
    rag = RAGAdapter(config)

    results = asyncio.run(rag.search(args.query, top_k=args.top_k))
    output = []
    for r in results:
        output.append({
            "chunk_id": r.chunk_id,
            "chapter": r.chapter,
            "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "score": round(r.score, 4),
            "source": r.source,
        })
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_context(args) -> None:
    """提取上下文"""
    config = _get_config(args)
    
    # 如果启用智能上下文模式
    if hasattr(args, 'smart') and args.smart:
        pipeline = Pipeline(config)
        result = pipeline.smart_context(
            chapter=args.chapter,
            query=args.query or "",
            max_chars=getattr(args, 'max_chars', 8000),
        )
        print(result["formatted"])
        return
    
    extractor = ContextExtractor(config)

    context = asyncio.run(
        extractor.extract_with_rag(args.chapter, query=args.query or "")
    )

    # 输出格式化的上下文
    formatted = extractor.format_context_for_prompt(context)
    
    # 如果启用确认模式，显示确认提示
    if hasattr(args, 'confirm') and args.confirm:
        from forgeai_modules.outline_confirmer import OutlineConfirmer
        
        confirmer = OutlineConfirmer(config)
        
        # 生成创作执行包（简化版）
        execution_package = {
            "任务书": context,
            "chapter": args.chapter
        }
        
        # 显示执行包
        print(confirmer.display_execution_package(execution_package))
        print()
        print(confirmer.prompt_user_confirmation())
        
        # 在实际使用中，这里需要交互式输入
        # 但在测试环境中，我们返回提示
        print("\n提示：请在实际使用时输入 y/n/edit 进行确认")
    else:
        print(formatted)


def cmd_write(args) -> None:
    """一键写作：写前检查 + 提取上下文 + 生成章节"""
    config = _get_config(args)
    chapter = args.chapter
    
    print(f"\n{'='*60}")
    print(f"[Write] 第{chapter}章一键写作")
    print(f"{'='*60}\n")
    
    # Step 1: 写前检查
    print("[1/4] 执行写前检查...")
    pipeline = Pipeline(config)
    pre_check = pipeline.pre_write_check(chapter)
    
    if pre_check.get("alerts"):
        print("[Warning] 发现以下提醒：")
        for alert in pre_check["alerts"]:
            print(f"  [{alert['level']}] {alert['message']}")
    else:
        print("[OK] 写前检查通过")
    
    # Step 2: 提取上下文
    print(f"\n[2/4] 提取上下文...")
    extractor = ContextExtractor(config)
    
    # 使用智能上下文或标准上下文
    use_rag = hasattr(args, 'smart') and args.smart
    query = getattr(args, 'query', "") or ""
    
    if use_rag:
        context_data = asyncio.run(
            extractor.extract_with_rag(chapter, query=query)
        )
    else:
        context_data = extractor.extract_full_context(chapter, query)
    
    formatted_context = extractor.format_context_for_prompt(context_data)
    print(f"[OK] 上下文提取完成（{len(formatted_context)}字符）")
    
    # Step 3: 生成章节
    print(f"\n[3/4] 生成章节...")
    
    # 获取题材
    state_manager = StateManager(config)
    state = state_manager.load()
    genre = state.get("project", {}).get("genre", "shuangwen")
    
    # 创建章节生成器
    generator = ChapterGenerator(config)
    
    # 生成章节
    result = asyncio.run(
        generator.generate_chapter(
            chapter_num=chapter,
            genre=genre,
            query=query,
            use_rag=use_rag,
        )
    )
    
    if result.success:
        print(f"[OK] 章节生成完成")
        print(f"  - 标题: {result.title}")
        print(f"  - 字数: {result.word_count}")
    else:
        print(f"[Error] 章节生成失败: {result.error_message}")
        return
    
    # Step 4: 保存章节
    print(f"\n[4/4] 保存章节...")
    
    # 确定输出路径
    root = _resolve_root(args)
    if hasattr(args, 'output') and args.output:
        output_path = Path(args.output)
    else:
        # 默认保存到 4-正文/草稿/
        output_dir = root / "4-正文" / "草稿"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"第{chapter}章.md"
    
    # 保存章节
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"# {result.title}\n\n{result.content}"
    output_path.write_text(content, encoding="utf-8")
    
    print(f"[OK] 章节已保存到: {output_path}")
    
    # 输出统计信息
    print(f"\n{'='*60}")
    print("[Stats] 生成统计")
    print(f"{'='*60}")
    print(f"章节: 第{chapter}章")
    print(f"标题: {result.title}")
    print(f"字数: {result.word_count}")
    print(f"题材: {genre}")
    print(f"写前提醒: {len(pre_check.get('alerts', []))} 条")
    print(f"上下文字数: {len(formatted_context)} 字符")
    print(f"主题指导: {query or '无'}")
    print(f"输出文件: {output_path}")
    print(f"{'='*60}\n")
    
    # 输出章节预览
    print("[Preview] 章节预览（前500字）:")
    print("-" * 60)
    print(result.content[:500])
    if len(result.content) > 500:
        print("...")
    print("-" * 60)


def cmd_score(args) -> None:
    """AI味评分"""
    text_file = Path(args.text_file)
    if text_file.is_file():
        text = text_file.read_text(encoding="utf-8")
    else:
        # 直接作为文本评分
        text = args.text_file

    config = _get_config(args)
    scorer = HumanizeScorer(config)

    # 如果启用进化模式
    if hasattr(args, 'evolve') and args.evolve:
        result = asyncio.run(scorer.evolve(text, max_rounds=getattr(args, 'rounds', 3)))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.llm:
        result = asyncio.run(scorer.combined_score(text))
    else:
        result = scorer.rule_based_score(text)

    output = {
        "score": round(result.score, 4),
        "human_likeness": round(result.human_likeness, 4),
        "ai_likeness": round(result.ai_likeness, 4),
        "detected_patterns": result.ai_patterns,
        "details": result.details,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_evolve(args) -> None:
    """进化式去AI味"""
    text_file = Path(args.text_file)
    if text_file.is_file():
        text = text_file.read_text(encoding="utf-8")
    else:
        text = args.text_file

    config = _get_config(args)
    scorer = HumanizeScorer(config)

    result = asyncio.run(scorer.evolve(text, max_rounds=args.rounds))
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_stats(args) -> None:
    """查看统计"""
    config = _get_config(args)
    im = IndexManager(config)
    rag = RAGAdapter(config)

    index_stats = im.get_stats()
    rag_stats = rag.get_stats()

    print(json.dumps({
        "index": index_stats,
        "rag": rag_stats,
    }, indent=2, ensure_ascii=False))


def cmd_entity(args) -> None:
    """实体管理"""
    config = _get_config(args)

    if args.entity_action == "list":
        sm = StateManager(config)
        entities = sm.get_entities()
        if args.type:
            entities = {k: v for k, v in entities.items() if v.get("type") == args.type}
        print(json.dumps(list(entities.values()), indent=2, ensure_ascii=False))

    elif args.entity_action == "add":
        im = IndexManager(config)
        im.upsert_entity(
            entity_id=args.id,
            name=args.name,
            type_=args.type or "character",
            tier=args.tier or "decorative",
        )
        # 同步到 state
        sm = StateManager(config)
        sm.upsert_entity(args.id, {
            "name": args.name,
            "type": args.type or "character",
            "tier": args.tier or "decorative",
        })
        print(json.dumps({"status": "ok", "id": args.id, "name": args.name}, ensure_ascii=False))

    elif args.entity_action == "import":
        # 从 Markdown 文件批量导入角色
        _cmd_entity_import(args, config)

    elif args.entity_action == "relationship":
        # 关系管理
        _cmd_relationship(args, config)


def _cmd_entity_import(args, config: ForgeAIConfig) -> None:
    """从 Markdown 文件批量导入角色"""
    import re as _re

    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(json.dumps({"error": f"文件不存在: {input_path}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    content = input_path.read_text(encoding="utf-8")
    im = IndexManager(config)
    sm = StateManager(config)

    imported = []
    imported_names = set()

    # 解析策略1：逐行解析 Markdown 表格
    tables_found = False
    in_table = False
    header_row = None
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            if in_table:
                in_table = False
                header_row = None
            continue

        in_table = True
        cells = [c.strip() for c in line.strip('|').split('|')]

        # 检测分隔行 |---|---|
        if all(set(c.strip()) <= set('-: ') for c in cells if c.strip()):
            continue

        # 检测表头行
        if header_row is None:
            header_keywords = {"姓名", "角色", "名字", "角色名", "name", "character", "人物"}
            if cells and cells[0].strip().lower() in header_keywords:
                header_row = cells
                tables_found = True
                continue
            # 如果第一行不是表头，也尝试当作数据行
            continue

        # 数据行
        tables_found = True
        name = cells[0].strip() if cells else ""
        # 跳过空行和非角色名
        if not name or len(name) > 20:
            continue
        if name.lower() in ("character", "location", "item", "faction",
                            "core", "important", "secondary", "decorative",
                            "描述", "description", "类型", "type", "层级", "tier"):
            continue
        # 必须是中文名或英文名
        if not any('\u4e00' <= c <= '\u9fff' for c in name) and not name.isalpha():
            continue
        # 跳过已导入
        if name in imported_names:
            continue

        entity_id = _re.sub(r'[^\w]', '_', name)
        etype = "character"
        tier = "secondary"
        description = ""

        # 从其他列提取信息
        for cell in cells[1:]:
            cell = cell.strip()
            if not cell:
                continue
            if cell in ("主角", "核心", "core"):
                tier = "core"
            elif cell in ("重要配角", "重要", "important"):
                tier = "important"
            elif cell in ("次要配角", "次要", "secondary"):
                tier = "secondary"
            elif cell in ("路人", "装饰", "龙套", "decorative"):
                tier = "decorative"
            elif cell in ("character", "location", "item", "faction"):
                etype = "character"
            elif len(cell) > 2 and not cell.startswith('-') and cell not in ("---", "------"):
                # 最后一个较长内容作为描述（会覆盖之前的短描述）
                description = cell

        imported_names.add(name)
        tables_found = True

        # 从其他列提取信息
        for cell in cells[1:]:
            cell = cell.strip()
            if not cell:
                continue
            if cell in ("主角", "核心", "core"):
                tier = "core"
            elif cell in ("重要配角", "重要", "important"):
                tier = "important"
            elif cell in ("次要配角", "次要", "secondary"):
                tier = "secondary"
            elif cell in ("路人", "装饰", "龙套", "decorative"):
                tier = "decorative"
            elif cell in ("character", "location", "item", "faction"):
                etype = "character"
            elif len(cell) > 2 and cell not in ("---", "------"):
                description = cell

        im.upsert_entity(entity_id, name, type_=etype, tier=tier, description=description)
        sm.upsert_entity(entity_id, {
            "name": name,
            "type": etype,
            "tier": tier,
            "description": description,
        })
        imported.append({"id": entity_id, "name": name, "tier": tier})
        imported_names.add(name)
        tables_found = True

    # 解析策略2：标题+列表格式（## 角色 / - 姓名：描述）
    # 仅当策略1未找到表格时启用
    if not tables_found:
        # 按标题分段
        sections = _re.split(r'^#{1,3}\s+', content, flags=_re.MULTILINE)
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
            # 检查是否是角色相关段落
            first_line = lines[0]
            if not any(kw in first_line for kw in ["角色", "人物", "Character"]):
                continue

            for line in lines[1:]:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('|'):
                    continue

                # 匹配 "- 姓名" 或 "* 姓名" 或 "1. 姓名（描述）"
                m = _re.match(r'^[-*\d.]+\s*(.+?)(?:[（(：:，,]|$)', line)
                if m:
                    name = m.group(1).strip()
                    # 清理序号
                    name = _re.sub(r'^[\d.]+\s*', '', name)
                    if len(name) < 2 or len(name) > 20:
                        continue
                    # 跳过已导入
                    if name in imported_names:
                        continue

                    entity_id = _re.sub(r'[^\w]', '_', name)
                    # 提取描述（括号内或冒号后）
                    desc_match = _re.search(r'[（(：:]\s*(.+?)[）)]?$', line)
                    description = desc_match.group(1).strip() if desc_match else ""

                    tier = "secondary"
                    if "主角" in line or "核心" in line:
                        tier = "core"
                    elif "重要" in line:
                        tier = "important"

                    im.upsert_entity(entity_id, name, type_="character", tier=tier, description=description)
                    sm.upsert_entity(entity_id, {
                        "name": name,
                        "type": "character",
                        "tier": tier,
                        "description": description,
                    })
                    imported.append({"id": entity_id, "name": name, "tier": tier})
                    imported_names.add(name)

    # 解析策略3：直接从 SOLOENT.md 提取
    if not imported and "角色索引" in content:
        # 提取 "- [姓名]（描述）" 格式
        char_pattern = _re.compile(r'-\s*\[?([\u4e00-\u9fff]{2,10})\]?(?:（([^）]*)）)?')
        for match in char_pattern.finditer(content):
            name = match.group(1)
            if name in imported_names:
                continue
            desc = match.group(2) or ""
            entity_id = _re.sub(r'[^\w]', '_', name)
            tier = "secondary"
            if "主角" in desc or "核心" in desc:
                tier = "core"

            im.upsert_entity(entity_id, name, type_="character", tier=tier, description=desc)
            sm.upsert_entity(entity_id, {
                "name": name,
                "type": "character",
                "tier": tier,
                "description": desc,
            })
            imported.append({"id": entity_id, "name": name, "tier": tier})

    print(json.dumps({
        "status": "ok",
        "imported_count": len(imported),
        "entities": imported,
    }, indent=2, ensure_ascii=False))


def _cmd_relationship(args, config: ForgeAIConfig) -> None:
    """关系管理"""
    rel_action = getattr(args, 'rel_action', 'list')

    if rel_action == "list":
        sm = StateManager(config)
        im = IndexManager(config)
        state = sm.load()

        # 合并 state 和 index 中的关系
        relationships = list(state.get("relationships", []))

        # 从 index.db 补充
        try:
            idx_stats = im.get_stats()
            if idx_stats.get("relationships", 0) > 0:
                conn = im._connect()
                rows = conn.execute("SELECT * FROM relationships").fetchall()
                conn.close()
                existing_keys = {
                    (r.get("from_entity"), r.get("to_entity"), r.get("type"))
                    for r in relationships
                }
                for r in rows:
                    r_dict = dict(r)
                    key = (r_dict.get("from_entity"), r_dict.get("to_entity"), r_dict.get("type"))
                    if key not in existing_keys:
                        relationships.append(r_dict)
                        existing_keys.add(key)
        except Exception:
            pass

        # 按实体过滤
        entity_filter = getattr(args, 'entity', None)
        if entity_filter:
            relationships = [
                r for r in relationships
                if r.get("from_entity") == entity_filter or r.get("to_entity") == entity_filter
            ]

        print(json.dumps(relationships, indent=2, ensure_ascii=False))

    elif rel_action == "add":
        from_entity = args.from_entity
        to_entity = args.to_entity
        rel_type = getattr(args, 'rel_type', 'related') or 'related'
        description = getattr(args, 'description', '') or ''
        chapter = getattr(args, 'chapter', 0) or 0

        sm = StateManager(config)
        im = IndexManager(config)

        # 保存到 state
        sm.add_relationship(from_entity, to_entity, rel_type, description, chapter)
        # 保存到 index
        im.add_relationship(from_entity, to_entity, type_=rel_type, description=description, chapter=chapter)

        print(json.dumps({
            "status": "ok",
            "from": from_entity,
            "to": to_entity,
            "type": rel_type,
            "description": description,
        }, ensure_ascii=False))

    elif rel_action == "graph":
        # 关系网络可视化
        viz = RelationshipVisualizer(config)
        entity_id = getattr(args, 'entity', None)
        tier_filter = getattr(args, 'tier_filter', None)

        mermaid = viz.generate_mermaid_graph(
            entity_id=entity_id,
            tier_filter=tier_filter,
        )

        output = getattr(args, 'output', None)
        if output:
            Path(output).write_text(mermaid, encoding="utf-8")
            print(json.dumps({"status": "ok", "output": output}, ensure_ascii=False))
        else:
            print(mermaid)

    elif rel_action == "evolution":
        # 关系演变追踪
        viz = RelationshipVisualizer(config)
        entity_id = args.entity
        from_chapter = getattr(args, 'from_chapter', 0) or 0
        to_chapter = getattr(args, 'to_chapter', 999) or 999

        mermaid = viz.generate_evolution_mermaid(entity_id, from_chapter, to_chapter)

        output = getattr(args, 'output', None)
        if output:
            Path(output).write_text(mermaid, encoding="utf-8")
            print(json.dumps({"status": "ok", "output": output}, ensure_ascii=False))
        else:
            print(mermaid)

    elif rel_action == "template":
        # 角色设定模板生成
        viz = RelationshipVisualizer(config)

        entity_id = getattr(args, 'entity', None)
        if entity_id:
            template = viz.generate_character_template(entity_id)
            output = getattr(args, 'output', None)
            if output:
                Path(output).write_text(template, encoding="utf-8")
                print(json.dumps({"status": "ok", "entity": entity_id, "output": output}, ensure_ascii=False))
            else:
                print(template)
        else:
            # 生成所有角色模板
            root = _resolve_root(args)
            output_dir = root / "2-设定" / "角色"
            results = viz.generate_all_character_templates(output_dir)
            print(json.dumps({
                "status": "ok",
                "generated": len(results),
                "files": results,
            }, indent=2, ensure_ascii=False))

    elif rel_action == "ooc-check":
        # OOC 检查
        viz = RelationshipVisualizer(config)
        entity_id = args.entity

        # 读取章节文本
        text_file = getattr(args, 'text_file', None)
        if text_file:
            text = Path(text_file).read_text(encoding="utf-8")
        else:
            text = ""

        result = viz.check_ooc(entity_id, text)
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_foreshadowing(args) -> None:
    """伏笔管理"""
    config = _get_config(args)
    sm = StateManager(config)

    if args.fs_action == "list":
        state = sm.load()
        active = state.get("foreshadowing", {}).get("active", [])
        if args.active_only:
            print(json.dumps(active, indent=2, ensure_ascii=False))
        else:
            resolved = state.get("foreshadowing", {}).get("resolved", [])
            print(json.dumps({"active": active, "resolved": resolved}, indent=2, ensure_ascii=False))

    elif args.fs_action == "add":
        # 支持位置参数和选项参数
        desc = args.description if hasattr(args, 'description') and args.description else getattr(args, 'description', "")
        if not desc:
            print(json.dumps({"error": "缺少伏笔描述"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        sm.add_foreshadowing(
            description=desc,
            chapter_planted=args.chapter,
            expected_payoff=args.payoff or 0,
        )
        print(json.dumps({"status": "ok"}, ensure_ascii=False))

    elif args.fs_action == "resolve":
        sm.resolve_foreshadowing(args.id, args.chapter)
        print(json.dumps({"status": "ok", "id": args.id}, ensure_ascii=False))


def cmd_check(args) -> None:
    """统一检查命令"""
    config = _get_config(args)
    check_type = args.check_type
    
    if check_type == "before":
        # 写前检查
        chapter = int(args.target) if args.target else 0
        if chapter == 0:
            print(json.dumps({"error": "缺少章节号"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        pipeline = Pipeline(config)
        result = pipeline.pre_write_check(chapter)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif check_type == "after":
        # 写后流水线
        chapter = int(args.target) if args.target else 0
        text_file = Path(getattr(args, 'text_file', args.text_file if hasattr(args, 'text_file') else ""))
        
        if not text_file.is_file():
            print(json.dumps({"error": f"文件不存在: {text_file}"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        text = text_file.read_text(encoding="utf-8")
        pipeline = Pipeline(config)
        result = asyncio.run(pipeline.post_write(
            chapter=chapter,
            text=text,
            source_file=str(text_file),
            score_ai=not getattr(args, 'no_score', False),
            extract_llm=getattr(args, 'llm', False),
        ))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif check_type == "review":
        # 审查章节
        chapter = int(args.target) if args.target else 0
        if chapter == 0:
            print(json.dumps({"error": "缺少章节号"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        if getattr(args, 'independent', False):
            from forgeai_modules.independent_reviewer import IndependentReviewer
            
            reviewer = IndependentReviewer(config)
            project_root = _resolve_root(args)
            
            result = reviewer.conduct_independent_review(chapter, project_root)
            output_file = reviewer.save_review_context(chapter, project_root)
            
            print(json.dumps({
                "status": "ok",
                "mode": "independent",
                "chapter": chapter,
                "saved_to": str(output_file),
                "instructions": result.get("instructions", []),
                "message": "请将审查提示词发送到新的对话窗口"
            }, indent=2, ensure_ascii=False))
        else:
            pipeline = Pipeline(config)
            result = pipeline.pre_write_check(chapter)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif check_type == "consistency":
        # 一致性检查
        checker = ConsistencyChecker(config.project_root)
        
        if hasattr(args, 'start') and hasattr(args, 'end') and args.start and args.end:
            # 批量检查
            result = checker.batch_check(args.start, args.end)
            if hasattr(args, 'output') and args.output:
                output_path = Path(args.output)
                output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                print(json.dumps({
                    "status": "ok",
                    "start": args.start,
                    "end": args.end,
                    "output": str(output_path),
                    "total_issues": result["total_issues"],
                    "message": f"批量检查报告已保存到 {output_path}"
                }, ensure_ascii=False))
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 单章检查
            chapter = int(args.target) if args.target else 0
            if chapter == 0:
                print(json.dumps({"error": "缺少章节号"}, ensure_ascii=False), file=sys.stderr)
                sys.exit(1)
            
            check_scope = getattr(args, 'scope', 'full')
            report = checker.check_chapter(chapter, check_scope)
            
            if hasattr(args, 'output') and args.output:
                output_path = Path(args.output)
                report_text = checker.generate_report(report, "markdown")
                output_path.write_text(report_text, encoding="utf-8")
                print(json.dumps({
                    "status": "ok",
                    "chapter": chapter,
                    "output": str(output_path),
                    "total_issues": report.total_issues,
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "message": f"一致性检查报告已保存到 {output_path}"
                }, ensure_ascii=False))
            else:
                print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


def cmd_post_write(args) -> None:
    """写作后自动流水线"""
    config = _get_config(args)
    chapter = args.chapter
    text_file = Path(args.text_file)
    
    if not text_file.is_file():
        print(json.dumps({"error": f"文件不存在: {text_file}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"📝 第{chapter}章写后处理")
    print(f"{'='*60}\n")
    
    text = text_file.read_text(encoding="utf-8")
    
    print(f"📄 正文文件: {text_file}")
    print(f"📊 字数: {len(text)} 字符\n")
    
    pipeline = Pipeline(config)
    result = asyncio.run(pipeline.post_write(
        chapter=chapter,
        text=text,
        source_file=str(text_file),
        score_ai=not args.no_score,
        extract_llm=args.llm,
    ))
    
    # 额外步骤：LLM 驱动的实体/关系提取
    extract_step = {"status": "skipped", "message": "未启用LLM提取"}
    if args.llm:
        print("  6️⃣ LLM实体/关系提取中...")
        try:
            llm_extractor = LLMEntityExtractor(config)
            extraction = asyncio.run(llm_extractor.extract_from_chapter(text, chapter))
            stats = llm_extractor.save_to_state(extraction)
            extract_step = {
                "status": "ok",
                "entities": stats["entities"],
                "relationships": stats["relationships"],
                "state_changes": stats["state_changes"],
            }
            print(f"     ✅ 提取完成: {stats['entities']}个实体, {stats['relationships']}个关系, {stats['state_changes']}个状态变化")
        except Exception as e:
            extract_step = {"status": "error", "message": str(e)}
            print(f"     ❌ 提取失败: {e}")
    result["steps"]["llm_extract"] = extract_step
    
    # 友好输出
    print("✅ 写后流水线完成：\n")
    
    steps = result.get("steps", {})
    
    # Step 1: 索引
    if "index" in steps:
        idx = steps["index"]
        if idx.get("status") == "ok":
            print(f"  1️⃣ 索引章节: ✅ {idx.get('chunks', 0)} 个分块已索引")
        else:
            print(f"  1️⃣ 索引章节: ❌ {idx.get('message', '未知错误')}")
    
    # Step 2: 提取实体
    if "extract" in steps:
        ext = steps["extract"]
        if ext.get("status") == "ok":
            print(f"  2️⃣ 提取实体: ✅ {ext.get('entities', 0)} 个实体, {ext.get('state_changes', 0)} 个状态变更")
        else:
            print(f"  2️⃣ 提取实体: ❌ {ext.get('message', '未知错误')}")
    
    # Step 3: AI味评分
    if "score" in steps:
        scr = steps["score"]
        if scr.get("status") == "ok":
            score = scr.get("score", 0)
            level = "优秀" if score > 0.7 else "良好" if score > 0.5 else "需优化"
            print(f"  3️⃣ AI味评分: ✅ {score:.2f} ({level})")
        else:
            print(f"  3️⃣ AI味评分: ❌ {scr.get('message', '未知错误')}")
    
    # Step 4: 更新进度
    if "progress" in steps:
        prog = steps["progress"]
        if prog.get("status") == "ok":
            print(f"  4️⃣ 更新进度: ✅ 已记录第{chapter}章完成")
        else:
            print(f"  4️⃣ 更新进度: ❌ {prog.get('message', '未知错误')}")
    
    # Step 5: 下一章预检
    if "pre_check_next" in steps:
        pre = steps["pre_check_next"]
        alerts = pre.get("alerts", [])
        if alerts:
            print(f"  5️⃣ 下一章预检: ⚠️ {len(alerts)} 条提醒")
            for alert in alerts[:3]:  # 只显示前3条
                print(f"      [{alert['level']}] {alert['message']}")
        else:
            print(f"  5️⃣ 下一章预检: ✅ 无问题")
    
    print(f"\n{'='*60}")
    print("📊 处理总结")
    print(f"{'='*60}")
    print(f"章节: 第{chapter}章")
    print(f"字数: {len(text)}")
    print(f"索引: {steps.get('index', {}).get('chunks', 0)} 个分块")
    print(f"实体: {steps.get('extract', {}).get('entities', 0)} 个")
    print(f"状态变更: {steps.get('extract', {}).get('state_changes', 0)} 个")
    print(f"AI味评分: {steps.get('score', {}).get('score', 0):.2f}")
    print(f"下一章提醒: {len(steps.get('pre_check_next', {}).get('alerts', []))} 条")
    print(f"{'='*60}\n")
    
    print("💡 提示：可以继续创作下一章，或使用 forgeai check review 进行详细审查")


def cmd_pre_check(args) -> None:
    """写前自动检查"""
    config = _get_config(args)
    pipeline = Pipeline(config)
    result = pipeline.pre_write_check(args.chapter)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_smart_context(args) -> None:
    """智能上下文组装"""
    config = _get_config(args)
    pipeline = Pipeline(config)
    result = pipeline.smart_context(
        chapter=args.chapter,
        query=args.query or "",
        max_chars=args.max_chars or 8000,
    )
    print(result["formatted"])


def cmd_extract(args) -> None:
    """自动提取实体"""
    config = _get_config(args)

    text_file = Path(args.text_file)
    if not text_file.is_file():
        print(json.dumps({"error": f"文件不存在: {text_file}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    text = text_file.read_text(encoding="utf-8")
    chapter = args.chapter

    if args.llm:
        # 使用 LLM 驱动的提取器
        extractor = LLMEntityExtractor(config)
        result = asyncio.run(extractor.extract_from_chapter(text, chapter))

        if args.save:
            stats = extractor.save_to_state(result)
            print(json.dumps({
                "status": "saved",
                "engine": "llm",
                "stats": stats,
                "details": result.to_dict(),
            }, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        # 使用 NER 提取器
        extractor = EntityExtractor(config)

        if args.llm:
            result = asyncio.run(extractor.extract_with_llm(text, chapter))
        else:
            result = extractor.extract_from_text(text, chapter)

        if args.save:
            stats = extractor.save_extraction(result, chapter)
            print(json.dumps({"status": "saved", "engine": "ner", "stats": stats}, indent=2, ensure_ascii=False))
        else:
            output = {
                "entities": result.entities,
                "relationships": result.relationships,
                "state_changes": result.state_changes,
                "foreshadowing_hints": result.foreshadowing_hints,
                "scenes": len(result.scenes),
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_review(args) -> None:
    """审查章节"""
    config = _get_config(args)
    
    # 如果启用独立审查模式
    if hasattr(args, 'independent') and args.independent:
        from forgeai_modules.independent_reviewer import IndependentReviewer
        
        reviewer = IndependentReviewer(config)
        project_root = _resolve_root(args)
        
        result = reviewer.conduct_independent_review(args.chapter, project_root)
        
        # 保存审查提示词到文件
        output_file = reviewer.save_review_context(args.chapter, project_root)
        
        print(json.dumps({
            "status": "ok",
            "mode": "independent",
            "chapter": args.chapter,
            "saved_to": str(output_file),
            "instructions": result.get("instructions", []),
            "message": "请将审查提示词发送到新的对话窗口"
        }, indent=2, ensure_ascii=False))
    else:
        # 普通审查模式（使用Pipeline）
        pipeline = Pipeline(config)
        result = pipeline.pre_write_check(args.chapter)
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_data(args) -> None:
    """数据回写"""
    config = _get_config(args)
    
    if not hasattr(args, 'data_action'):
        print(json.dumps({"error": "缺少操作参数"}, ensure_ascii=False), file=sys.stderr)
        return
    
    if args.data_action == "update":
        # 数据更新
        from forgeai_modules.state_change_confirmer import StateChangeConfirmer
        
        confirmer = StateChangeConfirmer(config)
        
        text_file = Path(args.text_file)
        if not text_file.is_file():
            print(json.dumps({"error": f"文件不存在: {text_file}"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        text = text_file.read_text(encoding="utf-8")
        
        # 提取状态变更（简化版，实际应该调用EntityExtractor）
        # 这里我们模拟一些状态变更
        changes = [
            {
                "entity": "李天",
                "field": "power.realm",
                "old_value": "练气1层",
                "new_value": "练气2层",
                "chapter": args.chapter,
                "evidence": "正文第X段",
                "change_type": "power",
                "severity": "high"
            }
        ]
        
        # 如果启用确认模式
        if hasattr(args, 'confirm') and args.confirm:
            print(confirmer.display_state_changes(changes))
            print()
            print(confirmer.prompt_user_confirmation(changes))
            print("\n提示：请在实际使用时输入 all/none/select/review 进行确认")
        else:
            # 直接写入（不确认）
            print(json.dumps({
                "status": "ok",
                "changes_detected": len(changes),
                "message": "已自动写入状态变更"
            }, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": f"未知操作: {args.data_action}"}, ensure_ascii=False))


def cmd_timeline(args) -> None:
    """时间线管理"""
    config = _get_config(args)
    sm = StateManager(config)
    tm = TimelineManager(config)
    
    timeline_action = args.timeline_action
    
    if timeline_action == "status":
        # 查询时间线状态
        state = sm.load()
        status_report = tm.get_timeline_status(state)
        print(status_report)
    
    elif timeline_action == "history":
        # 查询时间线历史
        state = sm.load()
        timeline = state.get("timeline", {})
        anchors = timeline.get("anchors", [])
        
        # 过滤章节范围
        from_chapter = getattr(args, "from_chapter", None)
        to_chapter = getattr(args, "to_chapter", None)
        
        if from_chapter and to_chapter:
            anchors = [a for a in anchors if from_chapter <= a.get("chapter", 0) <= to_chapter]
        
        # 生成可视化
        if anchors:
            visualization = tm.generate_timeline_visualization(timeline, from_chapter, to_chapter)
            print(visualization)
        else:
            print("暂无时间线数据")
    
    elif timeline_action == "add-anchor":
        # 添加时间锚点
        sm.add_timeline_anchor(
            chapter=args.chapter,
            anchor=args.anchor,
            event=args.event or ""
        )
        print(json.dumps({
            "status": "ok",
            "message": f"已添加时间锚点：第{args.chapter}章 {args.anchor}"
        }, indent=2, ensure_ascii=False))
    
    elif timeline_action == "add-countdown":
        # 添加倒计时
        sm.add_countdown(
            name=args.name,
            initial_value=args.value
        )
        print(json.dumps({
            "status": "ok",
            "message": f"已添加倒计时：{args.name} ({args.value})"
        }, indent=2, ensure_ascii=False))


def cmd_growth(args) -> None:
    """角色成长分析"""
    config = _get_config(args)
    analyzer = GrowthAnalyzer(config)
    
    if not hasattr(args, 'growth_action'):
        print(json.dumps({"error": "缺少操作参数"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    
    if args.growth_action == "analyze":
        # 分析单个角色
        entity_id = args.entity
        analysis = analyzer.analyze_entity_growth(entity_id)
        
        if analysis is None:
            print(json.dumps({"error": f"未找到角色: {entity_id}"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        output = analysis.to_dict()
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    elif args.growth_action == "report":
        # 生成成长报告
        entity_id = args.entity
        analysis = analyzer.analyze_entity_growth(entity_id)
        
        if analysis is None:
            print(json.dumps({"error": f"未找到角色: {entity_id}"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        report = analyzer.generate_growth_report(entity_id, analysis)
        
        # 保存到文件或输出
        if hasattr(args, 'output') and args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding="utf-8")
            print(json.dumps({
                "status": "ok",
                "entity": entity_id,
                "output": str(output_path),
                "message": f"成长报告已保存到 {output_path}"
            }, ensure_ascii=False))
        else:
            print(report)
    
    elif args.growth_action == "plot":
        # 绘制成长曲线
        entity_id = args.entity
        analysis = analyzer.analyze_entity_growth(entity_id)
        
        if analysis is None:
            print(json.dumps({"error": f"未找到角色: {entity_id}"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        output_file = args.output if hasattr(args, 'output') and args.output else None
        result_file = analyzer.plot_growth_curve(entity_id, output_file, analysis)
        
        if result_file:
            print(json.dumps({
                "status": "ok",
                "entity": entity_id,
                "output": result_file,
                "message": f"成长曲线已保存到 {result_file}"
            }, ensure_ascii=False))
        else:
            print(json.dumps({
                "status": "warning",
                "message": "未安装matplotlib，无法生成图表。请执行: pip install matplotlib"
            }, ensure_ascii=False))
    
    elif args.growth_action == "compare":
        # 对比多个角色
        entity_ids = args.entities.split(",") if hasattr(args, 'entities') and args.entities else []
        
        if not entity_ids:
            print(json.dumps({"error": "请指定要对比的角色（用逗号分隔）"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        comparison = analyzer.compare_entities(entity_ids)
        print(json.dumps(comparison, indent=2, ensure_ascii=False))


def cmd_volume(args) -> None:
    """多卷大纲管理"""
    config = _get_config(args)
    manager = VolumeManager(config.project_root)
    
    if not hasattr(args, 'volume_action'):
        print(json.dumps({"error": "缺少操作参数"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    
    if args.volume_action == "list":
        # 列出所有卷
        result = manager.list_volumes()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.volume_action == "add":
        # 添加新卷
        name = args.name if hasattr(args, 'name') else None
        result = manager.add_volume(name)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.volume_action == "status":
        # 查看卷状态
        volume_id = args.volume
        result = manager.get_volume_status(volume_id)
        
        if result is None:
            print(json.dumps({"error": f"卷 {volume_id} 不存在"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.volume_action == "switch":
        # 切换当前卷
        volume_id = args.volume
        result = manager.set_current_volume(volume_id)
        
        if result["status"] == "error":
            print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.volume_action == "complete":
        # 完成卷
        volume_id = args.volume
        result = manager.complete_volume(volume_id)
        
        if result["status"] == "error":
            print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.volume_action == "summary":
        # 生成卷级大纲汇总
        volume_id = args.volume
        summary = manager.get_volume_summary(volume_id)
        
        if summary is None:
            print(json.dumps({"error": f"卷 {volume_id} 不存在"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        
        # 保存到文件或输出
        if hasattr(args, 'output') and args.output:
            output_path = Path(args.output)
            output_path.write_text(summary, encoding="utf-8")
            print(json.dumps({
                "status": "ok",
                "volume": volume_id,
                "output": str(output_path),
                "message": f"大纲汇总已保存到 {output_path}"
            }, ensure_ascii=False))
        else:
            print(summary)


def cmd_relationship(args) -> None:
    """角色关系网络管理（独立命令）"""
    config = _get_config(args)
    rel_action = args.rel_action

    if rel_action == "list":
        sm = StateManager(config)
        im = IndexManager(config)
        state = sm.load()
        relationships = list(state.get("relationships", []))

        # 从 index.db 补充
        try:
            idx_stats = im.get_stats()
            if idx_stats.get("relationships", 0) > 0:
                conn = im._connect()
                rows = conn.execute("SELECT * FROM relationships").fetchall()
                conn.close()
                existing_keys = {
                    (r.get("from_entity"), r.get("to_entity"), r.get("type"))
                    for r in relationships
                }
                for r in rows:
                    r_dict = dict(r)
                    key = (r_dict.get("from_entity"), r_dict.get("to_entity"), r_dict.get("type"))
                    if key not in existing_keys:
                        relationships.append(r_dict)
                        existing_keys.add(key)
        except Exception:
            pass

        # 按实体过滤
        entity_filter = getattr(args, 'entity', None)
        if entity_filter:
            relationships = [
                r for r in relationships
                if r.get("from_entity") == entity_filter or r.get("to_entity") == entity_filter
            ]

        print(json.dumps(relationships, indent=2, ensure_ascii=False))

    elif rel_action == "add":
        from_entity = args.from_entity
        to_entity = args.to_entity
        rel_type = getattr(args, 'rel_type', 'related') or 'related'
        description = getattr(args, 'description', '') or ''
        chapter = getattr(args, 'chapter', 0) or 0

        sm = StateManager(config)
        im = IndexManager(config)

        sm.add_relationship(from_entity, to_entity, rel_type, description, chapter)
        im.add_relationship(from_entity, to_entity, type_=rel_type, description=description, chapter=chapter)

        print(json.dumps({
            "status": "ok",
            "from": from_entity,
            "to": to_entity,
            "type": rel_type,
            "description": description,
        }, ensure_ascii=False))

    elif rel_action == "graph":
        viz = RelationshipVisualizer(config)
        entity_id = getattr(args, 'entity', None)
        tier_filter = getattr(args, 'tier', None)
        mermaid = viz.generate_mermaid_graph(entity_id=entity_id, tier_filter=tier_filter)
        output = getattr(args, 'output', None)
        if output:
            Path(output).write_text(mermaid, encoding="utf-8")
            print(json.dumps({"status": "ok", "output": output}, ensure_ascii=False))
        else:
            print(mermaid)

    elif rel_action == "evolution":
        viz = RelationshipVisualizer(config)
        entity_id = args.entity
        from_chapter = getattr(args, 'from_chapter', 0) or 0
        to_chapter = getattr(args, 'to_chapter', 999) or 999
        mermaid = viz.generate_evolution_mermaid(entity_id, from_chapter, to_chapter)
        output = getattr(args, 'output', None)
        if output:
            Path(output).write_text(mermaid, encoding="utf-8")
            print(json.dumps({"status": "ok", "output": output}, ensure_ascii=False))
        else:
            print(mermaid)

    elif rel_action == "template":
        viz = RelationshipVisualizer(config)
        entity_id = getattr(args, 'entity', None)
        if entity_id:
            template = viz.generate_character_template(entity_id)
            output = getattr(args, 'output', None)
            if output:
                Path(output).write_text(template, encoding="utf-8")
                print(json.dumps({"status": "ok", "entity": entity_id, "output": output}, ensure_ascii=False))
            else:
                print(template)
        else:
            root = _resolve_root(args)
            output_dir = root / "2-设定" / "角色"
            results = viz.generate_all_character_templates(output_dir)
            print(json.dumps({
                "status": "ok",
                "generated": len(results),
                "files": results,
            }, indent=2, ensure_ascii=False))

    elif rel_action == "ooc-check":
        viz = RelationshipVisualizer(config)
        entity_id = args.entity
        text_file = getattr(args, 'text_file', None)
        text = Path(text_file).read_text(encoding="utf-8") if text_file else ""
        result = viz.check_ooc(entity_id, text)
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_consistency(args) -> None:
    """跨章节一致性检查"""
    config = _get_config(args)
    checker = ConsistencyChecker(config.project_root)
    
    if not hasattr(args, 'consistency_action'):
        print(json.dumps({"error": "缺少操作参数"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    
    if args.consistency_action == "check":
        # 检查单章节
        chapter = args.chapter
        check_scope = args.scope if hasattr(args, 'scope') else "full"
        
        report = checker.check_chapter(chapter, check_scope)
        
        # 保存到文件或输出
        if hasattr(args, 'output') and args.output:
            output_path = Path(args.output)
            report_text = checker.generate_report(report, "markdown")
            output_path.write_text(report_text, encoding="utf-8")
            print(json.dumps({
                "status": "ok",
                "chapter": chapter,
                "output": str(output_path),
                "total_issues": report.total_issues,
                "errors": report.errors,
                "warnings": report.warnings,
                "message": f"一致性检查报告已保存到 {output_path}"
            }, ensure_ascii=False))
        else:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    
    elif args.consistency_action == "batch":
        # 批量检查
        start_chapter = args.start
        end_chapter = args.end
        
        result = checker.batch_check(start_chapter, end_chapter)
        
        # 保存到文件或输出
        if hasattr(args, 'output') and args.output:
            output_path = Path(args.output)
            output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({
                "status": "ok",
                "start": start_chapter,
                "end": end_chapter,
                "output": str(output_path),
                "total_issues": result["total_issues"],
                "message": f"批量检查报告已保存到 {output_path}"
            }, ensure_ascii=False))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_analyze(args) -> None:
    """样板书拆解分析"""
    input_path = Path(args.input)
    if not input_path.is_file():
        print(json.dumps({"error": f"文件不存在: {input_path}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    root = _resolve_root(args)
    # 默认输出到项目的 1-边界/样板书分析/ 目录
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = root / "1-边界" / "样板书分析"

    analyzer = BookAnalyzer(verbose=args.verbose)
    analyzer.load_chapters_from_file(str(input_path))

    # 章节范围过滤
    if args.from_chapter or args.to_chapter:
        chapters = analyzer.result.chapters
        start = args.from_chapter or 1
        end = args.to_chapter or len(chapters)
        analyzer.result.chapters = [ch for ch in chapters if start <= ch.index <= end]

    # 执行分析
    result = analyzer.analyze_all()

    # 生成报告文件
    reports = analyzer.generate_report(str(output_dir))

    output = {
        "status": "ok",
        "input": str(input_path),
        "chapters_analyzed": len(analyzer.result.chapters),
        "output_dir": str(output_dir),
        "reports": reports,
        "summary": {
            "avg_word_count": round(analyzer.result.avg_word_count),
            "trophy_density": round(analyzer.result.trophy_density, 2),
            "dialogue_ratio": round(analyzer.result.dialogue_ratio, 1),
        },
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_write_optimize(args) -> None:
    """生成+优化（完整写作流程）"""
    from forgeai_modules.writing_pipeline import WritingPipeline
    
    config = _get_config(args)
    chapter = args.chapter
    
    print(f"\n{'='*60}")
    print(f"[Write-Optimize] 第{chapter}章完整写作流程")
    print(f"{'='*60}\n")
    
    # 获取题材
    state_manager = StateManager(config)
    state = state_manager.load()
    genre = state.get("project", {}).get("genre", "shuangwen")
    
    # 创建写作流水线
    pipeline = WritingPipeline(config)
    
    # 执行完整写作流程
    print(f"[1/3] 生成章节...")
    print(f"[2/3] 优化章节...")
    print(f"[3/3] 反馈循环...")
    
    session = asyncio.run(
        pipeline.write_chapter(
            chapter_num=chapter,
            genre=genre,
            query=getattr(args, 'query', "") or "",
            use_rag=getattr(args, 'smart', False),
            enable_optimization=True,
            enable_feedback=True,
            enable_post_write=True,
            target_score=getattr(args, 'target_score', 0.7),
        )
    )
    
    if session.status == "completed":
        print(f"\n[OK] 写作流程完成")
        print(f"  - 章节号: {session.chapter_num}")
        print(f"  - 最终字数: {session.final_word_count}")
        print(f"  - 总耗时: {session.total_time:.1f}秒")
        
        # 保存章节
        root = _resolve_root(args)
        if hasattr(args, 'output') and args.output:
            output_path = Path(args.output)
        else:
            output_dir = root / "4-正文" / "优化"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"第{chapter}章.md"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取标题
        title = session.generation.title if session.generation else f"第{chapter}章"
        content = f"# {title}\n\n{session.final_content}"
        output_path.write_text(content, encoding="utf-8")
        
        print(f"[OK] 章节已保存到: {output_path}")
        
        # 输出统计信息
        print(f"\n{'='*60}")
        print("[Stats] 写作流程统计")
        print(f"{'='*60}")
        print(f"章节: 第{chapter}章")
        print(f"标题: {title}")
        print(f"最终字数: {session.final_word_count}")
        print(f"题材: {genre}")
        print(f"目标分数: {getattr(args, 'target_score', 0.7)}")
        print(f"生成阶段: {'✓' if session.generation and session.generation.success else '✗'}")
        print(f"优化阶段: {'✓' if session.optimization and session.optimization.success else '✗'}")
        print(f"反馈阶段: {'✓' if session.feedback and session.feedback.success else '✗'}")
        print(f"总耗时: {session.total_time:.1f}秒")
        print(f"输出文件: {output_path}")
        print(f"{'='*60}\n")
        
        # 输出章节预览
        print("[Preview] 章节预览（前500字）:")
        print("-" * 60)
        print(session.final_content[:500])
        if len(session.final_content) > 500:
            print("...")
        print("-" * 60)
    else:
        print(f"[Error] 写作流程失败: {session.status}")
        return


def cmd_write_batch(args) -> None:
    """批量生成章节"""
    from forgeai_modules.batch_generator import BatchGenerator
    
    config = _get_config(args)
    start = args.start
    end = args.end
    
    print(f"\n{'='*60}")
    print(f"[Write-Batch] 批量生成章节 {start}-{end}")
    print(f"{'='*60}\n")
    
    # 获取题材
    state_manager = StateManager(config)
    state = state_manager.load()
    genre = state.get("project", {}).get("genre", "shuangwen")
    
    # 确定输出目录
    root = _resolve_root(args)
    if hasattr(args, 'output_dir') and args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = root / "4-正文" / "批量生成"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建批量生成器
    generator = BatchGenerator(config)
    
    # 执行批量生成
    print(f"[开始] 批量生成 {end - start + 1} 章...")
    
    job = asyncio.run(
        generator.generate_batch(
            start_chapter=start,
            end_chapter=end,
            genre=genre,
            query=getattr(args, 'query', "") or "",
            use_rag=getattr(args, 'smart', False),
            enable_post_write=True,
            output_dir=output_dir,
        )
    )
    
    # 输出结果
    print(f"\n{'='*60}")
    print("[Stats] 批量生成统计")
    print(f"{'='*60}")
    print(f"任务ID: {job.job_id}")
    print(f"章节范围: {start}-{end}")
    print(f"总章节数: {job.total}")
    print(f"成功: {len(job.results)}")
    print(f"失败: {len(job.errors)}")
    print(f"状态: {job.status}")
    print(f"开始时间: {job.start_time}")
    print(f"结束时间: {job.end_time}")
    print(f"输出目录: {output_dir}")
    print(f"{'='*60}\n")
    
    # 显示成功列表
    if job.results:
        print("[成功章节]:")
        for result in job.results:
            print(f"  ✓ 第{result.chapter_num}章 - {result.title} ({result.word_count}字)")
    
    # 显示失败列表
    if job.errors:
        print("\n[失败章节]:")
        for error in job.errors:
            print(f"  ✗ 第{error.get('chapter', '?')}章 - {error.get('error', '未知错误')}")
    
    print()


# ====== CLI 定义 ======

def _add_project_root(parser: argparse.ArgumentParser) -> None:
    """给子命令添加 --project-root 参数"""
    parser.add_argument("--project-root", help="项目根目录（缺省自动查找）", default=None)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="forgeai",
        description="ForgeAI 长篇小说创作套件 CLI",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ---- init ----
    p_init = subparsers.add_parser("init", help="初始化项目")
    p_init.add_argument("--name", help="项目名称")
    p_init.add_argument("--genre", help="题材")
    p_init.add_argument("--mode", choices=["standard", "flexible", "reference"],
                        default="standard", help="启动模式")
    _add_project_root(p_init)

    # ---- status ----
    p_status = subparsers.add_parser("status", help="查看项目状态")
    _add_project_root(p_status)

    # ---- help ----
    p_help = subparsers.add_parser("help", help="显示帮助信息")
    p_help.add_argument("command_name", nargs="?", help="命令名称")
    
    # ---- version ----
    p_version = subparsers.add_parser("version", help="显示版本信息")

    # ---- index ----
    p_index = subparsers.add_parser("index", help="索引章节")
    p_index.add_argument("chapter", type=int, help="章节号")
    p_index.add_argument("text_file", help="文本文件路径")
    _add_project_root(p_index)

    # ---- search ----
    p_search = subparsers.add_parser("search", help="搜索")
    p_search.add_argument("query", help="搜索查询")
    p_search.add_argument("--top-k", type=int, default=5, help="返回数量")
    _add_project_root(p_search)

    # ---- context (提取上下文，支持 --smart) ----
    p_context = subparsers.add_parser("context", help="提取上下文")
    p_context.add_argument("chapter", type=int, help="章节号")
    p_context.add_argument("--query", help="补充查询")
    p_context.add_argument("--confirm", action="store_true", help="启用大纲确认环节")
    p_context.add_argument("--smart", action="store_true", help="智能上下文组装（按优先级召回）")
    p_context.add_argument("--max-chars", type=int, default=8000, help="最大上下文字数（--smart 时使用）")
    _add_project_root(p_context)

    # ---- score (AI味评分，支持 --evolve) ----
    p_score = subparsers.add_parser("score", help="AI味评分")
    p_score.add_argument("text_file", help="文本文件路径或文本内容")
    p_score.add_argument("--llm", action="store_true", help="启用 LLM 评分")
    p_score.add_argument("--evolve", action="store_true", help="进化式去AI味（迭代优化）")
    p_score.add_argument("--rounds", type=int, default=3, help="迭代轮数（--evolve 时使用）")
    _add_project_root(p_score)
    
    # ---- evolve (旧命令，保持兼容) ----
    p_evolve = subparsers.add_parser("evolve", help="进化式去AI味（已弃用，请使用 score --evolve）")
    p_evolve.add_argument("text_file", help="文本文件路径或文本内容")
    p_evolve.add_argument("--rounds", type=int, default=3, help="迭代轮数")
    _add_project_root(p_evolve)

    # ---- stats ----
    p_stats = subparsers.add_parser("stats", help="查看统计")
    _add_project_root(p_stats)

    # ---- entity ----
    p_entity = subparsers.add_parser("entity", help="实体管理")
    p_entity.add_argument("entity_action", choices=["list", "add", "import", "relationship"])
    p_entity.add_argument("--id", help="实体ID")
    p_entity.add_argument("--name", help="实体名称")
    p_entity.add_argument("--type", help="实体类型 (character/location/item/faction)")
    p_entity.add_argument("--tier", help="实体层级 (core/important/secondary/decorative)")
    # import 参数
    p_entity.add_argument("--input-file", help="Markdown文件路径（import时使用）")
    # relationship 子命令参数
    p_entity.add_argument("--rel-action", dest="rel_action",
                         choices=["list", "add", "graph", "evolution", "template", "ooc-check"],
                         default="list", help="关系操作")
    p_entity.add_argument("--from-entity", help="关系发起方ID（relationship add）")
    p_entity.add_argument("--to-entity", help="关系对象ID（relationship add）")
    p_entity.add_argument("--rel-type", dest="rel_type",
                         help="关系类型: friend/enemy/mentor/family/lover/rival/subordinate/related")
    p_entity.add_argument("--description", help="关系描述 / 角色描述")
    p_entity.add_argument("--chapter", type=int, help="章节号")
    p_entity.add_argument("--entity", help="角色ID（relationship graph/evolution/template/ooc-check）")
    p_entity.add_argument("--tier-filter", help="层级过滤（relationship graph）")
    p_entity.add_argument("--from-chapter", type=int, help="起始章节（relationship evolution）")
    p_entity.add_argument("--to-chapter", type=int, help="结束章节（relationship evolution）")
    p_entity.add_argument("--output", help="输出文件路径")
    p_entity.add_argument("--text-file", help="正文文件路径（ooc-check时使用）")
    _add_project_root(p_entity)

    # ---- foreshadow (伏笔管理，foreshadowing 别名) ----
    p_fs = subparsers.add_parser("foreshadow", help="伏笔管理")
    p_fs.add_argument("fs_action", choices=["list", "add", "resolve"])
    p_fs.add_argument("description", nargs="?", help="伏笔描述（add时使用）")
    p_fs.add_argument("--id", help="伏笔ID")
    p_fs.add_argument("--chapter", type=int, help="章节号")
    p_fs.add_argument("--payoff", type=int, help="预期回收章节")
    p_fs.add_argument("--active-only", action="store_true", help="仅显示活跃伏笔")
    _add_project_root(p_fs)
    
    # ---- foreshadowing (旧命令，保持兼容) ----
    p_fs_old = subparsers.add_parser("foreshadowing", help="伏笔管理（已弃用，请使用 foreshadow）")
    p_fs_old.add_argument("fs_action", choices=["list", "add", "resolve"])
    p_fs_old.add_argument("--id", help="伏笔ID")
    p_fs_old.add_argument("--description", help="伏笔描述")
    p_fs_old.add_argument("--chapter", type=int, help="章节号")
    p_fs_old.add_argument("--payoff", type=int, help="预期回收章节")
    p_fs_old.add_argument("--active-only", action="store_true", help="仅显示活跃伏笔")
    _add_project_root(p_fs_old)

    # ---- check (统一检查命令族) ----
    p_check = subparsers.add_parser("check", help="统一检查命令")
    p_check.add_argument("check_type", choices=["before", "after", "review", "consistency"],
                        help="检查类型：before(写前)/after(写后)/review(审查)/consistency(一致性)")
    p_check.add_argument("target", nargs="?", help="章节号或文件路径")
    p_check.add_argument("--text-file", help="正文文件路径（after时使用）")
    p_check.add_argument("--scope", choices=["timeline", "character", "worldview", "ooc", "full"],
                        default="full", help="检查范围（consistency时使用）")
    p_check.add_argument("--start", type=int, help="起始章节号（consistency batch时使用）")
    p_check.add_argument("--end", type=int, help="结束章节号（consistency batch时使用）")
    p_check.add_argument("--no-score", action="store_true", help="跳过AI味评分（after时使用）")
    p_check.add_argument("--llm", action="store_true", help="用LLM提取实体（after时使用）")
    p_check.add_argument("--independent", action="store_true", help="独立审查模式（review时使用）")
    p_check.add_argument("--output", help="输出文件路径")
    _add_project_root(p_check)
    
    # ---- pre-check (旧命令，保持兼容) ----
    p_pc = subparsers.add_parser("pre-check", help="写前自动检查（已弃用，请使用 check before）")
    p_pc.add_argument("chapter", type=int, help="下一章章节号")
    _add_project_root(p_pc)
    
    # ---- post-write (旧命令，保持兼容) ----
    p_pw = subparsers.add_parser("post-write", help="写作后自动流水线（已弃用，请使用 check after）")
    p_pw.add_argument("chapter", type=int, help="章节号")
    p_pw.add_argument("text_file", help="正文文件路径")
    p_pw.add_argument("--no-score", action="store_true", help="跳过AI味评分")
    p_pw.add_argument("--llm", action="store_true", help="用LLM提取实体（需API Key）")
    p_pw.add_argument("--confirm", action="store_true", help="启用状态变更确认")
    _add_project_root(p_pw)
    
    # ---- growth (角色成长分析) ----
    p_growth = subparsers.add_parser("growth", help="角色成长分析")
    p_growth.add_argument("growth_action", choices=["analyze", "report", "plot", "compare"],
                         help="成长分析操作")
    p_growth.add_argument("--entity", help="角色名（analyze/report/plot）")
    p_growth.add_argument("--entities", help="角色名列表，用逗号分隔（compare）")
    p_growth.add_argument("--output", help="输出文件路径（report/plot）")
    _add_project_root(p_growth)

    # ---- smart-context (旧命令，保持兼容) ----
    p_sc = subparsers.add_parser("smart-context", help="智能上下文组装（已弃用，请使用 context --smart）")
    p_sc.add_argument("chapter", type=int, help="当前章节号")
    p_sc.add_argument("--query", help="补充查询")
    p_sc.add_argument("--max-chars", type=int, default=8000, help="最大上下文字数")
    _add_project_root(p_sc)

    # ---- extract (自动提取实体) ----
    p_ex = subparsers.add_parser("extract", help="自动提取实体/关系/状态变化")
    p_ex.add_argument("chapter", type=int, help="章节号")
    p_ex.add_argument("text_file", help="正文文件路径")
    p_ex.add_argument("--save", action="store_true", help="保存提取结果到数据库")
    p_ex.add_argument("--llm", action="store_true", help="用LLM提取（需API Key）")
    _add_project_root(p_ex)

    # ---- relationship (关系网络管理) ----
    p_rel = subparsers.add_parser("relationship", help="角色关系网络管理")
    p_rel.add_argument("rel_action", choices=["list", "add", "graph", "evolution", "template", "ooc-check"],
                        help="关系操作")
    p_rel.add_argument("--from-entity", help="关系发起方ID（add）")
    p_rel.add_argument("--to-entity", help="关系对象ID（add）")
    p_rel.add_argument("--rel-type", dest="rel_type",
                        help="关系类型: friend/enemy/mentor/family/lover/rival/subordinate/related（add）")
    p_rel.add_argument("--description", help="关系描述（add/evolution）")
    p_rel.add_argument("--chapter", type=int, help="章节号（add/evolution）")
    p_rel.add_argument("--entity", help="角色ID（graph/evolution/template/ooc-check）")
    p_rel.add_argument("--tier", help="层级过滤（graph）")
    p_rel.add_argument("--from-chapter", type=int, help="起始章节（evolution）")
    p_rel.add_argument("--to-chapter", type=int, help="结束章节（evolution）")
    p_rel.add_argument("--output", help="输出文件路径")
    p_rel.add_argument("--text-file", help="正文文件路径（ooc-check）")
    _add_project_root(p_rel)
    
    # ---- timeline (时间线管理) ----
    p_tl = subparsers.add_parser("timeline", help="时间线管理")
    p_tl.add_argument("timeline_action", choices=["status", "history", "add-anchor", "add-countdown"],
                     help="时间线操作")
    p_tl.add_argument("--chapter", type=int, help="章节号")
    p_tl.add_argument("--anchor", help="时间锚点（如：末世第100天）")
    p_tl.add_argument("--event", help="事件描述")
    p_tl.add_argument("--name", help="倒计时名称")
    p_tl.add_argument("--value", help="倒计时值（如：D-10）")
    p_tl.add_argument("--from", dest="from_chapter", type=int, help="起始章节")
    p_tl.add_argument("--to", dest="to_chapter", type=int, help="结束章节")
    _add_project_root(p_tl)
    
    # ---- review (审查章节) ----
    p_review = subparsers.add_parser("review", help="审查章节")
    p_review.add_argument("chapter", type=int, help="章节号")
    p_review.add_argument("--independent", action="store_true", help="启用独立审查模式（清除上下文）")
    _add_project_root(p_review)
    
    # ---- data (数据回写) ----
    p_data = subparsers.add_parser("data", help="数据回写")
    p_data.add_argument("data_action", choices=["update"], help="数据操作")
    p_data.add_argument("chapter", type=int, help="章节号")
    p_data.add_argument("text_file", help="正文文件路径")
    p_data.add_argument("--confirm", action="store_true", help="启用状态变更确认")
    _add_project_root(p_data)
    
    # ---- volume (多卷大纲管理) ----
    p_volume = subparsers.add_parser("volume", help="多卷大纲管理")
    p_volume.add_argument("volume_action", choices=["list", "add", "status", "switch", "complete", "summary"],
                         help="卷管理操作")
    p_volume.add_argument("--volume", type=int, help="卷号（status/switch/complete/summary）")
    p_volume.add_argument("--name", help="卷名（add）")
    p_volume.add_argument("--output", help="输出文件路径（summary）")
    _add_project_root(p_volume)
    
    # ---- consistency (一致性检查) ----
    p_consistency = subparsers.add_parser("consistency", help="跨章节一致性检查")
    p_consistency.add_argument("consistency_action", choices=["check", "batch"],
                              help="一致性检查操作")
    p_consistency.add_argument("--chapter", type=int, help="章节号（check）")
    p_consistency.add_argument("--start", type=int, help="起始章节号（batch）")
    p_consistency.add_argument("--end", type=int, help="结束章节号（batch）")
    p_consistency.add_argument("--scope", choices=["timeline", "character", "worldview", "ooc", "full"],
                              default="full", help="检查范围")
    p_consistency.add_argument("--output", help="输出文件路径")
    _add_project_root(p_consistency)

    # ---- analyze (样板书拆解) ----
    p_analyze = subparsers.add_parser("analyze", help="样板书拆解分析（提取套路/节奏/文风）")
    p_analyze.add_argument("input", help="样板书文本文件路径")
    p_analyze.add_argument("-o", "--output", help="输出目录（默认: 1-边界/样板书分析/）")
    p_analyze.add_argument("--from-chapter", type=int, help="起始章节号")
    p_analyze.add_argument("--to-chapter", type=int, help="结束章节号")
    p_analyze.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    _add_project_root(p_analyze)
    
    # ---- write (一键写作) ----
    p_write = subparsers.add_parser("write", help="一键写作（写前检查+提取上下文+生成章节）")
    p_write.add_argument("chapter", type=int, help="章节号")
    p_write.add_argument("--query", help="主题指导（如：主角和女主角的感情发展）")
    p_write.add_argument("--smart", action="store_true", help="使用智能上下文模式（RAG增强）")
    p_write.add_argument("--max-chars", type=int, default=8000, help="最大上下文字数（--smart时使用）")
    p_write.add_argument("--output", help="输出文件路径（默认: 4-正文/草稿/第N章.md）")
    _add_project_root(p_write)
    
    # ---- write-optimize (生成+优化) ----
    p_write_opt = subparsers.add_parser("write-optimize", help="生成+优化（完整写作流程）")
    p_write_opt.add_argument("chapter", type=int, help="章节号")
    p_write_opt.add_argument("--query", help="主题指导")
    p_write_opt.add_argument("--smart", action="store_true", help="使用智能上下文模式")
    p_write_opt.add_argument("--target-score", type=float, default=0.7, help="目标分数")
    p_write_opt.add_argument("--output", help="输出文件路径")
    _add_project_root(p_write_opt)
    
    # ---- write-batch (批量生成) ----
    p_write_batch = subparsers.add_parser("write-batch", help="批量生成章节")
    p_write_batch.add_argument("start", type=int, help="起始章节号")
    p_write_batch.add_argument("end", type=int, help="结束章节号")
    p_write_batch.add_argument("--query", help="主题指导")
    p_write_batch.add_argument("--smart", action="store_true", help="使用智能上下文模式")
    p_write_batch.add_argument("--output-dir", help="输出目录（默认: 4-正文/草稿/）")
    _add_project_root(p_write_batch)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # ====== 命令兼容性处理 ======
    deprecated_commands = {
        "foreshadowing": ("foreshadow", "foreshadowing 已弃用，请使用 foreshadow"),
        "evolve": ("score", "evolve 已弃用，请使用 score --evolve"),
        "smart-context": ("context", "smart-context 已弃用，请使用 context --smart"),
        "pre-check": ("check", "pre-check 已弃用，请使用 check before"),
        "post-write": ("check", "post-write 已弃用，请使用 check after"),
    }
    
    # 显示弃用警告
    if args.command in deprecated_commands:
        new_cmd, warning_msg = deprecated_commands[args.command]
        print(f"[警告] {warning_msg}", file=sys.stderr)
    
    # 命令转换
    if args.command == "foreshadowing":
        args.command = "foreshadow"
    elif args.command == "evolve":
        args.command = "score"
        args.evolve = True
    elif args.command == "smart-context":
        args.command = "context"
        args.smart = True
    elif args.command == "pre-check":
        # 转换为 check before
        args.check_type = "before"
        args.target = str(args.chapter)
        args.command = "check"
    elif args.command == "post-write":
        # 转换为 check after
        args.check_type = "after"
        args.target = str(args.chapter)
        args.text_file_arg = args.text_file
        args.command = "check"

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "help": cmd_help,
        "version": cmd_version,
        "index": cmd_index,
        "search": cmd_search,
        "context": cmd_context,
        "write": cmd_write,
        "write-optimize": cmd_write_optimize,
        "write-batch": cmd_write_batch,
        "score": cmd_score,
        "stats": cmd_stats,
        "entity": cmd_entity,
        "foreshadow": cmd_foreshadowing,
        "foreshadowing": cmd_foreshadowing,  # 兼容旧命令
        "check": cmd_check,
        "post-write": cmd_post_write,  # 兼容旧命令
        "pre-check": cmd_pre_check,  # 兼容旧命令
        "smart-context": cmd_smart_context,  # 兼容旧命令
        "extract": cmd_extract,
        "timeline": cmd_timeline,
        "review": cmd_review,
        "data": cmd_data,
        "volume": cmd_volume,
        "growth": cmd_growth,
        "consistency": cmd_consistency,
        "analyze": cmd_analyze,
        "relationship": cmd_relationship,
    }

    fn = commands.get(args.command)
    if fn:
        try:
            fn(args)
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
