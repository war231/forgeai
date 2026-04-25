# Token 管理指南

## 🎯 核心问题

长篇小说创作最容易遇到的问题：**Token 超载**

```
随着小说变长
    ↓
上下文越来越长
    ↓
超过模型上限
    ↓
API 报错或截断
```

---

## 📋 配置方案

### 1. 配置 Token 限制

```env
# 上下文长度配置
LLM_MAX_CONTEXT_TOKENS=128000    # 最大上下文长度（根据模型调整）
LLM_RESERVE_TOKENS=4096          # 预留 tokens（用于输出和系统提示）
```

### 2. 不同模型的配置建议

| 模型 | Context Window | 推荐配置 |
|------|----------------|---------|
| **Kimi** | 128K | `LLM_MAX_CONTEXT_TOKENS=128000` |
| **GPT-4-Turbo** | 128K | `LLM_MAX_CONTEXT_TOKENS=128000` |
| **DeepSeek** | 64K | `LLM_MAX_CONTEXT_TOKENS=64000` |
| **Claude 3** | 200K | `LLM_MAX_CONTEXT_TOKENS=200000` |
| **Qwen** | 32K | `LLM_MAX_CONTEXT_TOKENS=32000` |

---

## 🔧 Token 管理工具

### 1. Token 估算

```python
from forgeai_modules.token_manager import estimate_tokens

# 估算文本的 Token 数量
text = "这是一段测试文本，包含中文和 English words。"
tokens = estimate_tokens(text)
print(f"估算 Tokens: {tokens}")
```

**估算规则**：
- 中文字符：约 1.5 tokens/字
- 英文单词：约 1 token/词
- 标点符号：约 1 token/个

---

### 2. 文本截断

```python
from forgeai_modules.token_manager import truncate_text

# 截断文本到指定 Token 数量
long_text = "这是一段很长的文本。" * 100
truncated, actual_tokens = truncate_text(long_text, max_tokens=50)

print(f"截断后长度: {len(truncated)} 字符")
print(f"实际 Tokens: {actual_tokens}")
```

**截断策略**：
- 按句子分割（优先保留完整句子）
- 从后向前截断（保留开头）

---

### 3. RAG 内容截断

```python
from forgeai_modules.token_manager import truncate_rag_content

# 截断 RAG 召回内容
rag_results = [
    {"content": "角色设定：李天，筑基初期。", "score": 0.9},
    {"content": "世界观：末世修炼体系。", "score": 0.8},
    # ... 更多结果
]

truncated_results, total_tokens = truncate_rag_content(
    rag_results,
    max_tokens=1000,
    keep_first=1  # 保留前 1 个结果
)
```

**截断策略**：
- 保留前 N 个结果（最相关）
- 按优先级截断后续结果

---

### 4. 上下文构建（自动截断）

```python
from forgeai_modules.token_manager import build_context_with_limit

# 构建上下文（自动截断）
context, tokens = build_context_with_limit(
    system_prompt="你是一位小说创作助手。",
    user_prompt="请生成第1章大纲。",
    rag_content="角色设定：李天，筑基初期。",
    previous_chapters="前文内容...",
    max_tokens=128000  # 可选，默认从配置读取
)

print(f"构建的上下文: {tokens} tokens")
```

**优先级**：
```
system_prompt > user_prompt > rag_content > previous_chapters
```

**自动截断流程**：
1. 保留 `system_prompt` 和 `user_prompt`
2. 分配剩余 tokens 给 `rag_content` 和 `previous_chapters`
3. RAG 内容占 70%，前文占 30%

---

## 📊 Token 统计

```python
from forgeai_modules.token_manager import print_token_stats

# 打印 Token 统计信息
print_token_stats(
    system_prompt="你是一位小说创作助手。",
    user_prompt="请生成第1章大纲。",
    rag_content="角色设定：李天，筑基初期。",
    previous_chapters="前文内容..."
)
```

**输出示例**：

```
============================================================
Token 统计
============================================================
系统提示: 16 tokens
用户提示: 12 tokens
RAG 内容: 180 tokens
前文章节: 180 tokens
------------------------------------------------------------
总计: 388 tokens
最大限制: 128,000 tokens
预留空间: 4,096 tokens
可用空间: 123,904 tokens

[OK] 剩余空间 123,516 tokens
============================================================
```

---

## 🚀 实际应用场景

### 场景 1：长篇小说创作

