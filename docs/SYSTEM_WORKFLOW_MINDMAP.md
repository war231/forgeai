# ForgeAI 系统工作流程思维导图

> 完整的 AI 小说创作系统工作流程全景图

---

## 🎯 系统核心架构

```
ForgeAI 系统
│
├─ 📁 项目管理层
│   ├─ 多小说项目管理
│   ├─ 项目隔离机制
│   └─ 状态跟踪系统
│
├─ 🤖 Agent 协作层
│   ├─ Context Agent (上下文提取)
│   ├─ Data Agent (数据管理)
│   └─ 审查 Agents (质量保障)
│       ├─ consistency-checker (设定一致性)
│       ├─ ooc-checker (人物OOC)
│       ├─ continuity-checker (连贯性)
│       ├─ reader-pull-checker (追读力)
│       ├─ high-point-checker (高潮点)
│       └─ pacing-checker (节奏把控)
│
├─ 🔧 核心功能层
│   ├─ RAG 检索系统
│   ├─ Token 管理系统
│   ├─ 实体管理系统
│   ├─ 伏笔管理系统
│   ├─ 时间线管理
│   └─ AI 味检测系统
│
└─ 📊 数据层
    ├─ 向量数据库 (vectors.db)
    ├─ 索引数据库 (index.db)
    ├─ 状态文件 (state.json)
    └─ 配置文件 (config.json)
```

---

## 🚀 完整创作流程

### 〇、系统安装与配置阶段（首次使用）

```
系统安装与全局配置
│
├─ Step 1: 安装 ForgeAI
│   ├─ 克隆仓库: git clone <repo-url>
│   ├─ 安装依赖: pip install -r requirements.txt
│   └─ 验证安装: python forgeai.py --version
│
├─ Step 2: 配置全局 API Key（重要！）
│   │
│   ├─ 创建 .env 文件（项目根目录）
│   │   └─ 位置: forge-ai/.env
│   │
│   ├─ LLM API 配置（创作模型）
│   │   ├─ LLM_PROVIDER=kimi (服务商: kimi/openai/deepseek)
│   │   ├─ LLM_BASE_URL=https://modelservice.jdcloud.com/coding/openai/v1
│   │   ├─ LLM_MODEL=Kimi-K2.5 (模型名称)
│   │   └─ LLM_API_KEY=pk-xxx (你的密钥)
│   │
│   ├─ Embedding API 配置（向量化）
│   │   ├─ EMBED_BASE_URL=https://api.siliconflow.cn/v1
│   │   ├─ EMBED_MODEL=Qwen/Qwen3-Embedding-8B
│   │   └─ EMBED_API_KEY=sk-xxx
│   │
│   ├─ Reranker API 配置（重排序）
│   │   ├─ RERANK_BASE_URL=https://api.siliconflow.cn/v1
│   │   ├─ RERANK_MODEL=Qwen/Qwen3-Reranker-8B
│   │   └─ RERANK_API_KEY=sk-xxx
│   │
│   └─ 创作参数配置（可选）
│       ├─ LLM_TEMPERATURE=0.7 (全局默认温度)
│       ├─ LLM_TOP_P=0.9 (核采样)
│       ├─ LLM_MAX_OUTPUT_TOKENS=4096 (最大输出)
│       ├─ LLM_TEMPERATURE_OUTLINE=0.4 (大纲温度)
│       ├─ LLM_TEMPERATURE_WRITING=1.0 (正文温度)
│       └─ LLM_TEMPERATURE_REVIEW=0.3 (审查温度)
│
├─ Step 3: 验证全局配置
│   ├─ 检查配置: python forgeai.py config-check
│   └─ 测试连接: python forgeai.py test-connection
│
└─ Step 4: 系统就绪
    └─ 可以开始创建项目了！
```

**重要说明**：
- ✅ API Key 是**全局配置**，所有项目共享
- ✅ 配置一次，永久生效（除非更换密钥）
- ✅ `.env` 文件应该添加到 `.gitignore`（避免泄露密钥）
- ❌ 不要在每个项目中重复配置 API Key

---

### 一、项目初始化阶段

```
项目初始化
│
├─ Step 1: 创建项目目录
│   ├─ 使用 CLI: forgeai init --name "小说名" --genre "题材"
│   └─ 手动创建: mkdir -p projects/小说名/{1-边界,2-设定,3-大纲,4-正文,5-审查,.forgeai}
│
├─ Step 2: 创建项目配置（可选）
│   └─ 创建: projects/小说名/novel.config.json
│       ├─ 小说名称、题材、状态
│       └─ 字数要求、创作参数（可覆盖全局配置）
│
└─ Step 3: 验证项目
    └─ forgeai status --project-root projects/小说名
```

