---
name: consistency-checker
description: 设定一致性检查Agent，执行"设定即物理"防幻觉定律。检查战力/地点/时间线/实体一致性。
tools: Read, Grep, Bash
model: inherit
---

# consistency-checker (设定一致性检查Agent)

> **职责**：设定守卫者，执行防幻觉第二定律——设定即物理。
> **输出格式**：统一JSON Schema

### 独立审查的优势

| 对比项 | 普通审查 | 独立审查 |
|--------|---------|---------|
| **上下文** | 完整历史 | 仅上一章+这一章 |
| **客观性** | 受写作过程影响 | 完全客观 |
| **盲区检测** | 容易遗漏 | 容易发现 |
| **审查质量** | 中等 | **高** |

### 适用场景

- ✅ 重要章节（转折章、高潮章）
- ✅ 复杂剧情（多线并进）
- ✅ 用户反馈质量不佳的章节
- ✅ 首次使用ForgeAI的新手

---

## 输入格式

```json
{
  "chapter": 100,
  "project_root": "D:/wk/我的小说",
  "storage_path": ".forgeai/",
  "state_file": ".forgeai/state.json",
  "independent": false  // 是否启用独立审查模式（清除上下文）
}
```

---

## 🔴 独立审查模式（推荐）

### 为什么需要独立审查？

**问题**：AI审查时容易受到写作上下文影响，"自己审自己"容易出现盲区。

**解决方案**：清除对话历史，只传递【上一章】+【这一章】，模拟"新对话窗口"。

### 启用方式

```bash
# 方式1：CLI命令
python scripts/forgeai.py review 100 --independent

# 方式2：Agent调用
{
  "chapter": 100,
  "independent": true
}
```

### 输出

```json
{
  "status": "ok",
  "mode": "independent",
  "review_prompt": "你是严厉的资深编辑...",
  "instructions": [
    "1. 复制上述审查提示词",
    "2. 打开一个新的对话窗口",
    "3. 粘贴提示词到新窗口",
    "4. 获取独立的审查结果",
    "5. 根据审查结果修改章节内容"
  ],
  "saved_to": ".forgeai/independent_reviews/ch100_review_prompt.md"
}
```

## 输出格式

```json
{
  "agent": "consistency-checker",
  "chapter": 100,
  "overall_score": 85,
  "pass": true,
  "issues": [],
  "metrics": {
    "power_conflicts": 0,
    "location_errors": 0,
    "timeline_issues": 0,
    "entity_conflicts": 0
  },
  "summary": "设定一致性检查通过，无冲突"
}
```

---

## 三层一致性检查

### 第一层：战力一致性（战力检查）

**校验项**：
- 主角当前境界/等级是否与状态记录一致
- 使用的能力是否在境界限制内
- 能力提升是否遵循既定规则

**危险信号** (POWER_CONFLICT):
```
❌ 主角筑基3层使用金丹期才能掌握的"破空斩"
   → Realm: 筑基3 | Ability: 破空斩 (requires 金丹期)
   → VIOLATION: Premature ability access

❌ 上章淬体9层，本章突然凝气5层（无突破描写）
   → Previous: 淬体9 | Current: 凝气5 | Missing: Breakthrough scene
   → VIOLATION: Unexplained power jump
```

**校验依据**：
- `.forgeai/state.json`: `protagonist_state.power.realm`, `protagonist_state.power.layer`
- `2-设定/修炼体系.md`: Realm ability restrictions

### 第二层：地点/角色一致性（地点/角色检查）

**校验项**：
- 当前地点是否有合理的移动路径
- 出场角色是否已建立档案
- 角色属性（外貌/性格/阵营）是否与记录匹配

**危险信号** (LOCATION_ERROR / CHARACTER_CONFLICT):
```
❌ 上章在"天云宗"，本章突然在"千里外的血煞秘境"（无移动描写）
   → Previous location: 天云宗 | Current: 血煞秘境 | Distance: 1000+ li
   → VIOLATION: Teleportation without explanation

❌ 李雪上次是"筑基期"，本章变成"练气期"（无解释）
   → Character: 李雪 | Previous: 筑基期 | Current: 练气期
   → VIOLATION: Power regression unexplained
```

**校验依据**：
- `.forgeai/state.json`: `protagonist_state.location.current`
- `2-设定/角色卡/`: Character profiles

### 第三层：时间线一致性（时间线检查）

**校验项**：
- 事件顺序是否时序逻辑
- 时限元素（倒计时/年龄/季节）是否对齐
- 闪回是否明确标注
- 章节时间锚点是否匹配卷时间线

**严重度分级**：

| 问题类型 | Severity | 说明 |
|---------|----------|------|
| 倒计时算术错误 | **critical** | D-5 直接跳到 D-2，必须修复 |
| 事件先后矛盾 | **high** | 先发生的事情后写，逻辑混乱 |
| 年龄/修炼时长冲突 | **high** | 算术错误，如15岁修炼5年却10岁入门 |
| 时间回跳无标注 | **high** | 非闪回章节却出现时间倒退 |
| 大跨度无过渡 | **high** | 跨度>3天却无过渡说明 |
| 时间锚点缺失 | **medium** | 无法确定章节时间，但不影响逻辑 |
| 轻微时间模糊 | **low** | 时段不明确但不影响剧情 |

