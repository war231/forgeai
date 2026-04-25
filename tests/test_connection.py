#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 SiliconFlow API 连接

测试项目：
1. Embedding API 连接
2. Reranker API 连接
"""

import asyncio
import aiohttp
import os
from pathlib import Path

# 尝试加载 dotenv
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def load_env():
    """加载环境变量"""
    if DOTENV_AVAILABLE:
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"\n[OK] 已加载配置文件: {env_file}")
            return True
        else:
            print(f"\n[ERR] 未找到配置文件: {env_file}")
            return False
    else:
        print("\n[WARN] 未安装 python-dotenv，使用系统环境变量")
        return True


async def test_embedding():
    """测试 Embedding API"""
    print("\n" + "=" * 60)
    print("测试 Embedding API (Qwen/Qwen3-Embedding-8B)")
    print("=" * 60)
    
    base_url = os.getenv("EMBED_BASE_URL", "").rstrip("/")
    model = os.getenv("EMBED_MODEL", "")
    api_key = os.getenv("EMBED_API_KEY", "")
    
    if not all([base_url, model, api_key]):
        print("[ERR] 未配置 Embedding API")
        return False
    
    # 构建 URL
    url = f"{base_url}/embeddings"
    
    print(f"URL: {url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:20]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "input": ["测试文本"]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                print(f"状态码: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        embedding = data["data"][0].get("embedding", [])
                        print(f"[OK] 成功！向量维度: {len(embedding)}")
                        return True
                    else:
                        print(f"[ERR] 响应格式错误: {data}")
                        return False
                else:
                    error_text = await resp.text()
                    print(f"[ERR] 请求失败: {error_text[:500]}")
                    return False
                    
    except Exception as e:
        print(f"[ERR] 异常: {e}")
        return False


async def test_reranker():
    """测试 Reranker API"""
    print("\n" + "=" * 60)
    print("测试 Reranker API (Qwen/Qwen3-Reranker-8B)")
    print("=" * 60)
    
    base_url = os.getenv("RERANK_BASE_URL", "").rstrip("/")
    model = os.getenv("RERANK_MODEL", "")
    api_key = os.getenv("RERANK_API_KEY", "")
    
    if not all([base_url, model, api_key]):
        print("[ERR] 未配置 Reranker API")
        return False
    
    # 构建 URL
    url = f"{base_url}/rerank"
    
    print(f"URL: {url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:20]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "query": "测试查询",
        "documents": ["文档1", "文档2", "文档3"]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                print(f"状态码: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    if "results" in data:
                        results = data["results"]
                        print(f"[OK] 成功！返回 {len(results)} 个结果")
                        for i, r in enumerate(results[:3], 1):
                            score = r.get("relevance_score", 0)
                            print(f"   结果{i}: 分数 {score:.3f}")
                        return True
                    else:
                        print(f"[ERR] 响应格式错误: {data}")
                        return False
                else:
                    error_text = await resp.text()
                    print(f"[ERR] 请求失败: {error_text[:500]}")
                    return False
                    
    except Exception as e:
        print(f"[ERR] 异常: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("SiliconFlow API 连接测试")
    print("=" * 60)
    
    # 加载环境变量
    if not load_env():
        return
    
    # 显示配置
    print("\n当前配置:")
    print(f"  EMBED_BASE_URL: {os.getenv('EMBED_BASE_URL')}")
    print(f"  EMBED_MODEL: {os.getenv('EMBED_MODEL')}")
    print(f"  RERANK_BASE_URL: {os.getenv('RERANK_BASE_URL')}")
    print(f"  RERANK_MODEL: {os.getenv('RERANK_MODEL')}")
    
    # 执行测试
    results = []
    
    # 测试 Embedding
    result1 = await test_embedding()
    results.append(("Embedding", result1))
    
    # 测试 Reranker
    result2 = await test_reranker()
    results.append(("Reranker", result2))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, success in results:
        status = "[OK] 通过" if success else "[FAIL] 失败"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！API 连接正常")
    else:
        print("\n[WARNING] 部分测试失败，请检查配置")


if __name__ == "__main__":
    asyncio.run(main())
