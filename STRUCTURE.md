# ForgeAI 系统结构文档

> 最后更新：2026-04-17

---

## 📁 目录结构总览

```
novel-forge-kit/
├── system/                     # 核心系统资源
├── projects/                   # 小说项目目录
├── docs/                       # 文档目录
├── src/                        # VS Code 扩展源码
├── out/                        # 扩展编译输出
├── tests/                      # 测试文件
├── .env                        # 环境配置
├── .env.example               # 配置模板
├── package.json               # 项目配置
├── README.md                  # 项目说明
└── LICENSE                    # 许可证
```

---

## 📂 核心目录详解

### 1. `system/` - 系统核心

```
system/
│
├── agents/                    # Agent定义（9个）
│   ├── consistency-checker.md    # 一致性检查
│   ├── ooc-checker.md           # OOC检查
│   ├── continuity-checker.md    # 连贯性检查
│   ├── reader-pull-checker.md   # 追读力检查
│   ├── high-point-checker.md    # 高潮检查
│   ├── pacing-checker.md        # 节奏检查
│   └── [其他Agent]
│
├── checkers/                  # 检查器模块
│   └── [检查器配置]
│
├── constitution/              # 宪章（创作规范）
│   ├── MASTER.md              # 主宪章
│   └── [其他规范]
│
├── references/                # 参考资料
│   └── [参考文档]
│
├── scripts/                   # Python脚本
│   ├── forgeai.py          # 统一 CLI 入口
│   ├── forgeai_modules/    # 核心模块
│   │   ├── __init__.py
│   │   ├── cloud_llm_client.py      # LLM客户端
│   │   ├── rag_adapter.py           # RAG适配器
│   │   ├── entity_extractor_v3_ner.py # 实体抽取
│   │   ├── qwen_reranker.py         # Reranker客户端
│   │   ├── config.py                # 配置管理
│   │   ├── state_manager.py         # 状态管理
│   │   ├── timeline_manager.py      # 时间线管理
│   │   ├── volume_manager.py        # 卷管理
│   │   ├── growth_analyzer.py       # 成长分析
│   │   ├── rhythm_analyzer.py       # 节奏分析
│   │   ├── humanize_scorer.py       # 人性化评分
│   │   ├── consistency_checker.py   # 一致性检查
│   │   ├── independent_reviewer.py  # 独立审查
│   │   ├── auto_fixer.py            # 自动修复
│   │   ├── context_extractor.py     # 上下文提取
│   │   ├── outline_confirmer.py     # 大纲确认
│   │   ├── state_change_confirmer.py # 状态变更确认
│   │   ├── index_manager.py         # 索引管理
│   │   ├── book_analyzer.py         # 样板书拆解
│   │   └── pipeline.py              # 流水线
│   │
│   └── [其他脚本]
│
├── skills/                    # 技能定义
│   ├── SKILL.md              # 主技能文件
│   ├── define.md             # 定义技能
│   ├── ideation.md           # 构思技能
│   ├── outline.md            # 大纲技能
│   ├── write.md              # 写作技能
│   ├── review.md             # 审查技能
│   ├── book-analyzer.md      # 样板书拆解技能
│   └── guide.md              # 指导技能
│
├── templates/                # 模板文件
│   └── [各种模板]
│
└── genres/                   # 题材模板
    └── [题材配置]
```

### 1b. `projects/` - 小说项目

```
projects/
├── 样板书库/                  # 集中式样板书存储
│   └── {小说名}/
│       └── [样板书文本文件]
│
└── {小说名}/                 # 单个小说项目
    ├── 1-边界/                # 边界条件定义
    ├── 2-设定/                # 小说设定存储
    ├── 3-大纲/                # 章节大纲
    ├── 4-正文/                # 正文内容
    ├── 5-审查/                # 审查报告
    ├── .forgeai/           # 项目配置与运行时数据
    │   ├── memory/           # 记忆存储
    │   ├── constitution/     # 项目级宪章覆盖
    │   └── scripts/          # Python后端副本
    └── SOLOENT.md            # 项目控制面板
```

---

### 2. `tests/` - 测试文件

```
tests/
├── test_connection.py        # API连接测试
└── count_words.py           # 字数统计工具
```

---

### 3. `docs/` - 文档目录

```
docs/
└── [预留，可放置详细文档]
```

---

## 🔧 核心模块说明

### `scripts/forgeai_modules/` 模块功能

