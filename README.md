# ForgeAI - AI小说创作系统

> 一个基于多Agent协作的长篇小说创作系统

---

## 🎯 项目简介

ForgeAI 是一个创新的长篇小说创作系统，通过多Agent协作、RAG检索增强、智能审查等技术，实现高质量的AI辅助小说创作。

### 核心特性

- **多小说项目管理**：支持同时创作多部小说，项目完全隔离
- **样板书拆解**：分析对标作品，提取结构/套路/爽点/文风
- **多Agent协作审查**：9个专业Agent并行审查，确保质量
- **RAG语义检索**：智能召回伏笔、角色状态、相关章节
- **字数智能控制**：每章2300-3000字，符合网文平台要求
- **去AI痕迹**：24种AI写作特征检测，自然流畅
- **环节特定参数**：针对大纲/正文/审查自动调整生成温度
- **Token溢出保护**：智能上下文管理和截断，支持长篇创作

---

## 📁 项目结构

```
forge-ai/
│
├── system/                    # 系统核心（共享）
│   ├── agents/               # 9个Agent定义
│   ├── skills/               # 7个技能定义
│   │   ├── ideation.md       # 创意脑暴
│   │   ├── define.md         # 设定构建
│   │   ├── outline.md        # 大纲规划
│   │   ├── write.md          # 正文创作
│   │   ├── review.md         # 多Agent审查
│   │   ├── humanize.md       # 去AI痕迹
│   │   └── book-analyzer.md  # 样板书拆解（含套路/节奏/文风/爽点分析）
│   ├── constitution/         # 创作宪章
│   ├── scripts/              # 核心Python模块（21个）
│   │   └── forgeai_modules/
│   │       ├── env_loader.py        # 环境配置加载器
│   │       ├── token_manager.py      # Token管理
│   │       ├── cloud_llm_client.py   # LLM客户端
│   │       ├── rag_adapter.py        # RAG检索
│   │       └── ...
│   ├── templates/            # 通用模板
│   └── references/           # 参考资料
│
├── projects/                  # 小说项目（隔离）
│   └── [小说名称]/           # 每部小说独立目录
│       ├── 1-边界/           # 边界约束
│       ├── 2-设定/           # 世界观、角色设定
│       ├── 3-大纲/           # 章节大纲
│       ├── 4-正文/           # 正文内容
│       ├── 5-审查/           # 审查报告
│       └── .forgeai/      # 小说数据（state.json/index.db/vectors.db）
│
├── tests/                     # 测试文件
├── docs/                      # 文档
└── .env                       # 环境配置
```

---

## 🚀 快速开始

### 0. 首次使用：全局配置 API Key

> **重要**：API Key 是全局配置，所有项目共享，配置一次永久生效！

**Step 1: 创建 .env 文件**

在 ForgeAI 根目录创建 `.env` 文件：

```bash
# 位置：forge-ai/.env
# 注意：此文件应添加到 .gitignore，避免泄露密钥
```

**Step 2: 配置 API Key**

编辑 `.env` 文件：

```env
# ==================== 创作大模型 ====================
LLM_PROVIDER=kimi                    # 服务商标识（kimi/openai/deepseek）
LLM_BASE_URL=https://modelservice.jdcloud.com/coding/openai/v1  # API端点
LLM_MODEL=Kimi-K2.5                  # 模型名称
LLM_API_KEY=pk-xxx                   # 你的API密钥

# ==================== 创作参数配置 ====================
LLM_TEMPERATURE=0.7                  # 全局默认温度
LLM_TOP_P=0.9                        # 核采样
LLM_MAX_OUTPUT_TOKENS=4096           # 最大输出tokens

# 环节特定温度（可选）
LLM_TEMPERATURE_OUTLINE=0.4          # 大纲：严谨
LLM_TEMPERATURE_WRITING=1.0          # 正文：发散
LLM_TEMPERATURE_REVIEW=0.3           # 审查：严谨

# ==================== Token管理 ====================
LLM_MAX_CONTEXT_TOKENS=128000         # 模型上下文上限
LLM_RESERVE_TOKENS=4096              # 保留空间

# ==================== Embedding 模型 ====================
EMBED_BASE_URL=https://api.siliconflow.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=sk-xxx

# ==================== Reranker 模型 ====================
RERANK_BASE_URL=https://api.siliconflow.cn/v1
RERANK_MODEL=Qwen/Qwen3-Reranker-8B
RERANK_API_KEY=sk-xxx
```

**Step 3: 验证配置**

```bash
# 检查配置是否正确
python system/scripts/forgeai.py config-check

# 测试 API 连接
python system/scripts/forgeai.py test-connection
```

