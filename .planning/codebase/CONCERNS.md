# Concerns — ForgeAI Kit

> Generated: 2026-04-19

---

## Technical Debt

### High Priority

| Issue | Description | Location |
|-------|-------------|----------|
| **遗留 assets 目录** | `assets/forgeai/` 与 `system/` 功能重复 | `assets/` |
| **Extension 路径硬编码** | `extension.ts` 引用 `assets/forgeai/` 而非 `system/` | `src/extension.ts:7-13` |
| **测试覆盖不足** | 29 个 Python 模块仅有 2 个基础测试 | `tests/` |
| **无 CI/CD** | 无自动化测试和发布流水线 | - |

### Medium Priority

| Issue | Description | Location |
|-------|-------------|----------|
| **样板书分析脚本未集成** | `book_analyzer.py` 存在但未被 CLI 调用 | `system/scripts/forgeai_modules/book_analyzer.py` |
| **路径不一致** | 部分文件引用 `.forgeai/constitution/`，实际在 `system/constitution/` | 已修复（2026-04-17） |
| **旧版 Python 模块** | `entity_extractor_v3_ner.py` 版本号暗示存在旧版 | - |
| **配置验证器** | `config_validator.py` 存在但未在主流程调用 | `system/scripts/forgeai_modules/config_validator.py` |

---

## Security Concerns

| Issue | Severity | Description |
|-------|----------|-------------|
| **API Key 明文存储** | ⚠️ Medium | `.env` 文件存储 API Key，无加密 |
| **无输入验证** | ⚠️ Medium | CLI 参数缺少严格验证 |
| **SQL 注入风险** | Low | SQLite 查询使用参数化，但需审查 |

---

## Performance Concerns

| Issue | Description | Impact |
|-------|-------------|--------|
| **Token 消耗** | 深度分析 50 章约消耗 5-10 万 Token | 高（成本） |
| **RAG 向量检索** | ChromaDB 随章节增长可能变慢 | 中 |
| **Python 启动开销** | 每次命令调用都启动 Python 进程 | Low |

---

## Fragile Areas

| Area | Why Fragile | Risk |
|------|------------|------|
| **Extension ↔ Python 通信** | 通过 `execFile` 调用，错误处理不完善 | 进程崩溃、超时 |
| **状态管理** | `state.json` 可能不同步 | 数据不一致 |
| **LLM 响应解析** | AI 输出格式不稳定 | 解析失败 |
| **模板文件同步** | 多处模板需要同步更新 | 流程断裂 |

---

## Known Bugs (Fixed)

| Bug | Fix Date | Description |
|-----|----------|-------------|
| 分析技能冲突 | 2026-04-17 | `analyze.md` 与 `book-analyzer.md` 功能重叠 → 删除 `analyze.md` |
| Constitution 路径不一致 | 2026-04-17 | `.forgeai/constitution/` → `system/constitution/` |
| 武行示例项目名 | 2026-04-17 | `PROJECT_RESTRUCTURE_PROPOSAL.md` 中"武行" → "示例小说" |

---

## Recommendations

1. **清理 assets 目录**：删除或合并到 system/
2. **更新 Extension 路径**：`src/extension.ts` 改为引用 `system/`
3. **添加单元测试**：优先覆盖核心模块
4. **添加 CI/CD**：GitHub Actions 自动测试
5. **API Key 加密**：使用 keychain 或 secrets manager
6. **输入验证**：CLI 参数严格验证
7. **集成 book_analyzer.py**：在 forgeai.py CLI 中添加 `analyze` 命令
