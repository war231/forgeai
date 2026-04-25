# ForgeAI 命令迁移指南

> 从 v1.x 升级到 v2.0 的命令变更指南

---

## 📋 快速迁移对照表

### CLI 命令

| 旧命令 (v1.x) | 新命令 (v2.0) | 说明 |
|--------------|--------------|------|
| `foreshadowing` | `foreshadow` | 缩短名称 |
| `smart-context <chapter>` | `context <chapter> --smart` | 合并到 context |
| `evolve <file>` | `score <file> --evolve` | 合并到 score |
| `pre-check <chapter>` | `check before <chapter>` | 统一 check 命令族 |
| `post-write <chapter> <file>` | `check after <file>` | 统一 check 命令族 |
| `review <chapter>` | `check review <chapter>` | 统一 check 命令族 |
| `consistency check --chapter` | `check consistency <chapter>` | 统一 check 命令族 |

### VSCode 命令

| 旧命令 (v1.x) | 新命令 (v2.0) | 说明 |
|--------------|--------------|------|
| `forgeAI.initKit` | `forgeAI.init` | 简化名称 |
| `forgeAI.sixDimReview` | `forgeAI.review` | 简化名称 |
| `forgeAI.scoreText` | `forgeAI.score` | 简化名称 |
| `forgeAI.extractContext` | `forgeAI.context` | 简化名称 |
| `forgeAI.indexChapter` | `forgeAI.index` | 简化名称 |
| `forgeAI.postWrite` | `forgeAI.afterWrite` | 更清晰命名 |
| `forgeAI.preCheck` | `forgeAI.beforeWrite` | 更清晰命名 |

---

## 🔄 自动兼容

**好消息：v2.0 保持向后兼容！**

所有旧命令仍然可用，但会显示弃用警告：

```bash
$ python forgeai.py foreshadowing list
[警告] foreshadowing 已弃用，请使用 foreshadow
# ... 正常输出 ...
```

---

## 📝 迁移步骤

### 1. 更新脚本和别名

如果你有自定义脚本使用旧命令：

```bash
# 旧脚本
python forgeai.py smart-context 10 --query "战斗场景"

# 新脚本
python forgeai.py context 10 --smart --query "战斗场景"
```

### 2. 更新 VSCode 快捷键绑定

如果你在 `keybindings.json` 中配置了快捷键：

```json
// 旧配置
{
    "key": "ctrl+shift+r",
    "command": "forgeAI.sixDimReview"
}

// 新配置
{
    "key": "ctrl+shift+r",
    "command": "forgeAI.review"
}
```

### 3. 更新文档和教程

搜索并替换以下内容：

```
foreshadowing → foreshadow
smart-context → context --smart
evolve → score --evolve
pre-check → check before
post-write → check after
```

---

## 🎯 新命令优势

### 1. 更简洁

```bash
# 旧命令
python forgeai.py foreshadowing add --description "神秘玉佩" --chapter 1

# 新命令（支持位置参数）
python forgeai.py foreshadow add "神秘玉佩" --chapter 1
```

### 2. 更统一

```bash
# 所有检查命令统一为 check
python forgeai.py check before 10      # 写前检查
python forgeai.py check after file.md  # 写后流水线
python forgeai.py check review 10      # 审查章节
python forgeai.py check consistency 10 # 一致性检查
```

### 3. 更易记

```bash
# 命令合并，减少记忆负担
python forgeai.py context 10           # 普通上下文
python forgeai.py context 10 --smart   # 智能上下文

python forgeai.py score file.md        # AI味评分
python forgeai.py score file.md --evolve  # 进化式优化
```

---

## 📊 完整命令列表

### 核心命令（15个）

```bash
# 项目管理
forgeai init [name]              # 初始化项目
forgeai status                   # 项目状态
forgeai stats                    # 统计信息

# 章节管理
forgeai index <file>             # 索引章节
forgeai search <query>           # 搜索内容
forgeai context <chapter>        # 提取上下文
forgeai score <file>             # AI味评分

# 统一检查
forgeai check before <chapter>   # 写前检查
forgeai check after <file>       # 写后流水线
forgeai check review <chapter>   # 审查章节
forgeai check consistency <chapter>  # 一致性检查

# 数据管理
forgeai update <file>            # 更新数据
forgeai analyze <file>           # 分析样板书
```

### 管理命令（4组）

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

## ⚠️ 弃用时间表

| 版本 | 状态 | 说明 |
|------|------|------|
| v2.0 | 弃用警告 | 旧命令可用，显示警告 |
| v2.1 | 保留 | 旧命令可用，无警告 |
| v3.0 | 移除 | 旧命令不再支持 |

**建议：在 v3.0 发布前完成迁移**

---

## 🔧 迁移工具

### 自动迁移脚本

```bash
# 在项目根目录运行
python scripts/migrate_commands.py
```

该脚本会：
1. 扫描所有 `.md`, `.sh`, `.py` 文件
2. 替换旧命令为新命令
3. 生成迁移报告

### 手动检查

```bash
# 查找使用旧命令的文件
grep -r "foreshadowing\|smart-context\|evolve\|pre-check\|post-write" .
```

---

## 💡 常见问题

### Q: 旧命令会立即失效吗？

**A: 不会。** v2.0 保持完全向后兼容，旧命令会继续工作，只显示弃用警告。

### Q: 必须立即迁移吗？

**A: 不必须。** 但建议在 v3.0 发布前完成迁移，届时旧命令将被移除。

### Q: 新旧命令可以混用吗？

**A: 可以。** 但建议统一使用新命令，避免混淆。

### Q: VSCode 快捷键需要重新配置吗？

**A: 不需要。** 旧命令的快捷键仍然有效，但建议更新为新命令。

---

## 📚 相关文档

- [命令命名规范](./COMMAND_NAMING_CONVENTION.md)
- [CLI 完整文档](./CLI_REFERENCE.md)
- [VSCode 扩展文档](./VSCODE_EXTENSION.md)

---

## 🎉 迁移完成后

迁移完成后，你将享受：

✅ 更简洁的命令（平均减少 33% 字符）  
✅ 更统一的命名规范  
✅ 更少的命令数量（22 → 15）  
✅ 更好的可发现性（check 命令族）  
✅ 更低的学习曲线

---

**需要帮助？** 在 GitHub Issues 中提问，或查看 [命令命名规范](./COMMAND_NAMING_CONVENTION.md)。
