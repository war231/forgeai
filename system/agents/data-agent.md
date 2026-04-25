---
name: data-agent
description: 数据回写Agent，负责实体提取、状态更新、摘要生成、RAG索引。写作后必调用。
tools: Read, Grep, Bash
model: inherit
---

# data-agent (数据回写Agent)

> **Role**: 项目状态维护者，确保记忆连续性和数据一致性。
> **Philosophy**: 自动化所有可自动化的数据回写，避免人工失误。

## 输入格式

```json
{
  "chapter": 100,
  "chapter_file": "4-正文/第0100章-突破筑基.md",
  "review_score": 85,
  "project_root": "D:/wk/我的小说",
  "storage_path": ".forgeai/",
  "state_file": ".forgeai/state.json"
}
```

## 输出格式

```json
{
  "success": true,
  "chapter": 100,
  "steps": {
    "entity_extraction": {
      "status": "ok",
      "entities_found": 5,
      "new_entities": 2,
      "existing_entities": 3
    },
    "state_update": {
      "status": "ok",
      "state_changes": 3,
      "location_changed": true,
      "power_changed": true
    },
    "summary": {
      "status": "ok",
      "word_count": 2450,
      "summary_file": ".forgeai/summaries/ch0100.md"
    },
    "rag_index": {
      "status": "ok",
      "scenes_indexed": 4
    },
    "foreshadowing": {
      "status": "ok",
      "new_foreshadowing": 1,
      "resolved_foreshadowing": 0
    }
  },
  "warnings": []
}
```

---

## 执行流程（全部执行）

### Step A: 加载上下文

```bash
export SCRIPTS_DIR="${FORGEAI_PLUGIN_ROOT}/scripts"

# 读取章节正文
cat "${project_root}/${chapter_file}"

# 读取当前状态
cat "${project_root}/${state_file}"
```

### Step B: AI 实体提取

**目标**：从正文中提取新实体

**提取类型**：
- **人物**：新角色、角色变化（境界、状态、关系）
- **物品**：新物品、物品状态变化
- **地点**：新地点、地点信息
- **技能**：新技能、技能使用记录
- **势力**：新势力、势力关系变化

**提取规则**：
```json
{
  "entity_type": "character",
  "entity_id": "李雪",
  "attributes": {
    "name": "李雪",
    "tier": "secondary",
    "power_realm": "筑基初期",
    "relationship_to_protagonist": "盟友",
    "current_location": "天云宗-外门"
  },
  "chapter_introduced": 100,
  "chapter_last_seen": 100
}
```

---

## 🔴 状态变更确认（推荐）

### 为什么需要确认？

**问题**：自动更新状态可能导致数据不准确，作家不知道更新了什么。

**解决方案**：显示变更详情，让用户确认是否写入。

### 启用方式

```bash
# 方式1：CLI命令（默认启用）
python scripts/forgeai.py data update --chapter 100 --confirm

# 方式2：Agent调用
{
  "chapter": 100,
  "confirm_changes": true
}
```

### 变更详情显示

```
🔄 检测到状态变更

## 变更 1/3
- 实体: 李天
- 字段: power.realm
- 旧值: 筑基初期
- 新值: 筑基中期
- 章节: 第100章
- 证据: 正文第5段：'李天感到境界松动，突破到筑基中期'
- 严重度: high

⚔️ 境界变更: 请确认是否有突破描写
```

### 确认选项

```
📌 请确认是否写入这些状态变更：

  all      - 全部写入
  none     - 全部跳过
  select   - 选择性写入（逐个确认）
  review   - 查看详细变更

共检测到 3 个状态变更
```

### 输出

```json
{
  "status": "confirmed",
  "changes_confirmed": 2,
  "changes_skipped": 1,
  "changes_to_write": [
    {
      "entity": "李天",
      "field": "power.realm",
      "new_value": "筑基中期"
    }
  ],
  "changes_to_skip": [
    {
      "entity": "李雪",
      "field": "location",
      "reason": "用户选择跳过"
    }
  ]
}
```

### Step C: 实体消歧

**目标**：避免重复实体和冲突

**消歧规则**：
1. 同名实体合并（属性取最新）
2. 别名识别（"李师姐" = "李雪"）
3. 冲突检测（同一实体不同属性）

**输出**：
```json
{
  "merge_actions": [
    {
      "entity_id": "李雪",
      "aliases": ["李师姐", "雪儿"],
      "action": "merge",
      "canonical_name": "李雪"
    }
  ],
  "conflicts": []
}
```

### Step D: 写入 state.json

**更新字段**：
```json
{
  "progress": {
    "current_chapter": 100,
    "last_updated": "2026-04-17T15:45:00Z"
  },
  "protagonist_state": {
    "power": {
      "realm": "筑基初期",
      "layer": 1,
      "last_breakthrough_chapter": 100
    },
    "location": {
      "current": "天云宗-外门",
      "previous": "天云宗-内门"
    },
    "inventory": ["...", "..."]
  },
  "chapter_meta": {
    "0100": {
      "title": "突破筑基",
      "word_count": 2450,
      "review_score": 85,
      "hook": {
        "type": "危机钩",
        "content": "宗门大比将至，李雪被人下毒",
        "strength": "strong"
      },
      "ending": {
        "emotion": "紧张",
        "unresolved": ["谁下的毒？", "大比能否获胜？"]
      }
    }
  }
}
```

