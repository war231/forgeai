# ForgeAI 全新创作小说完整流程

> 从零开始创作一本长篇小说的完整指南

---

## 📋 流程概览

```
1. 项目初始化
   ↓
2. 边界定义（可选：样板书分析）
   ↓
3. 世界观与角色设定
   ↓
4. 大纲规划
   ↓
5. 正文创作（循环）
   ↓
6. 审查优化
   ↓
7. 发布
```

---

## 🚀 第一阶段：项目初始化

### 1. 创建项目目录

```bash
# 方式一：使用 CLI 初始化（推荐）
cd e:/xiangmu/小说/forge-ai
python system/scripts/forgeai.py init --name "仙途无双" --genre "玄幻"

# 方式二：手动创建
mkdir -p projects/仙途无双/{1-边界,2-设定,3-大纲,4-正文,5-审查,.forgeai}
```

### 2. 配置 API Key

编辑项目根目录的 `.env` 文件：

```env
# ==================== 创作大模型 ====================
LLM_PROVIDER=kimi
LLM_BASE_URL=https://modelservice.jdcloud.com/coding/openai/v1
LLM_MODEL=Kimi-K2.5
LLM_API_KEY=pk-xxx

# ==================== Embedding 模型 ====================
EMBED_BASE_URL=https://api.siliconflow.cn/v1
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_API_KEY=sk-xxx

# ==================== Reranker 模型 ====================
RERANK_BASE_URL=https://api.siliconflow.cn/v1
RERANK_MODEL=Qwen/Qwen3-Reranker-8B
RERANK_API_KEY=sk-xxx
```

### 3. 验证环境

```bash
# 检查项目状态
python system/scripts/forgeai.py status --project-root projects/仙途无双

# 预期输出：
# {
#   "project": {"name": "仙途无双", "genre": "玄幻"},
#   "progress": {"current_chapter": 0},
#   "entity_count": 0,
#   "active_foreshadowing": 0
# }
```

---

## 📚 第二阶段：边界定义

### 方式一：参考模式（推荐新手）

#### 1. 分析样板书

```bash
# 准备样板书文本文件（如：爆款玄幻小说.txt）
python system/scripts/forgeai.py analyze 样板书.txt \
  --project-root projects/仙途无双 \
  -o projects/仙途无双/1-边界/样板书分析 \
  --from-chapter 1 --to-chapter 50 \
  -v
```

**输出文件**：
```
projects/仙途无双/1-边界/样板书分析/
├── 分析报告.md        # 综合报告
├── 结构分析.md        # 章节结构、字数分布
├── 爽点分析.md        # 爽点类型、密度曲线
├── 文风提取.md        # 叙事风格、对白风格
└── 套路提取.md        # 主线套路、黄金三章
```

#### 2. 创建边界约束文档

在 AI 对话中输入：

```
读取以下文件：
- projects/仙途无双/1-边界/样板书分析/*.md

基于样板书分析，帮我创建：
1. 题材定位（玄幻/都市/仙侠）
2. 目标读者（男频/女频、年龄段）
3. 核心爽点类型（装逼打脸/扮猪吃虎/越级反杀）
4. 字数目标（每章2300-3000字）
5. 节奏要求（爽点密度、付费点布局）
```

将输出保存到 `projects/仙途无双/1-边界/边界约束.md`

### 方式二：标准模式（有经验作者）

直接创建边界文档：

```bash
# 创建边界约束文档
cat > projects/仙途无双/1-边界/边界约束.md << 'EOF'
# 仙途无双 - 边界约束

## 题材定位
- 类型：玄幻修仙
- 风格：热血爽文
- 受众：男频 18-35岁

## 核心爽点
1. 装逼打脸：每3章至少1次
2. 扮猪吃虎：隐藏实力，关键时刻爆发
3. 越级反杀：主角境界低于敌人但仍获胜

## 字数要求
- 每章：2300-3000字
- 每卷：30-50章
- 目标：100万字

## 节奏设计
- 黄金三章：第1章穿越，第2章金手指觉醒，第3章首次打脸
- 付费点：第15章
- 爽点密度：每章至少1个小爽点，每5章1个大爽点

## 禁忌
- 不写女主戏份过多
- 不写主角性格软弱
- 不写重复套路（打脸方式要创新）
EOF
```

---

## 🌍 第三阶段：世界观与角色设定

### 1. 使用技能系统

在 AI 对话中输入：

```
执行技能：define

边界约束：读取 projects/仙途无双/1-边界/边界约束.md

帮我创建：
1. 世界观设定（修炼体系、势力分布、世界地图）
2. 主角设定（姓名、性格、金手指、成长路线）
3. 核心配角（女主、兄弟、反派）
4. 物品设定（法宝、丹药、功法）
```

### 2. 保存设定文档

将输出保存到对应目录：

```
projects/仙途无双/2-设定/
├── 世界观设定.md
├── 主角设定.md
├── 配角设定.md
├── 物品设定.md
└── 势力设定.md
```

### 3. 注册核心实体