**重要说明**：
- ✅ API Key 配置一次，所有项目共享
- ✅ `.env` 文件位于 ForgeAI 根目录，不是项目目录
- ✅ `.env` 文件应添加到 `.gitignore`（避免泄露密钥）
- ❌ 不要在每个项目中重复配置 API Key

---

### 1. 创建新小说项目

```bash
# 方式一：使用 CLI 创建（推荐）
python system/scripts/forgeai.py init --name "我的小说" --genre "玄幻"

# 方式二：手动创建
mkdir -p projects/我的小说/{1-边界,2-设定,3-大纲,4-正文,5-审查,.forgeai}

# 创建项目配置文件（可选）
cat > projects/我的小说/novel.config.json << 'EOF'
{
  "novel": {
    "name": "我的小说",
    "genre": "玄幻",
    "status": "连载中"
  },
  "settings": {
    "word_count_per_chapter": {
      "min": 2300,
      "max": 3000
    }
  }
}
EOF
```

**项目配置说明**：
- 项目配置仅包含项目特定参数（名称、题材、字数）
- 不包含 API Key（API Key 是全局配置）
- 可以创建多个项目，共享同一套 API Key

---

### 2. 开始创作

使用技能系统开始创作流程：

1. **拆书**（book-analyzer）- 分析样板书，提取套路/节奏/文风
2. **构思**（ideation）- 确定题材、风格、目标读者
3. **定义**（define）- 世界观、角色、金手指设定
4. **大纲**（outline）- 章节规划、情节节奏
5. **写作**（write）- 正文创作
6. **审查**（review）- 多Agent并行审查
7. **分析**（analyze）- 数据统计、质量分析

---

## 🔧 系统架构

### 创作流程

```
参考模式：
样板书 → book-analyzer → 提取套路/文风
              ↓
         ideation → define → outline → write → review

标准模式：
ideation → define → outline → write → review
```

### Agent协作

```
写作完成
    ↓
并行审查
    ├─ consistency-checker  (设定一致性)
    ├─ ooc-checker          (人物OOC)
    ├─ continuity-checker   (连贯性)
    └─ reader-pull-checker  (追读力)
    ↓
审查报告生成
```

### RAG检索流程

```
章节文本
    ↓
分块 (500字/块)
    ↓
向量化 (Qwen3-Embedding-8B)
    ↓
存入向量数据库
    ↓
查询时：
    ↓
向量检索 + BM25检索
    ↓
RRF融合
    ↓
Reranker精排 (Qwen3-Reranker-8B)
    ↓
返回Top-K结果
```

### 环节参数自动切换

```
创作环节         → 温度   → 适用场景
─────────────────────────────────────
outline (大纲)   → 0.4    → 严谨逻辑，避免矛盾
writing (正文)   → 1.0    → 发散创意，文采飞扬
review (审查)    → 0.3    → 严谨判断，精准识别
default (默认)   → 0.7    → 通用场景
```

---

## 📊 核心模块

| 模块 | 功能 |
|------|------|
| `env_loader.py` | 环境配置加载，支持环节特定参数 |
| `token_manager.py` | Token预算管理与智能截断 |
| `cloud_llm_client.py` | LLM API客户端，自动应用环节参数 |
| `rag_adapter.py` | RAG检索适配器（向量+BM25混合） |
| `entity_extractor_v3_ner.py` | NER实体抽取 |
| `qwen_reranker.py` | Qwen3重排序 |
| `state_manager.py` | 角色状态管理 |
| `timeline_manager.py` | 时间线管理 |
| `growth_analyzer.py` | 角色成长分析 |
| `consistency_checker.py` | 设定一致性检查 |
| `humanize_scorer.py` | AI痕迹检测 |
| `book_analyzer.py` | 样板书拆解分析 |

---

## 📖 样板书拆解

### 使用场景

- **参考模式创作**：分析对标作品，学习其结构和套路
- **套路研究**：提取爽点模式、节奏设计、付费点布局
- **文风学习**：分析叙事风格、对白风格、章节开头结尾模式

### 分析维度

| 维度 | 输出内容 |
|------|---------|
| 结构分析 | 章节字数分布、节奏比例、卷结构 |
| 爽点分析 | 爽点类型分布、密度曲线、高/低密度章节 |
| 套路提取 | 主线套路、黄金三章、付费点设计、周期性套路 |
| 文风提取 | 叙事视角、句长分布、对白密度、开头结尾模式 |
| 人物分析 | 主角塑造方式、配角功能、反派设计 |