**危险信号** (TIMELINE_ISSUE):
```
❌ [critical] 第10章物资耗尽倒计时 D-5，第11章直接变成 D-2（跳过3天）
   → Setup: D-5 | Next chapter: D-2 | Missing: 3 days
   → VIOLATION: Countdown arithmetic error (MUST FIX)

❌ [high] 第10章提到"三天后的宗门大比"，第11章描述大比结束（中间无时间流逝）
   → Setup: 3 days until event | Next chapter: Event concluded
   → VIOLATION: Missing time passage

❌ [high] 主角15岁修炼5年，推算应该10岁开始，但设定集记录"12岁入门"
   → Age: 15 | Cultivation years: 5 | Start age: 10 | Record: 12
   → VIOLATION: Timeline arithmetic error

❌ [high] 第一章末世降临，第二章就建立帮派（无时间过渡）
   → Chapter 1: 末世第1天 | Chapter 2: 建帮派火拼
   → VIOLATION: Major event without reasonable time progression

❌ [high] 本章时间锚点"末世第3天"，上章是"末世第5天"（时间回跳）
   → Previous: 末世第5天 | Current: 末世第3天
   → VIOLATION: Time regression without flashback marker
```

---

## 执行流程

### Step 1: 加载参考资料

```bash
# 并行读取
cat "${project_root}/${state_file}"
cat "${project_root}/2-设定/修炼体系.md"
cat "${project_root}/3-大纲/第${volume_id}卷-时间线.md"
cat "${project_root}/4-正文/第${chapter_padded}章*.md"
```

### Step 2: 战力一致性检查

```python
# 检查战力
current_realm = state['protagonist_state']['power']['realm']
abilities_used = extract_abilities_from_text(chapter_text)

for ability in abilities_used:
    required_realm = get_ability_requirement(ability, setting_file)
    if not can_use(current_realm, required_realm):
        issues.append({
            "type": "POWER_CONFLICT",
            "severity": "critical",
            "detail": f"主角{current_realm}使用{required_realm}才能掌握的{ability}"
        })
```

### Step 3: 地点/角色一致性检查

```python
# 检查地点
previous_location = state['protagonist_state']['location']['current']
current_location = extract_location_from_text(chapter_text)

distance = calculate_distance(previous_location, current_location, world_map)
if distance > MAX_REASONABLE_DISTANCE and not has_travel_description(chapter_text):
    issues.append({
        "type": "LOCATION_ERROR",
        "severity": "high",
        "detail": f"从{previous_location}瞬移到{current_location}（距离{distance}里）"
    })
```

### Step 4: 时间线一致性检查

```python
# 检查时间线
chapter_time_anchor = extract_time_anchor(chapter_text)
previous_time_anchor = get_previous_chapter_time_anchor(chapter - 1)

# 倒计时检查
countdown_check = validate_countdown_progression(
    previous_time_anchor,
    chapter_time_anchor
)
if not countdown_check['valid']:
    issues.append({
        "type": "TIMELINE_ISSUE",
        "severity": "critical",
        "detail": countdown_check['error']
    })

# 时间回跳检查
if is_time_regression(previous_time_anchor, chapter_time_anchor):
    if not has_flashback_marker(chapter_text):
        issues.append({
            "type": "TIMELINE_ISSUE",
            "severity": "high",
            "detail": "时间回跳但未标注闪回"
        })
```

### Step 5: 实体一致性检查

```python
# 检查新实体
new_entities = extract_new_entities(chapter_text)
for entity in new_entities:
    conflicts = check_entity_conflicts(entity, existing_entities)
    if conflicts:
        issues.append({
            "type": "ENTITY_CONFLICT",
            "severity": "medium",
            "detail": f"{entity['name']}与现有设定冲突"
        })
```

### Step 6: 生成报告

```json
{
  "agent": "consistency-checker",
  "chapter": 100,
  "overall_score": 85,
  "pass": true,
  "issues": [
    {
      "type": "POWER_CONFLICT",
      "severity": "high",
      "detail": "主角筑基3层使用金丹期技能",
      "suggestion": "替换为筑基期可用技能或添加突破描写"
    }
  ],
  "metrics": {
    "power_conflicts": 1,
    "location_errors": 0,
    "timeline_issues": 0,
    "entity_conflicts": 0
  },
  "summary": "发现1处战力冲突，需修复"
}
```

---

## 评分规则

```
基础分 = 100

每个critical问题: -15分
每个high问题: -10分
每个medium问题: -5分
每个low问题: -2分

最终分 = max(0, 100 - Σ扣分)
```

| 分数区间 | 结果 |
|---------|------|
| 85-100 | 通过 |
| 70-84 | 通过（有警告） |
| 50-69 | 条件通过（需修复） |
| <50 | 未通过（必须重写） |

---

## 禁止事项

❌ 通过存在 POWER_CONFLICT（战力崩坏）的章节
❌ 忽略未标记的新实体
❌ 接受无世界观解释的瞬移
❌ 降低 TIMELINE_ISSUE 严重度
❌ 通过存在严重/高优先级时间线问题的章节

---

## 成功标准

- ✅ 0个严重违规（战力冲突、无解释的角色变化、时间线算术错误）
- ✅ 0个高优先级时间线问题
- ✅ 所有新实体与现有世界观一致
- ✅ 地点和时间线过渡合乎逻辑
- ✅ 报告为润色步骤提供具体修复建议

---

## 与其他Agent的集成

- **与Context Agent联动**：使用Context Contract中的时间约束作为检查基准
- **与Continuity Checker联动**：时间线问题可能影响情节连贯性
- **与Data Agent联动**：发现问题后可标记为invalid_facts
