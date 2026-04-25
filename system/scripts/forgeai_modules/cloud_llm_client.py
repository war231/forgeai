"""
云端LLM客户端 - 统一接口
支持OpenAI、DeepSeek、通义千问、文心一言、Claude等主流模型
"""
import os
import json
import time
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

# 延迟导入 logger 以避免循环导入
_logger = None

def _get_logger():
    """延迟获取 logger"""
    global _logger
    if _logger is None:
        from .logger import get_logger
        _logger = get_logger(__name__)
    return _logger


class LLMClient(ABC):
    """LLM客户端抽象基类"""
    
    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话补全"""
        pass
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """文本嵌入"""
        pass
    
    @abstractmethod
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取"""
        pass
    
    @abstractmethod
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI客户端（兼容自定义端点）"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # 使用 env_loader 统一获取配置
        from .env_loader import get_llm_config
        llm_config = get_llm_config()

        self.api_key = api_key or llm_config.get("api_key")
        self.base_url = base_url or llm_config.get("base_url")

        if not self.api_key:
            raise ValueError("缺少 API Key（请设置 LLM_API_KEY 环境变量）")
        
        try:
            import openai
            # 支持自定义 Base URL（如 Kimi API）
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self.client = openai.OpenAI(**client_kwargs)
        except ImportError:
            raise ImportError("请安装openai: pip install openai")
    
    def chat(self, messages: List[Dict], model: str = "gpt-4-turbo-preview", **kwargs) -> str:
        """对话补全"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    def embed(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """文本嵌入"""
        response = self.client.embeddings.create(
            model=model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取"""
        prompt = f"""请从以下文本中提取所有实体，包括：
- 角色（PER）
- 地点（LOC）
- 物品（ITEM）
- 组织（ORG）

文本：
{text}

请以JSON格式输出：
{{
  "characters": ["角色1", "角色2"],
  "locations": ["地点1", "地点2"],
  "items": ["物品1"],
  "organizations": ["组织1"]
}}"""
        
        response = self.chat([{"role": "user", "content": prompt}])
        
        # 解析JSON
        try:
            # 提取JSON部分
            json_match = response[response.find("{"):response.rfind("}")+1]
            return json.loads(json_match)
        except:
            return {"error": "解析失败", "raw_response": response}
    
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析"""
        prompt = f"""你是一位小说编辑，需要检查章节的一致性问题。

上下文信息：
{context}

待检查章节：
{chapter_text}

请检查以下方面：
1. 时间线是否合理
2. 角色状态是否一致（修为、位置、关系）
3. 是否有矛盾或OOC（Out of Character）
4. 是否有未回收的伏笔

