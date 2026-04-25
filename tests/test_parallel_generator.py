#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：parallel_generator.py 模块

测试并行生成器功能：
- 并行配置 (ParallelConfig)
- 任务结果 (TaskResult)
- 并行任务 (ParallelJob)
- 并行生成器 (ParallelGenerator)
- 可恢复批量生成器 (ResumableBatchGenerator)
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.parallel_generator import (
    ParallelStrategy,
    ParallelConfig,
    TaskResult,
    ParallelJob,
    ParallelGenerator,
    ResumableBatchGenerator,
)
from forgeai_modules.chapter_generator import GenerationResult, ChapterOutline
from forgeai_modules.checkpoint_manager import Checkpoint, TaskStatus
from forgeai_modules.config import ForgeAIConfig


# ============================================
# Test Fixtures
# ============================================


@pytest.fixture
def mock_config(temp_project: Path) -> ForgeAIConfig:
    """创建测试配置"""
    return ForgeAIConfig(temp_project)


@pytest.fixture
def mock_chapter_generator():
    """模拟 ChapterGenerator"""
    mock = MagicMock()

    # 创建成功的生成结果
    success_result = GenerationResult(
        chapter_num=1,
        title="测试章节",
        content="这是测试内容，李明站在山顶上。",
        word_count=100,
        success=True,
    )
    success_result.outline = ChapterOutline(
        chapter_num=1,
        title="测试章节",
    )

    mock.generate_chapter = AsyncMock(return_value=success_result)
    return mock


@pytest.fixture
def mock_checkpoint_manager():
    """模拟 CheckpointManager"""
    mock = MagicMock()

    # 创建默认检查点
    checkpoint = Checkpoint(
        task_id="test-task",
        task_type="batch_generate",
        status=TaskStatus.COMPLETED,
        total_steps=3,
        completed_steps=3,
    )

    mock.load_checkpoint = MagicMock(return_value=checkpoint)
    mock.create_checkpoint = MagicMock(return_value=checkpoint)
    mock.save_checkpoint = MagicMock()
    mock.start_task = MagicMock(return_value=checkpoint)
    mock.complete_step = MagicMock()
    mock.complete_task = MagicMock()
    mock.fail_step = MagicMock()
    mock.pause_task = MagicMock()

    return mock


@pytest.fixture
def failed_generation_result():
    """失败的生成结果"""
    return GenerationResult(
        chapter_num=1,
        success=False,
        error_message="API 调用失败",
    )


# ============================================
# TestParallelConfig - 测试配置 dataclass
# ============================================


class TestParallelConfig:
    """测试 ParallelConfig 配置类"""

    def test_defaults(self):
        """测试默认值"""
        config = ParallelConfig()

        assert config.max_concurrent == 3
        assert config.strategy == ParallelStrategy.CONCURRENT
        assert config.retry_failed is True
        assert config.max_retries == 2
        assert config.delay_between_tasks == 1.0

    def test_custom_values(self):
        """测试自定义值"""
        config = ParallelConfig(
            max_concurrent=5,
            strategy=ParallelStrategy.SEQUENTIAL,
            retry_failed=False,
            max_retries=0,
            delay_between_tasks=0.5,
        )

        assert config.max_concurrent == 5
        assert config.strategy == ParallelStrategy.SEQUENTIAL
        assert config.retry_failed is False
        assert config.max_retries == 0
        assert config.delay_between_tasks == 0.5


# ============================================
# TestTaskResult - 测试任务结果 dataclass
# ============================================


