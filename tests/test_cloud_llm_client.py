#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端LLM客户端测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from forgeai_modules.cloud_llm_client import (
    LLMClient,
    OpenAIClient,
    DeepSeekClient,
    QwenClient,
    ErnieClient,
    ClaudeClient,
    CloudLLMManager,
    get_cost_estimate,
)


class TestLLMClient:
    """LLMClient抽象基类测试"""
    
    def test_llm_client_is_abstract(self):
        """测试LLMClient是抽象类"""
        with pytest.raises(TypeError):
            LLMClient()
    
    def test_llm_client_subclass_must_implement_methods(self):
        """测试子类必须实现所有抽象方法"""
        class IncompleteClient(LLMClient):
            def chat(self, messages, **kwargs):
                return "test"
        
        with pytest.raises(TypeError):
            IncompleteClient()


class TestOpenAIClient:
    """OpenAI客户端测试"""
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_init_with_api_key(self, mock_openai, mock_get_config):
        """测试使用API Key初始化"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_openai.return_value = Mock()
        
        client = OpenAIClient(api_key="custom-key")
        assert client.api_key == "custom-key"
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_init_with_base_url(self, mock_openai, mock_get_config):
        """测试使用自定义Base URL初始化"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_openai.return_value = Mock()
        
        client = OpenAIClient(api_key="test-key", base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    def test_init_without_api_key(self, mock_get_config):
        """测试缺少API Key时抛出异常"""
        mock_get_config.return_value = {"api_key": None, "base_url": None}
        
        with pytest.raises(ValueError, match="缺少 API Key"):
            OpenAIClient()
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_chat(self, mock_openai, mock_get_config):
        """测试对话补全"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="测试回复"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test-key")
        result = client.chat([{"role": "user", "content": "你好"}])
        
        assert result == "测试回复"
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_embed(self, mock_openai, mock_get_config):
        """测试文本嵌入"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test-key")
        result = client.embed(["测试文本"])
        
        assert result == [[0.1, 0.2, 0.3]]
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_extract_entities(self, mock_openai, mock_get_config):
        """测试实体提取"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"characters": ["李天"], "locations": []}'))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test-key")
        result = client.extract_entities("李天是一个修仙者")
        
        assert "characters" in result
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_analyze_consistency(self, mock_openai, mock_get_config):
        """测试一致性分析"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"issues": [], "overall_quality": 8}'))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test-key")
        result = client.analyze_consistency("上下文", "章节内容")
        
        assert "issues" in result


class TestDeepSeekClient:
    """DeepSeek客户端测试"""
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_init(self, mock_openai, mock_get_config):
        """测试初始化"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_openai.return_value = Mock()
        
        client = DeepSeekClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert "deepseek" in client.base_url.lower()
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_chat(self, mock_openai, mock_get_config):
        """测试对话补全"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="DeepSeek回复"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = DeepSeekClient(api_key="test-key")
        result = client.chat([{"role": "user", "content": "你好"}])
        
        assert result == "DeepSeek回复"


class TestQwenClient:
    """通义千问客户端测试"""
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('dashscope.Generation')
    def test_chat(self, mock_generation, mock_get_config):
        """测试对话补全"""
        mock_get_config.return_value = {"api_key": "test-key", "base_url": None}
        mock_response = Mock()
        mock_response.output.choices = [Mock(message=Mock(content="通义千问回复"))]
        mock_generation.call.return_value = mock_response
        
        with patch.dict('sys.modules', {'dashscope': Mock()}):
            client = QwenClient(api_key="test-key")
            client.dashscope = Mock()
            client.dashscope.Generation = mock_generation
            
            result = client.chat([{"role": "user", "content": "你好"}])
            assert result == "通义千问回复"