```python
# 问题：小说已写 100 章，上下文超载

# 解决方案：使用 Token 管理器自动截断
from forgeai_modules.token_manager import build_context_with_limit

# 1. 准备各部分内容
system_prompt = "你是一位小说创作助手。"
user_prompt = "请生成第101章大纲。"

# 2. RAG 召回相关内容（可能很长）
rag_content = retrieve_relevant_content("第101章")

# 3. 前文章节（可能很长）
previous_chapters = load_previous_chapters(1, 100)

# 4. 自动构建上下文（自动截断）
context, tokens = build_context_with_limit(
    system_prompt,
    user_prompt,
    rag_content,
    previous_chapters
)

# 5. 发送给 LLM
response = llm.chat([{"role": "user", "content": context}])
```

---

### 场景 2：RAG 内容优化

```python
# 问题：RAG 召回内容过多，占用大量 tokens

# 解决方案：智能截断 RAG 内容
from forgeai_modules.token_manager import truncate_rag_content

# 1. RAG 召回
rag_results = retrieve_relevant_content("主角修炼")

# 2. 智能截断（保留最相关的内容）
truncated_results, tokens = truncate_rag_content(
    rag_results,
    max_tokens=5000,  # 限制 RAG 内容占用
    keep_first=3      # 保留前 3 个最相关结果
)

# 3. 拼接到上下文
rag_content = "\n\n".join([r["content"] for r in truncated_results])
```

---

### 场景 3：多轮对话管理

```python
# 问题：多轮对话历史越来越长

# 解决方案：限制对话历史长度
from forgeai_modules.token_manager import truncate_text

# 1. 加载对话历史
conversation_history = load_conversation_history()

# 2. 截断到指定长度
truncated_history, tokens = truncate_text(
    conversation_history,
    max_tokens=10000  # 限制对话历史占用
)

# 3. 构建消息
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": truncated_history},
    {"role": "user", "content": current_prompt}
]
```

---

## ✅ 最佳实践

### 1. 合理配置 Token 限制

```env
# 根据模型调整
LLM_MAX_CONTEXT_TOKENS=128000  # Kimi/GPT-4-Turbo
LLM_RESERVE_TOKENS=4096        # 预留输出空间
```

### 2. 分层管理上下文

```
系统提示（必须保留）
    ↓
用户提示（必须保留）
    ↓
RAG 内容（优先级高，占 70%）
    ↓
前文章节（优先级低，占 30%）
```

### 3. 监控 Token 使用

```python
# 定期检查 Token 使用情况
from forgeai_modules.token_manager import print_token_stats

print_token_stats(system_prompt, user_prompt, rag_content, previous_chapters)
```

### 4. 避免常见错误

❌ **错误做法**：
```python
# 直接拼接所有内容，可能超载
context = system_prompt + rag_content + previous_chapters + user_prompt
```

✅ **正确做法**：
```python
# 使用 Token 管理器自动截断
context, tokens = build_context_with_limit(
    system_prompt, user_prompt, rag_content, previous_chapters
)
```

---

## 📊 Token 分配示例

### Kimi (128K Context)

```
总容量: 128,000 tokens
    ↓
预留: 4,096 tokens（输出）
    ↓
可用: 123,904 tokens
    ↓
├─ 系统提示: 500 tokens
├─ 用户提示: 200 tokens
├─ RAG 内容: 86,000 tokens (70%)
└─ 前文章节: 37,000 tokens (30%)
```

---

## 🔧 高级用法

### 1. 动态调整 Token 分配

```python
# 根据内容类型动态调整
def get_token_allocation(content_type):
    if content_type == "大纲生成":
        return {"rag": 0.5, "prev": 0.5}  # 大纲需要更多前文
    elif content_type == "正文扩写":
        return {"rag": 0.8, "prev": 0.2}  # 正文需要更多 RAG
    else:
        return {"rag": 0.7, "prev": 0.3}  # 默认
```

### 2. 渐进式截断

```python
# 先尝试完整内容，再逐步截断
def safe_build_context(system, user, rag, prev, max_tokens):
    # 第一次尝试：完整内容
    context, tokens = build_context_with_limit(system, user, rag, prev, max_tokens)
    
    if tokens <= max_tokens:
        return context, tokens
    
    # 第二次尝试：截断前文
    truncated_prev, _ = truncate_text(prev, max_tokens * 0.3)
    context, tokens = build_context_with_limit(system, user, rag, truncated_prev, max_tokens)
    
    if tokens <= max_tokens:
        return context, tokens
    
    # 第三次尝试：截断 RAG
    truncated_rag, _ = truncate_text(rag, max_tokens * 0.7)
    context, tokens = build_context_with_limit(system, user, truncated_rag, truncated_prev, max_tokens)
    
    return context, tokens
```

---

**Token 管理是长篇小说创作的核心，合理配置和自动截断能有效避免超载问题！**
