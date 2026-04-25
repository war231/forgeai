# Phase 3: 测试覆盖 - Plan

**Phase:** 03-testing
**Created:** 2026-04-23
**Status:** Ready for execution

---

## Objective

为 ForgeAI 18 个缺少测试的新增模块编写单元测试，使总覆盖率从当前 64% 提升到 >85%，并添加 CLI 集成测试。

---

## Plan Structure

由于 18 个模块可按功能分组，分为 3 个执行波次（Wave），每波内的测试可并行编写。

---

## Wave 1: 核心新功能测试（优先级最高）

### Task 3.1: llm_entity_extractor 单元测试
- **File:** `tests/test_llm_entity_extractor.py`
- **Test cases:**
  1. `test_extract_from_chapter_sync_success` — Mock LLM 返回有效 JSON，验证实体/关系/状态变更提取
  2. `test_extract_with_code_block_json` — 测试从 ```json 代码块提取
  3. `test_extract_with_brace_extraction` — 测试从纯文本提取花括号 JSON
  4. `test_extract_malformed_json_repair` — 测试 JSON 修复逻辑
  5. `test_extract_empty_text` — 空文本返回空结果
  6. `test_extract_llm_error` — LLM 调用异常时的降级处理
  7. `test_save_to_state` — 验证写入 state.json 和 index.db
  8. `test_entity_deduplication` — 重复实体合并
- **Dependencies:** Mock cloud_llm_client, Mock state_manager

### Task 3.2: relationship_visualizer 单元测试
- **File:** `tests/test_relationship_visualizer.py`
- **Test cases:**
  1. `test_generate_mermaid_graph_all` — 生成完整关系图
  2. `test_generate_mermaid_graph_by_entity` — 按实体过滤
  3. `test_generate_mermaid_graph_by_tier` — 按层级过滤
  4. `test_generate_evolution_mermaid` — 关系演变时间线
  5. `test_generate_character_template` — 角色模板生成
  6. `test_generate_all_character_templates` — 批量模板生成
  7. `test_check_ooc_power_regression` — 战力倒退检测
  8. `test_check_ooc_personality_contradiction` — 性格矛盾检测
  9. `test_check_ooc_relationship_contradiction` — 关系矛盾检测
  10. `test_tier_color_mapping` — 层级颜色映射
- **Dependencies:** Mock state_manager (with entities and relationships data)

### Task 3.3: CLI entity/relationship 集成测试
- **File:** `tests/test_cli_entity_relationship.py`
- **Test cases:**
  1. `test_entity_add` — 添加实体
  2. `test_entity_import_markdown_table` — 从 Markdown 表格导入
  3. `test_entity_import_heading_list` — 从标题+列表格式导入
  4. `test_entity_import_soloent` — 从 SOLOENT 格式导入
  5. `test_relationship_add` — 添加关系
  6. `test_relationship_list` — 列出关系
  7. `test_relationship_graph` — 生成 Mermaid 图
  8. `test_stats_command` — 统计命令一致性
- **Dependencies:** tmp_path, subprocess

---

## Wave 2: 写作流水线测试

### Task 3.4: chapter_generator 单元测试
- **File:** `tests/test_chapter_generator.py`
- **Test cases:**
  1. `test_generate_chapter_success` — 正常生成章节
  2. `test_generate_with_context` — 带上下文生成
  3. `test_generate_empty_outline` — 空大纲处理
  4. `test_generate_llm_error` — LLM 错误处理

### Task 3.5: writing_pipeline 单元测试
- **File:** `tests/test_writing_pipeline.py`
- **Test cases:**
  1. `test_pipeline_init` — 流水线初始化
  2. `test_pipeline_run_full` — 完整流水线执行
  3. `test_pipeline_step_failure` — 步骤失败处理

### Task 3.6: batch_generator 单元测试
- **File:** `tests/test_batch_generator.py`
- **Test cases:**
  1. `test_batch_generate` — 批量生成
  2. `test_batch_with_progress` — 进度跟踪
  3. `test_batch_partial_failure` — 部分失败处理

### Task 3.7: parallel_generator 单元测试
- **File:** `tests/test_parallel_generator.py`
- **Test cases:**
  1. `test_parallel_generate` — 并行生成
  2. `test_parallel_concurrency_limit` — 并发限制
  3. `test_parallel_error_aggregation` — 错误聚合

---

## Wave 3: 辅助模块测试

### Task 3.8: cache_manager 单元测试
- **File:** `tests/test_cache_manager.py`
- **Test cases:**
  1. `test_cache_set_get` — 缓存读写
  2. `test_cache_ttl_expiry` — TTL 过期
  3. `test_cache_lru_eviction` — LRU 淘汰
  4. `test_cache_clear` — 缓存清除

### Task 3.9: retry_handler 单元测试
- **File:** `tests/test_retry_handler.py`
- **Test cases:**
  1. `test_retry_success_first_try` — 首次成功
  2. `test_retry_success_after_retries` — 重试后成功
  3. `test_retry_max_retries_exceeded` — 超过最大重试
  4. `test_retry_backoff_delay` — 退避延迟

### Task 3.10: error_handler 单元测试
- **File:** `tests/test_error_handler.py`
- **Test cases:**
  1. `test_handle_known_error` — 已知错误处理
  2. `test_handle_unknown_error` — 未知错误处理
  3. `test_error_classification` — 错误分类

### Task 3.11: 其余辅助模块测试（每组 2-3 个基础测试）
- **Files:** 
  - `tests/test_chapter_optimizer.py`
  - `tests/test_checkpoint_manager.py`
  - `tests/test_genre_profile_loader.py`
  - `tests/test_interactive_writer.py`
  - `tests/test_llm_optimizer.py`
  - `tests/test_reference_integrator.py`
  - `tests/test_review_feedback_loop.py`
  - `tests/test_template_system.py`
  - `tests/test_review_pipeline.py`
- **Test cases per file:** 基础初始化测试 + 核心方法测试 + 错误处理测试

### Task 3.12: 更新覆盖率报告
- **File:** `tests/TEST_COVERAGE_REPORT.md`
- 更新模块覆盖统计
- 运行 pytest --cov 生成实际覆盖率数据

---

## Verification

1. `pytest tests/ -v` — 所有测试通过
2. `pytest tests/ --cov=forgeai_modules --cov-report=term` — 覆盖率 >60%
3. 无 import 错误
4. 无测试间的相互依赖

---

## Dependencies

- Wave 1 → Wave 2 → Wave 3（顺序执行，每波内可并行）
- 总计新增 ~18 个测试文件，~100+ 测试用例

---

*Phase: 03-testing*
*Plan created: 2026-04-23*
