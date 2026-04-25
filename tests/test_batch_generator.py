#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成器单元测试
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from forgeai_modules.batch_generator import (
    BatchJob,
    BatchGenerator,
    GenerationResult,
)


class TestBatchJob:
    """测试 BatchJob dataclass"""

    def test_defaults(self):
        """测试默认值"""
        job = BatchJob(
            job_id="test123",
            start_chapter=1,
            end_chapter=5,
        )
        assert job.status == "pending"
        assert job.progress == 0
        assert job.total == 0
        assert job.results == []
        assert job.errors == []
        assert job.start_time == ""
        assert job.end_time == ""

    def test_to_dict(self):
        """测试转换为字典"""
        job = BatchJob(
            job_id="test456",
            start_chapter=1,
            end_chapter=3,
            status="running",
            progress=2,
            total=3,
            results=[
                GenerationResult(chapter_num=1, title="第一章", content="内容1", word_count=1000),
                GenerationResult(chapter_num=2, title="第二章", content="内容2", word_count=1200),
            ],
            errors=[{"chapter": 3, "error": "测试错误"}],
            start_time="2024-01-01T10:00:00",
            end_time="",
        )
        result = job.to_dict()
        assert result["job_id"] == "test456"
        assert result["start_chapter"] == 1
        assert result["end_chapter"] == 3
        assert result["status"] == "running"
        assert result["progress"] == 2
        assert result["total"] == 3
        assert result["completed"] == 2
        assert result["errors"] == 1
        assert result["start_time"] == "2024-01-01T10:00:00"


class TestBatchGeneratorInit:
    """测试初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        mock_config = MagicMock()
        with patch('forgeai_modules.batch_generator.ChapterGenerator') as MockGenerator:
            with patch('forgeai_modules.batch_generator.Pipeline') as MockPipeline:
                with patch('forgeai_modules.batch_generator.get_config') as mock_get_config:
                    mock_get_config.return_value = mock_config

                    generator = BatchGenerator()

                    mock_get_config.assert_called_once()
                    # ChapterGenerator receives the config from get_config()
                    MockGenerator.assert_called_once()
                    MockPipeline.assert_called_once()

    def test_init_with_config(self):
        """测试使用配置初始化"""
        mock_config = MagicMock()
        with patch('forgeai_modules.batch_generator.ChapterGenerator') as MockGenerator:
            with patch('forgeai_modules.batch_generator.Pipeline') as MockPipeline:
                generator = BatchGenerator(config=mock_config)

                MockGenerator.assert_called_once_with(mock_config)
                MockPipeline.assert_called_once_with(mock_config)


class TestGenerateBatch:
    """测试批量生成"""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, tmp_path):
        """测试批量生成成功"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator') as MockGenerator:
            with patch('forgeai_modules.batch_generator.Pipeline') as MockPipeline:
                # 模拟 ChapterGenerator
                mock_generator = MagicMock()
                mock_generator.generate_chapter = AsyncMock()
                mock_generator.generate_chapter.side_effect = [
                    GenerationResult(chapter_num=1, title="第一章", content="内容1", word_count=1000, success=True),
                    GenerationResult(chapter_num=2, title="第二章", content="内容2", word_count=1200, success=True),
                ]
                MockGenerator.return_value = mock_generator

                # 模拟 Pipeline
                mock_pipeline = MagicMock()
                mock_pipeline.post_write = AsyncMock(return_value={"steps": {"review": "passed"}})
                MockPipeline.return_value = mock_pipeline

                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()
                    job = await generator.generate_batch(
                        start_chapter=1,
                        end_chapter=2,
                        genre="玄幻",
                        query="修仙之路",
                        output_dir=tmp_path,
                    )

                assert job.status == "completed"
                assert job.progress == 2
                assert job.total == 2
                assert len(job.results) == 2
                assert len(job.errors) == 0

    @pytest.mark.asyncio
    async def test_batch_generate_partial_failure(self, tmp_path):
        """测试部分章节失败"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator') as MockGenerator:
            with patch('forgeai_modules.batch_generator.Pipeline') as MockPipeline:
                # 模拟 ChapterGenerator - 第2章失败
                mock_generator = MagicMock()
                mock_generator.generate_chapter = AsyncMock()
                mock_generator.generate_chapter.side_effect = [
                    GenerationResult(chapter_num=1, title="第一章", content="内容1", word_count=1000, success=True),
                    GenerationResult(chapter_num=2, title="", content="", word_count=0, success=False, error_message="生成失败"),
                ]
                MockGenerator.return_value = mock_generator

                mock_pipeline = MagicMock()
                mock_pipeline.post_write = AsyncMock(return_value={"steps": {}})
                MockPipeline.return_value = mock_pipeline

                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()
                    job = await generator.generate_batch(
                        start_chapter=1,
                        end_chapter=2,
                        output_dir=tmp_path,
                    )

                assert job.status == "partial"
                assert job.progress == 1
                assert len(job.results) == 1
                assert len(job.errors) == 1
                assert job.errors[0]["chapter"] == 2

    @pytest.mark.asyncio
    async def test_batch_generate_all_failed(self, tmp_path):
        """测试全部失败"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator') as MockGenerator:
            with patch('forgeai_modules.batch_generator.Pipeline') as MockPipeline:
                # 模拟 ChapterGenerator - 全部失败
                mock_generator = MagicMock()
                mock_generator.generate_chapter = AsyncMock()
                mock_generator.generate_chapter.side_effect = [
                    GenerationResult(chapter_num=1, title="", content="", word_count=0, success=False, error_message="错误1"),
                    GenerationResult(chapter_num=2, title="", content="", word_count=0, success=False, error_message="错误2"),
                ]
                MockGenerator.return_value = mock_generator

                mock_pipeline = MagicMock()
                MockPipeline.return_value = mock_pipeline

                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()
                    job = await generator.generate_batch(
                        start_chapter=1,
                        end_chapter=2,
                        output_dir=tmp_path,
                    )

                assert job.status == "failed"
                assert job.progress == 0
                assert len(job.results) == 0
                assert len(job.errors) == 2

    @pytest.mark.asyncio
    async def test_batch_with_progress_callback(self, tmp_path):
        """测试进度回调"""
        progress_calls = []

        def on_progress(job):
            progress_calls.append({
                "progress": job.progress,
                "total": job.total,
            })

        with patch('forgeai_modules.batch_generator.ChapterGenerator') as MockGenerator:
            with patch('forgeai_modules.batch_generator.Pipeline') as MockPipeline:
                mock_generator = MagicMock()
                mock_generator.generate_chapter = AsyncMock()
                mock_generator.generate_chapter.side_effect = [
                    GenerationResult(chapter_num=1, title="第一章", content="内容1", word_count=1000, success=True),
                    GenerationResult(chapter_num=2, title="第二章", content="内容2", word_count=1200, success=True),
                ]
                MockGenerator.return_value = mock_generator

                mock_pipeline = MagicMock()
                mock_pipeline.post_write = AsyncMock(return_value={"steps": {}})
                MockPipeline.return_value = mock_pipeline

                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()
                    job = await generator.generate_batch(
                        start_chapter=1,
                        end_chapter=2,
                        on_progress=on_progress,
                    )

                assert len(progress_calls) == 2
                assert progress_calls[0]["progress"] == 1
                assert progress_calls[1]["progress"] == 2


