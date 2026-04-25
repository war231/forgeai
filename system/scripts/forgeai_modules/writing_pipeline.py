#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作流水线

整合新旧功能的完整写作流程
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import get_config, ForgeAIConfig
from .pipeline import Pipeline
from .chapter_generator import ChapterGenerator, GenerationResult
from .chapter_optimizer import ChapterOptimizer, OptimizationResult
from .review_feedback_loop import ReviewFeedbackLoop, FeedbackResult
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class WritingSession:
    """写作会话"""
    session_id: str
    chapter_num: int
    status: str = "pending"
    
    # 各阶段结果
    generation: Optional[GenerationResult] = None
    optimization: Optional[OptimizationResult] = None
    feedback: Optional[FeedbackResult] = None
    
    # 最终结果
    final_content: str = ""
    final_word_count: int = 0
    
    # 元数据
    start_time: str = ""
    end_time: str = ""
    total_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "chapter_num": self.chapter_num,
            "status": self.status,
            "final_word_count": self.final_word_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_time": self.total_time,
            "stages": {
                "generation": self.generation.success if self.generation else False,
                "optimization": self.optimization.success if self.optimization else False,
                "feedback": self.feedback.success if self.feedback else False,
            },
        }


class WritingPipeline:
    """写作流水线 - 整合新旧功能"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        
        # 现有流水线
        self.pipeline = Pipeline(self.config)
        
        # 新功能模块
        self.generator = ChapterGenerator(self.config)
        self.optimizer = ChapterOptimizer(self.config)
        self.feedback_loop = ReviewFeedbackLoop(self.config)
    
    async def write_chapter(self,
                           chapter_num: int,
                           genre: str = "",
                           query: str = "",
                           use_rag: bool = False,
                           book_analysis: Optional[Dict[str, Any]] = None,
                           enable_optimization: bool = True,
                           enable_feedback: bool = True,
                           enable_post_write: bool = True,
                           target_score: float = 0.7) -> WritingSession:
        """
        完整的写作流程
        
        Args:
            chapter_num: 章节号
            genre: 题材
            query: 主题指导
            use_rag: 是否使用 RAG
            book_analysis: 样板书分析结果
            enable_optimization: 是否启用优化
            enable_feedback: 是否启用反馈循环
            enable_post_write: 是否启用写后流水线
            target_score: 目标分数
        
        Returns:
            写作会话
        """
        import uuid
        import time
        
        session = WritingSession(
            session_id=str(uuid.uuid4())[:8],
            chapter_num=chapter_num,
            start_time=datetime.now().isoformat(),
        )
        
        start_time = time.time()
        
        try:
            # Stage 1: 生成章节
            logger.info(f"[Session {session.session_id}] Stage 1: 生成章节...")
            session.status = "generating"
            
            gen_result = await self.generator.generate_chapter(
                chapter_num=chapter_num,
                genre=genre,
                query=query,
                use_rag=use_rag,
                book_analysis=book_analysis,
            )
            
            session.generation = gen_result
            
            if not gen_result.success:
                session.status = "failed"
                logger.error(f"[Session {session.session_id}] 生成失败: {gen_result.error_message}")
                return session
            
            current_content = gen_result.content
            logger.info(f"[Session {session.session_id}] 生成完成，字数: {len(current_content)}")
            
            # Stage 2: 优化（可选）
            if enable_optimization:
                logger.info(f"[Session {session.session_id}] Stage 2: 优化章节...")
                session.status = "optimizing"
                
                opt_result = await self.optimizer.optimize_chapter(
                    chapter_num=chapter_num,
                    content=current_content,
                    target_score=target_score,
                )
                
                session.optimization = opt_result
                current_content = opt_result.final_content
                
                logger.info(
                    f"[Session {session.session_id}] 优化完成，"
                    f"分数: {opt_result.final_score:.3f}, "
                    f"提升: {opt_result.total_improvement:.3f}"
                )
            
            # Stage 3: 反馈循环（可选）
            if enable_feedback:
                logger.info(f"[Session {session.session_id}] Stage 3: 应用反馈...")
                session.status = "reviewing"
                
                fb_result = await self.feedback_loop.apply_feedback(
                    chapter_num=chapter_num,
                    content=current_content,
                )
                
                session.feedback = fb_result
                current_content = fb_result.final_content
                
                logger.info(
                    f"[Session {session.session_id}] 反馈完成，"
                    f"修复: {fb_result.total_fixes} 个问题"
                )
            
            # Stage 4: 写后流水线
            if enable_post_write:
                logger.info(f"[Session {session.session_id}] Stage 4: 写后流水线...")
                session.status = "post_processing"
                
                try:
                    post_result = await self.pipeline.post_write(
                        chapter=chapter_num,
                        text=current_content,
                        score_ai=True,
                        enable_review=True,
                    )
                    logger.info(f"[Session {session.session_id}] 写后流水线完成")
                except Exception as e:
                    logger.warning(f"[Session {session.session_id}] 写后流水线失败: {e}")
            
            # 完成
            session.final_content = current_content
            session.final_word_count = len(current_content)
            session.status = "completed"
            
            logger.info(
                f"[Session {session.session_id}] 完成，"
                f"最终字数: {session.final_word_count}"
            )
            
        except Exception as e:
            session.status = "failed"
            logger.error(f"[Session {session.session_id}] 失败: {e}")
        
        session.end_time = datetime.now().isoformat()
        session.total_time = time.time() - start_time
        
        return session
    
    async def write_batch(self,
                         start_chapter: int,
                         end_chapter: int,
                         genre: str = "",
                         query: str = "",
                         use_rag: bool = False,
                         enable_optimization: bool = False,  # 批量默认不优化
                         enable_feedback: bool = False,      # 批量默认不反馈
                         output_dir: Optional[Path] = None,
                         on_progress: Optional[callable] = None) -> List[WritingSession]:
        """
        批量写作
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            genre: 题材
            query: 主题指导
            use_rag: 是否使用 RAG
            enable_optimization: 是否启用优化
            enable_feedback: 是否启用反馈
            output_dir: 输出目录
            on_progress: 进度回调
        
        Returns:
            写作会话列表
        """
        sessions = []
        total = end_chapter - start_chapter + 1
        
        logger.info(f"开始批量写作: {start_chapter}-{end_chapter}章，共{total}章")
        
        for i, chapter_num in enumerate(range(start_chapter, end_chapter + 1), 1):
            logger.info(f"进度: {i}/{total} - 第{chapter_num}章")
            
            session = await self.write_chapter(
                chapter_num=chapter_num,
                genre=genre,
                query=query,
                use_rag=use_rag,
                enable_optimization=enable_optimization,
                enable_feedback=enable_feedback,
            )
            
            sessions.append(session)
            
            # 保存章节
            if output_dir and session.status == "completed":
                self._save_chapter(session, output_dir)
            
            # 进度回调
            if on_progress:
                on_progress(i, total, session)
        
        # 统计
        completed = sum(1 for s in sessions if s.status == "completed")
        logger.info(f"批量写作完成: {completed}/{total} 章")
        
        return sessions
    
    def _save_chapter(self, session: WritingSession, output_dir: Path) -> None:
        """保存章节"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"第{session.chapter_num}章.md"
        
        # 添加标题
        title = session.generation.title if session.generation else f"第{session.chapter_num}章"
        content = f"# {title}\n\n{session.final_content}"
        
        output_file.write_text(content, encoding="utf-8")
        
        logger.info(f"章节已保存: {output_file}")
    
    def export_session_report(self, sessions: List[WritingSession], output_file: Path) -> None:
        """导出会话报告"""
        import json
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_sessions": len(sessions),
            "completed": sum(1 for s in sessions if s.status == "completed"),
            "failed": sum(1 for s in sessions if s.status == "failed"),
            "total_words": sum(s.final_word_count for s in sessions),
            "sessions": [s.to_dict() for s in sessions],
        }
        
        output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.info(f"会话报告已导出: {output_file}")


# 便捷函数
async def write_chapter(chapter_num: int,
                       genre: str = "",
                       query: str = "",
                       config: Optional[ForgeAIConfig] = None) -> WritingSession:
    """一键写作"""
    pipeline = WritingPipeline(config)
    return await pipeline.write_chapter(chapter_num, genre, query)


async def write_batch(start_chapter: int,
                     end_chapter: int,
                     genre: str = "",
                     output_dir: Optional[Path] = None,
                     config: Optional[ForgeAIConfig] = None) -> List[WritingSession]:
    """批量写作"""
    pipeline = WritingPipeline(config)
    return await pipeline.write_batch(
        start_chapter, end_chapter, genre, output_dir=output_dir
    )
