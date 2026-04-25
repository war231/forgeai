#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成器

支持一次生成多章
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import get_config, ForgeAIConfig
from .chapter_generator import ChapterGenerator, GenerationResult
from .pipeline import Pipeline
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class BatchJob:
    """批量任务"""
    job_id: str
    start_chapter: int
    end_chapter: int
    status: str = "pending"  # pending/running/completed/failed/paused
    progress: int = 0
    total: int = 0
    results: List[GenerationResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "start_chapter": self.start_chapter,
            "end_chapter": self.end_chapter,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "completed": len(self.results),
            "errors": len(self.errors),
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class BatchGenerator:
    """批量生成器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.generator = ChapterGenerator(config)
        self.pipeline = Pipeline(config)
    
    async def generate_batch(self,
                            start_chapter: int,
                            end_chapter: int,
                            genre: str = "",
                            query: str = "",
                            use_rag: bool = False,
                            enable_post_write: bool = True,
                            output_dir: Optional[Path] = None,
                            on_progress: Optional[callable] = None) -> BatchJob:
        """
        批量生成章节
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            genre: 题材
            query: 主题指导
            use_rag: 是否使用 RAG
            enable_post_write: 是否启用写后流水线
            output_dir: 输出目录
            on_progress: 进度回调
        
        Returns:
            批量任务
        """
        import uuid
        
        job = BatchJob(
            job_id=str(uuid.uuid4())[:8],
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            total=end_chapter - start_chapter + 1,
            start_time=datetime.now().isoformat(),
        )
        
        logger.info(f"[Batch {job.job_id}] 开始批量生成: {start_chapter}-{end_chapter}章")
        
        job.status = "running"
        
        try:
            for chapter_num in range(start_chapter, end_chapter + 1):
                logger.info(f"[Batch {job.job_id}] 生成第 {chapter_num} 章...")
                
                try:
                    # 生成章节
                    result = await self.generator.generate_chapter(
                        chapter_num, genre, query, use_rag
                    )
                    
                    if result.success:
                        job.results.append(result)
                        job.progress += 1
                        
                        # 保存章节
                        if output_dir:
                            self._save_chapter(result, output_dir)
                        
                        # 执行写后流水线
                        if enable_post_write:
                            await self._run_post_write(result)
                        
                        # 进度回调
                        if on_progress:
                            on_progress(job)
                        
                        logger.info(f"[Batch {job.job_id}] 第 {chapter_num} 章完成")
                    else:
                        # 记录错误
                        job.errors.append({
                            "chapter": chapter_num,
                            "error": result.error_message,
                        })
                        logger.error(f"[Batch {job.job_id}] 第 {chapter_num} 章失败: {result.error_message}")
                
                except Exception as e:
                    job.errors.append({
                        "chapter": chapter_num,
                        "error": str(e),
                    })
                    logger.error(f"[Batch {job.job_id}] 第 {chapter_num} 章异常: {e}")
            
            # 完成
            if job.progress == job.total:
                job.status = "completed"
            elif job.progress > 0:
                job.status = "partial"
            else:
                job.status = "failed"
            
        except Exception as e:
            job.status = "failed"
            logger.error(f"[Batch {job.job_id}] 批量生成失败: {e}")
        
        job.end_time = datetime.now().isoformat()
        
        logger.info(f"[Batch {job.job_id}] 完成: {job.progress}/{job.total} 章, {len(job.errors)} 个错误")
        
        return job
    
    def _save_chapter(self, result: GenerationResult, output_dir: Path) -> None:
        """保存章节"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"第{result.chapter_num}章.md"
        content = f"# {result.title}\n\n{result.content}"
        
        output_file.write_text(content, encoding="utf-8")
        
        logger.info(f"  保存到: {output_file}")
    
    async def _run_post_write(self, result: GenerationResult) -> None:
        """执行写后流水线"""
        try:
            post_result = await self.pipeline.post_write(
                chapter=result.chapter_num,
                text=result.content,
                score_ai=True,
                enable_review=True,
            )
            
            logger.info(f"  写后流水线完成: {post_result.get('steps', {})}")
        except Exception as e:
            logger.warning(f"  写后流水线失败: {e}")
    
    async def generate_with_outline(self,
                                   outline: Dict[int, Dict[str, Any]],
                                   genre: str = "",
                                   use_rag: bool = False,
                                   output_dir: Optional[Path] = None) -> BatchJob:
        """
        根据大纲批量生成
        
        Args:
            outline: 大纲字典 {章节号: 章节信息}
            genre: 题材
            use_rag: 是否使用 RAG
            output_dir: 输出目录
        
        Returns:
            批量任务
        """
        chapters = sorted(outline.keys())
        
        if not chapters:
            raise ValueError("大纲为空")
        
        return await self.generate_batch(
            start_chapter=chapters[0],
            end_chapter=chapters[-1],
            genre=genre,
            use_rag=use_rag,
            output_dir=output_dir,
        )
    
    def get_job_status(self, job: BatchJob) -> Dict[str, Any]:
        """获取任务状态"""
        return job.to_dict()
    
    def export_results(self, job: BatchJob, output_dir: Path) -> Dict[str, str]:
        """导出结果"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported = {}
        
        # 导出章节
        for result in job.results:
            output_file = output_dir / f"第{result.chapter_num}章.md"
            content = f"# {result.title}\n\n{result.content}"
            output_file.write_text(content, encoding="utf-8")
            exported[f"chapter_{result.chapter_num}"] = str(output_file)
        
        # 导出统计
        stats_file = output_dir / "batch_stats.json"
        stats = {
            "job_id": job.job_id,
            "status": job.status,
            "total": job.total,
            "completed": len(job.results),
            "errors": len(job.errors),
            "start_time": job.start_time,
            "end_time": job.end_time,
            "chapters": [
                {
                    "chapter": r.chapter_num,
                    "title": r.title,
                    "word_count": r.word_count,
                }
                for r in job.results
            ],
        }
        stats_file.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        exported["stats"] = str(stats_file)
        
        return exported


# 便捷函数
async def generate_batch(start_chapter: int,
                        end_chapter: int,
                        genre: str = "",
                        query: str = "",
                        output_dir: Optional[Path] = None,
                        config: Optional[ForgeAIConfig] = None) -> BatchJob:
    """批量生成"""
    generator = BatchGenerator(config)
    return await generator.generate_batch(
        start_chapter, end_chapter, genre, query, output_dir=output_dir
    )
