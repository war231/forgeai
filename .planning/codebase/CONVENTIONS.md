# Conventions — ForgeAI Kit

> Generated: 2026-04-19

---

## Code Style

### Python

- **命名**：snake_case（模块、函数、变量）
- **类命名**：PascalCase
- **常量**：UPPER_SNAKE_CASE
- **文档字符串**：模块级和类级使用 docstring
- **类型提示**：部分使用，非强制
- **行宽**：无严格限制，但建议 120 字符以内

### TypeScript

- **命名**：camelCase（函数、变量）
- **类命名**：PascalCase
- **常量**：UPPER_SNAKE_CASE
- **导入**：使用 ES Module 风格

### Markdown (技能/Agent 定义)

- **文件头**：YAML front matter（name, description）
- **步骤编号**：`## 步骤 N:` 或 `## Step N:`
- **表情符号**：步骤标题使用 emoji 前缀
- **引用块**：使用 `>` 标注来源和约束
- **表格**：使用 Markdown 表格展示参数和参考

---

## Error Handling

### Python

| Pattern | Usage | File |
|---------|-------|------|
| 自定义异常类 | 业务异常 | `exceptions.py` |
| try/except + logging | 错误捕获 | 全局 |
| return code | CLI 命令返回码 | `forgeai.py` |
| 超时控制 | API 调用超时 | `cloud_llm_client.py` |

### TypeScript

| Pattern | Usage | File |
|---------|-------|------|
| Promise + reject | 异步错误 | `extension.ts` |
| try/catch | 同步错误 | `extension.ts` |

---

## Configuration Pattern

### 环境变量 (.env)

```python
# env_loader.py 加载 .env 文件
# 支持多 Provider（kimi/openai/deepseek）
LLM_PROVIDER=kimi
LLM_BASE_URL=...
LLM_API_KEY=...
```

### 项目配置 (SOLOENT.md)

```markdown
## 1. 项目基因
## 2. 世界体系
## 3. 角色
...
## 9. 样板书参考
```

---

## AI Workflow Conventions

### 技能定义规范

1. **YAML Front Matter**：`name` + `description`
2. **来源标注**：`> **来源**：武行 xxx.md`
3. **步骤编号**：从 0 或 1 开始，逐步递增
4. **输入/输出**：每个步骤明确标注输入文件和输出文件
5. **CRITICAL 标注**：关键步骤使用 `> **CRITICAL**`
6. **下一步指引**：技能末尾标注 `## ⏭️ 下一步`

### Agent 定义规范

1. **角色定义**：Agent 名称和职责
2. **输入 Schema**：JSON 格式
3. **输出 Schema**：JSON 格式
4. **硬要求**：`❌` 和 `✅` 标注

---

## Git Conventions

- **提交信息**：中文，格式 `第X章: 标题`
- **提交时机**：验证、回写、清理全部完成后
- **分支**：主分支 main