---

### 二、边界定义阶段

```
边界定义
│
├─ 方式一：参考模式（推荐新手）
│   │
│   ├─ Step 1: 分析样板书
│   │   ├─ 命令: forgeai analyze 样板书.txt
│   │   └─ 输出:
│   │       ├─ 分析报告.md (综合报告)
│   │       ├─ 结构分析.md (章节结构、字数分布)
│   │       ├─ 爽点分析.md (爽点类型、密度曲线)
│   │       ├─ 文风提取.md (叙事风格、对白风格)
│   │       └─ 套路提取.md (主线套路、黄金三章)
│   │
│   └─ Step 2: 创建边界约束文档
│       ├─ 题材定位 (玄幻/都市/仙侠)
│       ├─ 目标读者 (男频/女频、年龄段)
│       ├─ 核心爽点类型 (装逼打脸/扮猪吃虎/越级反杀)
│       ├─ 字数目标 (每章2300-3000字)
│       ├─ 节奏要求 (爽点密度、付费点布局)
│       └─ 禁忌事项
│
└─ 方式二：标准模式（有经验作者）
    └─ 直接创建边界文档
        ├─ 题材定位
        ├─ 核心爽点
        ├─ 字数要求
        ├─ 节奏设计
        └─ 禁忌
```

---

### 三、设定构建阶段

```
世界观与角色设定
│
├─ Step 1: 使用技能系统
│   └─ 执行技能: define
│       ├─ 输入: 边界约束文档
│       └─ 输出:
│           ├─ 世界观设定 (修炼体系、势力分布、世界地图)
│           ├─ 主角设定 (姓名、性格、金手指、成长路线)
│           ├─ 核心配角 (女主、兄弟、反派)
│           └─ 物品设定 (法宝、丹药、功法)
│
├─ Step 2: 保存设定文档
│   └─ 保存到: projects/小说名/2-设定/
│       ├─ 世界观设定.md
│       ├─ 主角设定.md
│       ├─ 配角设定.md
│       ├─ 物品设定.md
│       └─ 势力设定.md
│
└─ Step 3: 注册核心实体
    ├─ forgeai entity add "主角名" --type character --tier core
    ├─ forgeai entity add "女主名" --type character --tier important
    ├─ forgeai entity add "势力名" --type faction --tier important
    └─ forgeai entity list (查看所有实体)
```

---

### 四、大纲规划阶段

```
大纲规划
│
├─ Step 1: 使用技能系统创建大纲
│   └─ 执行技能: outline
│       ├─ 输入: 边界约束 + 设定文档
│       └─ 输出:
│           ├─ 整体大纲 (100章规划)
│           ├─ 第一卷详细大纲 (30章)
│           └─ 黄金三章详细大纲 (前3章)
│
├─ Step 2: 保存大纲文档
│   └─ 保存到: projects/小说名/3-大纲/
│       ├─ 整体大纲.md
│       ├─ 第一卷大纲.md
│       └─ 黄金三章大纲.md
│
└─ Step 3: 添加伏笔
    ├─ forgeai foreshadow add "伏笔描述" --chapter 1 --payoff 20
    └─ forgeai foreshadow list (查看所有伏笔)
```

---

### 五、正文创作阶段（核心循环）

