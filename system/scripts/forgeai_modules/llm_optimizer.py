#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM调用优化器

减少LLM调用次数的策略:
1. 批量请求合并
2. 响应缓存
3. 智能重试
4. 请求去重
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from collections import defaultdict

from .cache_manager import get_cache_manager
from .retry_handler import RetryHandler, RetryConfig, RETRY_CONFIGS
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMRequest:
    """LLM请求"""
    request_id: str
    messages: List[Dict[str, str]]
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_cache_key(self) -> str:
        """生成缓存键"""
        # 基于消息内容生成hash
        content = str(self.messages) + str(self.temperature) + str(self.max_tokens)
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class LLMResponse:
    """LLM响应"""
    request_id: str
    content: str
    usage: Dict[str, int] = field(default_factory=dict)
    cached: bool = False
    duration: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "content": self.content,
            "usage": self.usage,
            "cached": self.cached,
            "duration": round(self.duration, 2),
        }


@dataclass
class BatchRequest:
    """批量请求"""
    batch_id: str
    requests: List[LLMRequest]
    status: str = "pending"
    responses: List[LLMResponse] = field(default_factory=list)


class LLMOptimizer:
    """LLM调用优化器"""
    
    def __init__(
        self,
        llm_client: Any,
        enable_cache: bool = True,
        cache_ttl: int = 3600,  # 1小时
        enable_batch: bool = True,
        batch_size: int = 5,
    ):
        self.llm_client = llm_client
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.enable_batch = enable_batch
        self.batch_size = batch_size
        
        self.cache = get_cache_manager()
        self.retry_handler = RetryHandler(RETRY_CONFIGS["llm_api"])
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "batch_requests": 0,
            "retries": 0,
            "total_tokens": 0,
        }
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        use_cache: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        生成响应(带优化)
        
        Args:
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大token数
            use_cache: 是否使用缓存
            metadata: 元数据
        
        Returns:
            LLM响应
        """
        import uuid
        
        request = LLMRequest(
            request_id=str(uuid.uuid4())[:8],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )
        
        self.stats["total_requests"] += 1
        
        # 尝试从缓存获取
        if use_cache and self.enable_cache:
            cache_key = f"llm:{request.get_cache_key()}"
            cached_content = self.cache.get(cache_key)
            
            if cached_content is not None:
                self.stats["cache_hits"] += 1
                logger.debug(f"LLM缓存命中: {request.request_id}")
                
                return LLMResponse(
                    request_id=request.request_id,
                    content=cached_content,
                    cached=True,
                )
        
        # 调用LLM(带重试)
        response = await self._call_llm_with_retry(request)
        
        # 缓存结果
        if use_cache and self.enable_cache and response.content:
            cache_key = f"llm:{request.get_cache_key()}"
            self.cache.set(cache_key, response.content, self.cache_ttl)
        
        return response
    
    async def _call_llm_with_retry(self, request: LLMRequest) -> LLMResponse:
        """调用LLM(带重试)"""
        start_time = datetime.now()
        
        async def call_llm():
            return await self.llm_client.chat_completion_async(
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        
        # 使用重试处理器
        retry_result = await self.retry_handler.execute_with_retry(call_llm)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if retry_result.success:
            response_data = retry_result.result
            usage = response_data.get("usage", {})
            
            # 更新统计
            self.stats["total_tokens"] += usage.get("total_tokens", 0)
            if retry_result.attempts > 1:
                self.stats["retries"] += retry_result.attempts - 1
            
            return LLMResponse(
                request_id=request.request_id,
                content=response_data.get("content", ""),
                usage=usage,
                duration=duration,
            )
        else:
            # 重试失败
            raise retry_result.error
    
    async def generate_batch(
        self,
        requests: List[LLMRequest],
        max_concurrent: int = 3,
    ) -> List[LLMResponse]:
        """
        批量生成(并发控制)
        
        Args:
            requests: 请求列表
            max_concurrent: 最大并发数
        
        Returns:
            响应列表
        """
        import uuid
        
        batch_id = str(uuid.uuid4())[:8]
        logger.info(f"批量生成: {len(requests)}个请求, 最大并发: {max_concurrent}")
        
        self.stats["batch_requests"] += 1
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_generate(request: LLMRequest):
            async with semaphore:
                return await self.generate(
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    use_cache=True,
                    metadata=request.metadata,
                )
        
        # 并发执行
        tasks = [limited_generate(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        return list(responses)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.stats["total_requests"]
        cache_hit_rate = (self.stats["cache_hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "cache_hit_rate": round(cache_hit_rate, 2),
        }
    
    def reset_stats(self) -> None:
        """重置统计"""
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "batch_requests": 0,
            "retries": 0,
            "total_tokens": 0,
        }


class PromptOptimizer:
    """提示词优化器"""
    
    @staticmethod
    def compress_context(context: str, max_length: int = 4000) -> str:
        """压缩上下文"""
        if len(context) <= max_length:
            return context
        
        # 简单截断(可以更智能)
        return context[:max_length] + "\n...(已截断)"
    
    @staticmethod
    def deduplicate_examples(examples: List[str], max_count: int = 5) -> List[str]:
        """去重示例"""
        # 去重
        unique = list(dict.fromkeys(examples))
        
        # 限制数量
        return unique[:max_count]
    
    @staticmethod
    def optimize_messages(
        messages: List[Dict[str, str]],
        max_context_length: int = 8000,
    ) -> List[Dict[str, str]]:
        """优化消息列表"""
        optimized = []
        total_length = 0
        
        for msg in messages:
            content = msg.get("content", "")
            content_length = len(content)
            
            # 检查是否超出限制
            if total_length + content_length > max_context_length:
                # 压缩内容
                remaining = max_context_length - total_length
                if remaining > 500:  # 至少保留500字符
                    content = content[:remaining] + "\n...(已压缩)"
                    content_length = len(content)
                else:
                    break
            
            optimized.append({
                "role": msg["role"],
                "content": content,
            })
            total_length += content_length
        
        return optimized


class SmartContextBuilder:
    """智能上下文构建器"""
    
    def __init__(self, config: Any):
        self.config = config
    
    def build_minimal_context(
        self,
        chapter_num: int,
        essentials: Dict[str, Any],
    ) -> str:
        """
        构建最小化上下文
        
        Args:
            chapter_num: 章节号
            essentials: 必要信息
        
        Returns:
            最小化上下文
        """
        lines = []
        
        # 项目信息(压缩)
        if "project" in essentials:
            proj = essentials["project"]
            lines.append(f"项目: {proj.get('name', '')} ({proj.get('genre', '')})")
        
        # 当前章节
        lines.append(f"\n当前章节: 第{chapter_num}章")
        
        # 核心角色(只保留核心)
        if "entities" in essentials:
            core_entities = [
                e for e in essentials["entities"]
                if e.get("tier") == "core"
            ]
            if core_entities:
                lines.append("\n核心角色:")
                for e in core_entities[:5]:  # 最多5个
                    lines.append(f"  - {e.get('name', '')}")
        
        # 活跃伏笔(只保留最近)
        if "foreshadowing" in essentials:
            active = essentials["foreshadowing"].get("active", [])
            if active:
                lines.append("\n活跃伏笔:")
                for f in active[:3]:  # 最多3个
                    lines.append(f"  - {f.get('description', '')}")
        
        return "\n".join(lines)
    
    def estimate_tokens(self, text: str) -> int:
        """估算token数"""
        # 简单估算: 中文约1.5字/token, 英文约4字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        return int(chinese_chars / 1.5 + other_chars / 4)


# 便捷函数
def optimize_llm_call(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    cache_key: Optional[str] = None,
):
    """
    优化LLM调用装饰器
    
    用法:
        @optimize_llm_call(cache_key="my_prompt")
        async def my_llm_function():
            return messages
    """
    def decorator(func):
        @asyncio.coroutine
        async def wrapper(*args, **kwargs):
            # 获取缓存管理器
            cache = get_cache_manager()
            
            # 生成缓存键
            if cache_key:
                key = f"llm_opt:{cache_key}"
            else:
                content_hash = hashlib.md5(str(messages).encode()).hexdigest()
                key = f"llm_opt:{content_hash}"
            
            # 尝试从缓存获取
            cached = cache.get(key)
            if cached:
                return cached
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache.set(key, result, ttl_seconds=3600)
            
            return result
        
        return wrapper
    
    return decorator
