# Phase 2: 文档完善 - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

完善 ForgeAI 系统文档,提升用户体验。包括命令文档、Agent文档、工作流文档、API文档的完善和重组。

</domain>

<decisions>
## Implementation Decisions

### 文档组织结构
- **D-01:** 按用户流程组织文档结构,而非按功能模块
- **D-02:** 创建6个主要目录: 01-快速开始、02-创作流程、03-命令参考、04-Agent详解、05-API文档、06-故障排查
- **D-03:** 每个目录包含多个相关文档,形成清晰的学习路径

### 文档详细程度
- **D-04:** 采用分层文档策略,满足不同用户需求
- **D-05:** 第一层:快速开始(5分钟上手,极简)
- **D-06:** 第二层:详细指南(完整步骤,配图/代码)
- **D-07:** 第三层:API参考(完整参数,所有选项)
- **D-08:** 第四层:示例库(真实案例,可复制粘贴)

### 示例代码策略
- **D-09:** 示例代码应完整可运行,而非仅片段
- **D-10:** 每个示例包含完整上下文(配置、输入、输出)
- **D-11:** 提供多种场景的示例(基础、进阶、故障排查)

### 多语言支持
- **D-12:** 优先完成中文文档
- **D-13:** 英文文档作为后续扩展,不在本阶段范围内
- **D-14:** 代码注释和变量名保持英文,文档内容使用中文

### Claude's Discretion
- 具体文档的章节划分
- 示例的选择和编排
- 图表和截图的添加位置
- 文档格式细节(标题层级、代码块样式等)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 现有文档参考
- `README.md` — 项目简介和快速开始
- `docs/SYSTEM_WORKFLOW_MINDMAP.md` — 系统工作流程思维导图
- `docs/WRITE_COMMAND.md` — 写作命令文档
- `docs/AFTER_WRITE_WORKFLOW.md` — 写后处理流程文档
- `docs/MULTI_AGENT_REVIEW.md` — 多Agent审查文档

### 代码库参考
- `system/skills/` — 8个技能定义文件
- `system/agents/` — 9个Agent定义文件
- `system/scripts/forgeai_modules/` — 29个Python模块
- `system/scripts/forgeai.py` — CLI命令实现

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **现有文档**: 已有10个文档可作为基础材料
- **命令文档模板**: WRITE_COMMAND.md 可作为命令文档模板
- **Agent文档模板**: MULTI_AGENT_REVIEW.md 可作为Agent文档模板

### Established Patterns
- **Markdown格式**: 所有文档使用Markdown格式
- **代码示例**: 使用代码块展示命令和代码
- **结构化组织**: 使用标题层级组织内容

### Integration Points
- **文档目录**: `docs/` 目录需要重组
- **README更新**: README.md 需要更新以反映新文档结构
- **导航链接**: 各文档间需要建立导航链接

</code_context>

<specifics>
## Specific Ideas

- 文档应该让新手能在5分钟内上手
- 每个命令都应该有完整的示例(输入、输出、预期结果)
- Agent文档应该包含具体的问题示例和修复建议
- 应该有一个完整的创作流程示例(从创建项目到完成第一章)

</specifics>

<deferred>
## Deferred Ideas

- 英文文档翻译 — 后续版本
- 视频教程制作 — 后续版本
- 交互式文档网站 — 后续版本
- 文档自动化测试 — 后续版本

</deferred>

---

*Phase: 02-documentation*
*Context gathered: 2026-04-19*