class TestSaveChapter:
    """测试章节保存"""

    def test_save_chapter_creates_file(self, tmp_path):
        """测试保存章节创建文件"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator'):
            with patch('forgeai_modules.batch_generator.Pipeline'):
                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()
                    result = GenerationResult(
                        chapter_num=5,
                        title="第五章 测试标题",
                        content="这是测试内容。\n\n第二段落。",
                        word_count=100,
                    )

                    generator._save_chapter(result, tmp_path)

                    output_file = tmp_path / "第5章.md"
                    assert output_file.exists()

    def test_save_chapter_content_format(self, tmp_path):
        """测试章节内容格式"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator'):
            with patch('forgeai_modules.batch_generator.Pipeline'):
                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()
                    result = GenerationResult(
                        chapter_num=1,
                        title="第一章 开始",
                        content="李明站在山顶上，望着远方。\n\n风吹过他的脸庞。",
                        word_count=50,
                    )

                    generator._save_chapter(result, tmp_path)

                    output_file = tmp_path / "第1章.md"
                    content = output_file.read_text(encoding="utf-8")

                    assert content.startswith("# 第一章 开始")
                    assert "李明站在山顶上" in content
                    assert "\n\n" in content  # 标题与内容之间有空行


class TestExportResults:
    """测试结果导出"""

    def test_export_results_creates_files(self, tmp_path):
        """测试导出结果创建文件"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator'):
            with patch('forgeai_modules.batch_generator.Pipeline'):
                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()

                    job = BatchJob(
                        job_id="export_test",
                        start_chapter=1,
                        end_chapter=2,
                        status="completed",
                        progress=2,
                        total=2,
                        results=[
                            GenerationResult(chapter_num=1, title="第一章", content="内容1", word_count=1000),
                            GenerationResult(chapter_num=2, title="第二章", content="内容2", word_count=1200),
                        ],
                        start_time="2024-01-01T10:00:00",
                        end_time="2024-01-01T11:00:00",
                    )

                    exported = generator.export_results(job, tmp_path)

                    assert "chapter_1" in exported
                    assert "chapter_2" in exported
                    assert "stats" in exported
                    assert Path(exported["chapter_1"]).exists()
                    assert Path(exported["chapter_2"]).exists()

    def test_export_stats_json(self, tmp_path):
        """测试导出统计JSON"""
        with patch('forgeai_modules.batch_generator.ChapterGenerator'):
            with patch('forgeai_modules.batch_generator.Pipeline'):
                with patch('forgeai_modules.batch_generator.get_config'):
                    generator = BatchGenerator()

                    job = BatchJob(
                        job_id="stats_test",
                        start_chapter=1,
                        end_chapter=3,
                        status="partial",
                        progress=2,
                        total=3,
                        results=[
                            GenerationResult(chapter_num=1, title="第一章", content="内容1", word_count=1000),
                            GenerationResult(chapter_num=2, title="第二章", content="内容2", word_count=1200),
                        ],
                        errors=[{"chapter": 3, "error": "失败"}],
                        start_time="2024-01-01T10:00:00",
                        end_time="2024-01-01T11:00:00",
                    )

                    exported = generator.export_results(job, tmp_path)

                    stats_file = Path(exported["stats"])
                    assert stats_file.exists()

                    with open(stats_file, encoding="utf-8") as f:
                        stats = json.load(f)

                    assert stats["job_id"] == "stats_test"
                    assert stats["status"] == "partial"
                    assert stats["total"] == 3
                    assert stats["completed"] == 2
                    assert stats["errors"] == 1
                    assert len(stats["chapters"]) == 2
                    assert stats["chapters"][0]["chapter"] == 1
                    assert stats["chapters"][0]["title"] == "第一章"
                    assert stats["chapters"][0]["word_count"] == 1000
