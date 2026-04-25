# Phase 1: Bug修复和优化 - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

---

<domain>
## Phase Boundary

修复 ForgeAI v1.0 已知 bug，优化系统稳定性和性能，确保核心功能正常工作。

**范围**:
- 修复独立审查提示词生成 Bug
- 优化实体提取性能
- 修复 VSCode 扩展命令映射
- 优化 RAG 检索性能

**不包含**:
- 新功能开发（属于 Phase 2+）
- 文档完善（属于 Phase 2）
- 测试覆盖（属于 Phase 3）

</domain>

<decisions>
## Implementation Decisions

### Bug 分析

#### BUG-01: 独立审查提示词生成失败

**问题现象**:
```bash
forgeai check review 20 --independent
```
生成文件包含 "错误：缺少章节内容"，而非实际提示词。

**根本原因**:
在 `independent_reviewer.py` 的 `generate_review_prompt` 方法中：

```python:114
if not previous or not current:
    return "错误：缺少章节内容"
```

这个判断在 `prepare_minimal_context` 返回的 context 中，如果找不到章节文件，会返回 `None`，导致提示词生成失败。

**问题定位**:
1. `prepare_minimal_context` 方法使用 glob 匹配章节文件：
   ```python:90
   current_chapter_files = list(project_root.glob(f"4-正文/第{current_chapter:03d}章*.md"))
   ```
2. 如果章节文件不存在或命名不匹配，`current_chapter_files` 为空列表
3. 导致 `context["current_chapter"]` 为 `None`
4. 触发 `generate_review_prompt` 的错误返回

**修复方案**:

**方案 A: 改进错误处理（推荐）**
- 在 `prepare_minimal_context` 中添加详细错误信息
- 在 `generate_review_prompt` 中提供具体的缺失信息
- 添加日志输出，帮助用户定位问题

**方案 B: 放宽审查条件**
- 允许只审查当前章节（无需上一章）
- 修改提示词生成逻辑，适配单章节审查

**方案 C: 提供章节文件路径参数**
- 让用户显式指定章节文件路径
- 避免自动匹配失败

**选择**: 方案 A（改进错误处理）

**理由**:
1. 保持独立审查的完整性（需要上一章对比）
2. 提供清晰的错误信息，用户能快速定位问题
3. 不改变核心审查逻辑

---

### 实体提取优化

**当前问题**:
- 实体提取方法名已统一为 `extract`
- 但性能仍有优化空间
- 缺少缓存机制

**优化方向**:
1. 添加实体提取结果缓存
2. 优化 NER 模型调用
3. 添加实体去重逻辑

---

### VSCode 扩展命令映射

**当前问题**:
- 部分命令未正确映射
- 错误处理不完善

**优化方向**:
1. 检查 `extension.ts` 命令注册
2. 添加错误处理和日志
3. 测试所有命令

---

### RAG 检索优化

**当前问题**:
- 无检索缓存
- 向量索引可优化
- Reranker 调用可改进

**优化方向**:
1. 添加检索结果缓存（TTL: 5分钟）
2. 优化向量索引批量操作
3. 改进 Reranker 调用错误处理

---

### Claude's Discretion

- 具体修复实现细节由执行阶段决定
- 测试用例编写方式由执行阶段决定
- 性能优化具体参数由执行阶段决定

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Bug 相关代码
- `system/scripts/forgeai_modules/independent_reviewer.py` — 独立审查模块，需修复 `prepare_minimal_context` 和 `generate_review_prompt` 方法
- `system/scripts/forgeai_modules/entity_extractor_v3_ner.py` — 实体提取模块，需优化性能
- `src/extension.ts` — VSCode 扩展入口，需检查命令映射

### 配置和状态
- `.planning/STATE.md` — 项目状态跟踪
- `.planning/REQUIREMENTS.md` — REQ-006 多Agent审查需求

### 相关文档
- `docs/MULTI_AGENT_REVIEW.md` — 多Agent审查系统文档
- `docs/AFTER_WRITE_WORKFLOW.md` — 写后处理流程

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `forgeai_modules/config.py` — 配置管理，可用于添加缓存配置
- `forgeai_modules/logger.py` — 日志模块，可用于添加调试日志

### Established Patterns
- 错误处理模式：返回 JSON 格式错误信息
- 日志模式：使用 `logger.py` 统一日志

### Integration Points
- CLI 入口：`forgeai.py` 的 `cmd_check` 函数调用独立审查
- VSCode 扩展：`extension.ts` 调用 CLI 命令

</code_context>

<specifics>
## Specific Ideas

1. **错误信息改进示例**:
```python
# 改进前
if not previous or not current:
    return "错误：缺少章节内容"

# 改进后
if not previous:
    return f"错误：找不到第{current_chapter-1}章文件，请检查 4-正文/ 目录"
if not current:
    return f"错误：找不到第{current_chapter}章文件，请检查 4-正文/ 目录"
```

2. **日志添加示例**:
```python
logger.info(f"准备独立审查上下文：第{current_chapter}章")
logger.debug(f"查找章节文件：4-正文/第{current_chapter:03d}章*.md")
logger.warning(f"未找到章节文件：{current_chapter}")
```

</specifics>

<deferred>
## Deferred Ideas

None — 讨论保持在 Phase 1 范围内

</deferred>

---

*Phase: 01-bug-fix*
*Context gathered: 2026-04-19*