```
正文创作循环
│
├─ 📋 写前准备 (Write Before)
│   │
│   ├─ Step 1: 写前检查
│   │   ├─ 命令: forgeai check before <章节号>
│   │   └─ 检查内容:
│   │       ├─ 活跃伏笔提醒
│   │       ├─ 节奏状态检查
│   │       └─ 叙事债务提醒
│   │
│   ├─ Step 2: 提取上下文
│   │   ├─ 命令: forgeai context <章节号> --smart
│   │   └─ 提取内容:
│   │       ├─ 上一章内容
│   │       ├─ 相关章节 (RAG检索)
│   │       ├─ 角色状态
│   │       ├─ 活跃伏笔
│   │       └─ 时间线锚点
│   │
│   └─ Step 3: 生成创作提示词
│       ├─ 命令: forgeai write <章节号> --query "查询内容"
│       └─ 输出:
│           ├─ 任务书 (7板块)
│           ├─ Context Contract
│           └─ 直写提示词
│
├─ ✍️ 正文撰写
│   │
│   ├─ Step 1: Context Agent 生成创作执行包
│   │   ├─ 任务书 (核心任务、出场角色、场景约束)
│   │   ├─ Context Contract (目标、阻力、代价、追读力设计)
│   │   └─ 直写提示词 (章节节拍、不可变事实、禁止事项)
│   │
│   ├─ Step 2: 正文生成
│   │   ├─ 分场景生成 (按任务书节拍)
│   │   ├─ 字数锚定 (2300-3000字)
│   │   ├─ 文风执行 (遵守创作宪章)
│   │   └─ 结尾钩子 (追读力设计)
│   │
│   └─ Step 3: 保存正文
│       └─ 保存到: projects/小说名/4-正文/第N章.md
│
├─ 🔍 审查优化
│   │
│   ├─ Step 1: 并行审查 (多Agent)
│   │   ├─ consistency-checker (设定一致性)
│   │   ├─ ooc-checker (人物OOC)
│   │   ├─ continuity-checker (连贯性)
│   │   ├─ reader-pull-checker (追读力)
│   │   ├─ high-point-checker (高潮点，条件执行)
│   │   └─ pacing-checker (节奏把控，每10章)
│   │
│   ├─ Step 2: 问题修复
│   │   ├─ critical问题 (必须修复)
│   │   ├─ high问题 (记录deviation)
│   │   └─ medium/low问题 (择优修复)
│   │
│   └─ Step 3: 去AI味处理
│       ├─ 调用 humanize 技能
│       ├─ 进化式优化 (最多3轮)
│       ├─ 24种AI特征检测
│       └─ Anti-AI终检
│
└─ 📊 写后处理 (Write After)
    │
    ├─ Step 1: 索引章节
    │   ├─ 文本分块 (500字/块)
    │   ├─ 向量化 (Embedding模型)
    │   └─ 存入向量数据库
    │
    ├─ Step 2: 提取实体
    │   ├─ 人物 (出场、状态变化)
    │   ├─ 地点 (新地点、地点转换)
    │   ├─ 物品 (新物品、归属变化)
    │   └─ 势力 (关系变化)
    │
    ├─ Step 3: AI味评分
    │   ├─ 检测维度 (句式、修饰词、情感、对话)
    │   └─ 评分标准 (>0.7优秀, 0.5-0.7良好, <0.5需优化)
    │
    ├─ Step 4: 更新进度
    │   ├─ 当前章节号
    │   ├─ 总字数
    │   ├─ 创作阶段
    │   └─ 完成时间
    │
    └─ Step 5: 下一章预检
        ├─ 超期伏笔提醒
        ├─ 叙事债务提醒
        ├─ 节奏平衡提醒
        └─ 阅读力趋势
```

---

### 六、数据管理阶段

```
数据管理
│
├─ 项目状态查看
│   ├─ forgeai status (当前进度、实体数量、活跃伏笔)
│   └─ forgeai stats (统计数据)
│
├─ 实体管理
│   ├─ forgeai entity list --type character (列出角色)
│   ├─ forgeai entity add <name> (添加实体)
│   ├─ forgeai growth <entity> (查看角色成长)
│   └─ forgeai growth <entity> --report (生成成长报告)
│
├─ 伏笔管理
│   ├─ forgeai foreshadow list --active (列出活跃伏笔)
│   ├─ forgeai foreshadow add <desc> (添加伏笔)
│   └─ forgeai foreshadow resolve <id> (回收伏笔)
│
├─ 时间线管理
│   ├─ forgeai timeline status (查看时间线状态)
│   ├─ forgeai timeline add <anchor> (添加时间锚点)
│   └─ forgeai timeline list (查看时间线历史)
│
└─ 一致性检查
    ├─ forgeai check consistency <章节号> (单章检查)
    └─ forgeai check consistency --start 1 --end 30 (批量检查)
```

---

## 🔧 核心技术流程

### 一、RAG 检索流程