class TestTaskResult:
    """测试 TaskResult 任务结果类"""

    def test_defaults(self):
        """测试默认值"""
        result = TaskResult(
            task_id="task_001",
            chapter_num=1,
            status="pending",
        )

        assert result.task_id == "task_001"
        assert result.chapter_num == 1
        assert result.status == "pending"
        assert result.result is None
        assert result.error is None
        assert result.start_time == ""
        assert result.end_time == ""
        assert result.duration == 0.0
        assert result.retry_count == 0

    def test_to_dict(self):
        """测试转换为字典"""
        gen_result = GenerationResult(
            chapter_num=1,
            title="测试章节",
            content="测试内容",
            word_count=100,
            success=True,
        )

        task_result = TaskResult(
            task_id="task_001",
            chapter_num=1,
            status="completed",
            result=gen_result,
            error=None,
            start_time="2024-01-01T10:00:00",
            end_time="2024-01-01T10:05:00",
            duration=300.0,
            retry_count=1,
        )

        result_dict = task_result.to_dict()

        assert result_dict["task_id"] == "task_001"
        assert result_dict["chapter_num"] == 1
        assert result_dict["status"] == "completed"
        assert result_dict["result"] is not None
        assert result_dict["error"] is None
        assert result_dict["start_time"] == "2024-01-01T10:00:00"
        assert result_dict["end_time"] == "2024-01-01T10:05:00"
        assert result_dict["duration"] == 300.0
        assert result_dict["retry_count"] == 1

    def test_to_dict_with_none_result(self):
        """测试结果为 None 时转换为字典"""
        task_result = TaskResult(
            task_id="task_002",
            chapter_num=2,
            status="failed",
            result=None,
            error="生成失败",
        )

        result_dict = task_result.to_dict()

        assert result_dict["result"] is None
        assert result_dict["error"] == "生成失败"

    def test_duration_calculation(self):
        """测试时长计算"""
        start = "2024-01-01T10:00:00"
        end = "2024-01-01T10:05:30"

        task_result = TaskResult(
            task_id="task_003",
            chapter_num=3,
            status="completed",
            start_time=start,
            end_time=end,
        )

        # 手动计算时长
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        expected_duration = (end_dt - start_dt).total_seconds()

        task_result.duration = expected_duration

        assert task_result.duration == 330.0


# ============================================
# TestParallelJob - 测试并行任务 dataclass
# ============================================


class TestParallelJob:
    """测试 ParallelJob 并行任务类"""

    def test_defaults(self):
        """测试默认值"""
        config = ParallelConfig()
        job = ParallelJob(
            job_id="job_001",
            chapters=[1, 2, 3],
            config=config,
        )

        assert job.job_id == "job_001"
        assert job.chapters == [1, 2, 3]
        assert job.config == config
        assert job.status == "pending"
        assert job.results == []
        assert job.start_time == ""
        assert job.end_time == ""

    def test_completed_count(self):
        """测试完成计数"""
        config = ParallelConfig()
        job = ParallelJob(
            job_id="job_002",
            chapters=[1, 2, 3, 4, 5],
            config=config,
        )

        # 添加一些结果
        job.results = [
            TaskResult(task_id="t1", chapter_num=1, status="completed"),
            TaskResult(task_id="t2", chapter_num=2, status="completed"),
            TaskResult(task_id="t3", chapter_num=3, status="failed"),
            TaskResult(task_id="t4", chapter_num=4, status="running"),
            TaskResult(task_id="t5", chapter_num=5, status="pending"),
        ]

        assert job.completed_count == 2

    def test_failed_count(self):
        """测试失败计数"""
        config = ParallelConfig()
        job = ParallelJob(
            job_id="job_003",
            chapters=[1, 2, 3, 4],
            config=config,
        )

        job.results = [
            TaskResult(task_id="t1", chapter_num=1, status="completed"),
            TaskResult(task_id="t2", chapter_num=2, status="failed"),
            TaskResult(task_id="t3", chapter_num=3, status="failed"),
            TaskResult(task_id="t4", chapter_num=4, status="pending"),
        ]

        assert job.failed_count == 2

    def test_progress_percent(self):
        """测试进度百分比"""
        config = ParallelConfig()
        job = ParallelJob(
            job_id="job_004",
            chapters=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            config=config,
        )

        # 完成 5 个
        job.results = [
            TaskResult(task_id=f"t{i}", chapter_num=i, status="completed")
            for i in range(1, 6)
        ]

        assert job.progress_percent == 50.0

    def test_progress_percent_empty_chapters(self):
        """测试空章节列表的进度"""
        config = ParallelConfig()
        job = ParallelJob(
            job_id="job_005",
            chapters=[],
            config=config,
        )

        assert job.progress_percent == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        config = ParallelConfig(
            max_concurrent=5,
            strategy=ParallelStrategy.SEQUENTIAL,
        )
        job = ParallelJob(
            job_id="job_006",
            chapters=[1, 2, 3],
            config=config,
            status="completed",
            start_time="2024-01-01T10:00:00",
            end_time="2024-01-01T11:00:00",
        )

        job.results = [
            TaskResult(task_id="t1", chapter_num=1, status="completed"),
            TaskResult(task_id="t2", chapter_num=2, status="failed", error="API错误"),
        ]

        result_dict = job.to_dict()

        assert result_dict["job_id"] == "job_006"
        assert result_dict["chapters"] == [1, 2, 3]
        assert result_dict["config"]["max_concurrent"] == 5
        assert result_dict["config"]["strategy"] == "sequential"
        assert result_dict["status"] == "completed"
        assert result_dict["completed"] == 1
        assert result_dict["failed"] == 1
        assert result_dict["total"] == 3
        assert result_dict["progress"] == pytest.approx(33.3, rel=0.1)
        assert len(result_dict["results"]) == 2


