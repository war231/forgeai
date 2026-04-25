# Integrations — ForgeAI

**Last scanned:** 2026-04-21

---

## LLM API 集成

ForgeAI 通过 `cloud_llm_client.py` 提供统一的LLM客户端接口，支持5大主流模型提供商：

### 支持的LLM提供商

| Provider | 客户端类 | 模型示例 | 用途 |
|----------|---------|---------|------|
| OpenAI | `OpenAIClient` | GPT-4, GPT-3.5 | 通用对话、实体提取、评分 |
| Anthropic | `ClaudeClient` | Claude-3 | 通用对话、审查 |
| DeepSeek | `DeepSeekClient` | deepseek-chat | 通用对话 |
| 通义千问 | `QwenClient` | qwen-max | 通用对话、重排序 |
| 文心一言 | `ErnieClient` | ernie-bot-4 | 通用对话 |

### 抽象接口

```python
class LLMClient(ABC):
    def chat(self, messages, **kwargs) -> str      # 对话补全
    def embed(self, texts) -> List[List[float]]     # 文本嵌入
    def extract_entities(self, text) -> Dict         # 实体提取
```

### 调用场景

| 场景 | 模块 | 使用方式 |
|------|------|---------|
| AI味评分 | `humanize_scorer.py` | LLM辅助评分 |
| 实体提取 | `entity_extractor_v3_ner.py` | NER+LLM提取 |
| 独立审查 | `independent_reviewer.py` | 生成审查提示词 |
| 进化去AI味 | `humanize_scorer.py` | 迭代优化文本 |
| 重排序 | `qwen_reranker.py` | Qwen模型重排序检索结果 |

---

## 向量数据库集成

### ChromaDB

- **模块**: `rag_adapter.py`
- **用途**: 章节语义检索、上下文召回
- **配置**: 本地持久化存储 (`.forgeai/chromadb/`)
- **降级策略**: 当ChromaDB不可用时，回退到BM25检索

### 检索流程

```
用户查询 → RAGAdapter.search()
  → ChromaDB 语义检索 (余弦相似度)
  → 可选: QwenReranker 重排序
  → 返回 top-k 结果
```

---

## 嵌入模型集成

### Sentence-Transformers

- **用途**: 文本向量化
- **默认模型**: 内置中文模型
- **配置**: 通过 `ForgeAIConfig` 设置模型路径

---

## 存储集成

### SQLite

- **模块**: `index_manager.py`
- **用途**: 章节索引、实体数据、伏笔追踪
- **位置**: `.forgeai/index.db`
- **扩展**: `sqlite-vec` (可选向量扩展)

### JSON文件

- **模块**: `state_manager.py`
- **用途**: 项目状态、时间线、倒计时
- **位置**: `.forgeai/state.json`
- **并发控制**: `filelock` 文件锁

---

## API Key 管理

### 环境变量

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，支持自定义端点

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# DeepSeek
DEEPSEEK_API_KEY=...

# 通义千问
QWEN_API_KEY=...

# 文心一言
ERNIE_API_KEY=...
ERNIE_SECRET_KEY=...
```

### 配置文件

```yaml
# .forgeai/config.yaml
llm:
  provider: openai        # 默认提供商
  model: gpt-4            # 默认模型
  api_key: ${OPENAI_API_KEY}
  base_url: https://api.openai.com/v1
```

---

## 安全集成

### 模块: `security.py`

- **路径安全**: 防止路径遍历攻击
- **输入验证**: 配置项和文件输入验证
- **API Key保护**: 环境变量隔离，日志脱敏
- **异常体系**: `exceptions.py` 提供分层异常处理

---

## 外部数据流

```
┌─────────┐     API调用      ┌──────────┐
│ ForgeAI │ ───────────────→ │ LLM APIs │
│  CLI    │ ←─────────────── │ (5家)    │
└────┬────┘     响应结果     └──────────┘
     │
     │ 本地读写
     ▼
┌─────────────────────────────────────┐
│          本地存储层                   │
│  ┌──────────┐ ┌───────┐ ┌────────┐ │
│  │ SQLite   │ │ JSON  │ │ChromaDB│ │
│  │ index.db │ │ state │ │ 向量库 │ │
│  └──────────┘ └───────┘ └────────┘ │
└─────────────────────────────────────┘
```