```
RAG 检索系统
│
├─ 索引阶段
│   │
│   ├─ 文本分块
│   │   ├─ 分块大小: 500字/块
│   │   ├─ 重叠大小: 100字
│   │   └─ 句号/换行处截断
│   │
│   ├─ 向量化
│   │   ├─ 模型: Qwen3-Embedding-8B
│   │   ├─ 批量处理: batch_size=32
│   │   └─ 向量维度: 1536
│   │
│   └─ 存储
│       ├─ 向量数据库: vectors.db
│       ├─ BM25索引: bm25_index表
│       └─ 元数据: chunks表
│
├─ 检索阶段
│   │
│   ├─ 缓存检查 (LRU缓存)
│   │   ├─ 缓存命中: 直接返回
│   │   └─ 缓存未命中: 执行检索
│   │
│   ├─ 混合检索
│   │   ├─ 向量检索 (语义相似度)
│   │   │   ├─ 查询向量化
│   │   │   ├─ 余弦相似度计算
│   │   │   └─ Top-K召回
│   │   │
│   │   └─ BM25检索 (关键词匹配)
│   │       ├─ jieba分词
│   │       ├─ TF-IDF计算
│   │       └─ Top-K召回
│   │
│   ├─ 结果融合
│   │   ├─ 权重: 向量0.7 + BM25 0.3
│   │   ├─ 分数归一化
│   │   └─ RRF融合
│   │
│   └─ Reranker精排
│       ├─ 模型: Qwen3-Reranker-8B
│       ├─ 重排序Top-K结果
│       └─ 返回最终结果
│
└─ 性能优化
    ├─ LRU缓存 (TTL=300s, max_size=1000)
    ├─ 批量索引 (batch_size=100)
    └─ 性能日志 (耗时统计)
```

---

### 二、Token 管理流程

```
Token 管理系统
│
├─ Token 预算计算
│   │
│   ├─ 上下文上限: 128000 tokens
│   ├─ 输出预留: 4096 tokens
│   └─ 可用输入: 123904 tokens
│
├─ 智能截断策略
│   │
│   ├─ 优先级排序
│   │   ├─ P0: 系统提示词 (不可截断)
│   │   ├─ P1: 当前章节大纲 (不可截断)
│   │   ├─ P2: 角色状态 (尽量保留)
│   │   ├─ P3: 最近3章内容 (尽量保留)
│   │   ├─ P4: RAG检索内容 (可截断)
│   │   └─ P5: 历史章节 (优先截断)
│   │
│   └─ 截断算法
│       ├─ 计算各部分Token数
│       ├─ 按优先级截断
│       └─ 确保不超过预算
│
└─ 环节参数自动切换
    │
    ├─ 大纲阶段 (outline)
    │   ├─ temperature: 0.4 (严谨)
    │   └─ top_p: 0.9
    │
    ├─ 正文阶段 (writing)
    │   ├─ temperature: 1.0 (发散)
    │   └─ top_p: 0.9
    │
    └─ 审查阶段 (review)
        ├─ temperature: 0.3 (严谨)
        └─ top_p: 0.9
```

---

### 三、实体管理流程

```
实体管理系统
│
├─ 实体提取
│   │
│   ├─ NER识别
│   │   ├─ 人物 (PER)
│   │   ├─ 地点 (LOC)
│   │   ├─ 组织 (ORG)
│   │   └─ 物品 (MISC)
│   │
│   ├─ 缓存机制
│   │   ├─ TTL缓存 (5分钟)
│   │   └─ 去重逻辑
│   │
│   └─ 性能监控
│       └─ 耗时统计日志
│
├─ 实体消歧
│   │
│   ├─ 名称规范化
│   │   ├─ 别名识别
│   │   └─ 统一名称
│   │
│   └─ 实体链接
│       ├─ 关联已有实体
│       └─ 创建新实体
│
├─ 状态更新
│   │
│   ├─ 状态变更检测
│   │   ├─ 境界提升
│   │   ├─ 关系变化
│   │   └─ 物品归属
│   │
│   └─ 写入state.json
│       ├─ 更新实体状态
│       └─ 记录变更历史
│
└─ 成长分析
    │
    ├─ 角色成长轨迹
    │   ├─ 境界变化曲线
    │   ├─ 关系演变图
    │   └─ 关键事件时间线
    │
    └─ 成长报告生成
        ├─ 阶段性总结
        └─ 未来发展预测
```

---

### 四、伏笔管理流程