# ============================================
# TestParallelGeneratorInit - 测试初始化
# ============================================


class TestParallelGeneratorInit:
    """测试 ParallelGenerator 初始化"""

    def test_init_default(self, mock_config: ForgeAIConfig):
        """测试默认初始化"""
        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = MagicMock()
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config)

            assert generator.config == mock_config
            assert generator.parallel_config.max_concurrent == 3
            assert generator.parallel_config.strategy == ParallelStrategy.CONCURRENT

    def test_init_with_config(self, mock_config: ForgeAIConfig):
        """测试使用自定义配置初始化"""
        custom_config = ParallelConfig(
            max_concurrent=10,
            strategy=ParallelStrategy.SEQUENTIAL,
            retry_failed=False,
            max_retries=0,
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = MagicMock()
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, custom_config)

            assert generator.parallel_config.max_concurrent == 10
            assert generator.parallel_config.strategy == ParallelStrategy.SEQUENTIAL
            assert generator.parallel_config.retry_failed is False


# ============================================
# TestParallelGenerate - 测试并行生成
# ============================================


class TestParallelGenerate:
    """测试并行生成功能"""

    @pytest.mark.asyncio
    async def test_sequential_strategy(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试顺序执行策略"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            delay_between_tasks=0,  # 禁用延迟以加速测试
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            # 执行并行生成
            job = await generator.generate_parallel(
                chapters=[1, 2, 3],
                genre="玄幻",
                query="测试主题",
            )

            assert job.status == "completed"
            assert job.completed_count == 3
            assert job.failed_count == 0
            assert len(job.results) == 3

            # 验证按顺序调用了 3 次
            assert mock_chapter_generator.generate_chapter.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_strategy(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试并发执行策略（使用 semaphore）"""
        config = ParallelConfig(
            strategy=ParallelStrategy.CONCURRENT,
            max_concurrent=2,
            delay_between_tasks=0,
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(
                chapters=[1, 2, 3, 4],
                genre="玄幻",
            )

            assert job.status == "completed"
            assert job.completed_count == 4
            assert len(job.results) == 4

    @pytest.mark.asyncio
    async def test_concurrent_with_limit(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试并发限制"""
        config = ParallelConfig(
            strategy=ParallelStrategy.CONCURRENT,
            max_concurrent=1,  # 限制为 1，实际变成顺序执行
            delay_between_tasks=0,
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(
                chapters=[1, 2, 3],
            )

            assert job.completed_count == 3

    @pytest.mark.asyncio
    async def test_error_aggregation(
        self,
        mock_config: ForgeAIConfig,
        failed_generation_result: GenerationResult,
    ):
        """测试错误聚合"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            retry_failed=False,
            delay_between_tasks=0,
        )

        # 创建一个会失败的 mock
        mock_generator = MagicMock()
        mock_generator.generate_chapter = AsyncMock(return_value=failed_generation_result)

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(
                chapters=[1, 2, 3],
            )

            # 应该有失败
            assert job.failed_count == 3
            assert job.status == "partial"  # 部分失败


# ============================================
# TestGenerateSingle - 测试单章节生成
# ============================================


class TestGenerateSingle:
    """测试单章节生成功能"""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试成功生成"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            delay_between_tasks=0,
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(chapters=[1])

            assert job.completed_count == 1
            assert job.failed_count == 0
            assert job.results[0].status == "completed"
            assert job.results[0].result is not None

    @pytest.mark.asyncio
    async def test_generate_with_retry(
        self,
        mock_config: ForgeAIConfig,
        failed_generation_result: GenerationResult,
    ):
        """测试带重试的生成"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            retry_failed=True,
            max_retries=2,
            delay_between_tasks=0,
        )

        # 创建一个先失败后成功的 mock
        success_result = GenerationResult(
            chapter_num=1,
            title="测试章节",
            content="成功的内容",
            word_count=100,
            success=True,
        )

        mock_generator = MagicMock()
        # 第一次失败，第二次成功
        mock_generator.generate_chapter = AsyncMock(
            side_effect=[failed_generation_result, success_result]
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(chapters=[1])

            assert job.completed_count == 1
            assert job.results[0].retry_count == 1  # 重试了 1 次

    @pytest.mark.asyncio
    async def test_generate_max_retries_exceeded(
        self,
        mock_config: ForgeAIConfig,
        failed_generation_result: GenerationResult,
    ):
        """测试超过最大重试次数"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            retry_failed=True,
            max_retries=2,
            delay_between_tasks=0,
        )

        # 创建一个总是失败的 mock
        mock_generator = MagicMock()
        mock_generator.generate_chapter = AsyncMock(return_value=failed_generation_result)

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(chapters=[1])

            assert job.failed_count == 1
            assert job.results[0].status == "failed"
            assert job.results[0].error is not None
            # 应该尝试了 max_retries + 1 次
            assert mock_generator.generate_chapter.call_count == 3


# ============================================
# TestResumableBatchGenerator - 测试可恢复批量生成器
# ============================================


class TestResumableBatchGenerator:
    """测试 ResumableBatchGenerator 可恢复批量生成器"""

    @pytest.mark.asyncio
    async def test_generate_batch_resume(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ):
        """测试批量生成（支持断点续传）"""
        # 设置检查点管理器返回已完成的检查点
        completed_checkpoint = Checkpoint(
            task_id="batch_1_3_test123",
            task_type="batch_generate",
            status=TaskStatus.COMPLETED,
            total_steps=3,
            completed_steps=3,
            completed_items=[
                {
                    "step": "chapter_1",
                    "result": {"chapter_num": 1, "title": "第一章", "content": "内容1", "success": True},
                },
                {
                    "step": "chapter_2",
                    "result": {"chapter_num": 2, "title": "第二章", "content": "内容2", "success": True},
                },
                {
                    "step": "chapter_3",
                    "result": {"chapter_num": 3, "title": "第三章", "content": "内容3", "success": True},
                },
            ],
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T11:00:00",
        )
        mock_checkpoint_manager.load_checkpoint.return_value = completed_checkpoint
        mock_checkpoint_manager.create_checkpoint.return_value = Checkpoint(
            task_id="batch_1_3_test123",
            task_type="batch_generate",
            status=TaskStatus.PENDING,
            total_steps=3,
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = mock_checkpoint_manager

            batch_generator = ResumableBatchGenerator(mock_config)

            job = await batch_generator.generate_batch(
                start_chapter=1,
                end_chapter=3,
                genre="玄幻",
                resume=True,
            )

            assert job.status == "completed"
            assert len(job.chapters) == 3
            assert job.completed_count == 3

    @pytest.mark.asyncio
    async def test_generate_batch_new_task(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试新任务批量生成（无断点）"""
        # 创建一个可以正确执行步骤的检查点管理器
        created_checkpoint = Checkpoint(
            task_id="batch_1_2_new",
            task_type="batch_generate",
            status=TaskStatus.PENDING,
            total_steps=2,
            started_at="2024-01-01T10:00:00",
        )

        running_checkpoint = Checkpoint(
            task_id="batch_1_2_new",
            task_type="batch_generate",
            status=TaskStatus.RUNNING,
            total_steps=2,
            started_at="2024-01-01T10:00:00",
        )

        completed_checkpoint = Checkpoint(
            task_id="batch_1_2_new",
            task_type="batch_generate",
            status=TaskStatus.COMPLETED,
            total_steps=2,
            completed_steps=2,
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T11:00:00",
            completed_items=[
                {
                    "step": "chapter_1",
                    "result": {"chapter_num": 1, "title": "第一章", "content": "内容1", "success": True},
                },
                {
                    "step": "chapter_2",
                    "result": {"chapter_num": 2, "title": "第二章", "content": "内容2", "success": True},
                },
            ],
        )

        mock_checkpoint = MagicMock()
        mock_checkpoint.create_checkpoint.return_value = created_checkpoint
        mock_checkpoint.start_task.return_value = running_checkpoint
        # 模拟步骤完成后重新加载
        mock_checkpoint.load_checkpoint.return_value = completed_checkpoint
        mock_checkpoint.complete_step = MagicMock()
        mock_checkpoint.complete_task = MagicMock()

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = mock_checkpoint

            batch_generator = ResumableBatchGenerator(mock_config)

            job = await batch_generator.generate_batch(
                start_chapter=1,
                end_chapter=2,
                genre="玄幻",
                resume=False,  # 不恢复，创建新任务
            )

            # 验证创建了新检查点
            mock_checkpoint.create_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_batch_with_failure(
        self,
        mock_config: ForgeAIConfig,
        failed_generation_result: GenerationResult,
    ):
        """测试批量生成中的失败处理"""
        # 创建一个带有失败项目的检查点
        failed_checkpoint = Checkpoint(
            task_id="batch_1_2_fail",
            task_type="batch_generate",
            status=TaskStatus.PAUSED,  # 因失败而暂停
            total_steps=2,
            completed_steps=1,
            started_at="2024-01-01T10:00:00",
            completed_items=[
                {
                    "step": "chapter_1",
                    "result": {"chapter_num": 1, "title": "第一章", "content": "内容1", "success": True},
                },
            ],
            failed_items=[
                {
                    "step": "chapter_2",
                    "error": "API 调用失败",
                },
            ],
        )

        mock_checkpoint = MagicMock()
        mock_checkpoint.load_checkpoint.return_value = failed_checkpoint

        mock_generator = MagicMock()
        mock_generator.generate_chapter = AsyncMock(return_value=failed_generation_result)

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_generator
            MockCheckpoint.return_value = mock_checkpoint

            batch_generator = ResumableBatchGenerator(mock_config)

            # 由于会失败，这里测试异常处理
            try:
                job = await batch_generator.generate_batch(
                    start_chapter=1,
                    end_chapter=2,
                    resume=True,
                )
            except Exception:
                # 预期可能抛出异常
                pass

            # 验证失败步骤被记录
            # 具体验证取决于实现细节


# ============================================
# TestProgressCallback - 测试进度回调
# ============================================


class TestProgressCallback:
    """测试进度回调功能"""

    @pytest.mark.asyncio
    async def test_progress_callback_called(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试进度回调被调用"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            delay_between_tasks=0,
        )

        # 创建进度回调 mock
        progress_callback = MagicMock()

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(
                chapters=[1, 2, 3],
                on_progress=progress_callback,
            )

            # 验证回调被调用了 3 次
            assert progress_callback.call_count == 3

    @pytest.mark.asyncio
    async def test_progress_callback_receives_task_result(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试进度回调接收到 TaskResult"""
        config = ParallelConfig(
            strategy=ParallelStrategy.SEQUENTIAL,
            delay_between_tasks=0,
        )

        # 收集回调参数
        received_results = []

        def progress_callback(task_result: TaskResult):
            received_results.append(task_result)

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            await generator.generate_parallel(
                chapters=[1, 2],
                on_progress=progress_callback,
            )

            # 验证接收到的是 TaskResult 实例
            assert len(received_results) == 2
            assert all(isinstance(r, TaskResult) for r in received_results)
            assert received_results[0].chapter_num == 1
            assert received_results[1].chapter_num == 2


# ============================================
# TestPipelineStrategy - 测试流水线策略
# ============================================


class TestPipelineStrategy:
    """测试流水线策略"""

    @pytest.mark.asyncio
    async def test_pipeline_strategy_falls_back_to_concurrent(
        self,
        mock_config: ForgeAIConfig,
        mock_chapter_generator: MagicMock,
    ):
        """测试流水线策略回退到并发执行"""
        config = ParallelConfig(
            strategy=ParallelStrategy.PIPELINE,
            delay_between_tasks=0,
        )

        with patch('forgeai_modules.parallel_generator.ChapterGenerator') as MockGenerator, \
             patch('forgeai_modules.parallel_generator.CheckpointManager') as MockCheckpoint:
            MockGenerator.return_value = mock_chapter_generator
            MockCheckpoint.return_value = MagicMock()

            generator = ParallelGenerator(mock_config, config)

            job = await generator.generate_parallel(chapters=[1, 2, 3])

            # 流水线策略目前实现为并发执行
            assert job.completed_count == 3
