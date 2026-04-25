# 多Agent审查系统详解

## 概述

ForgeAI 配备了 **9个专业Agent**,每个Agent负责不同的审查维度,通过并行审查确保章节质量。

## 9个专业Agent

| Agent | 职责 | 检查重点 |
|-------|------|----------|
| **consistency-checker** | 设定一致性 | 战力/地点/时间线/实体一致性 |
| **ooc-checker** | 人物OOC检测 | 角色行为是否符合人设 |
| **continuity-checker** | 连贯性检查 | 情节衔接/伏笔回收/逻辑连贯 |
| **reader-pull-checker** | 追读力检查 | 开头吸引力/结尾悬念/爽点密度 |
| **high-point-checker** | 高潮点检查 | 高潮设计/情感爆发/节奏把控 |
| **pacing-checker** | 节奏检查 | 快慢节奏/信息密度/阅读疲劳 |
| **timeline-agent** | 时间线管理 | 时间锚点/倒计时/时间流逝 |
| **context-agent** | 上下文管理 | 上下文提取/RAG检索/记忆管理 |
| **data-agent** | 数据管理 | 实体状态/进度记录/数据同步 |

## 使用方式

### 基础审查

```bash
# 审查第20章
forgeai check review 20
```

### 独立审查模式(推荐)

```bash
# 清除上下文,客观审查
forgeai check review 20 --independent
```

**独立审查的优势**:
- ✅ 完全客观 - 不受写作过程影响
- ✅ 发现盲区 - 容易发现被忽略的问题
- ✅ 高质量审查 - 模拟"新读者"视角

## 审查流程

```
执行审查命令
    ↓
并行启动9个Agent
    ├─ consistency-checker  → 检查设定一致性
    ├─ ooc-checker          → 检查人物OOC
    ├─ continuity-checker   → 检查情节连贯
    ├─ reader-pull-checker  → 检查追读力
    ├─ high-point-checker   → 检查高潮设计
    ├─ pacing-checker       → 检查节奏
    ├─ timeline-agent       → 检查时间线
    ├─ context-agent        → 提取上下文
    └─ data-agent           → 更新数据
    ↓
汇总审查结果
    ↓
生成综合报告
    ├─ 总体评分
    ├─ 问题分类(严重/高/中/低)
    ├─ 修复建议
    └─ 自动修复方案
```

## 输出示例

### 独立审查模式

```bash
forgeai check review 20 --independent
```

输出:
```json
{
  "status": "ok",
  "mode": "independent",
  "chapter": 20,
  "saved_to": ".forgeai/independent_reviews/ch20_review_prompt.md",
  "instructions": [
    "1. 复制上述审查提示词",
    "2. 打开一个新的对话窗口",
    "3. 粘贴提示词到新窗口",
    "4. 获取独立的审查结果",
    "5. 根据审查结果修改章节内容"
  ],
  "message": "请将审查提示词发送到新的对话窗口"
}
```

### 标准审查模式

```bash
forgeai check review 20
```

输出:
```json
{
  "chapter": 20,
  "overall_score": 85,
  "passed": true,
  "agent_results": [
    {
      "agent": "consistency-checker",
      "overall_score": 90,
      "passed": true,
      "issues": []
    },
    {
      "agent": "ooc-checker",
      "overall_score": 85,
      "passed": true,
      "issues": [
        {
          "severity": "medium",
          "category": "character_behavior",
          "description": "林月的反应略显平淡,建议增加情感波动",
          "suggestion": "在告白场景中增加林月的内心独白"
        }
      ]
    },
    {
      "agent": "reader-pull-checker",
      "overall_score": 80,
      "passed": true,
      "issues": [
        {
          "severity": "low",
          "category": "opening",
          "description": "开头战斗场景较长,可能影响追读",
          "suggestion": "缩短战斗描写,更快进入感情主线"
        }
      ]
    }
  ],
  "critical_issues": [],
  "high_issues": [],
  "medium_issues": [
    {
      "agent": "ooc-checker",
      "description": "林月的反应略显平淡",
      "suggestion": "增加情感波动描写"
    }
  ],
  "low_issues": [
    {
      "agent": "reader-pull-checker",
      "description": "开头战斗场景较长",
      "suggestion": "缩短战斗,快速进入主线"
    }
  ],
  "summary": "章节质量良好,建议优化林月的情感表达和开头节奏"
}
```

## Agent详细说明

### 1. consistency-checker (设定一致性检查)

**检查维度**:
- **战力一致性** - 主角境界与能力是否匹配
- **地点一致性** - 地点转换是否合理
- **时间线一致性** - 时间流逝是否逻辑
- **实体一致性** - 人物/物品属性是否一致

**常见问题**:
```
❌ [critical] 主角筑基3层使用金丹期技能"破空斩"
❌ [high] 上章在天云宗,本章突然在千里外的血煞秘境(无移动描写)
❌ [critical] 倒计时D-5直接跳到D-2(跳过3天)
```

---

### 2. ooc-checker (人物OOC检测)

**检查维度**:
- **性格一致性** - 角色行为是否符合人设
- **动机合理性** - 角色行为是否有合理动机
- **情感真实性** - 情感表达是否自然
- **成长合理性** - 角色成长是否合理

**常见问题**:
```
❌ [high] 高冷女配突然变得话痨(无解释)
❌ [medium] 林月对告白反应过于平淡(不符合人设)
❌ [low] 主角决策略显冲动(可接受但建议优化)
```

---

### 3. continuity-checker (连贯性检查)

