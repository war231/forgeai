#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-Reranker客户端测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path

from forgeai_modules.qwen_reranker import (
    APIStats,
    QwenRerankerClient,
    qwen_rerank,
)


class TestAPIStats:
    """APIStats数据类测试"""
    
    def test_default_values(self):
        """测试默认值"""
        stats = APIStats()
        
        assert stats.total_calls == 0
        assert stats.total_time == 0.0
        assert stats.errors == 0
    
    def test_custom_values(self):
        """测试自定义值"""
        stats = APIStats(
            total_calls=10,
            total_time=5.5,
            errors=2
        )
        
        assert stats.total_calls == 10
        assert stats.total_time == 5.5
        assert stats.errors == 2


class TestQwenRerankerClient:
    """QwenRerankerClient测试"""
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return {"api_key": "test-api-key"}
    
    @pytest.fixture
    def client(self, mock_config):
        """创建客户端实例"""
        with patch('forgeai_modules.qwen_reranker.get_rerank_config') as mock_get_config:
            mock_get_config.return_value = mock_config
            return QwenRerankerClient(api_key="test-key")
    
    def test_init_with_api_key(self):
        """测试使用API Key初始化"""
        with patch('forgeai_modules.qwen_reranker.get_rerank_config') as mock_get_config:
            mock_get_config.return_value = {}
            client = QwenRerankerClient(api_key="custom-key")
            
            assert client.api_key == "custom-key"
            assert client.model == "qwen3-rerank"
    
    def test_init_without_api_key(self):
        """测试缺少API Key时抛出异常"""
        with patch('forgeai_modules.qwen_reranker.get_rerank_config') as mock_get_config:
            mock_get_config.return_value = {}
            
            with pytest.raises(ValueError, match="缺少 Rerank API Key"):
                QwenRerankerClient()
    
    def test_init_unsupported_model(self):
        """测试不支持的模型"""
        with patch('forgeai_modules.qwen_reranker.get_rerank_config') as mock_get_config:
            mock_get_config.return_value = {"api_key": "test-key"}
            
            with pytest.raises(ValueError, match="不支持的模型"):
                QwenRerankerClient(api_key="test-key", model="unknown-model")
    
    def test_supported_models(self, client):
        """测试支持的模型列表"""
        assert "qwen3-rerank" in QwenRerankerClient.MODELS
        assert "gte-rerank-v2" in QwenRerankerClient.MODELS
        assert "qwen3-vl-rerank" in QwenRerankerClient.MODELS
    
    def test_build_headers(self, client):
        """测试构建请求头"""
        headers = client._build_headers()
        
        assert "Authorization" in headers
        assert "Bearer" in headers["Authorization"]
        assert "Content-Type" in headers
    
    def test_build_payload_basic(self, client):
        """测试构建基本请求体"""
        payload = client._build_payload(
            query="测试查询",
            documents=["文档1", "文档2"]
        )
        
        assert payload["model"] == "qwen3-rerank"
        assert payload["input"]["query"] == "测试查询"
        assert len(payload["input"]["documents"]) == 2
    
    def test_build_payload_with_top_n(self, client):
        """测试构建带top_n的请求体"""
        payload = client._build_payload(
            query="测试查询",
            documents=["文档1", "文档2"],
            top_n=1
        )
        
        assert payload["parameters"]["top_n"] == 1
    
    def test_build_payload_with_instruct(self, client):
        """测试构建带instruct的请求体"""
        payload = client._build_payload(
            query="测试查询",
            documents=["文档1"],
            instruct="重排序任务"
        )
        
        assert payload["parameters"]["instruct"] == "重排序任务"
    
    def test_parse_response(self, client):
        """测试解析响应"""
        data = {
            "output": {
                "results": [
                    {"index": 0, "relevance_score": 0.95, "document": "文档1"},
                    {"index": 1, "relevance_score": 0.85, "document": "文档2"}
                ]
            }
        }
        
        result = client._parse_response(data)
        
        assert len(result) == 2
        assert result[0]["index"] == 0
        assert result[0]["relevance_score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, client):
        """测试空文档列表"""
        result = await client.rerank(
            query="测试查询",
            documents=[]
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_rerank_exceeds_max_documents(self, client):
        """测试超过最大文档数"""
        # qwen3-rerank最大500个文档
        documents = [f"文档{i}" for i in range(600)]
        
        with patch.object(client, '_get_session') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={
                "output": {"results": [{"index": 0, "relevance_score": 0.9}]}
            })
            
            mock_session_obj = AsyncMock()
            mock_session_obj.post = AsyncMock(return_value=mock_resp)
            mock_session.return_value = mock_session_obj
            
            result = await client.rerank(query="测试", documents=documents)
            
            # 应该截断到最大文档数
            call_args = mock_session_obj.post.call_args
            payload = call_args[1]['json']
            assert len(payload['input']['documents']) <= 500
    
    def test_get_stats(self, client):
        """测试获取统计信息"""
        client.stats.total_calls = 5
        client.stats.total_time = 2.5
        client.stats.errors = 1
        
        stats = client.get_stats()
        
        assert stats["total_calls"] == 5
        assert stats["total_time"] == 2.5
        assert stats["avg_time"] == 0.5
        assert stats["errors"] == 1
    
    def test_estimate_cost(self, client):
        """测试成本估算"""
        cost = client.estimate_cost(num_documents=100, avg_doc_tokens=100)
        
        # qwen3-rerank: 0.0005 per 1k tokens
        # 100 docs * 100 tokens = 10000 tokens
        # cost = 10000 * 0.0005 / 1000 = 0.005
        assert cost > 0
        assert isinstance(cost, float)


class TestQwenRerankerClientAsync:
    """异步操作测试"""
    
    @pytest.fixture
    def client(self):
        """创建客户端"""
        with patch('forgeai_modules.qwen_reranker.get_rerank_config') as mock_get_config:
            mock_get_config.return_value = {"api_key": "test-key"}
            return QwenRerankerClient(api_key="test-key")
    
    @pytest.mark.asyncio
    async def test_rerank_success(self, client):
        """测试成功的重排序"""
        with patch.object(client, '_get_session') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={
                "output": {
                    "results": [
                        {"index": 0, "relevance_score": 0.95},
                        {"index": 1, "relevance_score": 0.85}
                    ]
                }
            })
            
            mock_session_obj = AsyncMock()
            mock_session_obj.post = AsyncMock(return_value=mock_resp)
            mock_session.return_value = mock_session_obj
            
            result = await client.rerank(
                query="测试查询",
                documents=["文档1", "文档2"]
            )
            
            assert result is not None
            assert len(result) == 2
            assert result[0]["relevance_score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_rerank_retry_on_429(self, client):
        """测试429错误重试"""
        client.max_retries = 2
        
        with patch.object(client, '_get_session') as mock_session:
            # 第一次返回429，第二次成功
            mock_resp_429 = AsyncMock()
            mock_resp_429.status = 429
            
            mock_resp_ok = AsyncMock()
            mock_resp_ok.status = 200
            mock_resp_ok.json = AsyncMock(return_value={
                "output": {"results": [{"index": 0, "relevance_score": 0.9}]}
            })
            
            mock_session_obj = AsyncMock()
            mock_session_obj.post = AsyncMock(side_effect=[mock_resp_429, mock_resp_ok])
            mock_session.return_value = mock_session_obj
            
            result = await client.rerank(
                query="测试",
                documents=["文档"]
            )
            
            # 应该重试并成功
            assert result is not None
            assert mock_session_obj.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_rerank_timeout(self, client):
        """测试超时"""
        client.max_retries = 1
        
        with patch.object(client, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session.return_value = mock_session_obj
            
            result = await client.rerank(
                query="测试",
                documents=["文档"]
            )
            
            # 超时后应该返回None
            assert result is None
            assert client.stats.errors == 1
    
    @pytest.mark.asyncio
    async def test_warmup(self, client):
        """测试预热"""
        with patch.object(client, 'rerank', new_callable=AsyncMock) as mock_rerank:
            mock_rerank.return_value = []
            
            await client.warmup()
            
            assert client._warmed_up == True
            mock_rerank.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_session(self, client):
        """测试关闭会话"""
        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session
        
        await client.close()
        
        mock_session.close.assert_called_once()


class TestConvenienceFunction:
    """便捷函数测试"""
    
    @pytest.mark.asyncio
    async def test_qwen_rerank_function(self):
        """测试便捷重排序函数"""
        with patch('forgeai_modules.qwen_reranker.QwenRerankerClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.rerank = AsyncMock(return_value=[
                {"index": 0, "relevance_score": 0.95}
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await qwen_rerank(
                query="测试查询",
                documents=["文档1"],
                api_key="test-key"
            )
            
            assert result is not None
            mock_client.close.assert_called_once()


class TestModelConfigurations:
    """模型配置测试"""
    
    def test_qwen3_rerank_config(self):
        """测试qwen3-rerank配置"""
        config = QwenRerankerClient.MODELS["qwen3-rerank"]
        
        assert config["max_documents"] == 500
        assert config["max_tokens"] == 4000
        assert config["price_per_1k"] == 0.0005
    
    def test_gte_rerank_v2_config(self):
        """测试gte-rerank-v2配置"""
        config = QwenRerankerClient.MODELS["gte-rerank-v2"]
        
        assert config["max_documents"] == 30000
        assert config["max_tokens"] == 8000
    
    def test_qwen3_vl_rerank_config(self):
        """测试qwen3-vl-rerank配置"""
        config = QwenRerankerClient.MODELS["qwen3-vl-rerank"]
        
        assert config["max_documents"] == 100
        assert config["max_tokens"] == 8000


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def client(self):
        """创建客户端"""
        with patch('forgeai_modules.qwen_reranker.get_rerank_config') as mock_get_config:
            mock_get_config.return_value = {"api_key": "test-key"}
            return QwenRerankerClient(api_key="test-key")
    
    def test_parse_empty_response(self, client):
        """测试解析空响应"""
        data = {"output": {"results": []}}
        
        result = client._parse_response(data)
        
        assert result == []
    
    def test_parse_missing_fields(self, client):
        """测试解析缺少字段的响应"""
        data = {
            "output": {
                "results": [
                    {"index": 0}  # 缺少relevance_score
                ]
            }
        }
        
        result = client._parse_response(data)
        
        assert len(result) == 1
        assert result[0]["relevance_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_rerank_with_return_documents(self, client):
        """测试返回文档原文"""
        with patch.object(client, '_get_session') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={
                "output": {
                    "results": [
                        {
                            "index": 0,
                            "relevance_score": 0.95,
                            "document": {"text": "文档内容"}
                        }
                    ]
                }
            })
            
            mock_session_obj = AsyncMock()
            mock_session_obj.post = AsyncMock(return_value=mock_resp)
            mock_session.return_value = mock_session_obj
            
            result = await client.rerank(
                query="测试",
                documents=["文档"],
                return_documents=True
            )
            
            assert result[0]["document"]["text"] == "文档内容"
    
    def test_estimate_cost_zero_documents(self, client):
        """测试零文档成本估算"""
        cost = client.estimate_cost(num_documents=0)
        
        assert cost == 0.0
    
    def test_get_stats_zero_calls(self, client):
        """测试零调用统计"""
        stats = client.get_stats()
        
        # 避免除零错误
        assert stats["avg_time"] == 0.0
