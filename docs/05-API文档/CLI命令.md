# CLI命令参考

ForgeAI提供了完整的命令行工具，所有功能都可以通过命令行使用。

## 安装

```bash
pip install forgeai
```

## 全局命令

### forgeai --help

显示帮助信息。

```bash
forgeai --help
forgeai -h
```

### forgeai --version

显示版本信息。

```bash
forgeai --version
forgeai -v
```

### forgeai config

配置管理。

```bash
# 设置API密钥
forgeai config set api.key "your-api-key"

# 设置模型
forgeai config set api.model "gpt-4"

# 查看配置
forgeai config show

# 验证配置
forgeai config check

# 测试API连接
forgeai config test-api

# 应用配置预设
forgeai config apply --preset 轻松幽默
```

---

## 项目管理命令

### forgeai init

创建新项目。

```bash
# 基本创建
forgeai init 我的小说

# 指定类型
forgeai init 我的小说 --genre 都市

# 指定目标字数和章节数
forgeai init 我的小说 --words 500000 --chapters 200

# 从模板创建
forgeai init 我的小说 --template 都市职场

# 完整示例
forgeai init 我的小说 \
  --genre 都市 \
  --words 500000 \
  --chapters 200 \
  --template 都市职场
```

**选项：**
- `--genre`: 小说类型
- `--words`: 目标字数
- `--chapters`: 目标章节数
- `--template`: 项目模板

### forgeai list

列出所有项目。

```bash
forgeai list
forgeai ls
```

### forgeai status

查看项目状态。

```bash
# 当前项目状态
forgeai status

# 指定项目状态
forgeai status --project 我的小说

# 详细状态
forgeai status --verbose
```

### forgeai info

查看项目详细信息。

```bash
forgeai info
forgeai info --project 我的小说
```

---

## 创作命令

### forgeai write

生成章节内容。

```bash
# 生成下一章
forgeai write next

# 生成特定章节
forgeai write chapter 1

# 批量生成
forgeai write chapters 1-10

# 继续创作（从最后一章开始）
forgeai write continue

# 指定字数
forgeai write chapter 1 --words 3000

# 指定风格
forgeai write chapter 1 --style "更紧张悬疑"

# 指定视角
forgeai write chapter 1 --perspective "李明"

# 指定场景
forgeai write chapter 1 --scene "公司办公室"

# 指定情节点
forgeai write chapter 1 --plot-point "李明入职"

# 重新生成
forgeai write chapter 1 --regenerate

# 批量生成并自动审查
forgeai write chapters 1-10 --auto-review

# 批量生成并自动修复
forgeai write chapters 1-10 --auto-fix
```

**选项：**
- `--words`: 目标字数
- `--style`: 写作风格
- `--perspective`: 叙事视角
- `--scene`: 场景设定
- `--plot-point`: 情节点
- `--regenerate`: 重新生成
- `--auto-review`: 自动审查
- `--auto-fix`: 自动修复

### forgeai edit

编辑章节内容。

```bash
# 编辑章节
forgeai edit chapter 1

# 使用指定编辑器
forgeai edit chapter 1 --editor vim
```

### forgeai show

查看章节内容。

```bash
# 查看章节内容
forgeai show chapter 1

# 查看章节摘要
forgeai show chapter 1 --summary

# 查看最近章节
forgeai show last

# 查看多章内容
forgeai show chapters 1-5
```

---

## 审查命令

### forgeai review

审查章节。

```bash
# 审查单章
forgeai review chapter 1

# 审查多章
forgeai review chapters 1-10

# 审查最近章节
forgeai review last

# 使用特定Agent
forgeai review chapter 1 --agent ooc-checker

# 使用多个Agent
forgeai review chapter 1 --agents ooc-checker,continuity-checker

# 使用所有Agent
forgeai review chapter 1 --all-agents

# 全书审查
forgeai review all

# 全书一致性审查
forgeai review all --consistency

# 审查特定维度
forgeai review all --focus character
forgeai review all --focus timeline
forgeai review all --focus plot

# 设置严重度阈值
forgeai review chapter 1 --severity moderate
```

