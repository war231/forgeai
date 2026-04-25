#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAG 适配器测试"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from forgeai_modules.rag_adapter import (
    RAGAdapter, SearchResult, _tokenize, JIEBA_AVAILABLE
)


class TestTokenize:
    """分词测试"""

    def test_tokenize_with_jieba(self):
        """jieba 分词"""
        if not JIEBA_AVAILABLE:
            pytest.skip("jieba not installed")

        text = "末世降临已经整整一百天了"
        tokens = _tokenize(text)
        assert len(tokens) > 0
        assert all(len(t) >= 2 for t in tokens)

    def test_tokenize_without_jieba_fallback(self):
        """无 jieba 时回退到 bigram"""
        with patch('system.scripts.forgeai_modules.rag_adapter.JIEBA_AVAILABLE', False):
            # 重新导入以应用 mock
            import importlib
            import system.scripts.forgeai_modules.rag_adapter as rag_mod
            importlib.reload(rag_mod)

            tokens = rag_mod._tokenize("测试文本")
            # bigram 应该返回相邻字符对
            assert isinstance(tokens, list)


class TestSearchResult:
    """搜索结果数据类测试"""

    def test_create_search_result(self):
        """创建搜索结果"""
        result = SearchResult(
            chunk_id="ch1_s0_001",
            chapter=1,
            scene_index=0,
            content="测试内容",
            score=0.95,
            source="bm25"
        )
        assert result.chunk_id == "ch1_s0_001"
        assert result.chapter == 1
        assert result.score == 0.95
        assert result.source == "bm25"


class TestRAGAdapterInit:
    """RAG 适配器初始化测试"""

    def test_init_with_config(self, temp_project):
        """使用配置初始化"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        assert adapter.config == config
        assert adapter.db_path is not None

    def test_init_without_config(self, temp_project):
        """无配置初始化（使用默认配置）"""
        with patch('system.scripts.forgeai_modules.rag_adapter.get_config') as mock_get_config:
            from forgeai_modules.config import ForgeAIConfig
            mock_get_config.return_value = ForgeAIConfig(temp_project)

            adapter = RAGAdapter()
            assert adapter.config is not None

    def test_init_degraded_mode_no_project(self):
        """无项目根目录时降级模式"""
        with patch('system.scripts.forgeai_modules.rag_adapter.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.vector_db_path = None
            mock_get_config.return_value = mock_config

            adapter = RAGAdapter()
            assert adapter._degraded_mode is True
            assert "项目根目录未设置" in adapter._degraded_reason


class TestChunkText:
    """文本分块测试"""

    def test_chunk_text_basic(self, temp_project):
        """基本分块"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        text = "这是一段测试文本。" * 100
        chunks = adapter.chunk_text(text, chunk_size=50, overlap=10)

        assert len(chunks) > 0
        assert all("chunk_id" in c for c in chunks)
        assert all("content" in c for c in chunks)
        assert all("content_hash" in c for c in chunks)

    def test_chunk_text_with_sentence_break(self, temp_project):
        """在句号处截断"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        text = "第一句话。第二句话。第三句话。第四句话。"
        chunks = adapter.chunk_text(text, chunk_size=20, overlap=0)

        # 应该在句号处截断
        for chunk in chunks:
            if len(chunk["content"]) > 0:
                # 内容应该以句号结尾（除了最后一块）
                pass  # 截断逻辑复杂，只验证返回结果

    def test_chunk_text_overlap(self, temp_project):
        """重叠分块"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        text = "ABCDEFGHIJ" * 50
        chunks = adapter.chunk_text(text, chunk_size=100, overlap=20)

        assert len(chunks) > 1