class TestErnieClient:
    """文心一言客户端测试"""
    
    @patch.dict('os.environ', {'ERNIE_API_KEY': 'test-api', 'ERNIE_SECRET_KEY': 'test-secret'})
    @patch('requests.post')
    def test_get_access_token(self, mock_post):
        """测试获取access token"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'test-token'}
        mock_post.return_value = mock_response
        
        client = ErnieClient()
        assert client.access_token == 'test-token'
    
    @patch.dict('os.environ', {'ERNIE_API_KEY': 'test-api', 'ERNIE_SECRET_KEY': 'test-secret'})
    @patch('requests.post')
    def test_chat(self, mock_post):
        """测试对话补全"""
        # Mock获取token
        mock_token_response = Mock()
        mock_token_response.json.return_value = {'access_token': 'test-token'}
        
        # Mock对话
        mock_chat_response = Mock()
        mock_chat_response.json.return_value = {'result': '文心一言回复'}
        
        mock_post.side_effect = [mock_token_response, mock_chat_response]
        
        client = ErnieClient()
        result = client.chat([{"role": "user", "content": "你好"}])
        
        assert result == '文心一言回复'


class TestClaudeClient:
    """Claude客户端测试"""
    
    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('anthropic.Anthropic')
    def test_init(self, mock_anthropic):
        """测试初始化"""
        mock_anthropic.return_value = Mock()
        
        client = ClaudeClient()
        assert client.api_key == 'test-key'
    
    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('anthropic.Anthropic')
    def test_chat(self, mock_anthropic):
        """测试对话补全"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Claude回复")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        client = ClaudeClient()
        result = client.chat([{"role": "user", "content": "你好"}])
        
        assert result == "Claude回复"
    
    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('anthropic.Anthropic')
    def test_chat_with_system_message(self, mock_anthropic):
        """测试带系统消息的对话"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Claude回复")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        client = ClaudeClient()
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"}
        ]
        result = client.chat(messages)
        
        # 验证系统消息被正确提取
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['system'] == "你是一个助手"


class TestCloudLLMManager:
    """云端LLM管理器测试"""
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('forgeai_modules.cloud_llm_client.get_params_for_stage')
    @patch('openai.OpenAI')
    def test_init_openai(self, mock_openai, mock_get_params, mock_get_config):
        """测试初始化OpenAI"""
        mock_get_config.return_value = {
            "provider": "openai",
            "api_key": "test-key",
            "base_url": None,
            "model": "gpt-4"
        }
        mock_get_params.return_value = {}
        mock_openai.return_value = Mock()
        
        manager = CloudLLMManager(provider="openai", api_key="test-key")
        assert manager.provider == "openai"
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    def test_init_unsupported_provider(self, mock_get_config):
        """测试不支持的提供商"""
        mock_get_config.return_value = {
            "provider": "unknown",
            "api_key": "test-key",
            "base_url": None,
            "model": "unknown"
        }
        
        with pytest.raises(ValueError, match="不支持的提供商"):
            CloudLLMManager(provider="unknown")
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('forgeai_modules.cloud_llm_client.get_params_for_stage')
    @patch('openai.OpenAI')
    def test_chat(self, mock_openai, mock_get_params, mock_get_config):
        """测试对话补全"""
        mock_get_config.return_value = {
            "provider": "openai",
            "api_key": "test-key",
            "base_url": None,
            "model": "gpt-4"
        }
        mock_get_params.return_value = {"temperature": 0.7}
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="测试回复"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        manager = CloudLLMManager(provider="openai", api_key="test-key")
        result = manager.chat([{"role": "user", "content": "你好"}])
        
        assert result == "测试回复"
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_get_usage_info(self, mock_openai, mock_get_config):
        """测试获取使用信息"""
        mock_get_config.return_value = {
            "provider": "openai",
            "api_key": "test-key",
            "base_url": None,
            "model": "gpt-4"
        }
        mock_openai.return_value = Mock()
        
        manager = CloudLLMManager(provider="openai", api_key="test-key")
        info = manager.get_usage_info()
        
        assert info["provider"] == "openai"
        assert "context_window" in info
        assert "supported_features" in info


class TestGetCostEstimate:
    """成本估算测试"""
    
    def test_estimate_openai_chat(self):
        """测试OpenAI对话成本估算"""
        result = get_cost_estimate("openai", "chat", 2000)
        
        assert result["provider"] == "openai"
        assert "costs" in result
        assert "gpt-4" in result["costs"]
    
    def test_estimate_deepseek_chat(self):
        """测试DeepSeek对话成本估算"""
        result = get_cost_estimate("deepseek", "chat", 2000)
        
        assert result["provider"] == "deepseek"
        assert "cost" in result
    
    def test_estimate_with_local_model(self):
        """测试本地模型成本估算"""
        result = get_cost_estimate("deepseek", "embed", 2000)
        
        assert result["cost"] == 0
        assert "note" in result
    
    def test_estimate_unknown_provider(self):
        """测试未知提供商成本估算"""
        result = get_cost_estimate("unknown", "chat", 2000)
        
        assert result["cost"] == 0


class TestIntegration:
    """集成测试"""
    
    @patch('forgeai_modules.cloud_llm_client.get_llm_config')
    @patch('openai.OpenAI')
    def test_full_workflow(self, mock_openai, mock_get_config):
        """测试完整工作流"""
        mock_get_config.return_value = {
            "provider": "openai",
            "api_key": "test-key",
            "base_url": None,
            "model": "gpt-4"
        }
        
        mock_client = Mock()
        mock_chat_response = Mock()
        mock_chat_response.choices = [Mock(message=Mock(content="测试回复"))]
        mock_client.chat.completions.create.return_value = mock_chat_response
        
        mock_embed_response = Mock()
        mock_embed_response.data = [Mock(embedding=[0.1, 0.2])]
        mock_client.embeddings.create.return_value = mock_embed_response
        
        mock_openai.return_value = mock_client
        
        manager = CloudLLMManager(provider="openai", api_key="test-key")
        
        # 测试对话
        chat_result = manager.chat([{"role": "user", "content": "你好"}])
        assert chat_result == "测试回复"
        
        # 测试嵌入
        embed_result = manager.embed(["测试"])
        assert embed_result == [[0.1, 0.2]]
        
        # 测试使用信息
        info = manager.get_usage_info()
        assert info["provider"] == "openai"
