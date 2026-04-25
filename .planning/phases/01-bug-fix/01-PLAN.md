---
wave: 1
depends_on: []
files_modified:
  - system/scripts/forgeai_modules/independent_reviewer.py
autonomous: true
requirements_addressed: [REQ-006]
---

<objective>
修复独立审查提示词生成失败问题，提供清晰的错误信息和调试日志
</objective>

<tasks>
<task id="1" type="execute">
<read_first>
- system/scripts/forgeai_modules/independent_reviewer.py (file being modified)
- system/scripts/forgeai_modules/logger.py (logging module)
</read_first>

<action>
改进 `prepare_minimal_context` 方法的错误处理：

1. 在方法开头添加日志：
```python
logger.info(f"准备独立审查上下文：第{current_chapter}章")
logger.debug(f"查找章节文件：4-正文/第{current_chapter:03d}章*.md")
```

2. 在文件匹配失败时添加详细错误信息：
```python
if not current_chapter_files:
    logger.warning(f"未找到章节文件：4-正文/第{current_chapter:03d}章*.md")
    return {
        "error": f"找不到第{current_chapter}章文件，请检查 4-正文/ 目录下是否存在匹配的文件",
        "hint": f"期望文件名格式：第{current_chapter:03d}章*.md",
        "current_chapter": current_chapter
    }
```

3. 对上一章文件同样处理：
```python
if not previous_chapter_files:
    logger.warning(f"未找到上一章文件：4-正文/第{current_chapter-1:03d}章*.md")
    return {
        "error": f"找不到第{current_chapter-1}章文件，独立审查需要对比前后章节",
        "hint": f"期望文件名格式：第{current_chapter-1:03d}章*.md",
        "previous_chapter": current_chapter - 1
    }
```
</action>

<acceptance_criteria>
- `independent_reviewer.py contains "logger.info"`
- `independent_reviewer.py contains "logger.warning"`
- `independent_reviewer.py contains "找不到第"`
- `independent_reviewer.py contains "hint":`
</acceptance_criteria>
</task>

<task id="2" type="execute">
<read_first>
- system/scripts/forgeai_modules/independent_reviewer.py (file being modified)
</read_first>

<action>
改进 `generate_review_prompt` 方法的错误处理：

1. 替换原有的简单错误返回：
```python
# 改进前
if not previous or not current:
    return "错误：缺少章节内容"

# 改进后
if isinstance(context, dict) and "error" in context:
    # 返回详细的错误信息
    error_msg = context["error"]
    if "hint" in context:
        error_msg += f"\n提示：{context['hint']}"
    return error_msg

if not previous or not current:
    return f"错误：无法读取章节内容。请检查章节文件是否存在且格式正确。"
```

2. 添加成功日志：
```python
logger.info(f"成功生成独立审查提示词：第{current_chapter}章")
```
</action>

<acceptance_criteria>
- `independent_reviewer.py contains "isinstance(context, dict)"`
- `independent_reviewer.py contains '"error" in context'`
- `independent_reviewer.py contains "成功生成独立审查提示词"`
</acceptance_criteria>
</task>

<task id="3" type="execute">
<read_first>
- system/scripts/forgeai_modules/independent_reviewer.py (file being modified)
</read_first>

<action>
添加单元测试验证修复：

在 `tests/` 目录创建 `test_independent_reviewer.py`：

```python
import pytest
from forgeai_modules.independent_reviewer import IndependentReviewer

def test_prepare_minimal_context_missing_current_chapter():
    """测试当前章节文件不存在时的错误处理"""
    reviewer = IndependentReviewer()
    result = reviewer.prepare_minimal_context(project_root=".", current_chapter=999)
    
    assert "error" in result
    assert "找不到第999章" in result["error"]
    assert "hint" in result

def test_prepare_minimal_context_missing_previous_chapter():
    """测试上一章文件不存在时的错误处理"""
    reviewer = IndependentReviewer()
    # 假设第1章存在，但第0章不存在
    result = reviewer.prepare_minimal_context(project_root=".", current_chapter=1)
    
    if "error" in result:
        assert "找不到第0章" in result["error"] or "找不到第1章" in result["error"]

def test_generate_review_prompt_with_error_context():
    """测试错误上下文的提示词生成"""
    reviewer = IndependentReviewer()
    error_context = {
        "error": "测试错误",
        "hint": "测试提示"
    }
    result = reviewer.generate_review_prompt(error_context, 1)
    
    assert "测试错误" in result
    assert "测试提示" in result
```
</action>

<acceptance_criteria>
- `tests/test_independent_reviewer.py exists`
- `tests/test_independent_reviewer.py contains "test_prepare_minimal_context_missing_current_chapter"`
- `tests/test_independent_reviewer.py contains "test_generate_review_prompt_with_error_context"`
</acceptance_criteria>
</task>
</tasks>

<verification>
1. 运行测试：`pytest tests/test_independent_reviewer.py -v`
2. 手动测试：`forgeai check review 20 --independent` 应显示清晰的错误信息
3. 检查日志输出是否包含调试信息
</verification>

<must_haves>
- 错误信息必须包含具体的章节号
- 错误信息必须提示用户检查目录
- 必须添加日志记录
- 单元测试必须通过
</must_haves>
