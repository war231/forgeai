# Testing — ForgeAI Kit

> Generated: 2026-04-19

---

## Test Framework

| Component | Framework | Files |
|-----------|-----------|-------|
| Python | unittest（内置） | `tests/` |
| TypeScript | 无 | - |
| Integration | 手动测试 | - |

---

## Test Files

| File | Purpose |
|------|---------|
| `tests/test_connection.py` | API 连接测试 |
| `tests/count_words.py` | 字数统计工具 |
| `test_config.py`（根目录） | 配置测试 |
| `test_token_manager.py`（根目录） | Token 管理测试 |

---

## Test Coverage

**当前状态**：⚠️ 测试覆盖不足

| 模块 | 测试状态 |
|------|---------|
| `forgeai.py` (CLI) | ❌ 无测试 |
| `cloud_llm_client.py` | ⚠️ 连接测试 |
| `rag_adapter.py` | ❌ 无测试 |
| `state_manager.py` | ❌ 无测试 |
| `humanize_scorer.py` | ❌ 无测试 |
| `entity_extractor_v3_ner.py` | ❌ 无测试 |
| `book_analyzer.py` | ❌ 无测试 |
| `config.py` | ⚠️ 基础测试 |
| `token_manager.py` | ⚠️ 基础测试 |

---

## CI/CD

**当前状态**：❌ 无 CI/CD 配置

- 无 GitHub Actions / Jenkins 配置
- 无自动化测试流水线
- 依赖手动测试

---

## Testing Recommendations

1. **单元测试**：为 Python 模块添加 unittest
2. **集成测试**：测试 CLI 命令的端到端流程
3. **AI 评分测试**：验证 humanize_scorer 的评分准确性
4. **RAG 测试**：验证向量检索的召回率
5. **CI 配置**：添加 GitHub Actions 自动化测试