### 使用方式

**CLI 命令（推荐）**：

```bash
# 样板书拆解
python forgeai.py analyze 样板书.txt -o ./样板书分析

# 项目初始化
python forgeai.py init --name "我的小说" --genre "玄幻"

# 查看项目状态
python forgeai.py status

# 索引章节
python forgeai.py index 4-正文/第1章.md

# RAG搜索
python forgeai.py search "主角修炼突破"

# 提取上下文
python forgeai.py context 10 --smart

# 一键写作（写前检查+提取上下文+生成提示词）
python forgeai.py write 20 --query "主角和女主角的感情发展"

# AI味评分
python forgeai.py score 4-正文/第1章.md

# 写前检查
python forgeai.py check before 10

# 写后流水线
python forgeai.py check after 10 --text-file 4-正文/第10章.md

# 审查章节
python forgeai.py check review 10

# 独立审查模式(推荐)
python forgeai.py check review 10 --independent

# 一致性检查
python forgeai.py check consistency 10

# 实体管理
python forgeai.py entity list --type character
python forgeai.py entity add "李天" --type character --tier core

# 伏笔管理
python forgeai.py foreshadow list --active
python forgeai.py foreshadow add "神秘玉佩" --chapter 1 --payoff 20
python forgeai.py foreshadow resolve fs001 --chapter 20

# 时间线管理
python forgeai.py timeline status
python forgeai.py timeline add "末世第100天" --chapter 10

# 角色成长分析
python forgeai.py growth "李天" --report --output 成长报告.md
```

**Python 调用**：

```python
from forgeai_modules.book_analyzer import BookAnalyzer

analyzer = BookAnalyzer()
analyzer.load_chapters_from_file("样板书.txt")
analyzer.analyze_all()
analyzer.generate_report("./样板书分析")
```

**输出文件**：

```
1-边界/样板书分析/
├── 分析报告.md        # 综合报告
├── 结构分析.md        # 章节结构
├── 爽点分析.md        # 爽点分布
├── 文风提取.md        # 文风特征
└── 套路提取.md        # 套路模式
```

### 爽点类型

系统自动识别 8 种爽点：

| 类型 | 关键词 |
|------|--------|
| 装逼打脸 | 打脸、嘲讽、碾压、震惊 |
| 扮猪吃虎 | 隐藏、低调、没想到、竟然 |
| 越级反杀 | 越级、反杀、不可能 |
| 身份掉马 | 身份、暴露、真面目 |
| 反派翻车 | 翻车、自食其果、算计 |
| 甜蜜超预期 | 甜蜜、心动、惊喜 |
| 迪化误解 | 误解、以为、脑补 |
| 打脸权威 | 权威、长老、质疑 |

---

## 💡 高级配置

### 环节特定温度

不同创作环节需要不同的"幻觉容忍度"：

```python
from forgeai_modules.cloud_llm_client import CloudLLMManager

llm = CloudLLMManager()

# 大纲创作（自动使用 temperature=0.4）
response = llm.chat(messages, stage="outline")

# 正文创作（自动使用 temperature=1.0）
response = llm.chat(messages, stage="writing")

# 审查（自动使用 temperature=0.3）
response = llm.chat(messages, stage="review")
```

### Token溢出保护

长篇小说创作时自动管理上下文：

```python
from forgeai_modules.token_manager import TokenManager

tm = TokenManager(max_context=128000, reserve=4096)

# 构建带截断的上下文
context = tm.build_context_with_limit(
    system_prompt="...",
    recent_chapters=["第1章内容...", "第2章内容..."],
    rag_content=["相关片段..."],
    max_input_tokens=100000
)
```

---

## 💰 成本估算

### 100章小说创作成本

| 组件 | 模型 | 成本 |
|------|------|------|
| Embedding | Qwen3-Embedding-8B | ¥0.35 |
| Reranker | Qwen3-Reranker-8B | ¥2.50 |
| LLM创作 | DeepSeek/Kimi | ¥5.00 |
| **总计** | - | **¥8** |

---

## 📚 文档

- **配置指南**：`docs/CONFIG_GUIDE.md`
- **Token管理**：`docs/TOKEN_MANAGEMENT.md`
- **阶段参数示例**：`docs/STAGE_PARAMS_EXAMPLE.md`
- **系统结构**：`STRUCTURE.md`
- **变更日志**：`CHANGELOG.md`

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- 通义千问团队 - Qwen3系列模型
- DeepSeek / Kimi团队 - 高性价比LLM
- 所有贡献者

---

**ForgeAI - 让AI创作更自然、更高效**
