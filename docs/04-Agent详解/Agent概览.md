# Agent 概览

> **ForgeAI 多Agent协作审查系统** - 9个专业Agent并行审查，全方位确保质量

---

## Agent 架构

ForgeAI 采用多Agent协作架构，每个Agent专注于特定的审查维度，通过并行审查确保章节质量。

```
章节内容
    ↓
┌─────────────────────────────────────┐
│      多Agent并行审查系统              │
├─────────────────────────────────────┤
│  consistency-checker (设定一致性)    │
│  ooc-checker (人物OOC)              │
│  continuity-checker (连贯性)        │
│  reader-pull-checker (追读力)       │
│  high-point-checker (高潮点)        │
│  pacing-checker (节奏)              │
│  timeline-agent (时间线)            │
│  context-agent (上下文)             │
│  data-agent (数据管理)              │
└─────────────────────────────────────┘
    ↓
审查报告 + 修复建议
```

---

## 9个专业Agent

### 1. consistency-checker - 设定一致性检查

**职责:** 检查章节内容与已有设定的一致性

**审查维度:**
- 世界观设定一致性
- 角色设定一致性
- 金手指设定一致性
- 力量体系一致性

**典型问题:**
- 角色能力与设定不符
- 世界观规则违反
- 金手指使用不合理

**详细文档:** [设定一致性检查](./设定一致性检查.md)

---

### 2. ooc-checker - 人物OOC检测

**职责:** 检测人物行为是否符合性格设定

**审查维度:**
- 性格一致性
- 行为动机合理性
- 对话风格一致性
- 情感反应合理性

**典型问题:**
- 角色性格突变
- 行为缺乏动机
- 对话风格不一致

**详细文档:** [OOC检测](./OOC检测.md)

---

### 3. continuity-checker - 连贯性检查

**职责:** 检查章节间的连贯性和逻辑性

**审查维度:**
- 情节连贯性
- 时间线连贯性
- 场景转换合理性
- 因果关系合理性

**典型问题:**
- 情节跳跃
- 时间线混乱
- 场景转换生硬

**详细文档:** [连贯性检查](./连贯性检查.md)

---

### 4. reader-pull-checker - 追读力检查

**职责:** 评估章节的追读力（吸引读者继续阅读的能力）

**审查维度:**
- 悬念设置
- 冲突强度
- 节奏把控
- 爽点密度

**典型问题:**
- 缺乏悬念
- 冲突不足
- 节奏平淡

**详细文档:** [追读力检查](./追读力检查.md)

---

### 5. high-point-checker - 高潮点检查

**职责:** 检测章节中的高潮点和情绪峰值

**审查维度:**
- 高潮点位置
- 情绪曲线
- 爆发力度
- 铺垫充分性

**典型问题:**
- 高潮点缺失
- 情绪曲线平淡
- 爆发力度不足

**详细文档:** [高潮点检查](./高潮点检查.md)

---

### 6. pacing-checker - 节奏检查

**职责:** 检查章节的叙事节奏

**审查维度:**
- 快慢节奏比例
- 张弛有度
- 信息密度
- 情节推进速度

**典型问题:**
- 节奏单一
- 信息过载
- 情节推进缓慢

**详细文档:** [节奏检查](./节奏检查.md)

---

### 7. timeline-agent - 时间线管理

**职责:** 管理小说时间线，确保时间逻辑正确

**审查维度:**
- 时间锚点
- 时间流逝
- 倒计时管理
- 时间逻辑一致性

**典型问题:**
- 时间线矛盾
- 时间流逝不合理
- 倒计时缺失

**详细文档:** [时间线管理](./时间线管理.md)

---

### 8. context-agent - 上下文管理

**职责:** 管理章节上下文，确保信息完整

**审查维度:**
- 前文召回
- 实体状态更新
- 伏笔追踪
- 设定引用

**典型问题:**
- 前文信息遗漏
- 实体状态不一致
- 伏笔遗忘

**详细文档:** [上下文管理](./上下文管理.md)

---

### 9. data-agent - 数据管理

**职责:** 管理项目数据，确保数据一致性

**审查维度:**
- 实体数据
- 伏笔数据
- 时间线数据
- 进度数据

