#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行生成器

支持并行生成多章,包括:
1. 并发控制
2. 任务队列
3. 进度追踪
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
from enum import Enum

from .chapter_generator import ChapterGenerator, GenerationResult
from .config import ForgeAIConfig
from .logger import get_logger
from .checkpoint_manager import CheckpointManager, ResumableTask, TaskStatus

logger = get_logger(__name__)


class ParallelStrategy(Enum):
    """并行策略"""
    SEQUENTIAL = "sequential"  # 顺序执行
    CONCURRENT = "concurrent"  # 并发执行
    PIPELINE = "pipeline"  # 流水线执行


@dataclass
class ParallelConfig:
    """并行配置"""
    max_concurrent: int = 3  # 最大并发数
    strategy: ParallelStrategy = ParallelStrategy.CONCURRENT
    retry_failed: bool = True  # 是否重试失败任务
    max_retries: int = 2  # 最大重试次数
    delay_between_tasks: float = 1.0  # 任务间延迟(秒)


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    chapter_num: int
    status: str  # pending/running/completed/failed
    result: Optional[GenerationResult] = None
    error: Optional[str] = None
    start_time: str = ""
    end_time: str = ""
    duration: float = 0.0
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "chapter_num": self.chapter_num,
            "status": self.status,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 2),
            "retry_count": self.retry_count,
        }


@dataclass
class ParallelJob:
    """并行任务"""
    job_id: str
    chapters: List[int]
    config: ParallelConfig
    status: str = "pending"
    results: List[TaskResult] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    
    @property
    def completed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "completed")
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")
    
    @property
    def progress_percent(self) -> float:
        if not self.chapters:
            return 0.0
        return (self.completed_count / len(self.chapters)) * 100
    
    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "chapters": self.chapters,
            "config": {
                "max_concurrent": self.config.max_concurrent,
                "strategy": self.config.strategy.value,
            },
            "status": self.status,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "total": len(self.chapters),
            "progress": round(self.progress_percent, 1),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": [r.to_dict() for r in self.results],
        }


class ParallelGenerator:
    """并行生成器"""
    
    def __init__(
        self,
        config: ForgeAIConfig,
        parallel_config: Optional[ParallelConfig] = None,
    ):
        self.config = config
        self.parallel_config = parallel_config or ParallelConfig()
        self.generator = ChapterGenerator(config)
        self.checkpoint_manager = CheckpointManager(config.project_root / ".forgeai" / "checkpoints")
    
    async def generate_parallel(
        self,
        chapters: List[int],
        genre: str = "",
        query: str = "",
        use_rag: bool = False,
        book_analysis: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[TaskResult], None]] = None,
    ) -> ParallelJob:
        """
        并行生成多章
        
        Args:
            chapters: 章节号列表
            genre: 题材
            query: 主题指导
            use_rag: 是否使用RAG
            book_analysis: 样板书分析结果
            on_progress: 进度回调
        
        Returns:
            并行任务
        """
        import uuid
        
        job = ParallelJob(
            job_id=str(uuid.uuid4())[:8],
            chapters=chapters,
            config=self.parallel_config,
            start_time=datetime.now().isoformat(),
        )
        
        logger.info(
            f"[Parallel {job.job_id}] 开始并行生成: "
            f"{len(chapters)}章, 最大并发: {self.parallel_config.max_concurrent}"
        )
        
        job.status = "running"
        
        # 根据策略选择执行方式
        if self.parallel_config.strategy == ParallelStrategy.SEQUENTIAL:
            await self._execute_sequential(job, genre, query, use_rag, book_analysis, on_progress)
        elif self.parallel_config.strategy == ParallelStrategy.CONCURRENT:
            await self._execute_concurrent(job, genre, query, use_rag, book_analysis, on_progress)
        elif self.parallel_config.strategy == ParallelStrategy.PIPELINE:
            await self._execute_pipeline(job, genre, query, use_rag, book_analysis, on_progress)
        
        job.status = "completed" if job.failed_count == 0 else "partial"
        job.end_time = datetime.now().isoformat()
        
        logger.info(
            f"[Parallel {job.job_id}] 完成: "
            f"{job.completed_count}/{len(chapters)}章, "
            f"失败: {job.failed_count}"
        )
        
        return job
    
    async def _execute_sequential(
        self,
        job: ParallelJob,
        genre: str,
        query: str,
        use_rag: bool,
        book_analysis: Optional[Dict[str, Any]],
        on_progress: Optional[Callable],
    ) -> None:
        """顺序执行"""
        for chapter_num in job.chapters:
            task_result = await self._generate_single(
                job.job_id, chapter_num, genre, query, use_rag, book_analysis
            )
            
            job.results.append(task_result)
            
            if on_progress:
                on_progress(task_result)
            
            # 任务间延迟
            if self.parallel_config.delay_between_tasks > 0:
                await asyncio.sleep(self.parallel_config.delay_between_tasks)
    
    async def _execute_concurrent(
        self,
        job: ParallelJob,
        genre: str,
        query: str,
        use_rag: bool,
        book_analysis: Optional[Dict[str, Any]],
        on_progress: Optional[Callable],
    ) -> None:
        """并发执行"""
        semaphore = asyncio.Semaphore(self.parallel_config.max_concurrent)
        
        async def limited_generate(chapter_num: int):
            async with semaphore:
                task_result = await self._generate_single(
                    job.job_id, chapter_num, genre, query, use_rag, book_analysis
                )
                
                job.results.append(task_result)
                
                if on_progress:
                    on_progress(task_result)
                
                # 任务间延迟
                if self.parallel_config.delay_between_tasks > 0:
                    await asyncio.sleep(self.parallel_config.delay_between_tasks)
        
        # 并发执行所有任务
        tasks = [limited_generate(ch) for ch in job.chapters]
        await asyncio.gather(*tasks)
    
    async def _execute_pipeline(
        self,
        job: ParallelJob,
        genre: str,
        query: str,
        use_rag: bool,
        book_analysis: Optional[Dict[str, Any]],
        on_progress: Optional[Callable],
    ) -> None:
        """流水线执行(生成和保存并行)"""
        # 这里简化实现,实际可以实现更复杂的流水线
        await self._execute_concurrent(job, genre, query, use_rag, book_analysis, on_progress)
    
    async def _generate_single(
        self,
        job_id: str,
        chapter_num: int,
        genre: str,
        query: str,
        use_rag: bool,
        book_analysis: Optional[Dict[str, Any]],
    ) -> TaskResult:
        """生成单个章节"""
        task_id = f"{job_id}_ch{chapter_num}"
        
        result = TaskResult(
            task_id=task_id,
            chapter_num=chapter_num,
            status="running",
            start_time=datetime.now().isoformat(),
        )
        
        retry_count = 0
        max_retries = self.parallel_config.max_retries if self.parallel_config.retry_failed else 0
        
        while retry_count <= max_retries:
            try:
                logger.info(f"[{task_id}] 生成第{chapter_num}章 (尝试 {retry_count + 1}/{max_retries + 1})")
                
                # 生成章节
                gen_result = await self.generator.generate_chapter(
                    chapter_num=chapter_num,
                    genre=genre,
                    query=query,
                    use_rag=use_rag,
                    book_analysis=book_analysis,
                )
                
                if gen_result.success:
                    result.status = "completed"
                    result.result = gen_result
                    result.retry_count = retry_count
                    logger.info(f"[{task_id}] 第{chapter_num}章生成成功")
                    break
                else:
                    raise Exception(gen_result.error_message or "生成失败")
            
            except Exception as e:
                result.error = str(e)
                retry_count += 1
                
                if retry_count <= max_retries:
                    logger.warning(f"[{task_id}] 第{chapter_num}章生成失败,准备重试: {e}")
                    await asyncio.sleep(2 ** retry_count)  # 指数退避
                else:
                    result.status = "failed"
                    logger.error(f"[{task_id}] 第{chapter_num}章生成失败: {e}")
        
        result.end_time = datetime.now().isoformat()
        
        if result.start_time and result.end_time:
            start = datetime.fromisoformat(result.start_time)
            end = datetime.fromisoformat(result.end_time)
            result.duration = (end - start).total_seconds()
        
        return result


