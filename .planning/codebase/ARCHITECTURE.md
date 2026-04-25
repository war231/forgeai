# Architecture — ForgeAI

**Last scanned:** 2026-04-21  
**Architecture style:** Pipeline + Agent-based

---

## 系统架构概览

```
                         ┌─────────────────┐
                         │   ForgeAI CLI   │
                         │  (forgeai.py)   │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              ┌─────▼─────┐ ┌────▼────┐ ┌──────▼──────┐
              │  写前流程  │ │ 写作流程 │ │  写后流程   │
              │ pre-write │ │  write  │ │ post-write  │
              └─────┬─────┘ └────┬────┘ └──────┬──────┘
                    │            │             │
                    └─────────────┼─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │       Pipeline            │
                    │    (自动流水线协调器)       │
                    └─────────────┬─────────────┘
                                  │
           ┌──────────┬───────────┼───────────┬──────────┐
           │          │           │           │          │
     ┌─────▼──┐ ┌────▼────┐ ┌───▼────┐ ┌────▼────┐ ┌──▼──────┐
     │  RAG   │ │ 实体提取 │ │ AI味   │ │ 审查    │ │ 状态    │
     │ 检索   │ │ NER+LLM │ │ 评分   │ │ Pipeline│ │ 管理    │
     └────┬───┘ └────┬────┘ └───┬────┘ └────┬────┘ └──┬──────┘
          │          │          │           │         │
          └──────────┴──────────┴─────┬─────┴─────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │          审查Agent集群               │
                    │   (9个专业审查Agent并行/串行执行)     │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │           存储层                     │
                    │  SQLite + JSON + ChromaDB           │
                    └─────────────────────────────────────┘
```

---

## 核心模块架构

### 1. 配置层 (`config.py`)

```
ForgeAIConfig
├── project_root: Path        # 项目根目录
├── llm: LLMConfig           # LLM配置(provider/model/key)
├── rag: RAGConfig           # RAG配置(chunk_size/top_k)
├── scoring: ScoringConfig   # 评分配置(阈值/权重)
└── review: ReviewConfig     # 审查配置(启用/并行)
```

- **env_loader.py**: 环境变量加载，Token限制配置
- **config_validator.py**: 配置项校验与诊断

### 2. 存储层

| 模块 | 存储 | 数据 |
|------|------|------|
| `state_manager.py` | JSON | 项目状态、实体、伏笔、时间线 |
| `index_manager.py` | SQLite | 章节索引、实体数据、统计数据 |
| `rag_adapter.py` | ChromaDB | 向量索引、语义检索 |

**并发控制**: `filelock` 保护JSON文件并发写入

### 3. RAG检索层

```
RAGAdapter
├── index_chapter()       # 索引章节文本
├── search()             # 语义检索
├── get_stats()          # 检索统计
└── 内部:
    ├── ChromaDB 存储     # 向量数据库
    ├── BM25 降级         # SQLite FTS5
    └── QwenReranker     # 重排序(可选)
```

**检索策略**:
1. 优先使用ChromaDB语义检索
2. ChromaDB不可用时降级到BM25
3. 可选QwenReranker重排序提升精度

### 4. 实体提取层

```
SmartEntityExtractor
├── 规则提取 (NER)        # 正则+模式匹配
│   ├── 人名/地名/组织名
│   ├── 修炼境界
│   └── 关系/状态
├── LLM提取 (可选)        # 调用LLM增强
└── 结果合并              # 去重+置信度排序
```

### 5. AI味评分层

```
HumanizeScorer
├── rule_based_score()    # 规则评分(离线)
│   ├── 重复模式检测
│   ├── AI特征词检测
│   └── 句式多样性分析
├── combined_score()      # 规则+LLM评分
└── evolve()             # 进化式去AI味
    └── 迭代优化文本 → 重新评分 → 直到满意
```

### 6. 审查Agent集群

9个专业审查Agent，通过 `review_pipeline.py` 协调：

| Agent | 模块 | 职责 |
|-------|------|------|
| consistency-checker | `consistency_checker.py` | 设定一致性检查 |
| ooc-checker | `review_pipeline.py`内 | 角色OOC检测 |
| continuity-checker | `review_pipeline.py`内 | 连贯性检查 |
| reader-pull-checker | `review_pipeline.py`内 | 追读力检查 |
| high-point-checker | `review_pipeline.py`内 | 高潮点检查 |
| pacing-checker | `rhythm_analyzer.py` | 节奏检查 |
| timeline-agent | `timeline_manager.py` | 时间线管理 |
| context-agent | `context_extractor.py` | 上下文管理 |
| data-agent | `state_manager.py` + `index_manager.py` | 数据管理 |

**审查流程**:
```
ReviewPipeline
├── 并行执行各Agent审查
├── ReviewAggregator 汇总结果
├── 生成 AggregatedReport
│   ├── overall_score
│   ├── critical/high/medium/low issues
│   └── 各Agent详细报告
└── AutoFixer 自动修复(可选)
```

### 7. 独立审查模式

```
IndependentReviewer
├── 清除上下文 → 避免偏见
├── 生成审查提示词
├── 保存到文件 → 供新对话窗口使用
└── 与主流程解耦 → 独立运行
```

---

## 关键设计模式

### Pipeline模式
`Pipeline` 类协调写前/写后/审查流程，按顺序调用各模块。

### 策略模式
`CloudLLMManager` + `LLMClient` 抽象，支持多LLM提供商切换。

### 降级模式
RAG检索：ChromaDB → BM25，确保功能始终可用。

### 确认模式
`OutlineConfirmer`、`StateChangeConfirmer` 提供关键操作的人工确认环节。

---

## 数据流

### 写后流程 (post_write)

```
章节文本 → Pipeline.post_write()
  ├── RAGAdapter.index_chapter()     → 向量索引
  ├── EntityExtractor.extract()      → 实体/关系/状态
  ├── HumanizeScorer.score()         → AI味评分
  ├── StateManager.update()          → 更新进度
  ├── ReviewPipeline.review()        → 审查Agent集群
  └── 返回汇总结果
```

### 写前流程 (pre_write_check)

```
章节号 → Pipeline.pre_write_check()
  ├── StateManager.load()            → 加载状态
  ├── 检查超期伏笔                    → 提醒
  ├── RhythmAnalyzer.check()         → 节奏失衡警告
  └── 返回检查结果 + 提醒列表
```

### 智能上下文 (smart_context)

```
章节号 + 查询 → Pipeline.smart_context()
  ├── RAGAdapter.search()            → 语义检索相关段落
  ├── StateManager.get_entities()    → 相关实体
  ├── TimelineManager.get_status()   → 时间线状态
  ├── ContextExtractor.format()      → 格式化上下文
  └── 按优先级裁剪到max_chars
```