**检查维度**:
- **情节衔接** - 前后情节是否连贯
- **伏笔回收** - 伏笔是否合理回收
- **逻辑连贯** - 因果关系是否清晰
- **细节一致** - 细节是否前后一致

**常见问题**:
```
❌ [critical] 第5章埋下的伏笔"神秘玉佩"本章突然消失
❌ [high] 上章主角受伤,本章完全痊愈(无治疗描写)
❌ [medium] 配角名字前后不一致(李雪vs李月)
```

---

### 4. reader-pull-checker (追读力检查)

**检查维度**:
- **开头吸引力** - 开头3段是否抓住读者
- **结尾悬念** - 结尾是否留下悬念
- **爽点密度** - 爽点分布是否合理
- **阅读节奏** - 是否容易产生阅读疲劳

**常见问题**:
```
❌ [high] 开头战斗场景过长,影响追读
❌ [medium] 章节结尾平淡,无悬念
❌ [low] 中间段落信息密度过低
```

---

### 5. high-point-checker (高潮点检查)

**检查维度**:
- **高潮设计** - 高潮是否足够震撼
- **情感爆发** - 情感是否充分表达
- **节奏把控** - 高潮节奏是否合理
- **爽点设计** - 爽点是否足够爽

**常见问题**:
```
❌ [high] 告白场景情感铺垫不足
❌ [medium] 战斗高潮缺乏爆发感
❌ [low] 爽点设计略显平淡
```

---

### 6. pacing-checker (节奏检查)

**检查维度**:
- **快慢节奏** - 快慢节奏是否合理
- **信息密度** - 信息密度是否适中
- **阅读疲劳** - 是否容易疲劳
- **章节平衡** - 章节内容是否平衡

**常见问题**:
```
❌ [medium] 连续5章战斗场景,节奏单调
❌ [low] 本章信息密度过低
❌ [medium] 情感戏与战斗戏比例失衡
```

---

### 7. timeline-agent (时间线管理)

**检查维度**:
- **时间锚点** - 时间锚点是否清晰
- **倒计时** - 倒计时是否准确
- **时间流逝** - 时间流逝是否合理
- **时间线一致性** - 时间线是否一致

**常见问题**:
```
❌ [critical] 时间锚点"末世第5天"跳到"末世第3天"
❌ [high] 倒计时D-10突然变成D-5(无时间流逝)
❌ [medium] 章节时间跨度不明确
```

---

### 8. context-agent (上下文管理)

**职责**:
- 提取写作上下文
- 管理RAG检索
- 维护记忆系统
- 优化上下文长度

---

### 9. data-agent (数据管理)

**职责**:
- 更新实体状态
- 记录章节进度
- 同步数据变更
- 生成统计报告

## 审查报告解读

### 评分标准

```
总分 = Σ(Agent分数 × Agent权重) / Σ权重

Agent权重:
- consistency-checker: 1.0
- ooc-checker: 1.0
- continuity-checker: 1.0
- reader-pull-checker: 1.0
- high-point-checker: 0.8
- pacing-checker: 0.8
- timeline-agent: 0.9
```

### 通过标准

| 分数区间 | 结果 | 说明 |
|---------|------|------|
| **85-100** | ✅ 通过 | 质量优秀,可直接发布 |
| **70-84** | ⚠️ 通过(有警告) | 质量良好,建议优化 |
| **50-69** | 🔶 条件通过 | 需修复中等问题后发布 |
| **<50** | ❌ 未通过 | 必须重写或大幅修改 |

### 问题严重度

| 严重度 | 说明 | 处理方式 |
|--------|------|----------|
| **critical** | 必须修复 | 阻塞发布,必须立即修复 |
| **high** | 强烈建议修复 | 影响质量,建议修复 |
| **medium** | 建议修复 | 可选修复,提升质量 |
| **low** | 可选修复 | 锦上添花,可选修复 |

## 最佳实践

### 审查时机

1. **每次写完立即审查** - 及时发现问题
2. **重要章节加强审查** - 转折章、高潮章
3. **定期批量审查** - 每5-10章做一次全面审查
4. **发布前最终审查** - 确保质量达标

### 审查策略

```bash
# 日常审查(快速)
forgeai check review 20

# 重要章节(独立审查)
forgeai check review 20 --independent

# 批量审查
for i in {15..20}; do
    forgeai check review $i --independent
done
```

### 问题处理优先级

1. **critical问题** - 立即修复,不修复不发布
2. **high问题** - 优先修复,影响读者体验
3. **medium问题** - 建议修复,提升质量
4. **low问题** - 可选修复,锦上添花

## 常见问题

### Q: 为什么要用独立审查模式?

A: 独立审查清除上下文,模拟"新读者"视角,更容易发现被忽略的问题。

### Q: 9个Agent都需要运行吗?

A: 是的,每个Agent负责不同维度,缺一不可。但可以根据需要调整权重。

### Q: 审查发现问题必须修复吗?

A: critical和high问题必须修复,medium和low问题可选修复。

### Q: 可以自定义Agent吗?

A: 可以,在 `system/agents/` 目录下创建新的Agent定义文件。

### Q: 审查报告保存在哪里?

A: 独立审查报告保存在 `.forgeai/independent_reviews/`,标准审查输出到终端。

---

**总结**: 多Agent审查系统是 ForgeAI 的核心质量保障机制,通过9个专业Agent的并行审查,从设定一致性、人物塑造、情节连贯、追读力等多个维度确保章节质量。建议每次写完都进行审查,重要章节使用独立审查模式。
