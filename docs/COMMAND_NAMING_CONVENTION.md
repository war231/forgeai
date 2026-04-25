# ForgeAI 命令命名规范

## 一、命名原则

### 1. 统一分隔符
- **CLI主命令**：使用 `-` 连接（如 `post-write`, `smart-context`）
- **CLI子命令**：使用 ` ` 空格分隔（如 `entity list`, `volume add`）
- **VSCode命令**：使用驼峰式（如 `forgeAI.initKit`, `forgeAI.sixDimReview`）

### 2. 动词优先
命令以动词开头，明确操作类型：
- `init` - 初始化
- `list` - 列出
- `add` - 添加
- `remove` - 删除
- `update` - 更新
- `check` - 检查
- `analyze` - 分析
- `export` - 导出
- `import` - 导入

### 3. 名词分组
相关命令使用相同的名词前缀：
```
entity list        # 实体管理
entity add
entity remove

volume list        # 卷管理
volume add
volume switch

timeline status    # 时间线管理
timeline add-anchor
```

---

## 二、命令对照表

### 项目管理（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `init` | `init` | ✅ 保持不变 |
| `status` | `status` | ✅ 保持不变 |
| `stats` | `stats` | ✅ 保持不变 |

### 章节管理（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `index <chapter> <file>` | `index <file>` | 自动识别章节号 |
| `search <query>` | `search <query>` | ✅ 保持不变 |
| `context <chapter>` | `context <chapter>` | ✅ 保持不变 |
| `smart-context <chapter>` | `context <chapter> --smart` | 合并到 context |

### 实体管理（统一）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `entity list` | `entity list` | ✅ 保持不变 |
| `entity add --id --name` | `entity add <name>` | 简化参数 |
| `extract <chapter> <file>` | `entity extract <file>` | 归入实体管理 |

### 伏笔管理（统一）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `foreshadowing list` | `foreshadow list` | 缩短名称 |
| `foreshadowing add` | `foreshadow add` | 缩短名称 |
| `foreshadowing resolve` | `foreshadow resolve` | 缩短名称 |

### 时间线管理（统一）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `timeline status` | `timeline status` | ✅ 保持不变 |
| `timeline history` | `timeline list` | 统一动词 |
| `timeline add-anchor` | `timeline add <anchor>` | 简化参数 |
| `timeline add-countdown` | `timeline countdown <name>` | 拆分命令 |

### 写作流程（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `pre-check <chapter>` | `check before <chapter>` | 统一 check |
| `post-write <chapter> <file>` | `check after <file>` | 统一 check |
| `review <chapter>` | `check review <chapter>` | 统一 check |

### AI味处理（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `score <file>` | `score <file>` | ✅ 保持不变 |
| `evolve <file>` | `score <file> --evolve` | 合并到 score |

### 成长分析（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `growth analyze --entity` | `growth <entity>` | 简化参数 |
| `growth report --entity` | `growth <entity> --report` | 添加选项 |
| `growth plot --entity` | `growth <entity> --plot` | 添加选项 |
| `growth compare --entities` | `growth compare <entities>` | 简化参数 |

### 多卷管理（统一）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `volume list` | `volume list` | ✅ 保持不变 |
| `volume add --name` | `volume add <name>` | 简化参数 |
| `volume status --volume` | `volume <id>` | 简化命令 |
| `volume switch --volume` | `volume switch <id>` | 简化参数 |
| `volume complete --volume` | `volume complete <id>` | 简化参数 |
| `volume summary --volume` | `volume <id> --summary` | 添加选项 |

### 一致性检查（统一）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `consistency check --chapter` | `check consistency <chapter>` | 统一 check |
| `consistency batch --start --end` | `check consistency --batch 1-50` | 简化参数 |

### 样板书分析（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `analyze <file>` | `analyze <file>` | ✅ 保持不变 |

### 数据回写（简化）
| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `data update <chapter> <file>` | `update <file>` | 简化命令 |

---