**选项：**
- `--agent`: 使用特定Agent
- `--agents`: 使用多个Agent
- `--all-agents`: 使用所有Agent
- `--consistency`: 一致性审查
- `--focus`: 审查特定维度
- `--severity`: 严重度阈值

### forgeai review show

显示审查结果。

```bash
# 显示审查结果
forgeai review show chapter 1

# 详细显示
forgeai review show chapter 1 --verbose

# 显示特定Agent结果
forgeai review show chapter 1 --agent ooc-checker

# 显示已忽略的问题
forgeai review show chapter 1 --ignored
```

### forgeai review fix

修复审查问题。

```bash
# 自动修复所有问题
forgeai review fix chapter 1 --auto

# 自动修复特定问题
forgeai review fix chapter 1 --issue 1

# 自动修复中等及以上问题
forgeai review fix chapter 1 --severity moderate

# 交互式修复
forgeai review fix chapter 1 --interactive

# 批量修复
forgeai review fix chapters 1-10 --auto
```

**选项：**
- `--auto`: 自动修复
- `--issue`: 特定问题ID
- `--severity`: 严重度阈值
- `--interactive`: 交互式修复

### forgeai review ignore

忽略审查问题。

```bash
# 忽略特定问题
forgeai review ignore chapter 1 --issue 1

# 忽略轻微问题
forgeai review ignore chapter 1 --severity minor
```

### forgeai review export

导出审查结果。

```bash
# 导出审查结果
forgeai review export chapter 1 --output review.json

# 导出为Markdown
forgeai review export chapter 1 --format markdown --output review.md
```

---

## 优化命令

### forgeai optimize

优化章节内容。

```bash
# 优化追读力
forgeai optimize chapter 1 --focus reader-pull

# 优化节奏
forgeai optimize chapter 1 --focus pacing

# 优化对话
forgeai optimize chapter 1 --focus dialogue

# 优化描写
forgeai optimize chapter 1 --focus description

# 批量优化
forgeai optimize chapters 1-10 --focus quality

# 调整风格
forgeai optimize chapter 1 --style "更轻松幽默"
```

**选项：**
- `--focus`: 优化焦点（reader-pull/pacing/dialogue/description/quality）
- `--style`: 写作风格

---

## 角色管理命令

### forgeai character

角色管理。

```bash
# 添加角色
forgeai character add 李明 \
  --age 25 \
  --gender 男 \
  --occupation 程序员

# 查看角色
forgeai character show 李明

# 列出所有角色
forgeai character list

# 编辑角色
forgeai character edit 李明

# 删除角色
forgeai character delete 李明

# 添加角色关系
forgeai character relate 李明 王芳 --type 朋友 --closeness 7
```

---

## 设定管理命令

### forgeai setting

世界设定管理。

```bash
# 添加设定
forgeai setting add 世界观 \
  --time-period 2024年 \
  --technology-level 现代

# 查看设定
forgeai setting show 世界观

# 列出所有设定
forgeai setting list

# 编辑设定
forgeai setting edit 世界观

# 删除设定
forgeai setting delete 世界观
```

---

## 情节管理命令

### forgeai plot

情节管理。

```bash
# 查看情节大纲
forgeai plot show

# 查看情节图谱
forgeai plot view

# 添加情节点
forgeai plot add \
  --chapter 10 \
  --event "李明发现异常数据" \
  --significance 转折点

# 导出情节数据
forgeai plot export --output plot.json
```

---

## 时间线命令

### forgeai timeline

时间线管理。

```python
# 查看时间线
forgeai timeline view

# 检查时间线
forgeai timeline check

# 导出时间线
forgeai timeline export --output timeline.json

# 更新时间线
forgeai timeline update
```

---

## 上下文命令

### forgeai context

上下文管理。

