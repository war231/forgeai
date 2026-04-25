# Structure — ForgeAI

**Last scanned:** 2026-04-21

---

## 项目根目录

```
forge-ai/
├── .gitignore                  # Git忽略配置
├── .planning/                  # GSD项目管理
│   ├── codebase/               # 代码库分析文档
│   ├── phases/                 # 阶段规划与执行
│   ├── config.json             # GSD配置
│   ├── PROJECT.md              # 项目定义
│   ├── REQUIREMENTS.md         # 需求文档
│   ├── ROADMAP.md              # 路线图
│   └── STATE.md                # 项目状态
├── LICENSE                     # MIT许可证
├── README.md                   # 项目说明
├── CONTRIBUTING.md             # 贡献指南
├── pyproject.toml              # Python包配置 ⭐
├── CHANGELOG.md                # 更新日志
├── STRUCTURE.md                # 旧版结构说明
├── pytest.ini                  # 测试配置
│
├── assets/                     # 静态资源
├── docs/                       # 完整文档体系 ⭐
│   ├── 01-快速开始/             # 安装与入门
│   ├── 02-创作流程/             # 端到端创作流程
│   ├── 03-命令参考/             # CLI命令详解
│   ├── 04-Agent详解/            # 9个Agent详细文档
│   ├── 05-API文档/              # Python API参考
│   ├── 06-故障排查/             # 常见问题与优化
│   └── *.md                    # 历史文档(待整合)
│
├── projects/                   # 小说项目目录
│   └── 测试小说/               # 示例项目
│
├── system/                     # 系统核心 ⭐
│   ├── agents/                 # Agent提示词模板
│   ├── checkers/               # 检查器
│   ├── constitution/           # 创作准则
│   ├── genres/                 # 题材配置
│   ├── references/             # 参考资料
│   ├── scripts/                # 核心代码 ⭐⭐
│   │   ├── __init__.py         # Python包入口
│   │   ├── forgeai.py          # CLI主程序
│   │   ├── forgeai_modules/    # 核心模块 ⭐⭐⭐
│   │   ├── tests/              # 模块测试
│   │   └── requirements.txt    # 依赖清单
│   ├── skills/                 # 技能模板
│   └── templates/              # 项目模板
│
├── tests/                      # 集成测试
│
└── out/                        # 输出目录
```

---

## 核心模块详解 (`system/scripts/forgeai_modules/`)

### 按职责分组

#### 配置与初始化 (4个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `config.py` | 7.5KB | ForgeAIConfig配置类，项目配置加载 |
| `config_validator.py` | 14.6KB | 配置校验与诊断 |
| `env_loader.py` | 11.5KB | 环境变量加载，Token限制 |
| `init_project.py` | 6.2KB | 项目初始化 |

#### 存储层 (3个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `state_manager.py` | 16.4KB | JSON状态管理(实体/伏笔/时间线) |
| `index_manager.py` | 15.9KB | SQLite索引管理(章节/实体/统计) |
| `rag_adapter.py` | 25.5KB | ChromaDB向量检索适配器 |

#### AI/LLM集成 (2个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `cloud_llm_client.py` | 19.5KB | 统一LLM客户端(5家提供商) |
| `qwen_reranker.py` | 10.4KB | Qwen重排序器 |

#### 提取与分析 (4个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `entity_extractor_v3_ner.py` | 18.0KB | NER+LLM实体提取 |
| `context_extractor.py` | 8.4KB | 上下文提取与格式化 |
| `humanize_scorer.py` | 15.2KB | AI味评分与进化优化 |
| `token_manager.py` | 10.4KB | Token计数与预算管理 |

#### 审查系统 (4个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `consistency_checker.py` | 19.0KB | 跨章节一致性检查 |
| `review_pipeline.py` | 15.6KB | 审查流水线(OOC/连贯/追读/高潮) |
| `review_aggregator.py` | 10.8KB | 审查结果汇总 |
| `independent_reviewer.py` | 9.8KB | 独立审查模式 |

#### 专用管理器 (5个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `timeline_manager.py` | 12.8KB | 时间线管理(锚点/倒计时) |
| `growth_analyzer.py` | 21.8KB | 角色成长分析 |
| `volume_manager.py` | 10.1KB | 多卷大纲管理 |
| `rhythm_analyzer.py` | 11.8KB | 节奏分析 |
| `strand_tracker.py` | 12.7KB | 叙事线索追踪 |

#### 确认与修复 (3个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `outline_confirmer.py` | 8.9KB | 大纲确认环节 |
| `state_change_confirmer.py` | 9.3KB | 状态变更确认 |
| `auto_fixer.py` | 12.6KB | 自动修复建议 |

#### 基础设施 (4个模块)

| 文件 | 大小 | 职责 |
|------|------|------|
| `pipeline.py` | 16.2KB | 自动流水线(写前/写后/审查) |
| `logger.py` | 6.8KB | 日志系统(彩色输出) |
| `security.py` | 17.5KB | 安全验证(路径/输入/API Key) |
| `exceptions.py` | 13.7KB | 分层异常体系 |

---

## 文件统计

| 类别 | 数量 | 总大小 |
|------|------|--------|
| Python模块 | 31个 | ~410KB |
| CLI入口 | 1个 | ~50KB |
| 包初始化 | 1个 | ~0.4KB |
| 测试文件 | 32个 | ~200KB |
| 文档文件 | 46个 | ~350KB |
| 配置文件 | 5个 | ~15KB |

---

## 代码行数分布

```
forgeai_modules/          ~12,000行  (核心代码)
├── cloud_llm_client.py    ~700行    (最大单文件)
├── rag_adapter.py         ~900行
├── consistency_checker.py ~650行
├── growth_analyzer.py     ~750行
├── security.py            ~600行
├── 其余26个模块           ~8,400行

forgeai.py (CLI)          ~1,300行
tests/                    ~5,000行
docs/                     ~12,000行 (Markdown)
```

---

## 关键文件路径

| 用途 | 路径 |
|------|------|
| CLI入口 | `system/scripts/forgeai.py` |
| 包入口 | `system/scripts/__init__.py` |
| 核心模块 | `system/scripts/forgeai_modules/` |
| 包配置 | `pyproject.toml` |
| 依赖声明 | `system/scripts/requirements.txt` |
| 项目模板 | `system/templates/` |
| Agent提示词 | `system/agents/` |
| 文档首页 | `docs/01-快速开始/README.md` |
| 测试目录 | `tests/` |

---

## 旧文件清理建议

根目录下存在一些遗留文件，建议清理或整合：

| 文件 | 建议 |
|------|------|
| `None` | 删除（空文件） |
| `test_*.py`（根目录9个） | 移至 `tests/` |
| `test_output.txt` | 移至 `out/` 或删除 |
| `package.json` / `package-lock.json` | 如无Node.js用途则删除 |
| `tsconfig.json` | 如无TypeScript用途则删除 |
| `CLEANUP_SUMMARY.md` | 整合到CHANGELOG后删除 |
| `PROJECT_RESTRUCTURE_PROPOSAL.md` | 已完成重构，归档 |
| `restructure_log.md` | 已完成重构，归档 |
