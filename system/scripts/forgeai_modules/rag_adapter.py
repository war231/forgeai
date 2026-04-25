#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 适配器 - 向量 + BM25 混合检索

设计目标：
- 向量检索：基于 Embedding API 的语义搜索
- BM25 检索：基于 jieba 分词的关键词搜索
- 混合检索：加权融合两种结果
- 降级模式：无 API Key 时自动降级为纯 BM25
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import sqlite3
import hashlib
import time
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from dataclasses import dataclass

from .config import get_config, ForgeAIConfig
from .index_manager import IndexManager

# 初始化日志
logger = logging.getLogger(__name__)

try:
    import jieba
    JIEBA_AVAILABLE = True
    # 抑制 jieba 初始化日志
    import logging as _logging
    jieba.setLogLevel(_logging.WARNING)
except ImportError:
    JIEBA_AVAILABLE = False


def _tokenize(text: str) -> List[str]:
    """分词：优先 jieba，回退到 bigram"""
    if JIEBA_AVAILABLE:
        return [t for t in jieba.cut(text) if len(t.strip()) >= 2]
    # 回退：bigram（每两个字符为一个词）
    chars = [c for c in text if c.strip()]
    return [chars[i] + chars[i+1] for i in range(len(chars) - 1)]

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


@dataclass
class SearchResult:
    """搜索结果"""
    chunk_id: str
    chapter: int
    scene_index: int
    content: str
    score: float
    source: str  # "vector" | "bm25" | "hybrid"


class RAGCache:
    """RAG 检索结果缓存（LRU）"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: List[str] = []  # LRU 队列
        self._max_size = max_size
        self._ttl = ttl
    
    def _get_key(self, query: str, top_k: int, filters: dict) -> str:
        """生成缓存键"""
        filter_str = str(sorted(filters.items())) if filters else ""
        key_data = f"{query}_{top_k}_{filter_str}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, query: str, top_k: int, filters: dict = None) -> Optional[list]:
        """从缓存获取结果"""
        key = self._get_key(query, top_k, filters or {})
        
        if key in self._cache:
            # 检查 TTL
            if time.time() - self._timestamps[key] < self._ttl:
                logger.debug(f"RAG 缓存命中：{key[:8]}")
                # 更新访问顺序（LRU）
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            else:
                # 过期，删除
                self._remove(key)
        
        return None
    
    def set(self, query: str, top_k: int, result: list, filters: dict = None):
        """保存结果到缓存"""
        key = self._get_key(query, top_k, filters or {})
        
        # 检查缓存大小，超过则删除最旧的
        if len(self._cache) >= self._max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._remove(oldest_key)
        
        self._cache[key] = result
        self._timestamps[key] = time.time()
        self._access_order.append(key)
        logger.debug(f"RAG 缓存保存：{key[:8]}")
    
    def _remove(self, key: str):
        """删除缓存条目"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()
        self._access_order.clear()
        logger.info("RAG 缓存已清空")