```bash
# 注册主角
python system/scripts/forgeai.py entity add "李天" \
  --type character \
  --tier core \
  --project-root projects/仙途无双

# 注册重要配角
python system/scripts/forgeai.py entity add "苏婉儿" \
  --type character \
  --tier important \
  --project-root projects/仙途无双

# 注册势力
python system/scripts/forgeai.py entity add "青云宗" \
  --type faction \
  --tier important \
  --project-root projects/仙途无双

# 查看所有实体
python system/scripts/forgeai.py entity list --project-root projects/仙途无双
```

---

## 📝 第四阶段：大纲规划

### 1. 使用技能系统创建大纲

在 AI 对话中输入：

```
执行技能：outline

边界约束：读取 projects/仙途无双/1-边界/边界约束.md
设定文档：读取 projects/仙途无双/2-设定/*.md

帮我创建：
1. 整体大纲（100章规划）
2. 第一卷详细大纲（30章）
3. 黄金三章详细大纲（前3章）
```

### 2. 保存大纲文档

```
projects/仙途无双/3-大纲/
├── 整体大纲.md
├── 第一卷大纲.md
└── 黄金三章大纲.md
```

### 3. 添加伏笔

```bash
# 添加伏笔
python system/scripts/forgeai.py foreshadow add "神秘玉佩的来历" \
  --chapter 1 \
  --payoff 20 \
  --project-root projects/仙途无双

python system/scripts/forgeai.py foreshadow add "主角身世之谜" \
  --chapter 5 \
  --payoff 50 \
  --project-root projects/仙途无双

# 查看所有伏笔
python system/scripts/forgeai.py foreshadow list --project-root projects/仙途无双
```

---

## ✍️ 第五阶段：正文创作（循环）

### 第1章创作流程

#### 1. 写前检查

```bash
python system/scripts/forgeai.py check before 1 \
  --project-root projects/仙途无双
```

**输出示例**：
```json
{
  "active_foreshadowing": [
    {"id": "fs001", "description": "神秘玉佩的来历", "expected_payoff": 20}
  ],
  "rhythm_status": "正常",
  "debts": []
}
```

#### 2. 提取上下文

```bash
python system/scripts/forgeai.py context 1 \
  --smart \
  --max-chars 8000 \
  --project-root projects/仙途无双
```

#### 3. 使用技能创作

在 AI 对话中输入：

```
执行技能：write

章节号：1
大纲：读取 projects/仙途无双/3-大纲/黄金三章大纲.md 中第1章内容
上下文：[上一步输出的上下文]

创作第1章，要求：
- 字数：2300-3000字
- 埋下伏笔：神秘玉佩的来历
- 爽点：穿越后的首次打脸
```

#### 4. 保存正文

将输出保存到 `projects/仙途无双/4-正文/第1章.md`

#### 5. 写后流水线

```bash
python system/scripts/forgeai.py check after projects/仙途无双/4-正文/第1章.md \
  --project-root projects/仙途无双 \
  --llm \
  --no-score
```

**自动执行**：
1. ✅ 索引章节到向量库
2. ✅ 提取实体和关系
3. ✅ 更新角色状态
4. ✅ 检测伏笔埋设

#### 6. 审查章节

```bash
# 六维审查
python system/scripts/forgeai.py check review 1 \
  --project-root projects/仙途无双
```

**审查维度**：
- ✅ 设定一致性
- ✅ 人物OOC
- ✅ 情节连贯性
- ✅ 追读力
- ✅ 节奏把控
- ✅ 爽点密度

#### 7. AI味评分（可选）

```bash
python system/scripts/forgeai.py score projects/仙途无双/4-正文/第1章.md \
  --project-root projects/仙途无双
```

**输出示例**：
```json
{
  "score": 0.72,
  "human_likeness": 0.75,
  "ai_likeness": 0.28,
  "detected_patterns": [
    {"name": "过度使用形容词", "count": 3, "weight": 0.1}
  ]
}
```

### 第2-100章创作流程

重复以下步骤：

```bash
# 1. 写前检查
python system/scripts/forgeai.py check before <章节号> --project-root projects/仙途无双

# 2. 提取上下文
python system/scripts/forgeai.py context <章节号> --smart --project-root projects/仙途无双

# 3. 在AI对话中创作（使用 write 技能）

# 4. 保存正文到 4-正文/第N章.md

# 5. 写后流水线
python system/scripts/forgeai.py check after 4-正文/第N章.md --project-root projects/仙途无双

# 6. 审查章节
python system/scripts/forgeai.py check review <章节号> --project-root projects/仙途无双

# 7. AI味评分（可选）
python system/scripts/forgeai.py score 4-正文/第N章.md --project-root projects/仙途无双
```

---

## 🔍 第六阶段：数据管理

### 1. 查看项目状态

```bash
python system/scripts/forgeai.py status --project-root projects/仙途无双
```