**典型问题:**
- 数据不一致
- 数据丢失
- 数据冗余

**详细文档:** [数据管理](./数据管理.md)

---

## Agent 协作流程

### 标准审查流程

```bash
# 1. 写后自动审查（9个Agent并行）
forgeai check after 1 --text-file 4-正文/第1章.md

# 2. 查看审查报告
cat 5-审查/第1章-审查报告.md

# 3. 根据建议修改章节

# 4. 重新审查
forgeai check review 1
```

### 独立审查模式

```bash
# 独立审查模式（更严格的审查）
forgeai check review 1 --independent
```

### 指定Agent审查

```bash
# 只运行特定Agent
forgeai check review 1 --agents consistency,continuity

# 跳过某些Agent
forgeai check review 1 --skip-agents ooc,pacing
```

---

## 审查报告结构

每个Agent的审查报告包含：

```markdown
# [Agent名称] 审查报告

## 审查结果

- 状态: ✅ 通过 / ⚠️ 警告 / ❌ 失败
- 评分: X/10
- 问题数量: N

## 发现的问题

### 问题1: [问题标题]

**位置:** 第X段
**描述:** [问题描述]
**严重程度:** 高/中/低
**修复建议:** [具体建议]

### 问题2: ...

## 改进建议

1. [建议1]
2. [建议2]
```

---

## Agent 配置

### 全局配置

在 `config.json` 中配置Agent：

```json
{
  "agents": {
    "enabled": true,
    "parallel": true,
    "timeout": 30,
    "max_issues": 10
  }
}
```

### 单个Agent配置

```json
{
  "agents": {
    "consistency-checker": {
      "enabled": true,
      "strictness": "high",
      "check_worldview": true,
      "check_characters": true
    },
    "ooc-checker": {
      "enabled": true,
      "strictness": "medium",
      "check_dialogue": true,
      "check_behavior": true
    }
  }
}
```

---

## Agent 优先级

不同类型的章节，Agent优先级不同：

### 战斗章节

1. **high-point-checker** - 高潮点检测
2. **pacing-checker** - 节奏把控
3. **consistency-checker** - 设定一致性
4. **continuity-checker** - 连贯性

### 日常章节

1. **continuity-checker** - 连贯性
2. **ooc-checker** - 人物OOC
3. **reader-pull-checker** - 追读力
4. **pacing-checker** - 节奏

### 转折章节

1. **consistency-checker** - 设定一致性
2. **continuity-checker** - 连贯性
3. **timeline-agent** - 时间线
4. **context-agent** - 上下文

---

## 常见问题

### Q: 如何选择使用哪些Agent？

**A:** 根据章节类型选择：

```bash
# 战斗章节
forgeai check review 10 --agents high-point,pacing,consistency

# 日常章节
forgeai check review 5 --agents continuity,ooc,reader-pull

# 转折章节
forgeai check review 20 --agents consistency,continuity,timeline
```

### Q: Agent审查不通过怎么办？

**A:** 查看审查报告，根据建议修改：

1. 打开 `5-审查/第N章-审查报告.md`
2. 查看"发现的问题"部分
3. 根据"修复建议"修改章节
4. 重新运行审查

### Q: 如何调整Agent严格程度？

**A:** 在 `config.json` 中配置：

```json
{
  "agents": {
    "consistency-checker": {
      "strictness": "high"  // high, medium, low
    }
  }
}
```

---

## 最佳实践

### 1. 定期审查

每完成一章就进行审查，避免问题累积：

```bash
forgeai write 5
forgeai check after 5 --text-file 4-正文/第5章.md
```

### 2. 重点关注

根据章节类型选择重点Agent：

- 战斗章 → 高潮点、节奏
- 日常章 → 连贯性、追读力
- 转折章 → 设定一致性、时间线

### 3. 迭代优化

根据审查结果持续优化：

```bash
# 审查
forgeai check review 10

# 修改章节
# ...

# 重新审查
forgeai check review 10
```

---

## 下一步

- **[设定一致性检查](./设定一致性检查.md)** - 详细了解一致性检查
- **[OOC检测](./OOC检测.md)** - 详细了解人物OOC检测
- **[追读力检查](./追读力检查.md)** - 详细了解追读力评估

---

*Agent概览 - ForgeAI*