class RAGAdapter:
    """RAG 检索适配器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.index_manager = IndexManager(self.config)
        self._degraded_mode: bool = False
        self._degraded_reason: str = ""
        
        # 初始化缓存
        cache_enabled = self.config.get("rag.cache_enabled", True)
        cache_ttl = self.config.get("rag.cache_ttl", 300)
        cache_max_size = self.config.get("rag.cache_max_size", 1000)
        self.cache = RAGCache(max_size=cache_max_size, ttl=cache_ttl) if cache_enabled else None
        
        self._init_db()

    @property
    def db_path(self) -> Optional[Path]:
        return self.config.vector_db_path

    def _init_db(self) -> None:
        """初始化向量数据库"""
        if not self.db_path:
            self._degraded_mode = True
            self._degraded_reason = "项目根目录未设置"
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    chapter INTEGER NOT NULL,
                    scene_index INTEGER DEFAULT 0,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    chunk_type TEXT DEFAULT 'scene',
                    source_file TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    embedding BLOB,
                    model TEXT DEFAULT '',
                    dimension INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
                );

                CREATE TABLE IF NOT EXISTS bm25_index (
                    chunk_id TEXT NOT NULL,
                    term TEXT NOT NULL,
                    tf INTEGER DEFAULT 1,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id),
                    PRIMARY KEY (chunk_id, term)
                );

                CREATE TABLE IF NOT EXISTS bm25_stats (
                    key TEXT PRIMARY KEY,
                    value REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_chapter ON chunks(chapter);
                CREATE INDEX IF NOT EXISTS idx_bm25_term ON bm25_index(term);
            """)
            conn.commit()
        finally:
            conn.close()

        # 检查降级条件 - 自动从 .env 加载配置
        from .env_loader import get_embed_config
        embed_config = get_embed_config()
        api_key = embed_config.get("api_key")
        
        if not api_key:
            self._degraded_mode = True
            self._degraded_reason = "未配置 Embedding API Key，降级为纯 BM25"

    # ---- 分块 ----

    def chunk_text(self, text: str, chunk_size: int = 0,
                   overlap: int = 0) -> List[Dict[str, Any]]:
        """将文本分块"""
        chunk_size = chunk_size or self.config.get("rag.chunk_size", 500)
        overlap = overlap or self.config.get("rag.chunk_overlap", 100)

        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            # 在句号/换行处截断
            for sep in ["\n\n", "。", "！", "？", "\n"]:
                pos = chunk_text.rfind(sep)
                if pos > chunk_size // 2:
                    chunk_text = chunk_text[:pos + len(sep)]
                    end = start + pos + len(sep)
                    break

            content_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()
            chunks.append({
                "chunk_id": f"chunk_{idx:06d}",
                "content": chunk_text.strip(),
                "content_hash": content_hash,
                "chunk_type": "scene",
                "char_start": start,
                "char_end": end,
            })
            start = end - overlap
            idx += 1

        return chunks

    def index_chapter(self, chapter: int, text: str,
                      scene_index: int = 0, source_file: str = "") -> int:
        """索引一个章节的文本"""
        chunks = self.chunk_text(text)
        conn = sqlite3.connect(str(self.db_path))
        try:
            # 删除旧索引
            conn.execute("DELETE FROM chunks WHERE chapter = ? AND scene_index = ?",
                        (chapter, scene_index))

            for i, chunk in enumerate(chunks):
                chunk_id = f"ch{chapter}_s{scene_index}_{i:03d}"
                conn.execute("""
                    INSERT OR REPLACE INTO chunks
                        (chunk_id, chapter, scene_index, content, content_hash,
                         chunk_type, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (chunk_id, chapter, scene_index, chunk["content"],
                      chunk["content_hash"], chunk["chunk_type"], source_file))

                # BM25 索引
                self._index_bm25(conn, chunk_id, chunk["content"])

            conn.commit()
            return len(chunks)
        finally:
            conn.close()
    
    def batch_index(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量索引文档"""
        if not documents:
            return {"indexed": 0, "errors": []}
        
        start_time = time.time()
        indexed_count = 0
        errors = []
        
        # 批量处理
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    for j, doc in enumerate(batch):
                        chunk_id = doc.get('id', f'doc_{i+j}')
                        content = doc.get('content', '')
                        chapter = doc.get('chapter', 0)
                        scene_index = doc.get('scene_index', 0)
                        metadata = doc.get('metadata', {})
                        
                        conn.execute("""
                            INSERT OR REPLACE INTO chunks
                                (chunk_id, chapter, scene_index, content, content_hash,
                                 chunk_type, source_file)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (chunk_id, chapter, scene_index, content,
                              hashlib.md5(content.encode('utf-8')).hexdigest(),
                              metadata.get('chunk_type', 'scene'),
                              metadata.get('source_file', '')))
                        
                        # BM25 索引
                        self._index_bm25(conn, chunk_id, content)
                    
                    conn.commit()
                    indexed_count += len(batch)
                    logger.debug(f"批量索引：{indexed_count}/{len(documents)}")
                    
                finally:
                    conn.close()
                
            except Exception as e:
                error_msg = f"批量索引失败（批次 {i//batch_size}）：{e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        elapsed = time.time() - start_time
        logger.info(f"批量索引完成：{indexed_count} 个文档，耗时 {elapsed:.2f}s")
        
        return {
            "indexed": indexed_count,
            "errors": errors,
            "elapsed": elapsed
        }

    def _index_bm25(self, conn: sqlite3.Connection,
                     chunk_id: str, text: str) -> None:
        """建立 BM25 索引"""
        terms = _tokenize(text)
        term_freq = Counter(terms)
        for term, freq in term_freq.items():
            conn.execute("""
                INSERT OR REPLACE INTO bm25_index (chunk_id, term, tf)
                VALUES (?, ?, ?)
            """, (chunk_id, term, freq))

        # 更新文档数
        conn.execute("""
            INSERT OR REPLACE INTO bm25_stats (key, value)
            VALUES ('total_docs', COALESCE(
                (SELECT value FROM bm25_stats WHERE key = 'total_docs'), 0) + 1)
        """)

    # ---- 向量嵌入 ----

    async def _get_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """调用 Embedding API 获取向量"""
        if self._degraded_mode:
            return None

        # 自动从 .env 加载配置
        from .env_loader import get_embed_config
        embed_config = get_embed_config()
        
        api_key = embed_config.get("api_key")
        base_url = embed_config.get("base_url") or "https://api.openai.com/v1"
        model = embed_config.get("model") or "text-embedding-3-small"

        if not api_key or not AIOHTTP_AVAILABLE:
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": texts,
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{base_url}/embeddings"
                async with session.post(url, json=payload, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    embeddings = [d["embedding"] for d in data["data"]]
                    return embeddings
        except Exception:
            return None

    async def _store_embeddings(self, chunk_ids: List[str],
                                 embeddings: List[List[float]]) -> None:
        """存储向量"""
        model = self.config.get("embedding.model", "text-embedding-3-small")
        dimension = len(embeddings[0]) if embeddings else 0

        conn = sqlite3.connect(str(self.db_path))
        try:
            for chunk_id, emb in zip(chunk_ids, embeddings):
                emb_blob = json.dumps(emb).encode("utf-8")
                conn.execute("""
                    INSERT OR REPLACE INTO embeddings (chunk_id, embedding, model, dimension)
                    VALUES (?, ?, ?, ?)
                """, (chunk_id, emb_blob, model, dimension))
            conn.commit()
        finally:
            conn.close()

    # ---- 搜索 ----

    async def search(self, query: str, top_k: int = 0,
                     chapter_filter: Optional[int] = None) -> List[SearchResult]:
        """混合搜索（向量 + BM25）"""
        start_time = time.time()
        top_k = top_k or self.config.get("rag.top_k", 10)
        
        # 1. 检查缓存
        if self.cache:
            cached = self.cache.get(query, top_k, {"chapter": chapter_filter})
            if cached:
                elapsed = time.time() - start_time
                logger.info(f"RAG 检索（缓存）：耗时 {elapsed:.2f}s")
                return cached

        if self._degraded_mode:
            results = await self._bm25_search(query, top_k, chapter_filter)
            # 保存缓存
            if self.cache:
                self.cache.set(query, top_k, results, {"chapter": chapter_filter})
            return results

        # 2. 并行执行两种搜索
        try:
            vector_results, bm25_results = await asyncio.gather(
                self._vector_search(query, top_k * 2, chapter_filter),
                self._bm25_search(query, top_k * 2, chapter_filter),
            )

            # 混合排序
            results = self._merge_results(vector_results, bm25_results, top_k)
            
            # 3. 保存缓存
            if self.cache:
                self.cache.set(query, top_k, results, {"chapter": chapter_filter})
            
            elapsed = time.time() - start_time
            logger.info(f"RAG 检索完成：耗时 {elapsed:.2f}s，返回 {len(results)} 条结果")
            
            return results
            
        except Exception as e:
            logger.error(f"RAG 检索失败：{e}")
            return []

    async def _vector_search(self, query: str, top_k: int,
                              chapter_filter: Optional[int] = None) -> List[SearchResult]:
        """向量搜索"""
        embeddings = await self._get_embeddings([query])
        if not embeddings:
            return []

        query_vec = embeddings[0]
        conn = sqlite3.connect(str(self.db_path))
        try:
            sql = "SELECT c.chunk_id, c.chapter, c.scene_index, c.content, e.embedding FROM chunks c JOIN embeddings e ON c.chunk_id = e.chunk_id"
            params = []
            if chapter_filter is not None:
                sql += " WHERE c.chapter = ?"
                params.append(chapter_filter)

            rows = conn.execute(sql, params).fetchall()
            results = []

            for row in rows:
                chunk_id, chapter, scene_index, content, emb_blob = row
                emb = json.loads(emb_blob.decode("utf-8"))
                score = self._cosine_similarity(query_vec, emb)
                results.append(SearchResult(
                    chunk_id=chunk_id, chapter=chapter,
                    scene_index=scene_index, content=content,
                    score=score, source="vector"
                ))

            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
        finally:
            conn.close()

    async def _bm25_search(self, query: str, top_k: int,
                            chapter_filter: Optional[int] = None) -> List[SearchResult]:
        """BM25 搜索"""
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        conn = sqlite3.connect(str(self.db_path))
        try:
            # 获取文档数和平均文档长度
            total_docs = conn.execute(
                "SELECT value FROM bm25_stats WHERE key = 'total_docs'"
            ).fetchone()
            N = int(total_docs[0]) if total_docs else 1

            avg_dl = conn.execute(
                "SELECT AVG(LENGTH(content)) FROM chunks"
            ).fetchone()[0] or 500

            # BM25 参数
            k1 = 1.5
            b = 0.75

            # 计算每个 chunk 的 BM25 分数
            scores: Dict[str, float] = {}
            chunk_info: Dict[str, Tuple[int, int, str]] = {}

            for term in query_terms:
                # DF: 包含该 term 的文档数
                df = conn.execute(
                    "SELECT COUNT(DISTINCT chunk_id) FROM bm25_index WHERE term = ?",
                    (term,)
                ).fetchone()[0]
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

                # 查找包含该 term 的 chunks
                rows = conn.execute(
                    "SELECT bi.chunk_id, bi.tf, c.chapter, c.scene_index, c.content "
                    "FROM bm25_index bi JOIN chunks c ON bi.chunk_id = c.chunk_id "
                    "WHERE bi.term = ?",
                    (term,)
                ).fetchall()

                for row in rows:
                    chunk_id, tf, chapter, scene_index, content = row
                    if chapter_filter is not None and chapter != chapter_filter:
                        continue

                    dl = len(content)
                    tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
                    scores[chunk_id] = scores.get(chunk_id, 0) + idf * tf_norm
                    chunk_info[chunk_id] = (chapter, scene_index, content)

            results = []
            for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]:
                chapter, scene_index, content = chunk_info[chunk_id]
                results.append(SearchResult(
                    chunk_id=chunk_id, chapter=chapter,
                    scene_index=scene_index, content=content,
                    score=score, source="bm25"
                ))

            return results
        finally:
            conn.close()

    def _merge_results(self, vector_results: List[SearchResult],
                        bm25_results: List[SearchResult],
                        top_k: int) -> List[SearchResult]:
        """混合排序"""
        v_weight = self.config.get("rag.vector_weight", 0.7)
        b_weight = self.config.get("rag.bm25_weight", 0.3)

        # 归一化分数
        merged: Dict[str, SearchResult] = {}

        if vector_results:
            max_v = max(r.score for r in vector_results) or 1.0
            for r in vector_results:
                merged[r.chunk_id] = SearchResult(
                    chunk_id=r.chunk_id, chapter=r.chapter,
                    scene_index=r.scene_index, content=r.content,
                    score=(r.score / max_v) * v_weight,
                    source="hybrid"
                )

        if bm25_results:
            max_b = max(r.score for r in bm25_results) or 1.0
            for r in bm25_results:
                norm_score = (r.score / max_b) * b_weight
                if r.chunk_id in merged:
                    merged[r.chunk_id].score += norm_score
                else:
                    merged[r.chunk_id] = SearchResult(
                        chunk_id=r.chunk_id, chapter=r.chapter,
                        scene_index=r.scene_index, content=r.content,
                        score=norm_score, source="hybrid"
                    )

        results = sorted(merged.values(), key=lambda x: x.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if not NUMPY_AVAILABLE:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b + 1e-8)

        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-8))
    
    def rerank_results(self, query: str, results: List[SearchResult], 
                       top_k: int = 10) -> List[SearchResult]:
        """重排序检索结果（预留接口）"""
        if not results:
            return []
        
        try:
            # 简单的重排序逻辑：基于 BM25 分数重新排序
            # 实际项目中可以调用 Reranker API
            reranked = sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
            
            logger.info(f"Rerank 完成：{len(reranked)} 条结果")
            return reranked
            
        except Exception as e:
            logger.warning(f"Rerank 失败，返回原始排序：{e}")
            # 降级：返回原始排序的前 top_k 条
            return results[:top_k]

    # ---- 上下文构建 ----

    async def extract_context(self, chapter: int, query: str = "",
                               top_k: int = 5) -> Dict[str, Any]:
        """提取章节上下文"""
        # 1. 从 index.db 获取章节元信息
        chapter_meta = self.index_manager.get_chapter(chapter)

        # 2. 搜索相关内容
        search_query = query or f"第{chapter}章"
        results = await self.search(search_query, top_k=top_k)

        # 3. 获取章节内实体的出场记录
        entities_in_chapter = []
        if chapter_meta:
            conn = self.index_manager._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM entity_appearances WHERE chapter = ? ORDER BY scene_index",
                    (chapter,)
                ).fetchall()
                entities_in_chapter = [dict(r) for r in rows]
            finally:
                conn.close()

        return {
            "chapter": chapter,
            "chapter_meta": chapter_meta,
            "relevant_chunks": [
                {"chunk_id": r.chunk_id, "chapter": r.chapter,
                 "content": r.content, "score": r.score, "source": r.source}
                for r in results
            ],
            "entities_in_chapter": entities_in_chapter,
            "degraded_mode": self._degraded_mode,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取 RAG 统计"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            embeddings = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            bm25_terms = conn.execute("SELECT COUNT(DISTINCT term) FROM bm25_index").fetchone()[0]
            return {
                "total_chunks": chunks,
                "embedded_chunks": embeddings,
                "bm25_vocabulary": bm25_terms,
                "degraded_mode": self._degraded_mode,
                "degraded_reason": self._degraded_reason,
            }
        finally:
            conn.close()
