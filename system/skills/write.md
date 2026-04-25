---
name: novel-write
description: 逐章正文创作，集成Agent系统。前置检查→Context Agent→撰写→审查Agents→润色→Data Agent→备份。
allowed-tools: Read Write Edit Grep Bash Task
---

# Workflow: Write（逐章写作 - Agent化版本）

> **核心升级**：集成Context Agent + 审查Agents + Data Agent，实现真正的Agent化流程。

## 流程硬约束（禁止事项）

| 禁止项 | 说明 |
|--------|------|
| **禁止并步** | 不得将两个 Step 合并为一个动作执行 |
| **禁止跳步** | 不得跳过未被模式定义标记为可跳过的 Step |
| **禁止自审替代** | 审查必须由 Task 子代理执行，主流程不得内联伪造审查结果 |
| **禁止占位符** | 禁止输出 `[待补充]`、`[TODO]`、`...（省略）...` |
| **禁止自创模式** | 只允许按定义裁剪步骤，不允许自创混合模式 |

## 执行原则

1. **必须用Task工具调用Agent**，禁止主流程内联Agent逻辑
2. **Agent可并行调用**，审查Agents支持同时运行
3. **参考Webnovel Writer流程**，确保流程标准化
4. **任何一步失败优先做最小回滚**，不重跑全流程
5. **严格遵守防幻觉三定律**：大纲即法律、设定即物理、发明需识别

---

## 步骤 0: 环境校验

```bash
export FORGEAI_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
export SCRIPTS_DIR="${FORGEAI_PLUGIN_ROOT}/scripts"
export PROJECT_ROOT="$(python "${SCRIPTS_DIR}/forgeai.py" --project-root "${WORKSPACE_ROOT}" where)"

python "${SCRIPTS_DIR}/forgeai.py" --project-root "${PROJECT_ROOT}" preflight
```

**硬门槛**：preflight必须成功，检查：
- `CLAUDE_PLUGIN_ROOT`环境变量
- `forgeai.py`存在
- 项目根目录解析正确

---

## 步骤 1：Context Agent（生成创作执行包）

> **CRITICAL**：写作前必须调用，确保创作执行包完整。

**使用Task调用context-agent**：

```json
{
  "agent": "context-agent",
  "input": {
    "chapter": ${chapter_num},
    "project_root": "${PROJECT_ROOT}",
    "storage_path": ".forgeai/",
    "state_file": ".forgeai/state.json"
  }
}
```

**样板书文风参考（可选）**：

若 `SOLOENT.md` §9 有样板书文风参考，Context Agent 应额外读取：

| 文风维度 | 参考内容 | 应用方式 |
|---------|---------|---------|
| **叙事视角** | 第一人称/第三人称 | 确保叙事视角一致 |
| **对白密度** | 高/中/低 | 控制对话占比 |
| **开头模式** | 场景切入/对话切入/心理切入 | 参考章节开头写法 |
| **结尾模式** | 悬念钩子/高潮截断/过渡收束 | 参考章节结尾写法 |
| **句式特点** | 平均句长、长短句比例 | 模仿语言风格 |
| **对白风格** | 主角说话方式、配角说话风格 | 参考角色对白风格 |

**输出（三合一创作执行包）**：

### 1.1 任务书（7板块）
- 本章核心任务（目标/阻力/代价/冲突）
- 接住上章（钩子/期待/开头建议）
- 出场角色（状态/动机/情绪/红线）
- 场景与力量约束
- 时间约束（锚点/跨度/过渡要求）
- 风格指导（类型/样本/模式）
- 连续性与伏笔（必须处理/可选）

### 1.2 Context Contract
- 目标/阻力/代价/本章变化
- 未闭合问题/核心冲突
- 开头类型/情绪节奏/信息密度
- 追读力设计（钩子类型/强度/微兑现）

### 1.3 直写提示词
- 章节节拍（开场→推进→反转→钩子）
- 不可变事实清单
- 禁止事项
- 终检清单

**硬要求**：
- ❌ 若Context Agent返回`MISSING_INPUT`，立即阻断并提示补齐
- ❌ 若返回`DATA_INCONSISTENCY`，提示用户确认后才能继续
- ✅ 输出可直接给写作步骤使用，无需补问

---

## 步骤 2：正文撰写

**基于Context Agent的创作执行包**：

- **分场景生成**：按任务书节拍逐个撰写
- **字数锚定**：2300-3000字/章（Context Contract可覆盖）
- **文风执行**：严格执行 `system/constitution/MASTER.md`
- **结尾钩子**：按Context Contract的追读力设计设置
- **创作范围**：严格遵守章纲，不得超出

**中文思维写作约束**：
- ❌ 禁止"先英后中"（不得用英文结构驱动）
- ✅ 中文叙事单元优先（动作/反应/代价/情绪）
- ❌ 禁止英文结论话术（Overall/PASS/FAIL等）

