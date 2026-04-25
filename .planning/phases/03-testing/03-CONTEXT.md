# Phase 3: 测试覆盖 - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

为 ForgeAI 系统添加测试覆盖，确保代码质量。目标覆盖率>60%。

当前状态：47个模块中有30个已有测试，18个新增模块缺少测试。现有覆盖率约64%（30/47），但新增模块（llm_entity_extractor、relationship_visualizer等）完全没有测试。

</domain>

<decisions>
## Implementation Decisions

### 测试框架
- **D-01:** 继续使用 pytest 作为测试框架，保持一致性
- **D-02:** 使用 unittest.mock 进行 LLM 依赖隔离，不调用真实 API
- **D-03:** 使用 conftest.py 中的共享 fixture 模式

### 优先级策略
- **D-04:** 优先为核心新模块添加测试：llm_entity_extractor、relationship_visualizer（用户最关心的功能）
- **D-05:** 其次为写作流水线模块添加测试：chapter_generator、writing_pipeline、batch_generator
- **D-06:** 最后为辅助模块添加测试：cache_manager、retry_handler、error_handler 等

### 集成测试策略
- **D-07:** 使用临时目录（tmp_path fixture）创建测试项目，不依赖真实项目数据
- **D-08:** 实体/关系提取集成测试使用 Mock LLM 返回预定义 JSON
- **D-09:** CLI 命令测试使用 subprocess 调用 forgeai.py

### LLM 相关测试
- **D-10:** 所有 LLM 调用必须 Mock，不产生真实 API 开销
- **D-11:** 为 LLM 返回格式异常情况添加容错测试

### Claude's Discretion
- 测试文件结构（类名、方法名）
- 具体 mock 数据设计
- 测试粒度（每个函数 vs 每个类）

</decisions>

<canonical_refs>
## Canonical References

### 测试相关
- `tests/conftest.py` — 共享 fixture 定义
- `tests/TEST_COVERAGE_REPORT.md` — 当前覆盖率报告
- `tests/test_entity_extractor_v3_ner.py` — 实体提取测试模式参考
- `tests/test_state_manager.py` — 状态管理测试模式参考

### 被测模块
- `system/scripts/forgeai_modules/llm_entity_extractor.py` — LLM实体提取器
- `system/scripts/forgeai_modules/relationship_visualizer.py` — 关系可视化
- `system/scripts/forgeai_modules/chapter_generator.py` — 章节生成器
- `system/scripts/forgeai_modules/writing_pipeline.py` — 写作流水线
- `system/scripts/forgeai_modules/batch_generator.py` — 批量生成器
- `system/scripts/forgeai_modules/cache_manager.py` — 缓存管理器
- `system/scripts/forgeai_modules/error_handler.py` — 错误处理器
- `system/scripts/forgeai_modules/retry_handler.py` — 重试处理器
- `system/scripts/forgeai_modules/chapter_optimizer.py` — 章节优化器
- `system/scripts/forgeai_modules/checkpoint_manager.py` — 检查点管理器
- `system/scripts/forgeai_modules/genre_profile_loader.py` — 题材配置加载器
- `system/scripts/forgeai_modules/interactive_writer.py` — 交互式写作器
- `system/scripts/forgeai_modules/llm_optimizer.py` — LLM优化器
- `system/scripts/forgeai_modules/parallel_generator.py` — 并行生成器
- `system/scripts/forgeai_modules/reference_integrator.py` — 参考整合器
- `system/scripts/forgeai_modules/review_feedback_loop.py` — 审查反馈循环
- `system/scripts/forgeai_modules/template_system.py` — 模板系统
- `system/scripts/forgeai_modules/review_pipeline.py` — 审查流水线

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `conftest.py`: 提供了 mock_config、mock_state_manager、temp_project 等 fixture
- 现有测试模式：每个模块一个 test_ 文件，使用 Mock 隔离依赖
- `test_cloud_llm_client.py`: LLM Mock 模式参考

### Established Patterns
- 测试类命名：Test{ModuleName}
- 测试方法命名：test_{function_name}_{scenario}
- Mock 模式：使用 @patch 装饰器 + MagicMock
- Fixture 模式：conftest.py 提供 tmp_path 和 mock 对象

### Integration Points
- 新测试需要 import forgeai_modules 中的模块
- llm_entity_extractor 依赖 cloud_llm_client（需 Mock）
- relationship_visualizer 依赖 state_manager（需 Mock）

</code_context>

<specifics>
## Specific Ideas

- 优先确保 llm_entity_extractor 和 relationship_visualizer 的测试覆盖
  （这两个是上一轮会话新增的核心功能）
- 为 forgeai.py CLI 的 entity import 和 relationship 命令添加集成测试
- 更新 TEST_COVERAGE_REPORT.md

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-testing*
*Context gathered: 2026-04-23*