请以JSON格式输出：
{{
  "issues": [
    {{
      "type": "timeline/character/worldview/ooc",
      "severity": "error/warning/info",
      "description": "问题描述",
      "suggestion": "修复建议"
    }}
  ],
  "overall_quality": 1-10,
  "summary": "总体评价"
}}"""
        
        response = self.chat([{"role": "user", "content": prompt}])
        
        try:
            json_match = response[response.find("{"):response.rfind("}")+1]
            return json.loads(json_match)
        except:
            return {"error": "解析失败", "raw_response": response}


class DeepSeekClient(LLMClient):
    """DeepSeek客户端"""

    def __init__(self, api_key: Optional[str] = None):
        from .env_loader import get_llm_config
        llm_config = get_llm_config()

        self.api_key = api_key or llm_config.get("api_key")
        if not self.api_key:
            raise ValueError("缺少 API Key（请设置 LLM_API_KEY 环境变量）")

        self.base_url = llm_config.get("base_url") or "https://api.deepseek.com/v1"
        
        try:
            import openai
            # DeepSeek兼容OpenAI接口
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except ImportError:
            raise ImportError("请安装openai: pip install openai")
    
    def chat(self, messages: List[Dict], model: str = "deepseek-chat", **kwargs) -> str:
        """对话补全"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """DeepSeek暂不支持嵌入，使用本地模型"""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            return model.encode(texts).tolist()
        except:
            raise NotImplementedError("DeepSeek不支持嵌入，请安装sentence-transformers")
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取（同OpenAI）"""
        # 实现同OpenAI
        pass
    
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析（同OpenAI）"""
        # 实现同OpenAI
        pass


class QwenClient(LLMClient):
    """通义千问客户端（阿里云）"""

    def __init__(self, api_key: Optional[str] = None):
        from .env_loader import get_llm_config
        llm_config = get_llm_config()

        self.api_key = api_key or llm_config.get("api_key")
        if not self.api_key:
            raise ValueError("缺少 API Key（请设置 LLM_API_KEY 环境变量）")

        try:
            import dashscope
            dashscope.api_key = self.api_key
            self.dashscope = dashscope
        except ImportError:
            raise ImportError("请安装dashscope: pip install dashscope")
    
    def chat(self, messages: List[Dict], model: str = "qwen-plus", **kwargs) -> str:
        """对话补全"""
        from dashscope import Generation
        
        response = Generation.call(
            model=model,
            messages=messages,
            result_format='message',
            **kwargs
        )
        
        return response.output.choices[0].message.content
    
    def embed(self, texts: List[str], model: str = "text-embedding-v2") -> List[List[float]]:
        """文本嵌入"""
        from dashscope import TextEmbedding
        
        response = TextEmbedding.call(
            model=model,
            input=texts
        )
        
        return [item['embedding'] for item in response.output['embeddings']]
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取"""
        # 实现同上
        pass
    
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析"""
        # 实现同上
        pass


class ErnieClient(LLMClient):
    """文心一言客户端（百度）"""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ERNIE_API_KEY")
        self.secret_key = secret_key or os.getenv("ERNIE_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError("缺少 ERNIE_API_KEY 或 ERNIE_SECRET_KEY")

        self.access_token = self._get_access_token()
    
    def _get_access_token(self) -> str:
        """获取access token"""
        import requests
        
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
        
        response = requests.post(url)
        return response.json()['access_token']
    
    def chat(self, messages: List[Dict], model: str = "ernie-bot-4", **kwargs) -> str:
        """对话补全"""
        import requests
        
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxin/workshop/chat/{model}?access_token={self.access_token}"
        
        payload = {
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(url, json=payload)
        return response.json()['result']
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """文本嵌入"""
        import requests
        
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxin_workshop/embedding/embedding-v1?access_token={self.access_token}"
        
        payload = {"input": texts}
        response = requests.post(url, json=payload)
        
        return [item['embedding'] for item in response.json()['data']]
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取"""
        # 实现同上
        pass
    
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析"""
        # 实现同上
        pass


class ClaudeClient(LLMClient):
    """Claude客户端（Anthropic）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("缺少 ANTHROPIC_API_KEY")

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装anthropic: pip install anthropic")
    
    def chat(self, messages: List[Dict], model: str = "claude-3-opus-20240229", **kwargs) -> str:
        """对话补全"""
        # Claude需要提取system message
        system = ""
        chat_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system = msg['content']
            else:
                chat_messages.append(msg)
        
        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=chat_messages,
            **kwargs
        )
        
        return response.content[0].text
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Claude暂不支持嵌入，使用本地模型"""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            return model.encode(texts).tolist()
        except:
            raise NotImplementedError("Claude不支持嵌入，请安装sentence-transformers")
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取"""
        # 实现同上
        pass
    
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析"""
        # 实现同上
        pass


class CloudLLMManager:
    """云端LLM管理器"""
    
    PROVIDERS = {
        "openai": OpenAIClient,
        "deepseek": DeepSeekClient,
        "qwen": QwenClient,
        "ernie": ErnieClient,
        "claude": ClaudeClient,
    }
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """初始化LLM客户端
        
        Args:
            provider: 提供商（kimi/openai/deepseek/qwen/ernie/claude）
            api_key: API密钥（可选，默认从环境变量读取）
            base_url: API端点（可选，默认从环境变量读取）
            model: 模型名称（可选，默认从环境变量读取）
        """
        # 自动从 .env 加载配置
        from .env_loader import get_llm_config
        
        llm_config = get_llm_config()
        
        # 优先使用传入参数，其次使用配置文件
        self.provider = provider or llm_config.get("provider", "openai")
        self.api_key = api_key or llm_config.get("api_key")
        self.base_url = base_url or llm_config.get("base_url")
        self.model = model or llm_config.get("model")
        
        # 根据服务商选择客户端
        if self.provider in ["openai", "kimi"]:
            # OpenAI 客户端支持自定义端点（Kimi 也兼容 OpenAI 接口）
            self.client = OpenAIClient(api_key=self.api_key, base_url=self.base_url)
        elif self.provider not in self.PROVIDERS:
            raise ValueError(f"不支持的提供商: {self.provider}，支持: {list(self.PROVIDERS.keys()) + ['kimi']}")
        else:
            self.client = self.PROVIDERS[self.provider](api_key)
    
    def chat(self, messages: List[Dict], stage: str = "default", **kwargs) -> str:
        """对话补全
        
        Args:
            messages: 对话消息列表
            stage: 创作环节（default/outline/writing/review）
            **kwargs: 其他参数（会覆盖默认参数）
        """
        # 自动加载环节特定参数
        from .env_loader import get_params_for_stage
        stage_params = get_params_for_stage(stage)
        
        # 合并参数（kwargs 优先级最高）
        final_params = {
            "model": self.model,
            **stage_params,
            **kwargs
        }
        
        return self.client.chat(messages, **final_params)
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """文本嵌入"""
        return self.client.embed(texts)
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """实体提取"""
        return self.client.extract_entities(text)
    
    def analyze_consistency(self, context: str, chapter_text: str) -> Dict[str, Any]:
        """一致性分析"""
        return self.client.analyze_consistency(context, chapter_text)
    
    async def chat_completion_async(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """异步对话补全（兼容旧接口）
        
        Args:
            messages: 对话消息列表
            **kwargs: 其他参数
            
        Returns:
            响应字典 {"content": str, "usage": dict, ...}
        """
        # CloudLLMManager 使用同步调用，这里包装为异步
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self.chat(messages, **kwargs))
        # 返回字典格式，兼容旧接口
        return {"content": result}
    
    def get_usage_info(self) -> Dict[str, Any]:
        """获取使用信息"""
        # 服务商特定配置
        PROVIDER_CONFIGS = {
            "kimi": {
                "context_window": 128000,  # Kimi 支持 128K context
                "max_output_tokens": 8192,
                "supports_streaming": True,
            },
            "openai": {
                "context_window": 128000,  # GPT-4-turbo
                "max_output_tokens": 4096,
                "supports_streaming": True,
            },
            "deepseek": {
                "context_window": 64000,
                "max_output_tokens": 4096,
                "supports_streaming": True,
            },
            "qwen": {
                "context_window": 32000,
                "max_output_tokens": 2048,
                "supports_streaming": True,
            },
            "ernie": {
                "context_window": 8000,
                "max_output_tokens": 2048,
                "supports_streaming": False,
            },
            "claude": {
                "context_window": 200000,  # Claude 3
                "max_output_tokens": 4096,
                "supports_streaming": True,
            },
        }
        
        provider_config = PROVIDER_CONFIGS.get(self.provider, {})
        
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "context_window": provider_config.get("context_window", 4096),
            "max_output_tokens": provider_config.get("max_output_tokens", 2048),
            "supports_streaming": provider_config.get("supports_streaming", True),
            "supported_features": {
                "chat": True,
                "embed": hasattr(self.client, 'embed'),
                "extract_entities": True,
                "analyze_consistency": True,
            }
        }


def get_cost_estimate(provider: str, operation: str, tokens: int) -> Dict[str, Any]:
    """获取成本估算
    
    Args:
        provider: 提供商
        operation: 操作类型（chat/embed）
        tokens: token数量
    
    Returns:
        成本信息
    """
    # 价格表（每1K tokens）
    PRICES = {
        "openai": {
            "chat": {"gpt-4": 0.03, "gpt-3.5-turbo": 0.0015},
            "embed": 0.00002,
        },
        "deepseek": {
            "chat": 0.001,
            "embed": None,  # 使用本地模型
        },
        "qwen": {
            "chat": 0.008,
            "embed": 0.0007,
        },
        "ernie": {
            "chat": 0.12,  # 文心一言按次计费，这里估算
            "embed": 0.0002,
        },
        "claude": {
            "chat": {"claude-3-opus": 0.015, "claude-3-sonnet": 0.003},
            "embed": None,  # 使用本地模型
        }
    }
    
    price_info = PRICES.get(provider, {}).get(operation, 0)
    
    if isinstance(price_info, dict):
        # 多个模型价格
        costs = {model: (price * tokens / 1000) for model, price in price_info.items()}
        return {
            "provider": provider,
            "operation": operation,
            "tokens": tokens,
            "costs": costs,
            "cheapest": min(costs.values()),
        }
    elif price_info:
        cost = price_info * tokens / 1000
        return {
            "provider": provider,
            "operation": operation,
            "tokens": tokens,
            "cost": cost,
        }
    else:
        return {
            "provider": provider,
            "operation": operation,
            "tokens": tokens,
            "cost": 0,
            "note": "使用本地模型，无API成本"
        }


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("云端LLM客户端测试")
    print("=" * 60)
    
    # 加载 .env 配置
    from env_loader import print_config_status
    print_config_status()
    
    # 成本估算示例
    print("\n" + "=" * 60)
    print("成本估算示例（检查1章，约2000 tokens）")
    print("=" * 60)
    
    for provider in CloudLLMManager.PROVIDERS:
        estimate = get_cost_estimate(provider, "chat", 2000)
        print(f"\n{provider}:")
        if "costs" in estimate:
            for model, cost in estimate["costs"].items():
                print(f"  {model}: ${cost:.4f}")
        elif "cost" in estimate:
            print(f"  成本: ${estimate['cost']:.4f}")
            if "note" in estimate:
                print(f"  备注: {estimate['note']}")