```
伏笔管理系统
│
├─ 伏笔添加
│   │
│   ├─ 命令: forgeai foreshadow add "描述" --chapter 1 --payoff 20
│   │
│   └─ 记录内容
│       ├─ 伏笔ID (自动生成)
│       ├─ 描述内容
│       ├─ 埋设章节
│       ├─ 预期回收章节
│       └─ 状态 (active)
│
├─ 伏笔检测
│   │
│   ├─ 写后自动检测
│   │   ├─ 检测新埋伏笔
│   │   └─ 检测伏笔回收
│   │
│   └─ 超期提醒
│       ├─ 计算超期章节数
│       └─ 写前检查时提醒
│
├─ 伏笔回收
│   │
│   ├─ 命令: forgeai foreshadow resolve <id> --chapter 20
│   │
│   └─ 更新状态
│       ├─ 状态: resolved
│       ├─ 实际回收章节
│       └─ 回收时间
│
└─ 伏笔查询
    │
    ├─ 列出活跃伏笔
    │   └─ forgeai foreshadow list --active
    │
    └─ 搜索相关章节
        └─ forgeai search "伏笔关键词"
```

---

## 📊 质量保障体系

```
质量保障体系
│
├─ 多Agent审查
│   │
│   ├─ 设定一致性检查
│   │   ├─ 检查世界观设定
│   │   ├─ 检查角色设定
│   │   └─ 检查物品设定
│   │
│   ├─ 人物OOC检查
│   │   ├─ 检查性格一致性
│   │   ├─ 检查行为合理性
│   │   └─ 检查对话风格
│   │
│   ├─ 连贯性检查
│   │   ├─ 检查情节连贯
│   │   ├─ 检查时间线连贯
│   │   └─ 检查空间连贯
│   │
│   ├─ 追读力检查
│   │   ├─ 检查开头钩子
│   │   ├─ 检查结尾钩子
│   │   └─ 检查悬念设置
│   │
│   ├─ 高潮点检查 (条件执行)
│   │   ├─ 检查战斗场景
│   │   └─ 检查关键情节
│   │
│   └─ 节奏把控检查 (每10章)
│       ├─ 检查爽点密度
│       └─ 检查节奏平衡
│
├─ AI味检测
│   │
│   ├─ 24种AI特征检测
│   │   ├─ 句式重复度
│   │   ├─ 过度修饰词
│   │   ├─ 情感表达模式
│   │   ├─ 对话模式
│   │   └─ 段落结构
│   │
│   ├─ 进化式优化
│   │   ├─ Baseline评分
│   │   ├─ 生成3个挑战者版本
│   │   ├─ 选择最佳版本
│   │   └─ 最多3轮优化
│   │
│   └─ Anti-AI终检
│       ├─ 执行24种特征检测
│       └─ 输出 pass/fail
│
└─ 一致性检查
    │
    ├─ 单章检查
    │   └─ forgeai check consistency <章节号>
    │
    └─ 批量检查
        └─ forgeai check consistency --start 1 --end 30
```

---

## 🎨 文风管理系统

```
文风管理系统
│
├─ 样板书文风提取
│   │
│   ├─ 叙事视角
│   │   ├─ 第一人称
│   │   └─ 第三人称
│   │
│   ├─ 对白密度
│   │   ├─ 高密度 (对话为主)
│   │   ├─ 中密度 (平衡)
│   │   └─ 低密度 (叙述为主)
│   │
│   ├─ 开头模式
│   │   ├─ 场景切入
│   │   ├─ 对话切入
│   │   └─ 心理切入
│   │
│   ├─ 结尾模式
│   │   ├─ 悬念钩子
│   │   ├─ 高潮截断
│   │   └─ 过渡收束
│   │
│   ├─ 句式特点
│   │   ├─ 平均句长
│   │   └─ 长短句比例
│   │
│   └─ 对白风格
│       ├─ 主角说话方式
│       └─ 配角说话风格
│
└─ 文风应用
    │
    ├─ Context Agent集成
    │   └─ 在创作执行包中包含文风指导
    │
    └─ 创作宪章遵守
        └─ system/constitution/MASTER.md
```

---

## 🔄 完整工作流示例

### 单章创作完整流程

