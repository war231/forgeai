#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理器

提供多层缓存支持:
1. 内存缓存 (快速访问)
2. 文件缓存 (持久化)
3. LRU淘汰策略
"""

from __future__ import annotations

import json
import hashlib
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from collections import OrderedDict
import threading

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    @property
    def is_expired(self) -> bool:
        """是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class LRUCache(Generic[T]):
    """LRU缓存"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存"""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            
            # 检查过期
            if entry.is_expired:
                del self.cache[key]
                return None
            
            # 移到末尾(最近使用)
            self.cache.move_to_end(key)
            entry.touch()
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: T,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """设置缓存"""
        with self.lock:
            now = datetime.now()
            expires_at = None
            if ttl_seconds:
                expires_at = now + timedelta(seconds=ttl_seconds)
            
            # 如果已存在,先删除
            if key in self.cache:
                del self.cache[key]
            
            # 添加新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
            )
            self.cache[key] = entry
            
            # 淘汰旧条目
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "entries": [
                    {
                        "key": key,
                        "access_count": entry.access_count,
                        "created_at": entry.created_at.isoformat(),
                        "is_expired": entry.is_expired,
                    }
                    for key, entry in self.cache.items()
                ],
            }


class FileCache:
    """文件缓存"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(".forgeai/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用hash作为文件名
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        path = self._get_cache_path(key)
        
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            
            # 检查过期
            expires_at = data.get("expires_at")
            if expires_at:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    path.unlink()
                    return None
            
            return data.get("value")
        
        except Exception as e:
            logger.warning(f"读取缓存失败: {key}, 错误: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """设置缓存"""
        path = self._get_cache_path(key)
        
        now = datetime.now()
        expires_at = None
        if ttl_seconds:
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        
        data = {
            "key": key,
            "value": value,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
        }
        
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        path = self._get_cache_path(key)
        
        if path.exists():
            path.unlink()
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        
        for path in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                expires_at = data.get("expires_at")
                
                if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                    path.unlink()
                    count += 1
            except:
                pass
        
        if count > 0:
            logger.info(f"清理过期缓存: {count} 个")
        
        return count


class CacheManager:
    """缓存管理器"""
    
    def __init__(
        self,
        memory_cache_size: int = 100,
        cache_dir: Optional[Path] = None,
    ):
        self.memory_cache = LRUCache(max_size=memory_cache_size)
        self.file_cache = FileCache(cache_dir)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存(先查内存,再查文件)"""
        # 查询内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 查询文件缓存
        value = self.file_cache.get(key)
        if value is not None:
            # 回填到内存缓存
            self.memory_cache.set(key, value)
            return value
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        persist: bool = False,
    ) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 过期时间(秒)
            persist: 是否持久化到文件
        """
        # 设置内存缓存
        self.memory_cache.set(key, value, ttl_seconds)
        
        # 设置文件缓存
        if persist:
            self.file_cache.set(key, value, ttl_seconds)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        memory_deleted = self.memory_cache.delete(key)
        file_deleted = self.file_cache.delete(key)
        return memory_deleted or file_deleted
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.memory_cache.clear()
        self.file_cache.clear()
    
    def cleanup(self) -> int:
        """清理过期缓存"""
        return self.file_cache.cleanup_expired()


# 全局缓存管理器
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(
    key_func: Optional[Callable[..., str]] = None,
    ttl_seconds: Optional[int] = None,
    persist: bool = False,
):
    """
    缓存装饰器
    
    用法:
        @cached(key_func=lambda x: f"result_{x}", ttl_seconds=3600)
        async def my_function(x):
            # 耗时计算
            return result
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数生成键
                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()
                cache_key = f"{func.__name__}:{args_hash}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result, ttl_seconds, persist)
            logger.debug(f"缓存设置: {cache_key}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()
                cache_key = f"{func.__name__}:{args_hash}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result, ttl_seconds, persist)
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 题材配置缓存装饰器
def cache_genre_profile(func):
    """缓存题材配置"""
    return cached(
        key_func=lambda genre: f"genre_profile:{genre}",
        ttl_seconds=3600,  # 1小时
        persist=True,
    )(func)


# 上下文缓存装饰器
def cache_context(func):
    """缓存上下文"""
    return cached(
        key_func=lambda chapter, query="": f"context:{chapter}:{hashlib.md5(query.encode()).hexdigest()[:8]}",
        ttl_seconds=600,  # 10分钟
        persist=False,
    )(func)