**输出示例**：
```json
{
  "project": {"name": "仙途无双", "genre": "玄幻"},
  "progress": {"current_chapter": 25, "total_words": 75000},
  "entity_count": 45,
  "active_foreshadowing": 8,
  "resolved_foreshadowing": 3,
  "avg_reading_power": 0.82
}
```

### 2. 实体管理

```bash
# 列出所有角色
python system/scripts/forgeai.py entity list --type character --project-root projects/仙途无双

# 查看角色成长
python system/scripts/forgeai.py growth "李天" --project-root projects/仙途无双

# 生成成长报告
python system/scripts/forgeai.py growth "李天" --report --output 成长报告.md --project-root projects/仙途无双
```

### 3. 伏笔管理

```bash
# 列出活跃伏笔
python system/scripts/forgeai.py foreshadow list --active-only --project-root projects/仙途无双

# 回收伏笔
python system/scripts/forgeai.py foreshadow resolve fs001 --chapter 20 --project-root projects/仙途无双
```

### 4. 时间线管理

```bash
# 查看时间线状态
python system/scripts/forgeai.py timeline status --project-root projects/仙途无双

# 添加时间锚点
python system/scripts/forgeai.py timeline add "修炼第100天" --chapter 25 --project-root projects/仙途无双

# 查看时间线历史
python system/scripts/forgeai.py timeline list --from 1 --to 30 --project-root projects/仙途无双
```

### 5. 一致性检查

```bash
# 单章检查
python system/scripts/forgeai.py check consistency 25 --project-root projects/仙途无双

# 批量检查
python system/scripts/forgeai.py check consistency --start 1 --end 30 --output 一致性报告.md --project-root projects/仙途无双
```

---

## 📊 第七阶段：质量分析

### 1. 统计数据

```bash
python system/scripts/forgeai.py stats --project-root projects/仙途无双
```

**输出示例**：
```json
{
  "index": {
    "total_chapters": 30,
    "total_chunks": 450,
    "total_words": 90000
  },
  "rag": {
    "vector_count": 450,
    "bm25_index_size": "2.3 MB"
  }
}
```

### 2. 搜索内容

```bash
# 搜索相关情节
python system/scripts/forgeai.py search "李天突破境界" --top-k 5 --project-root projects/仙途无双

# 搜索角色互动
python system/scripts/forgeai.py search "李天 苏婉儿" --project-root projects/仙途无双
```

---

## 🎯 完整命令速查表

### 项目管理
```bash
forgeai init --name "小说名" --genre "题材"
forgeai status
forgeai stats
```

### 章节管理
```bash
forgeai index <file>
forgeai search <query>
forgeai context <chapter> --smart
forgeai score <file>
```

### 检查命令
```bash
forgeai check before <chapter>
forgeai check after <file>
forgeai check review <chapter>
forgeai check consistency <chapter>
```

### 数据管理
```bash
forgeai entity list --type <type>
forgeai entity add <name>
forgeai foreshadow list --active
forgeai foreshadow add <desc>
forgeai foreshadow resolve <id>
forgeai timeline status
forgeai timeline add <anchor>
forgeai growth <entity> --report
```

---

## 💡 最佳实践

### 1. 创作节奏

```
每天创作流程：
1. 早上：写前检查 → 提取上下文 → 创作2章
2. 下午：写后流水线 → 审查 → 修改
3. 晚上：数据管理 → 伏笔规划 → 准备明天大纲
```

### 2. 质量控制

```
每5章做一次：
- 一致性检查
- AI味评分
- 伏笔盘点

每卷做一次：
- 角色成长分析
- 时间线梳理
- 整体质量评估
```

### 3. 数据备份

```bash
# 定期备份项目数据
cp -r projects/仙途无双/.forgeai backups/仙途无双_$(date +%Y%m%d)
```

---

## 🆘 常见问题

### Q1: 如何继续创作中断的小说？

```bash
# 1. 查看当前进度
forgeai status --project-root projects/仙途无双

# 2. 查看最后一章内容
forgeai context <最后一章> --smart --project-root projects/仙途无双

# 3. 继续创作
forgeai check before <下一章> --project-root projects/仙途无双
```

### Q2: 如何修改已发布的章节？

```bash
# 1. 重新索引修改后的章节
forgeai index 4-正文/第10章.md --project-root projects/仙途无双

# 2. 更新实体状态
forgeai update 4-正文/第10章.md --project-root projects/仙途无双

# 3. 重新审查
forgeai check consistency 10 --project-root projects/仙途无双
```

### Q3: 如何处理伏笔遗忘？

```bash
# 1. 查看所有活跃伏笔
forgeai foreshadow list --active --project-root projects/仙途无双

# 2. 搜索相关章节
forgeai search "玉佩" --project-root projects/仙途无双

# 3. 在新章节中回收
# 在创作时提醒AI回收该伏笔
```

---

## 📚 相关文档

- [命令命名规范](./COMMAND_NAMING_CONVENTION.md)
- [迁移指南](./MIGRATION_GUIDE.md)
- [样板书拆解指南](./BOOK_ANALYSIS_GUIDE.md)

---

**祝你创作顺利！** 🎉
