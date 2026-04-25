# Technology Stack — ForgeAI

**Last scanned:** 2026-04-21  
**Project version:** 1.0.0

---

## Runtime & Language

| Component | Version | Notes |
|-----------|---------|-------|
| Python | >=3.8 | 推荐 3.10+ |
| 操作系统 | OS Independent | Windows/macOS/Linux |
| 包管理 | pip + setuptools | pyproject.toml 配置 |

---

## Core Dependencies

### AI/LLM 集成

| Package | Version | 用途 |
|---------|---------|------|
| `openai` | >=1.0.0 | GPT系列API调用，AI味评分，实体提取 |
| `anthropic` | >=0.18.0 | Claude API调用 |
| `tiktoken` | >=0.5.0 | Token计数与预算管理 |

### 向量检索 (RAG)

| Package | Version | 用途 |
|---------|---------|------|
| `chromadb` | >=0.4.0 | 向量数据库，语义检索 |
| `sentence-transformers` | >=2.2.0 | 文本嵌入模型 |
| `numpy` | >=1.24.0 | 向量运算 |

### 数据处理

| Package | Version | 用途 |
|---------|---------|------|
| `pandas` | >=2.0.0 | 数据分析，统计 |
| `jieba` | >=0.42.0 | 中文分词，BM25检索 |
| `pyyaml` | >=6.0 | YAML配置文件读写 |
| `requests` | >=2.31.0 | HTTP请求 |

### CLI & 终端

| Package | Version | 用途 |
|---------|---------|------|
| `click` | >=8.0.0 | CLI参数解析 |
| `rich` | >=13.0.0 | 终端美化输出 |
| `tqdm` | >=4.65.0 | 进度条 |

### 环境配置

| Package | Version | 用途 |
|---------|---------|------|
| `python-dotenv` | >=1.0.0 | .env文件加载 |

---

## Internal Dependencies (requirements.txt)

| Package | Version | 用途 | 状态 |
|---------|---------|------|------|
| `aiohttp` | >=3.8.0 | 异步HTTP客户端(Embedding API) | 仅qwen_reranker使用 |
| `filelock` | >=3.0.0 | 文件锁(状态文件并发控制) | 仅state_manager使用 |
| `pydantic` | >=2.0.0 | Schema校验 | 内部模块 |
| `sqlite-vec` | >=0.1.0 | SQLite向量扩展(可选) | 可选，降级时回退BM25 |
| `pytest` | >=7.0.0 | 测试框架 | 开发依赖 |
| `pytest-asyncio` | >=0.23.0 | 异步测试 | 开发依赖 |

---

## Optional Dependencies

### 开发工具 (`pip install forgeai[dev]`)

| Package | Version | 用途 |
|---------|---------|------|
| `pytest` | >=7.0.0 | 单元测试 |
| `pytest-cov` | >=4.0.0 | 测试覆盖率 |
| `black` | >=23.0.0 | 代码格式化 |
| `flake8` | >=6.0.0 | 代码检查 |
| `mypy` | >=1.0.0 | 类型检查 |

### 文档工具 (`pip install forgeai[docs]`)

| Package | Version | 用途 |
|---------|---------|------|
| `sphinx` | >=6.0.0 | 文档生成 |
| `sphinx-rtd-theme` | >=1.2.0 | ReadTheDocs主题 |
| `myst-parser` | >=1.0.0 | Markdown解析 |

---

## Transitive Heavy Dependencies

这些依赖通过核心依赖间接引入，体积较大：

| Package | Size | 来源 |
|---------|------|------|
| `torch` | ~2GB | sentence-transformers → transformers |
| `transformers` | ~200MB | sentence-transformers |
| `onnxruntime` | ~150MB | chromadb |
| `scikit-learn` | ~30MB | sentence-transformers |

---

## Build System

| Component | Value |
|-----------|-------|
| Build backend | setuptools >=61.0 |
| Build wheel | Python wheel |
| Entry point | `forgeai = forgeai:main` |
| Package dir | `system/scripts/` |

---

## Version Policy

- Python: 最低支持3.8，推荐3.10+
- 依赖版本: 使用 `>=` 下限约束，不锁定上限
- 开发状态: Beta (4 - Beta)
