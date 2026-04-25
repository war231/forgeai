# Phase 4: CLI体验优化与通用化 - Plan

**Phase:** 04-cli-optimization
**Created:** 2026-04-25
**Status:** Ready for execution

---

## Objective

优化 ForgeAI CLI 的用户体验，通过彩色输出、错误提示优化、帮助系统完善和进度显示，让新用户更容易上手，提升整体易用性。

---

## Plan Structure

由于 4 个任务相对独立，分为 2 个执行波次（Wave），每波内的任务可并行执行。

---

## Wave 1: 输出体验优化（基础）

### Task 4.1: 彩色输出与格式化

- **File:** `system/scripts/forgeai_modules/cli_formatter.py` (新建)
- **Test:** `tests/test_cli_formatter.py` (新建)
- **Dependencies:** rich 库

**实现内容:**

1. **安装依赖**
   ```bash
   pip install rich
   ```

2. **创建 CLI 格式化模块**
   - `cli_formatter.py` - 统一的输出格式化工具
   - 提供成功、警告、错误、信息的彩色输出函数
   - 提供表格、面板、进度条的格式化工具

3. **核心函数**
   ```python
   def print_success(message: str)
   def print_error(message: str, suggestion: str = None)
   def print_warning(message: str)
   def print_info(message: str)
   def print_table(data: List[Dict], headers: List[str])
   def print_panel(content: str, title: str = None)
   ```

4. **集成到现有命令**
   - 更新 `forgeai.py` 使用新的格式化工具
   - 更新所有命令的输出格式

**验收标准:**
- [ ] 成功/警告/错误有明确的颜色区分
- [ ] 表格输出整齐美观
- [ ] 所有命令使用统一的输出格式

---

### Task 4.2: 错误提示优化

- **File:** `system/scripts/forgeai_modules/error_handler.py` (已存在，需增强)
- **Test:** `tests/test_error_handler.py` (已存在，需扩展)
- **Dependencies:** Task 4.1

**实现内容:**

1. **增强错误处理模块**
   - 添加错误分类（配置错误、API错误、文件错误等）
   - 为每类错误提供修复建议
   - 添加错误代码和文档链接

2. **核心功能**
   ```python
   class ForgeAIError(Exception):
       def __init__(self, message, error_code, suggestion, doc_url)
       
   def handle_error(error: Exception) -> ForgeAIError
   def print_error_with_suggestion(error: ForgeAIError)
   ```

3. **错误类型**
   - `ConfigError` - 配置错误
   - `APIError` - API 调用错误
   - `FileError` - 文件操作错误
   - `ValidationError` - 验证错误

4. **集成到现有命令**
   - 更新所有 try-catch 块使用新的错误处理
   - 添加错误日志记录

**验收标准:**
- [ ] 所有错误有清晰的错误信息
- [ ] 每个错误有具体的修复建议
- [ ] 错误日志记录完整

---

## Wave 2: 用户体验增强

### Task 4.3: 帮助系统完善

- **File:** `system/scripts/forgeai_modules/help_system.py` (新建)
- **Test:** `tests/test_help_system.py` (新建)
- **Dependencies:** Task 4.1

**实现内容:**

1. **创建帮助系统模块**
   - 为每个命令提供详细的帮助文档
   - 提供命令示例和用法说明
   - 提供快速入门指南

2. **核心功能**
   ```python
   def show_command_help(command: str)
   def show_quick_start()
   def show_examples(command: str)
   def show_faq()
   ```

3. **帮助内容**
   - 每个命令的详细说明
   - 参数说明和示例
   - 常见使用场景
   - 快速入门 5 步指南

4. **集成到 CLI**
   - `forgeai --help` 显示总体帮助
   - `forgeai <command> --help` 显示命令帮助
   - `forgeai quickstart` 显示快速入门

**验收标准:**
- [ ] 所有命令有详细的帮助文档
- [ ] 帮助文档包含示例
- [ ] 新用户能通过帮助快速上手

---

### Task 4.4: 进度显示优化

- **File:** `system/scripts/forgeai_modules/progress_display.py` (新建)
- **Test:** `tests/test_progress_display.py` (新建)
- **Dependencies:** Task 4.1, rich 库

**实现内容:**

1. **创建进度显示模块**
   - 为长时间操作提供进度条
   - 提供实时状态更新
   - 支持多步骤操作的进度跟踪

2. **核心功能**
   ```python
   class ProgressBar:
       def __init__(self, total, description)
       def update(self, amount)
       def complete()
       
   class StatusDisplay:
       def show_status(self, status, message)
       def show_step(self, step, total, message)
   ```

3. **集成到长时间操作**
   - `forgeai write` - 写作进度
   - `forgeai check` - 审查进度
   - `forgeai analyze` - 分析进度

4. **进度类型**
   - 确定进度（知道总数）
   - 不确定进度（旋转动画）
   - 多步骤进度（步骤列表）

**验收标准:**
- [ ] 长时间操作有进度条
- [ ] 进度信息实时更新
- [ ] 用户知道系统在工作

---

## Verification

1. **功能测试**
   ```bash
   pytest tests/test_cli_formatter.py -v
   pytest tests/test_error_handler.py -v
   pytest tests/test_help_system.py -v
   pytest tests/test_progress_display.py -v
   ```

2. **集成测试**
   ```bash
   forgeai --help
   forgeai init --help
   forgeai write --help
   forgeai quickstart
   ```

3. **用户体验测试**
   - 新用户能在 5 分钟内完成首次使用
   - 错误提示清晰易懂
   - 帮助文档完善

---

## Dependencies

- Wave 1 → Wave 2（顺序执行，每波内可并行）
- 总计新增 4 个模块，4 个测试文件

---

## Estimated Time

- Wave 1: 1-1.5 天
- Wave 2: 1-1.5 天
- 总计: 2-3 天

---

*Phase: 04-cli-optimization*
*Plan created: 2026-04-25*
