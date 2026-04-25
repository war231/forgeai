#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-Reranker 客户端 - 阿里云 DashScope API

支持模型：
- qwen3-rerank（推荐，MTEB第1名）
- gte-rerank-v2
- qwen3-vl-rerank（多模态）

文档：https://help.aliyun.com/zh/model-studio/text-rerank-api
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class APIStats:
    """API 调用统计"""
    total_calls: int = 0
    total_time: float = 0.0
    errors: int = 0


class QwenRerankerClient:
    """
    阿里云 DashScope Qwen3-Reranker 客户端
    
    使用方法：
    ```python
    client = QwenRerankerClient(api_key="your-api-key")
    
    results = await client.rerank(
        query="萧炎的师父是谁？",
        documents=[
            "药老传授给萧炎焚诀功法",
            "萧炎在沙漠遭遇美杜莎女王",
            "萧炎的父亲萧战是萧家族长"
        ],
        top_n=2
    )
    
    # 结果：[{"index": 0, "relevance_score": 0.93}, ...]
    ```
    """
    
    API_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    
    MODELS = {
        "qwen3-rerank": {
            "max_documents": 500,
            "max_tokens": 4000,
            "price_per_1k": 0.0005,
            "description": "推荐模型，MTEB第1名"
        },
        "gte-rerank-v2": {
            "max_documents": 30000,
            "max_tokens": 8000,
            "price_per_1k": 0.0008,
            "description": "高吞吐量"
        },
        "qwen3-vl-rerank": {
            "max_documents": 100,
            "max_tokens": 8000,
            "price_per_1k": 0.0007,
            "description": "多模态"
        }
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen3-rerank",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
        concurrency: int = 32
    ):
        # 使用 env_loader 统一获取配置
        from .env_loader import get_rerank_config
        rerank_config = get_rerank_config()

        self.api_key = api_key or rerank_config.get("api_key")
        if not self.api_key:
            raise ValueError("缺少 Rerank API Key（请设置 RERANK_API_KEY 环境变量）")

        if model not in self.MODELS:
            raise ValueError(f"不支持的模型: {model}")
        
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.sem = asyncio.Semaphore(concurrency)
        self.stats = APIStats()
        self._warmed_up = False
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_payload(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
        return_documents: bool = False,
        instruct: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "input": {
                "query": query,
                "documents": documents
            },
            "parameters": {
                "return_documents": return_documents
            }
        }
        
        if top_n:
            payload["parameters"]["top_n"] = top_n
        
        if instruct and "qwen3" in self.model:
            payload["parameters"]["instruct"] = instruct
        
        return payload
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        output = data.get("output", {})
        results = output.get("results", [])
        
        parsed = []
        for item in results:
            parsed.append({
                "index": item.get("index", 0),
                "relevance_score": item.get("relevance_score", 0.0),
                "document": item.get("document", {})
            })
        
        return parsed
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
        return_documents: bool = False,
        instruct: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        文本重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_n: 返回 top_n 个结果
            return_documents: 是否返回文档原文
            instruct: 自定义任务指令
        
        Returns:
            排序结果列表
        """
        if not documents:
            return []
        
        max_docs = self.MODELS[self.model]["max_documents"]
        if len(documents) > max_docs:
            documents = documents[:max_docs]
        
        async with self.sem:
            start = time.time()
            session = await self._get_session()
            
            for attempt in range(self.max_retries):
                try:
                    payload = self._build_payload(query, documents, top_n, return_documents, instruct)
                    
                    async with session.post(
                        self.API_ENDPOINT,
                        json=payload,
                        headers=self._build_headers(),
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            self.stats.total_calls += 1
                            self.stats.total_time += time.time() - start
                            self._warmed_up = True
                            
                            return self._parse_response(data)
                        
                        if resp.status in (429, 500, 502, 503, 504) and attempt < self.max_retries - 1:
                            delay = self.retry_delay * (2 ** attempt)
                            await asyncio.sleep(delay)
                            continue
                        
                        self.stats.errors += 1
                        return None
                
                except asyncio.TimeoutError:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    self.stats.errors += 1
                    return None
                
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    self.stats.errors += 1
                    return None
            
            return None
    
    async def warmup(self):
        """预热服务"""
        await self.rerank("test", ["doc1", "doc2"], top_n=1)
        self._warmed_up = True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "model": self.model,
            "total_calls": self.stats.total_calls,
            "total_time": self.stats.total_time,
            "avg_time": self.stats.total_time / max(self.stats.total_calls, 1),
            "errors": self.stats.errors,
            "warmed_up": self._warmed_up
        }
    
    def estimate_cost(self, num_documents: int, avg_doc_tokens: int = 100) -> float:
        """估算成本"""
        total_tokens = num_documents * avg_doc_tokens
        price_per_1k = self.MODELS[self.model].get("price_per_1k", 0.0005)
        return total_tokens * price_per_1k / 1000


# ==================== 便捷函数 ====================

async def qwen_rerank(
    query: str,
    documents: List[str],
    api_key: Optional[str] = None,
    model: str = "qwen3-rerank",
    top_n: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    快捷重排序函数
    
    示例：
    ```python
    results = await qwen_rerank(
        query="萧炎的师父",
        documents=["药老传授斗技", "萧炎修炼焚诀"],
        top_n=2
    )
    ```
    """
    client = QwenRerankerClient(api_key=api_key, model=model)
    try:
        return await client.rerank(query, documents, top_n=top_n)
    finally:
        await client.close()


if __name__ == "__main__":
    import os
    
    print("=" * 60)
    print("Qwen3-Reranker 测试")
    print("=" * 60)
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("\n[错误] 未配置 DASHSCOPE_API_KEY")
        print("请设置环境变量或编辑 .env 文件")
    else:
        print(f"\n[OK] 已检测到 API Key: {api_key[:10]}...")
        
        async def test():
            client = QwenRerankerClient()
            
            results = await client.rerank(
                query="萧炎的师父是谁？",
                documents=[
                    "药老传授给萧炎焚诀功法",
                    "萧炎在沙漠遭遇美杜莎女王",
                    "萧炎的父亲萧战是萧家族长"
                ],
                top_n=2
            )
            
            if results:
                print("\n测试结果：")
                for i, r in enumerate(results, 1):
                    print(f"{i}. 索引: {r['index']}, 分数: {r['relevance_score']:.3f}")
            
            stats = client.get_stats()
            print(f"\n统计：调用 {stats['total_calls']} 次")
            
            await client.close()
        
        asyncio.run(test())
    
    print("\n" + "=" * 60)