| 模块 | 功能 | 状态 |
|------|------|------|
| `cloud_llm_client.py` | LLM API客户端 | ✅ 核心 |
| `rag_adapter.py` | RAG检索适配器 | ✅ 核心 |
| `entity_extractor_v3_ner.py` | NER实体抽取 | ✅ 核心 |
| `qwen_reranker.py` | Qwen3重排序 | ✅ 新增 |
| `config.py` | 配置管理 | ✅ 核心 |
| `state_manager.py` | 角色状态管理 | ✅ 核心 |
| `timeline_manager.py` | 时间线管理 | ✅ 核心 |
| `volume_manager.py` | 卷章节管理 | ✅ 核心 |
| `growth_analyzer.py` | 角色成长分析 | ✅ 核心 |
| `rhythm_analyzer.py` | 节奏分析 | ✅ 核心 |
| `humanize_scorer.py` | AI痕迹检测 | ✅ 核心 |
| `consistency_checker.py` | 设定一致性检查 | ✅ 核心 |
| `independent_reviewer.py` | 独立审查系统 | ✅ 核心 |
| `auto_fixer.py` | 自动修复系统 | ✅ 核心 |
| `context_extractor.py` | 上下文提取 | ✅ 核心 |
| `outline_confirmer.py` | 大纲确认 | ✅ 核心 |
| `state_change_confirmer.py` | 状态变更确认 | ✅ 核心 |
| `index_manager.py` | 索引管理 | ✅ 核心 |
| `pipeline.py` | 主流程流水线 | ✅ 核心 |

---

## 🎯 技能系统架构

### 创作流程

```
构思 (ideation)
    ↓
定义 (define)
    ↓
大纲 (outline)
    ↓
写作 (write)
    ↓
审查 (review)
    ↓
分析 (analyze)
```

### Agent协作

```
写作完成
    ↓
并行审查（Task工具）
    ├─ consistency-checker  (设定一致性)
    ├─ ooc-checker          (人物OOC)
    ├─ continuity-checker   (连贯性)
    └─ reader-pull-checker  (追读力)
    ↓
条件审查（auto路由）
    ├─ high-point-checker   (战斗/关键章)
    └─ pacing-checker       (每10章)
    ↓
审查报告生成
```

---

## 📝 配置文件说明

### `.env` - 环境配置

```bash
# Embedding模型配置
EMBED_BASE_URL=https://api.siliconflow.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=sk-***

# Reranker模型配置
RERANK_BASE_URL=https://api.siliconflow.cn/v1
RERANK_MODEL=Qwen/Qwen3-Reranker-8B
RERANK_API_KEY=sk-***

# LLM模型配置
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-***
```

---

## 🗂️ 数据流架构

### 创作数据流

```
用户输入
    ↓
构思阶段 → 1-边界/
    ↓
定义阶段 → 2-设定/
    ↓
大纲阶段 → 3-大纲/
    ↓
写作阶段 → 4-正文/
    ↓
审查阶段 → 5-审查/
    ↓
最终输出
```

### RAG检索流

```
章节文本
    ↓
分块 (chunk_size=500)
    ↓
Embedding向量化
    ↓
存入 vectors.db
    ↓
查询时：
    ↓
向量检索 + BM25检索
    ↓
RRF融合
    ↓
Reranker精排
    ↓
返回Top-K结果
```

---

## 📊 系统规模

| 项目 | 数量 |
|------|------|
| **总文件数** | 291 |
| **Markdown文档** | 48 |
| **Python文件** | 24 |
| **核心模块** | 19 |
| **Agent定义** | 9 |
| **技能定义** | 7 |
| **总大小** | 25.79 MB |

---

## 🔍 关键路径

### 快速开始

1. **配置API Key**：编辑 `.env` 文件
2. **运行测试**：`python tests/test_connection.py`
3. **启动创作**：使用 `skills/SKILL.md`

### 核心入口

- **技能入口**：`system/skills/SKILL.md`
- **协议定义**：`system/templates/SOLOENT.md`
- **主宪章**：`system/constitution/MASTER.md`

---

## 🎨 扩展建议

### 未来可添加

```
system/
├── plugins/              # 插件系统（预留）
├── themes/               # 主题模板（预留）
└── exports/              # 导出目录（预留）
```

### 文档增强

```
docs/
├── API.md               # API文档
├── CONTRIBUTING.md      # 贡献指南
├── CHANGELOG.md         # 变更日志
└── FAQ.md               # 常见问题
```

---

## 📌 总结

**系统架构特点**：

✅ **模块化设计**：功能分离，易于维护  
✅ **Agent协作**：多Agent并行审查  
✅ **技能驱动**：清晰的工作流程  
✅ **RAG增强**：智能检索与重排序  
✅ **配置灵活**：支持多种模型切换  

**文件组织原则**：

- 按创作阶段分类（1-边界、2-设定、3-大纲、4-正文、5-审查）
- 核心脚本统一管理（scripts/forgeai_modules/）
- 测试文件独立目录（tests/）
- 配置文件根目录（.env）

---

**文档版本**：v1.0  
**最后更新**：2026-04-17