```
第20章创作流程
│
├─ 📋 写前准备
│   ├─ forgeai check before 20
│   │   └─ 输出: 活跃伏笔、节奏状态、叙事债务
│   │
│   ├─ forgeai context 20 --smart
│   │   └─ 输出: 上一章内容、相关章节、角色状态、伏笔
│   │
│   └─ forgeai write 20 --query "感情线"
│       └─ 输出: 任务书、Context Contract、直写提示词
│
├─ ✍️ 正文撰写
│   ├─ Context Agent生成创作执行包
│   ├─ 按节拍生成正文 (2300-3000字)
│   └─ 保存到: 4-正文/第20章.md
│
├─ 🔍 审查优化
│   ├─ 并行调用审查Agents
│   │   ├─ consistency-checker ✅
│   │   ├─ ooc-checker ✅
│   │   ├─ continuity-checker ✅
│   │   └─ reader-pull-checker ✅
│   │
│   ├─ 修复critical问题
│   │
│   └─ 去AI味处理
│       ├─ Baseline评分: 0.65
│       ├─ 第1轮优化: 0.72
│       ├─ 第2轮优化: 0.78
│       └─ Anti-AI终检: pass ✅
│
├─ 📊 写后处理
│   ├─ forgeai check after 20 4-正文/第20章.md
│   │   ├─ 索引章节: 6个分块 ✅
│   │   ├─ 提取实体: 8个实体, 3个状态变更 ✅
│   │   ├─ AI味评分: 0.78 (优秀) ✅
│   │   ├─ 更新进度: 第20章完成 ✅
│   │   └─ 下一章预检: 2条提醒 ✅
│   │
│   └─ Data Agent回写
│       ├─ 更新state.json
│       ├─ 更新index.db
│       ├─ 生成章节摘要
│       └─ RAG向量索引
│
└─ 📦 Git备份
    └─ git commit -m "第20章: 感情升温"
```

---

## 📈 性能优化机制

```
性能优化
│
├─ 缓存机制
│   │
│   ├─ RAG检索缓存
│   │   ├─ LRU缓存
│   │   ├─ TTL: 300秒
│   │   ├─ Max Size: 1000条
│   │   └─ 性能提升: 100x
│   │
│   └─ 实体提取缓存
│       ├─ TTL缓存
│       ├─ TTL: 300秒
│       └─ 性能提升: 200x
│
├─ 批量处理
│   │
│   ├─ 批量索引
│   │   ├─ batch_size: 100
│   │   └─ 减少数据库连接开销
│   │
│   └─ 批量向量化
│       ├─ batch_size: 32
│       └─ 减少API调用次数
│
└─ 错误处理
    │
    ├─ Reranker降级
    │   └─ 失败时返回原始排序
    │
    └─ 详细错误信息
        ├─ 包含上下文
        ├─ 提供修复建议
        └─ 记录日志
```

---

## 🎯 最佳实践建议

### 每日创作流程

```
每日创作
│
├─ 早上 (2-3小时)
│   ├─ 写前检查 → 提取上下文
│   ├─ 创作2章
│   └─ 写后处理
│
├─ 下午 (1-2小时)
│   ├─ 审查章节
│   ├─ 修改优化
│   └─ AI味评分
│
└─ 晚上 (1小时)
    ├─ 数据管理
    ├─ 伏笔规划
    └─ 准备明天大纲
```

### 质量控制节点

```
质量控制
│
├─ 每5章
│   ├─ 一致性检查
│   ├─ AI味评分
│   └─ 伏笔盘点
│
├─ 每10章
│   ├─ 节奏把控检查
│   ├─ 角色成长分析
│   └─ 时间线梳理
│
└─ 每卷
    ├─ 整体质量评估
    ├─ 读者反馈分析
    └─ 下一卷规划
```

---

## 🆘 常见问题处理

```
问题处理
│
├─ 创作中断恢复
│   ├─ forgeai status (查看进度)
│   ├─ forgeai context <最后一章> (查看内容)
│   └─ forgeai check before <下一章> (继续创作)
│
├─ 章节修改
│   ├─ 重新索引: forgeai index 4-正文/第10章.md
│   ├─ 更新实体: forgeai update 4-正文/第10章.md
│   └─ 重新审查: forgeai check consistency 10
│
└─ 伏笔遗忘
    ├─ 查看活跃伏笔: forgeai foreshadow list --active
    ├─ 搜索相关章节: forgeai search "关键词"
    └─ 在新章节中回收
```

---

## 📚 相关文档

- [命令速查表](./COMMAND_REFERENCE.md)
- [样板书拆解指南](./BOOK_ANALYSIS_GUIDE.md)
- [配置指南](./CONFIG_GUIDE.md)
- [Token管理详解](./TOKEN_MANAGEMENT.md)
- [AI味检测原理](./HUMANIZE_SCORING.md)

---

**ForgeAI - 让AI创作更自然、更高效** 🎉
