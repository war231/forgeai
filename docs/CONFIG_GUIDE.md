# ForgeAI 配置指南

## 📋 配置文件格式

配置文件位于项目根目录的 `.env` 文件中：

```env
# ==================== 创作大模型 ====================
LLM_PROVIDER=kimi                    # 服务商标识（用于针对性处理）
LLM_BASE_URL=https://xxx/v1          # API 端点 URL
LLM_MODEL=Kimi-K2.5                  # 模型名称
LLM_API_KEY=pk-xxx                   # API 密钥

# ==================== 创作参数配置 ====================
# 全局默认参数
LLM_TEMPERATURE=0.7                  # 默认温度（0.0-2.0）
LLM_TOP_P=0.9                        # 默认核采样（0.0-1.0）
LLM_MAX_TOKENS=4096                  # 默认最大输出 tokens

# 环节特定参数（可选，不配置则使用默认值）
LLM_TEMPERATURE_OUTLINE=0.4          # 大纲温度（严谨）
LLM_TEMPERATURE_WRITING=1.0          # 正文温度（发散）
LLM_TEMPERATURE_REVIEW=0.3           # 审查温度（严谨）

# ==================== Embedding 模型 ====================
EMBED_BASE_URL=https://api.siliconflow.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=sk-xxx

# ==================== Reranker 模型 ====================
RERANK_BASE_URL=https://api.siliconflow.cn/v1
RERANK_MODEL=Qwen/Qwen3-Reranker-8B
RERANK_API_KEY=sk-xxx
```

---

## 🎯 配置项说明

### 创作大模型配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `LLM_PROVIDER` | 服务商标识（用于针对性处理） | `kimi`, `openai`, `deepseek` |
| `LLM_BASE_URL` | API 端点 URL | `https://modelservice.jdcloud.com/coding/openai/v1` |
| `LLM_MODEL` | 模型名称 | `Kimi-K2.5`, `gpt-4-turbo` |
| `LLM_API_KEY` | API 密钥 | `pk-xxx` |

---

## 🌡️ 创作参数配置

### 为什么不同环节需要不同的温度？

| 创作环节 | 温度范围 | 原因 |
|---------|---------|------|
| **大纲/世界观设定** | 0.3-0.5 | 需要严谨，避免逻辑矛盾 |
| **正文描写/扩写** | 0.8-1.2 | 需要发散和文采，增加创意 |
| **审查/分析** | 0.2-0.4 | 需要严谨判断，避免误判 |

### 配置示例

```env
# 全局默认参数
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9
LLM_MAX_TOKENS=4096

# 大纲环节：低温度（严谨）
LLM_TEMPERATURE_OUTLINE=0.4

# 正文环节：高温度（发散）
LLM_TEMPERATURE_WRITING=1.0

# 审查环节：低温度（严谨）
LLM_TEMPERATURE_REVIEW=0.3
```

---

## 💡 使用示例

### 自动应用环节参数

```python
from forgeai_modules.cloud_llm_client import CloudLLMManager

llm = CloudLLMManager()

# 大纲创作（自动使用 temperature=0.4）
response = llm.chat(
    messages=[{"role": "user", "content": "生成第1章大纲"}],
    stage="outline"  # 自动应用大纲参数
)

# 正文创作（自动使用 temperature=1.0）
response = llm.chat(
    messages=[{"role": "user", "content": "扩写第1章正文"}],
    stage="writing"  # 自动应用正文参数
)

# 审查（自动使用 temperature=0.3）
response = llm.chat(
    messages=[{"role": "user", "content": "审查第1章"}],
    stage="review"  # 自动应用审查参数
)
```

### 手动覆盖参数

```python
# 手动覆盖温度
response = llm.chat(
    messages=[{"role": "user", "content": "生成大纲"}],
    stage="outline",
    temperature=0.2  # 手动覆盖，优先级最高
)
```

---

## 🔄 参数加载流程

```
调用 chat(stage="outline")
    ↓
加载 .env 配置
    ↓
获取环节特定参数（temperature=0.4）
    ↓
合并默认参数（top_p=0.9, max_tokens=4096）
    ↓
应用最终参数到 LLM
    ↓
生成内容
```

---

## 📊 参数优先级

```
手动传入参数 > 环节特定参数 > 全局默认参数
```

示例：

```python
# 场景 1：使用全局默认参数
llm.chat(messages, stage="default")
# → temperature=0.7, top_p=0.9, max_tokens=4096

# 场景 2：使用环节特定参数
llm.chat(messages, stage="outline")
# → temperature=0.4, top_p=0.9, max_tokens=4096

# 场景 3：手动覆盖参数
llm.chat(messages, stage="outline", temperature=0.2)
# → temperature=0.2, top_p=0.9, max_tokens=4096
```

---

## ✅ 配置验证

运行测试脚本验证配置：

```bash
python test_config.py
```

输出示例：

```
[创作参数配置]
  默认温度: 0.7
  默认Top-P: 0.9
  默认Max Tokens: 4096
  大纲温度: 0.4 (严谨)
  正文温度: 1.0 (发散)
  审查温度: 0.3 (严谨)

[OK] 环节参数配置成功
```

---

## 🔧 常见问题

### Q: 为什么大纲需要低温度？

A: 大纲和世界观设定需要严谨的逻辑，避免出现矛盾。低温度（0.3-0.5）会让模型更保守，减少幻觉，确保设定的合理性。

### Q: 为什么正文需要高温度？

A: 正文描写需要创意和文采，高温度（0.8-1.2）会让模型更发散，产生更多样化的表达，避免内容单调。

### Q: 如何为其他环节添加参数？

A: 在 `.env` 中添加新的配置项：

```env
LLM_TEMPERATURE_BRAINSTORM=1.2  # 头脑风暴环节
```

然后在代码中使用：

```python
from forgeai_modules.env_loader import get_params_for_stage

params = get_params_for_stage("brainstorm")
```

---

**配置系统支持环节特定参数，让不同创作环节自动应用最优参数！**
