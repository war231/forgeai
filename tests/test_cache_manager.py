#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试缓存管理器
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from forgeai_modules.cache_manager import (
    CacheEntry,
    LRUCache,
    FileCache,
    CacheManager,
    get_cache_manager,
    cached,
    cache_genre_profile,
    cache_context,
)


class TestCacheEntry:
    """测试缓存条目"""

    def test_defaults(self):
        """测试默认值"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.last_accessed == entry.created_at
        assert entry.expires_at is None

    def test_is_expired_not_expired(self):
        """测试未过期"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
        )

        assert entry.is_expired is False

    def test_is_expired_expired(self):
        """测试已过期"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
        )

        assert entry.is_expired is True

    def test_is_expired_no_expiry(self):
        """测试无过期时间"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
        )

        assert entry.is_expired is False

    def test_touch(self):
        """测试访问更新"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
        )

        initial_count = entry.access_count
        initial_time = entry.last_accessed

        time.sleep(0.01)  # 确保时间差异
        entry.touch()

        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > initial_time


class TestLRUCache:
    """测试LRU缓存"""

    def test_init_default(self):
        """测试默认初始化"""
        cache = LRUCache()
        assert cache.max_size == 100
        assert len(cache.cache) == 0

    def test_init_custom_size(self):
        """测试自定义大小"""
        cache = LRUCache(max_size=10)
        assert cache.max_size == 10

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = LRUCache()
        assert cache.get("nonexistent") is None

    def test_get_expired(self):
        """测试获取过期条目"""
        cache = LRUCache()

        cache.set("key1", "value1", ttl_seconds=-1)  # 已过期

        # 等待过期
        time.sleep(0.01)

        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # 应该淘汰 key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_access_order(self):
        """测试访问顺序影响淘汰"""
        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 访问 key1 使其变为最近使用
        cache.get("key1")

        # 添加新条目，应该淘汰 key2（最久未使用）
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_delete(self):
        """测试删除"""
        cache = LRUCache()

        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False

    def test_clear(self):
        """测试清空"""
        cache = LRUCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert len(cache.cache) == 0

    def test_get_stats(self):
        """测试获取统计"""
        cache = LRUCache(max_size=5)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 5
        assert len(stats["entries"]) == 2

    def test_ttl_expiry(self):
        """测试TTL过期"""
        cache = LRUCache()

        cache.set("key1", "value1", ttl_seconds=1)

        assert cache.get("key1") == "value1"

        time.sleep(1.1)

        assert cache.get("key1") is None


class TestFileCache:
    """测试文件缓存"""

    def test_init_default(self, tmp_path):
        """测试默认初始化"""
        cache = FileCache(tmp_path / "cache")
        assert cache.cache_dir.exists()

    def test_set_and_get(self, tmp_path):
        """测试设置和获取"""
        cache = FileCache(tmp_path / "cache")

        cache.set("test_key", {"data": "test_value"})

        result = cache.get("test_key")
        assert result == {"data": "test_value"}

    def test_get_nonexistent(self, tmp_path):
        """测试获取不存在的键"""
        cache = FileCache(tmp_path / "cache")
        assert cache.get("nonexistent") is None

    def test_get_expired(self, tmp_path):
        """测试获取过期文件"""
        cache = FileCache(tmp_path / "cache")

        cache.set("test_key", "value", ttl_seconds=-1)

        assert cache.get("test_key") is None

    def test_delete(self, tmp_path):
        """测试删除"""
        cache = FileCache(tmp_path / "cache")

        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False

    def test_clear(self, tmp_path):
        """测试清空"""
        cache = FileCache(tmp_path / "cache")

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self, tmp_path):
        """测试清理过期"""
        cache = FileCache(tmp_path / "cache")

        cache.set("key1", "value1", ttl_seconds=-1)  # 已过期
        cache.set("key2", "value2", ttl_seconds=3600)  # 未过期

        count = cache.cleanup_expired()

        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestCacheManager:
    """测试缓存管理器"""

    def test_init_default(self):
        """测试默认初始化"""
        manager = CacheManager()
        assert manager.memory_cache is not None
        assert manager.file_cache is not None

    def test_get_from_memory(self, tmp_path):
        """测试从内存获取"""
        manager = CacheManager(cache_dir=tmp_path / "cache")

        manager.set("key1", "value1")

        # 应该从内存缓存获取
        assert manager.get("key1") == "value1"

    def test_get_from_file(self, tmp_path):
        """测试从文件获取"""
        manager = CacheManager(cache_dir=tmp_path / "cache")

        # 设置持久化缓存
        manager.set("key1", "value1", persist=True)

        # 清空内存缓存
        manager.memory_cache.clear()

        # 应该从文件缓存获取
        assert manager.get("key1") == "value1"

    def test_get_backfill(self, tmp_path):
        """测试回填到内存"""
        manager = CacheManager(cache_dir=tmp_path / "cache")

        manager.set("key1", "value1", persist=True)
        manager.memory_cache.clear()

        # 第一次获取会从文件读取
        result = manager.get("key1")
        assert result == "value1"

        # 检查是否回填到内存
        assert manager.memory_cache.get("key1") == "value1"

    def test_delete(self, tmp_path):
        """测试删除"""
        manager = CacheManager(cache_dir=tmp_path / "cache")

        manager.set("key1", "value1", persist=True)
        manager.delete("key1")

        assert manager.get("key1") is None

    def test_clear(self, tmp_path):
        """测试清空"""
        manager = CacheManager(cache_dir=tmp_path / "cache")

        manager.set("key1", "value1", persist=True)
        manager.set("key2", "value2")
        manager.clear()

        assert manager.get("key1") is None
        assert manager.get("key2") is None


class TestCachedDecorator:
    """测试缓存装饰器"""

    def test_cached_async(self, tmp_path):
        """测试异步函数缓存"""
        call_count = 0

        @cached(ttl_seconds=60)
        async def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 重置缓存管理器
        import forgeai_modules.cache_manager as cm
        cm._cache_manager = CacheManager(cache_dir=tmp_path / "cache")

        # 第一次调用
        result1 = asyncio.run(expensive_function(5))
        assert result1 == 10
        assert call_count == 1

        # 第二次调用（应该从缓存获取）
        result2 = asyncio.run(expensive_function(5))
        assert result2 == 10
        assert call_count == 1  # 没有增加

    def test_cached_sync(self, tmp_path):
        """测试同步函数缓存"""
        call_count = 0

        @cached(ttl_seconds=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 重置缓存管理器
        import forgeai_modules.cache_manager as cm
        cm._cache_manager = CacheManager(cache_dir=tmp_path / "cache")

        # 第一次调用
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用（应该从缓存获取）
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1

    def test_cached_with_key_func(self, tmp_path):
        """测试自定义键函数"""
        call_count = 0

        @cached(key_func=lambda x: f"custom_{x}", ttl_seconds=60)
        async def my_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 重置缓存管理器
        import forgeai_modules.cache_manager as cm
        cm._cache_manager = CacheManager(cache_dir=tmp_path / "cache")

        result = asyncio.run(my_function(5))
        assert result == 10

    def test_cached_persist(self, tmp_path):
        """测试持久化缓存"""

        @cached(ttl_seconds=60, persist=True)
        async def my_function(x):
            return x * 2

        # 重置缓存管理器
        import forgeai_modules.cache_manager as cm
        cm._cache_manager = CacheManager(cache_dir=tmp_path / "cache")

        result = asyncio.run(my_function(5))
        assert result == 10


class TestGetCacheManager:
    """测试获取缓存管理器"""

    def test_singleton(self):
        """测试单例模式"""
        import forgeai_modules.cache_manager as cm

        # 重置
        cm._cache_manager = None

        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2


class TestCacheGenreProfile:
    """测试题材配置缓存装饰器"""

    def test_decorator(self, tmp_path):
        """测试装饰器"""

        @cache_genre_profile
        async def load_genre(genre):
            return {"genre": genre, "data": "test"}

        # 重置缓存管理器
        import forgeai_modules.cache_manager as cm
        cm._cache_manager = CacheManager(cache_dir=tmp_path / "cache")

        result = asyncio.run(load_genre("xianxia"))
        assert result["genre"] == "xianxia"


class TestCacheContext:
    """测试上下文缓存装饰器"""

    def test_decorator(self, tmp_path):
        """测试装饰器"""

        @cache_context
        async def load_context(chapter, query=""):
            return {"chapter": chapter, "query": query}

        # 重置缓存管理器
        import forgeai_modules.cache_manager as cm
        cm._cache_manager = CacheManager(cache_dir=tmp_path / "cache")

        result = asyncio.run(load_context(1, "test"))
        assert result["chapter"] == 1