class ResumableBatchGenerator(ResumableTask):
    """可恢复的批量生成器"""
    
    def __init__(
        self,
        config: ForgeAIConfig,
        parallel_config: Optional[ParallelConfig] = None,
    ):
        checkpoint_manager = CheckpointManager(config.project_root / ".forgeai" / "checkpoints")
        super().__init__(checkpoint_manager)
        
        self.config = config
        self.parallel_config = parallel_config or ParallelConfig()
        self.generator = ChapterGenerator(config)
    
    async def generate_batch(
        self,
        start_chapter: int,
        end_chapter: int,
        genre: str = "",
        query: str = "",
        use_rag: bool = False,
        book_analysis: Optional[Dict[str, Any]] = None,
        resume: bool = True,
    ) -> ParallelJob:
        """
        批量生成章节(支持断点续传)
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            genre: 题材
            query: 主题指导
            use_rag: 是否使用RAG
            book_analysis: 样板书分析结果
            resume: 是否从断点恢复
        
        Returns:
            并行任务
        """
        import uuid
        
        task_id = f"batch_{start_chapter}_{end_chapter}_{uuid.uuid4().hex[:8]}"
        chapters = list(range(start_chapter, end_chapter + 1))
        
        # 准备步骤
        steps = [
            {
                "name": f"chapter_{ch}",
                "chapter_num": ch,
                "genre": genre,
                "query": query,
                "use_rag": use_rag,
                "book_analysis": book_analysis,
            }
            for ch in chapters
        ]
        
        # 执行任务
        checkpoint = await self.execute(
            task_id=task_id,
            task_type="batch_generate",
            steps=steps,
            params={
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "genre": genre,
                "query": query,
            },
            resume=resume,
        )
        
        # 构建结果
        job = ParallelJob(
            job_id=task_id,
            chapters=chapters,
            config=self.parallel_config,
            status=checkpoint.status.value,
            start_time=checkpoint.started_at,
            end_time=checkpoint.completed_at,
        )
        
        # 填充结果
        for item in checkpoint.completed_items:
            result_data = item.get("result", {})
            job.results.append(TaskResult(
                task_id=f"{task_id}_ch{result_data.get('chapter_num', 0)}",
                chapter_num=result_data.get("chapter_num", 0),
                status="completed",
                result=GenerationResult(**result_data) if result_data else None,
            ))
        
        for item in checkpoint.failed_items:
            job.results.append(TaskResult(
                task_id=f"{task_id}_ch{item.get('step', '').split('_')[-1]}",
                chapter_num=int(item.get('step', '').split('_')[-1]),
                status="failed",
                error=item.get("error"),
            ))
        
        return job
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        checkpoint,
    ) -> Optional[Dict[str, Any]]:
        """执行单个步骤"""
        chapter_num = step["chapter_num"]
        
        result = await self.generator.generate_chapter(
            chapter_num=chapter_num,
            genre=step.get("genre", ""),
            query=step.get("query", ""),
            use_rag=step.get("use_rag", False),
            book_analysis=step.get("book_analysis"),
        )
        
        if result.success:
            return result.to_dict()
        else:
            raise Exception(result.error_message or "生成失败")