## 三、VSCode命令对照

| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `forgeAI.initKit` | `forgeAI.init` | 简化 |
| `forgeAI.sixDimReview` | `forgeAI.review` | 简化 |
| `forgeAI.scoreText` | `forgeAI.score` | 简化 |
| `forgeAI.extractContext` | `forgeAI.context` | 简化 |
| `forgeAI.search` | `forgeAI.search` | ✅ 保持不变 |
| `forgeAI.status` | `forgeAI.status` | ✅ 保持不变 |
| `forgeAI.indexChapter` | `forgeAI.index` | 简化 |
| `forgeAI.postWrite` | `forgeAI.afterWrite` | 更清晰 |
| `forgeAI.preCheck` | `forgeAI.beforeWrite` | 更清晰 |
| `forgeAI.smartContext` | `forgeAI.smartContext` | ✅ 保持不变 |

---

## 四、实施建议

### 阶段1：保持向后兼容
在重构时保留旧命令，添加新命令作为别名：
```python
# 兼容旧命令
if args.command == "foreshadowing":
    args.command = "foreshadow"
elif args.command == "smart-context":
    args.command = "context"
    args.smart = True
```

### 阶段2：添加弃用警告
```python
if args.command == "foreshadowing":
    print("警告: 'foreshadowing' 已弃用，请使用 'foreshadow'", file=sys.stderr)
    args.command = "foreshadow"
```

### 阶段3：移除旧命令
在下一个主版本中移除旧命令。

---

## 五、最终命令清单

### 核心命令（10个）
```bash
forgeai init [name]              # 初始化项目
forgeai status                   # 项目状态
forgeai index <file>             # 索引章节
forgeai search <query>           # 搜索内容
forgeai context <chapter>        # 提取上下文
forgeai score <file>             # AI味评分
forgeai check <type> <target>    # 检查（before/after/review/consistency）
forgeai update <file>            # 更新数据
forgeai analyze <file>           # 分析样板书
forgeai export [target]          # 导出数据
```

### 管理命令（3组）
```bash
# 实体管理
forgeai entity list [--type]
forgeai entity add <name>
forgeai entity extract <file>

# 伏笔管理
forgeai foreshadow list [--active]
forgeai foreshadow add <desc>
forgeai foreshadow resolve <id>

# 时间线管理
forgeai timeline status
forgeai timeline list
forgeai timeline add <anchor>
forgeai timeline countdown <name>

# 卷管理
forgeai volume list
forgeai volume add <name>
forgeai volume <id>
forgeai volume switch <id>

# 成长分析
forgeai growth <entity>
forgeai growth compare <entities>
```

---

## 六、参数简化规则

1. **必需参数用位置参数**：`entity add <name>` 而非 `entity add --name <name>`
2. **可选参数用选项**：`entity list --type character`
3. **布尔值用标志**：`score --evolve` 而非 `score --evolve true`
4. **范围用简写**：`check consistency --batch 1-50` 而非 `--start 1 --end 50`

---

## 七、示例对比

### 旧命令（冗长）
```bash
python forgeai.py foreshadowing add --description "神秘玉佩" --chapter 1 --payoff 20
python forgeai.py consistency check --chapter 10 --scope full --output report.md
python forgeai.py growth report --entity "李天" --output 成长报告.md
```

### 新命令（简洁）
```bash
python forgeai.py foreshadow add "神秘玉佩" --chapter 1 --payoff 20
python forgeai.py check consistency 10 --output report.md
python forgeai.py growth "李天" --report --output 成长报告.md
```

---

## 八、总结

**优化效果：**
- 命令数量：从 22 个减少到 15 个核心命令
- 参数简化：必需参数改为位置参数，减少输入
- 命名统一：所有命令遵循"动词 名词"模式
- 易记性：命令名称更短、更直观

**实施时间表：**
- Week 1：实现新命令，保持向后兼容
- Week 2：添加弃用警告，更新文档
- Week 3：移除旧命令，发布新版本
