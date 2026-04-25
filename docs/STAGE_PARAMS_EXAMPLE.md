# 创作环节参数使用示例

## 📋 快速开始

### 1. 配置 `.env` 文件

```env
# 创作参数配置
LLM_TEMPERATURE=0.7
LLM_TEMPERATURE_OUTLINE=0.4
LLM_TEMPERATURE_WRITING=1.0
LLM_TEMPERATURE_REVIEW=0.3
```

### 2. 在代码中使用

```python
from forgeai_modules.cloud_llm_client import CloudLLMManager

# 初始化客户端（自动加载 .env 配置）
llm = CloudLLMManager()

# 大纲创作（temperature=0.4）
outline = llm.chat(
    messages=[{"role": "user", "content": "生成第1章大纲"}],
    stage="outline"
)

# 正文创作（temperature=1.0）
content = llm.chat(
    messages=[{"role": "user", "content": "扩写第1章正文"}],
    stage="writing"
)

# 审查（temperature=0.3）
review = llm.chat(
    messages=[{"role": "user", "content": "审查第1章"}],
    stage="review"
)
```

---

## 🎯 实际应用场景

### 场景 1：大纲生成

```python
# 大纲需要严谨，避免逻辑矛盾
outline_prompt = """
请生成第1章的大纲：
- 主角：李天
- 场景：修炼室
- 情节：突破境界

要求：
1. 时间线清晰
2. 因果关系合理
3. 避免矛盾
"""

outline = llm.chat(
    messages=[{"role": "user", "content": outline_prompt}],
    stage="outline"  # 自动使用 temperature=0.4
)
```

**效果**：
- ✅ 逻辑严谨
- ✅ 时间线清晰
- ✅ 避免矛盾

---

### 场景 2：正文扩写

```python
# 正文需要创意和文采
writing_prompt = """
请扩写第1章正文：

大纲：
- 李天在修炼室突破境界
- 突破过程中遇到瓶颈
- 最终成功突破

要求：
1. 描写细腻
2. 情节生动
3. 文采优美
"""

content = llm.chat(
    messages=[{"role": "user", "content": writing_prompt}],
    stage="writing"  # 自动使用 temperature=1.0
)
```

**效果**：
- ✅ 描写生动
- ✅ 创意丰富
- ✅ 文采优美

---

### 场景 3：一致性审查

```python
# 审查需要严谨判断
review_prompt = """
请审查第1章的一致性：

上下文：
- 主角修为：筑基初期
- 主角位置：修炼室

待审查章节：
{chapter_content}

检查：
1. 时间线是否合理
2. 角色状态是否一致
3. 是否有矛盾
"""

review = llm.chat(
    messages=[{"role": "user", "content": review_prompt}],
    stage="review"  # 自动使用 temperature=0.3
)
```

**效果**：
- ✅ 判断准确
- ✅ 避免误判
- ✅ 发现问题

---

## 📊 参数对比

### 大纲生成（temperature=0.4）

**输出特点**：
- 结构清晰
- 逻辑严谨
- 避免矛盾

**示例输出**：
```
第1章大纲：
1. 李天进入修炼室（时间：清晨）
2. 开始修炼，遇到瓶颈（时间：中午）
3. 突破成功（时间：傍晚）
```

---

### 正文扩写（temperature=1.0）

**输出特点**：
- 描写生动
- 创意丰富
- 文采优美

**示例输出**：
```
清晨的修炼室，晨曦透过窗户洒落在李天身上。他盘膝而坐，体内灵力如江河奔涌，冲击着筑基中期的瓶颈。

"轰！"

一声闷响，修炼室的禁制微微颤抖。李天额头渗出汗珠，瓶颈比想象中更难突破...
```

---

### 一致性审查（temperature=0.3）

**输出特点**：
- 判断准确
- 逻辑清晰
- 避免误判

**示例输出**：
```
审查结果：
✓ 时间线合理（清晨→中午→傍晚）
✓ 角色状态一致（筑基初期→筑基中期）
✓ 无矛盾

建议：
- 可增加突破后的心理描写
```

---

## 🔧 高级用法

### 1. 手动覆盖参数

```python
# 特殊场景需要更高创意
content = llm.chat(
    messages=[{"role": "user", "content": "生成战斗场景"}],
    stage="writing",
    temperature=1.2  # 手动覆盖，优先级最高
)
```

### 2. 查看当前参数

```python
from forgeai_modules.env_loader import get_params_for_stage

# 查看大纲参数
outline_params = get_params_for_stage("outline")
print(f"大纲温度: {outline_params['temperature']}")

# 查看正文参数
writing_params = get_params_for_stage("writing")
print(f"正文温度: {writing_params['temperature']}")
```

### 3. 动态调整参数

```python
# 根据内容类型动态调整
def get_temperature_for_content(content_type):
    if content_type == "战斗":
        return 1.2  # 战斗场景需要更高创意
    elif content_type == "对话":
        return 0.8  # 对话需要自然
    elif content_type == "心理":
        return 0.6  # 心理描写需要细腻
    else:
        return 1.0  # 默认

content = llm.chat(
    messages=[{"role": "user", "content": "生成战斗场景"}],
    stage="writing",
    temperature=get_temperature_for_content("战斗")
)
```

---

## ✅ 最佳实践

### 1. 根据创作环节选择参数

| 环节 | 推荐温度 | 原因 |
|------|---------|------|
| 大纲生成 | 0.3-0.5 | 需要严谨 |
| 世界观设定 | 0.3-0.5 | 需要严谨 |
| 正文扩写 | 0.8-1.2 | 需要创意 |
| 对话描写 | 0.7-0.9 | 需要自然 |
| 战斗场景 | 1.0-1.3 | 需要激烈 |
| 心理描写 | 0.6-0.8 | 需要细腻 |
| 一致性审查 | 0.2-0.4 | 需要严谨 |
| 质量评估 | 0.2-0.4 | 需要严谨 |

### 2. 避免极端值

- ❌ temperature=0.0：输出过于保守，缺乏创意
- ❌ temperature=2.0：输出过于发散，容易跑题

### 3. 结合 top_p 使用

```env
# 推荐配置
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9  # 核采样，控制输出质量
```

---

**通过环节特定参数，让系统自动应用最优配置，提升创作质量！**