```bash
# 查看上下文
forgeai context view

# 查看上下文摘要
forgeai context summary

# 更新上下文
forgeai context update

# 导出上下文
forgeai context export --output context.json

# 重置上下文
forgeai context reset
```

---

## 报告命令

### forgeai report

生成报告。

```bash
# 生成统计报告
forgeai report stats

# 详细统计
forgeai report stats --detailed

# 生成质量报告
forgeai report quality

# 生成一致性报告
forgeai report consistency

# 导出报告
forgeai report stats --output stats.json
```

---

## 导出命令

### forgeai export

导出成稿。

```bash
# 导出为Markdown
forgeai export --format markdown --output 我的小说.md

# 导出为Word
forgeai export --format docx --output 我的小说.docx

# 导出为PDF
forgeai export --format pdf --output 我的小说.pdf

# 导出为EPUB
forgeai export --format epub --output 我的小说.epub

# 导出为TXT
forgeai export --format txt --output 我的小说.txt

# 批量导出多种格式
forgeai export --formats markdown,docx,pdf --output 我的小说

# 分卷导出
forgeai export --format markdown --split-by 50 --output 卷

# 按三幕结构分卷
forgeai export --format markdown --split-by-act --output 卷

# 包含目录
forgeai export --format markdown --toc --output 我的小说.md

# 包含封面
forgeai export --format pdf --cover cover.jpg --output 我的小说.pdf
```

**选项：**
- `--format`: 导出格式
- `--formats`: 批量导出多种格式
- `--output`: 输出路径
- `--split-by`: 按章节数分卷
- `--split-by-act`: 按三幕结构分卷
- `--toc`: 包含目录
- `--cover`: 封面图片

---

## 备份命令

### forgeai backup

备份管理。

```bash
# 创建备份
forgeai backup create --name "进度备份"

# 创建带标签的备份
forgeai backup create --name "第一版完成" --tag "v1.0"

# 查看备份列表
forgeai backup list

# 查看备份详情
forgeai backup show --name "第一版完成"

# 恢复备份
forgeai backup restore --name "第一版完成"

# 删除备份
forgeai backup delete --name "旧版本"
```

---

## 数据命令

### forgeai data

数据管理。

```bash
# 查看数据统计
forgeai data stats

# 验证数据
forgeai data validate

# 清理数据
forgeai data cleanup

# 导出数据
forgeai data export --output data.json

# 导入数据
forgeai data import --input data.json
```

---

## 搜索命令

### forgeai search

RAG检索。

```bash
# 检索相似场景
forgeai search "职场冲突场景"

# 检索角色信息
forgeai search "李明的性格特点"

# 检索情节元素
forgeai search "悬念设置技巧"

# 设置检索数量
forgeai search "职场冲突" --limit 10
```

---

## 工具命令

### forgeai validate

验证项目。

```bash
# 验证整个项目
forgeai validate

# 验证设定
forgeai validate settings

# 验证角色
forgeai validate characters

# 验证情节
forgeai validate plots
```

### forgeai cleanup

清理临时文件。

```bash
# 清理临时文件
forgeai cleanup

# 清理审查缓存
forgeai cleanup --cache

# 清理旧备份
forgeai cleanup --old-backups --keep 5

# 完全清理
forgeai cleanup --all
```

---

## 环境变量

ForgeAI支持以下环境变量：

```bash
# API密钥
export FORGEAI_API_KEY="your-api-key"

# API模型
export FORGEAI_MODEL="gpt-4"

# API基础URL
export FORGEAI_BASE_URL="https://api.openai.com/v1"

# 配置文件路径
export FORGEAI_CONFIG="path/to/config.yaml"

# 日志级别
export FORGEAI_LOG_LEVEL="INFO"
```

---

## 配置文件

配置文件位于 `.forgeai/config.yaml`，详细说明请参考 [配置文件](配置文件.md)。

---

## 相关文档

- [Python API](Python API.md) - Python API使用
- [配置文件](配置文件.md) - 配置文件详解
- [数据结构](数据结构.md) - 数据结构说明
