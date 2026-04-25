#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动流水线

写完章节后一键执行：
1. 索引章节（RAG）
2. 自动提取实体/关系/状态变化
3. AI味评分
4. 记录追读力
5. 更新进度

写前自动检查：
1. 超期伏笔提醒
2. 节奏失衡警告
3. 叙事债务提醒
4. 智能上下文召回
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .state_manager import StateManager
from .index_manager import IndexManager
from .rag_adapter import RAGAdapter
from .context_extractor import ContextExtractor
from .humanize_scorer import HumanizeScorer
from .entity_extractor_v3_ner import SmartEntityExtractor as EntityExtractor
from .review_pipeline import ReviewPipeline
from .chapter_generator import ChapterGenerator, GenerationResult
from .reference_integrator import ReferenceIntegrator
from .genre_profile_loader import GenreProfileLoader


class Pipeline:
    """自动流水线 - 整合新旧功能"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        
        # 现有模块
        self.state_manager = StateManager(self.config)
        self.index_manager = IndexManager(self.config)
        self.rag_adapter = RAGAdapter(self.config)
        self.context_extractor = ContextExtractor(self.config)
        self.humanize_scorer = HumanizeScorer(self.config)
        self.entity_extractor = EntityExtractor(self.config)
        self.review_pipeline = ReviewPipeline(self.config)
        
        # 新增模块
        self.chapter_generator = ChapterGenerator(self.config)
        self.reference_integrator = ReferenceIntegrator(self.config)
        self.profile_loader = GenreProfileLoader(self.config)

    async def post_write(self, chapter: int, text: str,
                         source_file: str = "",
                         score_ai: bool = True,
                         extract_llm: bool = False,
                         enable_review: bool = True,
                         enable_auto_fix: bool = True) -> Dict[str, Any]:
        """
        写作后自动流水线

        Args:
            chapter: 章节号
            text: 正文内容
            source_file: 源文件路径
            score_ai: 是否做AI味评分
            extract_llm: 是否用LLM提取实体

        Returns:
            流水线执行结果
        """
        results = {"chapter": chapter, "steps": {}}

        # Step 1: 索引章节
        try:
            chunk_count = self.rag_adapter.index_chapter(
                chapter, text, source_file=source_file
            )
            self.index_manager.upsert_chapter(
                chapter, word_count=len(text)
            )
            results["steps"]["index"] = {"status": "ok", "chunks": chunk_count}
        except Exception as e:
            results["steps"]["index"] = {"status": "error", "message": str(e)}

        # Step 2: 自动提取实体
        try:
            # 使用 SmartEntityExtractor 的 extract 方法
            entities = self.entity_extractor.extract(text)
            
            # 统计实体数量
            entity_count = len(entities)
            
            # 按类型分组
            entity_types = {}
            for entity in entities:
                entity_type = entity.type
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            results["steps"]["extract"] = {
                "status": "ok",
                "entities": entity_count,
                "entity_types": entity_types,
                "state_changes": 0,  # 简化处理
                "relationships": 0,
                "foreshadowing": 0,
                "scenes": 0,
            }
        except Exception as e:
            results["steps"]["extract"] = {"status": "error", "message": str(e)}

        # Step 3: AI味评分
        if score_ai:
            try:
                score_result = self.humanize_scorer.rule_based_score(text)
                results["steps"]["score"] = {
                    "status": "ok",
                    "score": round(score_result.score, 4),
                    "detected_patterns": len(score_result.ai_patterns),
                    "needs_humanize": score_result.score < 0.6,
                }
            except Exception as e:
                results["steps"]["score"] = {"status": "error", "message": str(e)}

        # Step 4: 更新进度
        try:
            self.state_manager.update_progress(
                current_chapter=chapter,
                word_count=self._get_total_word_count() + len(text),
                phase="write",
            )
            results["steps"]["progress"] = {"status": "ok"}
        except Exception as e:
            results["steps"]["progress"] = {"status": "error", "message": str(e)}

        # Step 5: 写前检查（为下一章准备）
        try:
            pre_check = self.pre_write_check(chapter + 1)
            results["steps"]["pre_check_next"] = pre_check
        except Exception as e:
            results["steps"]["pre_check_next"] = {"status": "error", "message": str(e)}
        
        # Step 6: 审查流程（新增）
        if enable_review:
            try:
                review_result = self.review_pipeline.review_chapter(
                    chapter=chapter,
                    text=text,
                    check_scope="full",
                    enable_independent_review=True,
                    enable_auto_fix=enable_auto_fix
                )
                results["steps"]["review"] = {
                    "status": "ok",
                    "overall_passed": review_result["overall_passed"],
                    "overall_score": review_result["aggregated"]["overall_score"],
                    "critical_issues": len(review_result["critical_issues"]),
                    "auto_fixes": len(review_result["auto_fixes"]),
                }
                
                # 如果有严重问题，添加警告
                if review_result["critical_issues"]:
                    results["warnings"] = results.get("warnings", [])
                    results["warnings"].append({
                        "type": "critical_issues",
                        "message": f"发现{len(review_result['critical_issues'])}个严重问题",
                        "issues": review_result["critical_issues"][:3]  # 最多显示3个
                    })
            except Exception as e:
                results["steps"]["review"] = {"status": "error", "message": str(e)}
        else:
            results["steps"]["review"] = {"status": "skipped"}

        return results

    def pre_write_check(self, next_chapter: int) -> Dict[str, Any]:
        """
        写前自动检查

        返回所有需要作者注意的提醒
        """
        state = self.state_manager.load()
        alerts = []

        # 1. 超期伏笔提醒
        overdue = self.state_manager.get_overdue_foreshadowing(next_chapter, threshold=30)
        if overdue:
            for fs in overdue:
                planted = fs.get("chapter_planted", 0)
                age = next_chapter - planted
                alerts.append({
                    "level": "warning",
                    "type": "overdue_foreshadowing",
                    "message": f"伏笔 [{fs.get('id')}] 已超期{age}章未回收",
                    "detail": fs.get("description", ""),
                    "planted_chapter": planted,
                })

        # 2. 活跃伏笔太多
        active_fs = state.get("foreshadowing", {}).get("active", [])
        if len(active_fs) > 15:
            alerts.append({
                "level": "warning",
                "type": "too_many_foreshadowing",
                "message": f"活跃伏笔{len(active_fs)}个，超过15个阈值，建议回收部分",
            })

        # 3. 叙事债务过高
        debt = state.get("reading_power", {}).get("debt", 0.0)
        if debt > 5.0:
            alerts.append({
                "level": "warning",
                "type": "narrative_debt",
                "message": f"叙事债务{debt:.1f}，需要安排偿还（爽点/高潮）",
            })

        # 4. 节奏失衡
        strands = state.get("strands", {})
        quest = len(strands.get("quest", []))
        fire = len(strands.get("fire", []))
        constellation = len(strands.get("constellation", []))
        total = quest + fire + constellation
        if total > 10:
            quest_ratio = quest / total
            fire_ratio = fire / total
            if quest_ratio < 0.4:
                alerts.append({
                    "level": "info",
                    "type": "pacing",
                    "message": f"主线(Quest)占比{quest_ratio:.0%}偏低，建议推进主线",
                })
            if fire_ratio < 0.1:
                alerts.append({
                    "level": "info",
                    "type": "pacing",
                    "message": f"爽点(Fire)占比{fire_ratio:.0%}偏低，建议安排爆发",
                })

        # 5. 追读力下降趋势
        rp_history = state.get("reading_power", {}).get("history", [])
        if len(rp_history) >= 3:
            recent_3 = [r.get("score", 0) for r in rp_history[-3:]]
            if all(recent_3[i] > recent_3[i+1] for i in range(len(recent_3)-1)):
                alerts.append({
                    "level": "warning",
                    "type": "reading_power_decline",
                    "message": f"追读力连续3章下降: {recent_3}",
                })

        return {
            "next_chapter": next_chapter,
            "alerts": alerts,
            "alert_count": len(alerts),
            "warnings": len([a for a in alerts if a["level"] == "warning"]),
            "active_foreshadowing": len(active_fs),
            "narrative_debt": debt,
        }

    def smart_context(self, chapter: int, query: str = "",
                       max_chars: int = 8000) -> Dict[str, Any]:
        """
        智能上下文组装

        根据当前章节内容动态决定召回哪些前文，
        控制总长度在 max_chars 以内

        策略：
        1. 优先级：核心设定 > 超期伏笔 > 最近3章摘要 > RAG检索
        2. 动态裁剪：按优先级填充，超长则截断低优先级
        """
        budget = max_chars
        sections: List[Dict[str, Any]] = []

        # 1. 核心设定（最高优先级，约1000字）
        state = self.state_manager.load()
        core_settings = self._build_core_settings(state)
        if core_settings:
            sections.append({
                "priority": 0,
                "title": "核心设定",
                "content": core_settings,
            })

        # 2. 超期伏笔（高优先级）
        overdue = self.state_manager.get_overdue_foreshadowing(chapter)
        if overdue:
            content = "\n".join(
                f"- [{fs.get('id')}] {fs.get('description', '')} (第{fs.get('chapter_planted', '?')}章埋设，已{chapter - fs.get('chapter_planted', 0)}章未回收)"
                for fs in overdue[:5]
            )
            sections.append({
                "priority": 1,
                "title": "⚠️ 超期伏笔",
                "content": content,
            })

        # 3. 活跃实体状态
        entities = self.state_manager.get_entities()
        active_entities = self._get_active_entities(entities, chapter, lookback=20)
        if active_entities:
            content_lines = []
            for e in active_entities[:15]:
                content_lines.append(
                    f"- {e['name']} ({e['tier']}) - 上次出场: 第{e['last_appearance']}章"
                )
            sections.append({
                "priority": 2,
                "title": "活跃角色",
                "content": "\n".join(content_lines),
            })

        # 4. 最近N章摘要
        prev_chapters = self._get_recent_chapter_summaries(chapter, lookback=3)
        if prev_chapters:
            content_lines = []
            for ch in prev_chapters:
                summary = ch.get("summary", "")
                if summary:
                    content_lines.append(f"- 第{ch['chapter']}章: {summary[:100]}")
            if content_lines:
                sections.append({
                    "priority": 3,
                    "title": "近期章节",
                    "content": "\n".join(content_lines),
                })

        # 5. RAG 检索（最低优先级，动态填充）
        if query:
            try:
                rag_results = asyncio.run(
                    self.rag_adapter.search(query, top_k=5, chapter_filter=None)
                )
                if rag_results:
                    content_lines = []
                    for r in rag_results[:3]:
                        content_lines.append(
                            f"- [第{r.chapter}章 score={r.score:.2f}] {r.content[:150]}"
                        )
                    sections.append({
                        "priority": 4,
                        "title": "RAG 相关内容",
                        "content": "\n".join(content_lines),
                    })
            except Exception:
                pass

        # 按优先级排序，裁剪到预算内
        sections.sort(key=lambda x: x["priority"])
        final_sections = []
        used_chars = 0

        for sec in sections:
            content_len = len(sec["content"])
            if used_chars + content_len <= budget:
                final_sections.append(sec)
                used_chars += content_len
            else:
                # 部分填充
                remaining = budget - used_chars
                if remaining > 100:
                    sec["content"] = sec["content"][:remaining] + "\n...(截断)"
                    final_sections.append(sec)
                    used_chars += remaining
                break

        # 组装输出
        output_lines = [f"## 智能上下文（第{chapter}章，共{used_chars}字）\n"]
        for sec in final_sections:
            output_lines.append(f"### {sec['title']}\n{sec['content']}\n")

        return {
            "chapter": chapter,
            "total_chars": used_chars,
            "budget": budget,
            "sections": len(final_sections),
            "formatted": "\n".join(output_lines),
        }

    def _build_core_settings(self, state: Dict) -> str:
        """构建核心设定摘要"""
        lines = []
        project = state.get("project", {})
        if project.get("name"):
            lines.append(f"项目: {project['name']} ({project.get('genre', '')})")
        if project.get("mode"):
            lines.append(f"模式: {project['mode']}")
        progress = state.get("progress", {})
        if progress:
            lines.append(f"进度: 第{progress.get('current_chapter', 0)}章")
        debt = state.get("reading_power", {}).get("debt", 0.0)
        if debt > 0:
            lines.append(f"叙事债务: {debt:.1f}")
        return "\n".join(lines)

    def _get_active_entities(self, entities: Dict, chapter: int,
                              lookback: int = 20) -> List[Dict]:
        """获取活跃实体"""
        active = []
        for eid, edata in entities.items():
            last = edata.get("last_appearance", 0)
            if chapter - last <= lookback:
                active.append({
                    "id": eid,
                    "name": edata.get("name", ""),
                    "tier": edata.get("tier", "decorative"),
                    "last_appearance": last,
                    "type": edata.get("type", "character"),
                })
        tier_order = {"core": 0, "important": 1, "secondary": 2, "decorative": 3}
        active.sort(key=lambda x: tier_order.get(x["tier"], 99))
        return active

    def _get_recent_chapter_summaries(self, chapter: int,
                                       lookback: int = 3) -> List[Dict]:
        """获取最近N章摘要"""
        chapters = []
        for ch_num in range(max(1, chapter - lookback), chapter):
            meta = self.index_manager.get_chapter(ch_num)
            if meta:
                chapters.append(meta)
        return chapters

    def _get_total_word_count(self) -> int:
        """获取总字数"""
        state = self.state_manager.load()
        return state.get("progress", {}).get("word_count", 0)
    
    async def write_chapter(self,
                           chapter_num: int,
                           genre: str = "",
                           query: str = "",
                           use_rag: bool = False,
                           book_analysis: Optional[Dict[str, Any]] = None,
                           enable_post_write: bool = True) -> GenerationResult:
        """
        一键写作流程 - 整合新旧功能
        
        Args:
            chapter_num: 章节号
            genre: 题材（为空则自动从项目配置读取）
            query: 主题指导
            use_rag: 是否使用 RAG 增强
            book_analysis: 样板书分析结果（为空则自动读取）
            enable_post_write: 是否启用写后流水线
        
        Returns:
            生成结果
        """
        # 1. 自动获取题材
        if not genre:
            state = self.state_manager.load()
            genre = state.get("project", {}).get("genre", "shuangwen")
        
        # 2. 自动读取样板书分析结果
        if book_analysis is None:
            book_analysis = self._load_book_analysis()
        
        # 3. 生成章节
        result = await self.chapter_generator.generate_chapter(
            chapter_num=chapter_num,
            genre=genre,
            query=query,
            use_rag=use_rag,
            book_analysis=book_analysis,
        )
        
        # 4. 写后流水线
        if result.success and enable_post_write:
            try:
                post_result = await self.post_write(
                    chapter=chapter_num,
                    text=result.content,
                    score_ai=True,
                    enable_review=True,
                )
                result.llm_usage["post_write"] = post_result
            except Exception as e:
                # 写后流水线失败不影响生成结果
                import logging
                logging.warning(f"写后流水线失败: {e}")
        
        return result
    
    def _load_book_analysis(self) -> Optional[Dict[str, Any]]:
        """加载样板书分析结果"""
        if not self.config.project_root:
            return None
        
        # 尝试从多个位置读取
        analysis_paths = [
            self.config.project_root / ".forgeai" / "analysis_data.json",
            self.config.project_root / "1-边界" / "样板书分析" / "analysis_data.json",
            self.config.project_root.parent / "1-边界" / "样板书分析" / "analysis_data.json",
        ]
        
        for path in analysis_paths:
            if path.exists():
                try:
                    import json
                    return json.loads(path.read_text(encoding="utf-8"))
                except:
                    continue
        
        return None
    
    def apply_genre_profile(self, genre: str) -> Dict[str, Any]:
        """应用题材配置"""
        profile = self.profile_loader.get_profile(genre)
        if not profile:
            return {}
        
        return {
            "genre": genre,
            "profile": profile.to_dict(),
            "hook_guidance": self.profile_loader.get_hook_guidance(genre),
            "pattern_guidance": self.profile_loader.get_pattern_guidance(genre),
            "micro_payoff_suggestions": self.profile_loader.get_micro_payoff_suggestions(genre),
        }