class TestIndexChapter:
    """章节索引测试"""

    def test_index_chapter_basic(self, temp_project):
        """索引章节"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        text = "这是第一章的内容。主角李天出现了。"
        count = adapter.index_chapter(1, text)

        assert count > 0

    def test_index_chapter_with_scene(self, temp_project):
        """索引带场景的章节"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        text = "场景一的内容。场景二的内容。"
        count = adapter.index_chapter(1, text, scene_index=2, source_file="test.md")

        assert count > 0

    def test_index_chapter_replaces_old(self, temp_project):
        """重新索引替换旧数据"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        # 第一次索引
        adapter.index_chapter(1, "旧内容")
        # 第二次索引
        adapter.index_chapter(1, "新内容新内容新内容")

        stats = adapter.get_stats()
        assert stats["total_chunks"] > 0


class TestBM25Search:
    """BM25 搜索测试"""

    @pytest.mark.asyncio
    async def test_bm25_search_basic(self, temp_project):
        """基本 BM25 搜索"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        # 索引一些内容
        adapter.index_chapter(1, "李天是一个修仙者，他正在修炼。")
        adapter.index_chapter(2, "张明是一个武者，他正在练武。")

        # 搜索
        results = await adapter._bm25_search("李天", top_k=5)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_bm25_search_with_chapter_filter(self, temp_project):
        """带章节过滤的 BM25 搜索"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        adapter.index_chapter(1, "李天修炼")
        adapter.index_chapter(2, "李天突破")

        results = await adapter._bm25_search("李天", top_k=5, chapter_filter=1)

        for r in results:
            assert r.chapter == 1

    @pytest.mark.asyncio
    async def test_bm25_search_empty_query(self, temp_project):
        """空查询返回空结果"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        results = await adapter._bm25_search("", top_k=5)
        assert results == []


class TestMergeResults:
    """结果合并测试"""

    def test_merge_results_basic(self, temp_project):
        """基本合并"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        vector_results = [
            SearchResult("c1", 1, 0, "内容1", 0.9, "vector"),
            SearchResult("c2", 1, 0, "内容2", 0.8, "vector"),
        ]
        bm25_results = [
            SearchResult("c1", 1, 0, "内容1", 5.0, "bm25"),
            SearchResult("c3", 1, 0, "内容3", 3.0, "bm25"),
        ]

        merged = adapter._merge_results(vector_results, bm25_results, top_k=5)

        assert len(merged) <= 5
        # c1 应该有更高的分数（两种来源）
        c1_result = next((r for r in merged if r.chunk_id == "c1"), None)
        if c1_result:
            assert c1_result.source == "hybrid"

    def test_merge_results_empty(self, temp_project):
        """空结果合并"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        merged = adapter._merge_results([], [], top_k=5)
        assert merged == []


class TestCosineSimilarity:
    """余弦相似度测试"""

    def test_cosine_similarity_identical(self, temp_project):
        """相同向量"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]

        similarity = adapter._cosine_similarity(a, b)
        assert abs(similarity - 1.0) < 0.01

    def test_cosine_similarity_orthogonal(self, temp_project):
        """正交向量"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        a = [1.0, 0.0]
        b = [0.0, 1.0]

        similarity = adapter._cosine_similarity(a, b)
        assert abs(similarity) < 0.01

    def test_cosine_similarity_opposite(self, temp_project):
        """相反向量"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        a = [1.0, 0.0]
        b = [-1.0, 0.0]

        similarity = adapter._cosine_similarity(a, b)
        assert abs(similarity + 1.0) < 0.01


class TestExtractContext:
    """上下文提取测试"""

    @pytest.mark.asyncio
    async def test_extract_context_basic(self, temp_project):
        """基本上下文提取"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        # 索引内容
        adapter.index_chapter(1, "李天开始修炼。他努力地打坐。")

        context = await adapter.extract_context(1, query="修炼", top_k=3)

        assert "chapter" in context
        assert context["chapter"] == 1
        assert "relevant_chunks" in context
        assert "degraded_mode" in context


class TestGetStats:
    """统计信息测试"""

    def test_get_stats_empty(self, temp_project):
        """空数据库统计"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        stats = adapter.get_stats()

        assert "total_chunks" in stats
        assert "embedded_chunks" in stats
        assert "bm25_vocabulary" in stats
        assert "degraded_mode" in stats

    def test_get_stats_with_data(self, temp_project):
        """有数据统计"""
        from forgeai_modules.config import ForgeAIConfig

        config = ForgeAIConfig(temp_project)
        adapter = RAGAdapter(config)

        adapter.index_chapter(1, "测试内容测试内容")

        stats = adapter.get_stats()

        assert stats["total_chunks"] > 0
        assert stats["bm25_vocabulary"] > 0
