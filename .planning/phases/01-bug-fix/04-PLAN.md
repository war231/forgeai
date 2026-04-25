---
wave: 2
depends_on: [01]
files_modified:
  - system/scripts/forgeai_modules/rag_adapter.py
  - system/scripts/forgeai_modules/config.py
autonomous: true
requirements_addressed: [REQ-006]
---

<objective>
优化RAG检索性能，添加缓存机制和错误处理
</objective>

<tasks>
<task id="1" type="execute">
<read_first>
- system/scripts/forgeai_modules/rag_adapter.py (file being modified)
- system/scripts/forgeai_modules/config.py (config module)
</read_first>

<action>
添加检索结果缓存：

1. 在 `config.py` 中添加缓存配置：
```python
# RAG 检索缓存配置
RAG_CACHE_ENABLED = True
RAG_CACHE_TTL = 300  # 5分钟
RAG_CACHE_MAX_SIZE = 1000  # 最大缓存条目数
```

2. 在 `rag_adapter.py` 中添加缓存类：
```python
import hashlib
import time
from typing import Optional, Dict, Any
from config import RAG_CACHE_ENABLED, RAG_CACHE_TTL, RAG_CACHE_MAX_SIZE

class RAGCache:
    """RAG 检索结果缓存"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: list = []  # LRU 队列
    
    def _get_key(self, query: str, top_k: int, filters: dict) -> str:
        """生成缓存键"""
        filter_str = str(sorted(filters.items())) if filters else ""
        key_data = f"{query}_{top_k}_{filter_str}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, query: str, top_k: int, filters: dict = None) -> Optional[dict]:
        """从缓存获取结果"""
        if not RAG_CACHE_ENABLED:
            return None
        
        key = self._get_key(query, top_k, filters or {})
        
        if key in self._cache:
            # 检查 TTL
            if time.time() - self._timestamps[key] < RAG_CACHE_TTL:
                logger.debug(f"RAG 缓存命中：{key[:8]}")
                # 更新访问顺序（LRU）
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            else:
                # 过期，删除
                self._remove(key)
        
        return None
    
    def set(self, query: str, top_k: int, result: dict, filters: dict = None):
        """保存结果到缓存"""
        if not RAG_CACHE_ENABLED:
            return
        
        key = self._get_key(query, top_k, filters or {})
        
        # 检查缓存大小，超过则删除最旧的
        if len(self._cache) >= RAG_CACHE_MAX_SIZE:
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
```
</action>

<acceptance_criteria>
- `config.py contains "RAG_CACHE_ENABLED"`
- `config.py contains "RAG_CACHE_TTL"`
- `config.py contains "RAG_CACHE_MAX_SIZE"`
- `rag_adapter.py contains "class RAGCache"`
- `rag_adapter.py contains "def get(self, query"`
- `rag_adapter.py contains "def set(self, query"`
</acceptance_criteria>
</task>

<task id="2" type="execute">
<read_first>
- system/scripts/forgeai_modules/rag_adapter.py (file being modified)
</read_first>

<action>
集成缓存到检索流程：

```python
class RAGAdapter:
    def __init__(self):
        # ... 现有初始化 ...
        self.cache = RAGCache()
    
    def retrieve(self, query: str, top_k: int = 10, filters: dict = None) -> dict:
        """检索相关内容"""
        start_time = time.time()
        
        # 1. 检查缓存
        cached = self.cache.get(query, top_k, filters)
        if cached:
            logger.info(f"RAG 检索（缓存）：耗时 {time.time() - start_time:.2f}s")
            return cached
        
        # 2. 执行检索
        try:
            result = self._retrieve_impl(query, top_k, filters)
        except Exception as e:
            logger.error(f"RAG 检索失败：{e}")
            return {
                "error": str(e),
                "results": []
            }
        
        # 3. 保存缓存
        self.cache.set(query, top_k, result, filters)
        
        elapsed = time.time() - start_time
        logger.info(f"RAG 检索完成：耗时 {elapsed:.2f}s，返回 {len(result.get('results', []))} 条结果")
        
        return result
    
    def _retrieve_impl(self, query: str, top_k: int, filters: dict) -> dict:
        """实际检索实现"""
        # ... 现有检索逻辑 ...
        pass
```
</action>

<acceptance_criteria>
- `rag_adapter.py contains "self.cache = RAGCache()"`
- `rag_adapter.py contains "cached = self.cache.get"`
- `rag_adapter.py contains "self.cache.set"`
- `rag_adapter.py contains "RAG 检索（缓存）"`
- `rag_adapter.py contains "RAG 检索完成：耗时"`
</acceptance_criteria>
</task>

<task id="3" type="execute">
<read_first>
- system/scripts/forgeai_modules/rag_adapter.py (file being modified)
</read_first>

<action>
优化向量索引批量操作：

```python
def batch_index(self, documents: list) -> dict:
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
            # 批量生成向量
            texts = [doc.get('content', '') for doc in batch]
            embeddings = self._generate_embeddings_batch(texts)
            
            # 批量添加到向量数据库
            ids = [doc.get('id', f'doc_{i+j}') for j, doc in enumerate(batch)]
            metadatas = [doc.get('metadata', {}) for doc in batch]
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            indexed_count += len(batch)
            logger.debug(f"批量索引：{indexed_count}/{len(documents)}")
            
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

def _generate_embeddings_batch(self, texts: list) -> list:
    """批量生成向量"""
    # 使用批量 API 调用
    response = self.client.embeddings.create(
        input=texts,
        model=self.embedding_model
    )
    return [item.embedding for item in response.data]
```
</action>

<acceptance_criteria>
- `rag_adapter.py contains "def batch_index"`
- `rag_adapter.py contains "batch_size = 100"`
- `rag_adapter.py contains "_generate_embeddings_batch"`
- `rag_adapter.py contains "批量索引完成"`
</acceptance_criteria>
</task>

<task id="4" type="execute">
<read_first>
- system/scripts/forgeai_modules/rag_adapter.py (file being modified)
</read_first>

<action>
改进 Reranker 调用错误处理：

```python
def rerank_results(self, query: str, results: list, top_k: int = 10) -> list:
    """重排序检索结果"""
    if not results:
        return []
    
    try:
        # 准备重排序输入
        documents = [r.get('content', '') for r in results]
        
        # 调用 Reranker API
        response = self.reranker_client.rerank(
            query=query,
            documents=documents,
            top_k=top_k
        )
        
        # 重新排序结果
        reranked = []
        for item in response.results:
            idx = item.index
            score = item.relevance_score
            reranked.append({
                **results[idx],
                'rerank_score': score
            })
        
        logger.info(f"Rerank 完成：{len(reranked)} 条结果")
        return reranked
        
    except Exception as e:
        logger.warning(f"Rerank 失败，返回原始排序：{e}")
        # 降级：返回原始排序的前 top_k 条
        return results[:top_k]
```
</action>

<acceptance_criteria>
- `rag_adapter.py contains "def rerank_results"`
- `rag_adapter.py contains "try:"`
- `rag_adapter.py contains "except Exception as e:"`
- `rag_adapter.py contains "Rerank 失败，返回原始排序"`
</acceptance_criteria>
</task>
</tasks>

<verification>
1. 运行检索命令，检查缓存是否生效（第二次查询应更快）
2. 检查批量索引性能
3. 测试 Reranker 失败时的降级处理
4. 检查日志输出
</verification>

<must_haves>
- 缓存必须可配置
- 必须有 LRU 淘汰机制
- 批量索引必须正常工作
- Reranker 失败时必须降级
- 必须添加性能日志
</must_haves>