**输出**：`4-正文/第${chapter_padded}章_草稿.md`

---

## 步骤 3：审查（并行调用Agents）

> **CRITICAL**：必须用Task调用审查Agents，禁止主流程伪造审查结果。

**核心审查Agents（始终执行）**：
- `consistency-checker` - 设定一致性
- `ooc-checker` - 人物OOC
- `continuity-checker` - 连贯性
- `reader-pull-checker` - 追读力

**条件审查Agents（auto路由）**：
- `high-point-checker` - 战斗章/关键章
- `pacing-checker` - 每10章

### 调用方式（并行）

```markdown
使用Task工具同时调用多个Agents：

Task → consistency-checker
Task → ooc-checker
Task → continuity-checker
Task → reader-pull-checker
(并行执行，等待所有结果)
```

### 审查结果汇总

所有Agent返回统一JSON Schema：

```json
{
  "agent": "checker-name",
  "overall_score": 85,
  "pass": true,
  "issues": [...]
}
```

**评分计算**：
```
overall_score = (consistency + ooc + continuity + reader_pull) / 4
```

**硬要求**：
- ❌ 任一Agent返回`pass: false`，必须进入步骤4修复
- ✅ 所有Agent通过（`overall_score >= 85`），可直接进入步骤5

---

## 步骤 4：润色 + 去AI味

**优先级修复**：
1. **critical问题**（必须修复）
2. **high问题**（不能修复则记录deviation）
3. **medium/low问题**（按收益择优）

**去AI味流程**：

调用`skills/humanize.md`（进化式去AI味）：

```json
{
  "input_text": "${chapter_content}",
  "context": {
    "character_state": "...",
    "scene": "...",
    "emotion": "..."
  }
}
```

**Humanize输出**：
- baseline评分（双引擎：网文AI味60% + 通用AI味40%）
- 3个挑战者版本
- 最佳版本（综合分最高的）
- 修复轮（最多3轮，直到分数≥85）

**Anti-AI终检**：
- 执行24种AI特征检测
- 输出`anti_ai_force_check: pass/fail`
- ❌ `fail`时不得进入步骤5

**输出**：覆盖原章节文件

---

## 步骤 5：Data Agent（数据回写）

> **CRITICAL**：此步骤决定记忆连续性，绝对不可跳过！

**使用Task调用data-agent**：

```json
{
  "agent": "data-agent",
  "input": {
    "chapter": ${chapter_num},
    "chapter_file": "4-正文/第${chapter_padded}章_草稿.md",
    "review_score": ${overall_score},
    "project_root": "${PROJECT_ROOT}",
    "storage_path": ".forgeai/",
    "state_file": ".forgeai/state.json"
  }
}
```

**Data Agent自动执行**：

- ✅ AI实体提取
- ✅ 实体消歧
- ✅ 写入state.json
- ✅ 写入index.db
- ✅ 生成章节摘要
- ✅ AI场景切片
- ✅ RAG向量索引
- ✅ 风格样本评估（仅review_score ≥ 80）
- ✅ 伏笔管理（新增/收回）

**输出检查**：

```bash
test -f "${PROJECT_ROOT}/.forgeai/state.json"
test -f "${PROJECT_ROOT}/.forgeai/summaries/ch${chapter_padded}.md"
python "${SCRIPTS_DIR}/forgeai.py" --project-root "${PROJECT_ROOT}" status
```

**失败隔离规则**：
- RAG/style子步骤失败 → 仅补跑该子步骤，不回滚
- state/index写入失败 → 重跑Step 5，不回滚已通过步骤

---

## 步骤 6：Git备份（可失败但需说明）

```bash
cd "${PROJECT_ROOT}"
git add .
git -c i18n.commitEncoding=UTF-8 commit -m "第${chapter_num}章: ${title}"
```

**规则**：
- 提交时机：验证、回写、清理全部完成后
- 提交信息中文：`第X章: 标题`
- 若commit失败，给出失败原因与未提交文件范围

---

## 充分性闸门（必须通过）

未满足以下条件前，不得结束流程：

1. ✅ 章节正文文件存在且非空
2. ✅ Context Agent已生成创作执行包
3. ✅ 审查Agents已调用且结果落库
4. ✅ overall_score已产出
5. ✅ critical问题已处理，high未修项有deviation记录
6. ✅ anti_ai_force_check = pass
7. ✅ Data Agent已回写state.json、summaries、index.db
8. ✅ 无严重错误，警告已记录

---

## 🚫 循环阻断

- **有剩余章节**：询问"第X章完成。是否继续第X+1章？"
- **本卷已完**：提示调用outline规划下一卷
- **剧情偏离**：引导调用outline的动态修订

**等待用户指令，严禁自动开始下一章。**

---

## ⏭️ 下一步

- 审查通过 → 下一章 novel-write
- 审查未通过 → 根据报告修改
- 用户中止 → Workflow记录断点，可恢复