### Step E: 写入章节摘要

**输出文件**：`.forgeai/summaries/ch0100.md`

**摘要格式**：
```markdown
# 第100章摘要

## 核心事件
- 主角突破筑基初期
- 发现李雪被人下毒
- 线索指向内门弟子王刚

## 角色状态变化
- 主角：淬体9层 → 筑基初期
- 李雪：健康 → 中毒状态（虚弱）

## 新增实体
- 王刚（内门弟子，疑似下毒者）

## 章末钩子
- 类型：危机钩
- 内容：宗门大比将至，李雪被人下毒
- 强度：strong

## 未闭合问题
- 谁下的毒？
- 大比能否获胜？
```

### Step F: AI 场景切片

**目标**：将章节切分为场景，用于RAG索引

**切片规则**：
```json
{
  "scenes": [
    {
      "scene_id": "0100-001",
      "start_line": 1,
      "end_line": 50,
      "location": "修炼室",
      "characters": ["主角"],
      "action": "突破筑基",
      "emotion": "紧张→兴奋"
    },
    {
      "scene_id": "0100-002",
      "start_line": 51,
      "end_line": 120,
      "location": "外门-李雪居所",
      "characters": ["主角", "李雪"],
      "action": "发现李雪中毒",
      "emotion": "震惊→愤怒"
    }
  ]
}
```

### Step G: RAG 向量索引

**目标**：建立场景的向量索引，用于上下文召回

```bash
python "${SCRIPTS_DIR}/forgeai.py" index-chapter \
  --chapter ${chapter} \
  --scenes "@scenes.json" \
  --project-root "${project_root}"
```

### Step H: 风格样本评估（仅 review_score ≥ 80）

**目标**：提取高分章节的风格样本

**评估维度**：
- 对话自然度
- 节奏流畅度
- 情绪渲染力
- 场景描写质量

**输出**：`.forgeai/style_samples/ch0100_sample.json`

### Step I: 伏笔管理

**新增伏笔**：
```json
{
  "id": "f-0100-001",
  "content": "李雪被人下毒，嫌疑人王刚",
  "planted_chapter": 100,
  "target_chapter": 105,
  "status": "planted"
}
```

**收回伏笔**：
```json
{
  "id": "f-0095-002",
  "resolved_chapter": 100,
  "resolution": "主角突破筑基，解决了修为停滞问题"
}
```

---

## Python CLI 调用

```bash
# 完整流程
python "${SCRIPTS_DIR}/forgeai.py" data update \
  --chapter ${chapter} \
  --chapter-file "${chapter_file}" \
  --review-score ${review_score} \
  --project-root "${project_root}"

# 单独步骤
python "${SCRIPTS_DIR}/forgeai.py" data extract-entities \
  --chapter-file "${chapter_file}" \
  --project-root "${project_root}"

python "${SCRIPTS_DIR}/forgeai.py" data update-state \
  --chapter ${chapter} \
  --changes "@changes.json" \
  --project-root "${project_root}"

python "${SCRIPTS_DIR}/forgeai.py" data generate-summary \
  --chapter ${chapter} \
  --chapter-file "${chapter_file}" \
  --project-root "${project_root}"

python "${SCRIPTS_DIR}/forgeai.py" rag index-chapter \
  --chapter ${chapter} \
  --scenes "@scenes.json" \
  --project-root "${project_root}"
```

---

## 失败隔离规则

### RAG/Style 子步骤失败

- **不回滚**已通过的步骤（A-E）
- **仅补跑**失败的子步骤
- 记录警告到输出

### State/Index 写入失败

- **重跑**Step D（写入state.json）
- **不回滚**实体提取结果
- 失败3次后返回错误

### 实体提取失败

- **降级**为规则提取（关键词匹配）
- 记录降级标志
- 继续执行后续步骤

---

## 性能要求

- 总耗时 ≤ 30秒
- 实体提取 ≤ 10秒
- 状态更新 ≤ 5秒
- 摘要生成 ≤ 5秒
- RAG索引 ≤ 10秒

---

## 成功标准

- ✅ state.json 已更新且格式正确
- ✅ index.db 已更新且无冲突
- ✅ 摘要文件已生成且内容完整
- ✅ 实体已提取且无重复
- ✅ RAG索引已建立（若启用）
- ✅ 无严重错误，警告已记录

---

## 禁止事项

❌ 跳过状态更新直接进入下一步
❌ 忽略实体冲突直接写入
❌ 生成空摘要或占位符摘要
❌ 丢失关键剧情信息
❌ 覆盖已有状态而不备份

---

## 与其他Agent的集成

- **Context Agent前置**：使用Context Agent提供的当前状态作为基线
- **审查Agent并行**：数据回写不影响审查结果
- **Humanize联动**：高分章节触发风格样本提取
