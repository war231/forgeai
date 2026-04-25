# Phase 5: 发布准备 - 执行计划

**创建时间**: 2026-04-25
**阶段目标**: 准备 v1.1 版本发布
**预计时间**: 2-3 小时

---

## 📋 执行概览

**Wave 1: 发布准备** (基础设施)
- Task 5.1: 创建发布检查脚本
- Task 5.2: 创建发布检查清单

**Wave 2: 质量保证** (验证)
- Task 5.3: 执行自动化检查
- Task 5.4: 执行手动测试

**Wave 3: 发布执行** (发布)
- Task 5.5: 更新版本和文档
- Task 5.6: 创建发布

---

## Wave 1: 发布准备

### Task 5.1: 创建发布检查脚本

**目标**: 创建自动化发布检查脚本

**实现步骤**:
1. 创建 `scripts/pre-release-check.py`
2. 实现检查函数:
   - `check_tests()` - 运行 pytest
   - `check_code_style()` - 运行 flake8
   - `check_code_format()` - 运行 black
   - `check_types()` - 运行 mypy
   - `check_security()` - 运行 pip-audit
3. 实现结果汇总和报告
4. 添加颜色输出和进度显示

**验收标准**:
- [ ] 脚本可执行
- [ ] 所有检查函数正常工作
- [ ] 错误报告清晰详细
- [ ] 使用彩色输出

**预计时间**: 30 分钟

---

### Task 5.2: 创建发布检查清单

**目标**: 创建详细的发布检查清单文档

**实现步骤**:
1. 创建 `RELEASE_CHECKLIST.md`
2. 列出所有检查项目:
   - 自动化检查
   - 手动测试
   - 文档检查
   - 跨版本测试
   - 跨平台测试
3. 为每个检查提供方法说明
4. 添加检查命令示例

**验收标准**:
- [ ] 清单完整
- [ ] 每项都有方法说明
- [ ] 命令示例正确
- [ ] 格式清晰易读

**预计时间**: 15 分钟

---

## Wave 2: 质量保证

### Task 5.3: 执行自动化检查

**目标**: 运行所有自动化检查并确保通过

**实现步骤**:
1. 运行测试套件
   ```bash
   pytest tests/ -v --cov=forgeai_modules --cov-report=term-missing
   ```
2. 运行代码质量检查
   ```bash
   flake8 system/scripts/forgeai_modules/ --max-line-length=100
   black --check system/scripts/forgeai_modules/
   mypy system/scripts/forgeai_modules/
   ```
3. 运行安全检查
   ```bash
   pip-audit
   ```
4. 记录所有检查结果
5. 修复任何失败项

**验收标准**:
- [ ] 所有测试通过
- [ ] 代码质量检查通过
- [ ] 安全检查通过
- [ ] 无警告或错误

**预计时间**: 30 分钟

---

### Task 5.4: 执行手动测试

**目标**: 执行手动功能测试

**实现步骤**:
1. 测试基本功能:
   ```bash
   # 创建测试项目
   cd /tmp
   forgeai init 测试小说
   cd 测试小说
   
   # 测试基本命令
   forgeai status
   forgeai help
   forgeai version
   ```
2. 测试 CLI 优化功能:
   ```bash
   # 测试彩色输出
   forgeai help generate
   
   # 测试错误提示
   forgeai generate 999  # 应该显示友好的错误提示
   ```
3. 验证文档示例:
   - 检查 README.md 中的所有示例
   - 检查 CHANGELOG.md 的格式
4. 记录测试结果

**验收标准**:
- [ ] 基本功能正常
- [ ] CLI 优化功能正常
- [ ] 文档示例可运行
- [ ] 错误提示友好

**预计时间**: 20 分钟

---

## Wave 3: 发布执行

### Task 5.5: 更新版本和文档

**目标**: 更新版本号和相关文档

**实现步骤**:
1. 更新版本号:
   - `pyproject.toml`: version = "1.1.0"
   - `system/scripts/forgeai_modules/__init__.py`: __version__ = "1.1.0"
   - `system/scripts/forgeai_modules/help_system.py`: v1.1.0

2. 更新 CHANGELOG.md:
   ```markdown
   ## 2026-04-25 - v1.1.0 稳定版本
   
   ### ✨ 新特性
   
   #### CLI 体验优化
   - 彩色输出和格式化显示
   - 友好的错误提示和修复建议
   - 完整的帮助系统和快速入门
   - 进度显示和状态跟踪
   
   ### 🐛 Bug 修复
   
   - 修复独立审查提示词生成失败
   - 修复 VSCode 扩展命令映射问题
   
   ### 🔧 优化改进
   
   - 实体提取性能提升 200x
   - RAG 检索性能提升 100x
   - 测试覆盖率提升到 103.45%
   ```

3. 更新 README.md:
   - 更新版本号
   - 更新功能列表
   - 更新安装说明

**验收标准**:
- [ ] 版本号已更新到 1.1.0
- [ ] CHANGELOG.md 已更新
- [ ] README.md 已更新
- [ ] 所有版本号一致

**预计时间**: 20 分钟

---

### Task 5.6: 创建发布

**目标**: 创建 Git 标签和 GitHub Release

**实现步骤**:
1. 提交所有更改:
   ```bash
   git add .
   git commit -m "chore: release v1.1.0"
   ```

2. 创建 Git 标签:
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0 - CLI 体验优化"
   git push origin main
   git push origin v1.1.0
   ```

3. 构建 Python 包:
   ```bash
   python -m build
   ```

4. 发布到 PyPI:
   ```bash
   twine upload dist/*
   ```

5. 创建 GitHub Release:
   - 使用 CHANGELOG.md 的 v1.1.0 部分
   - 附加构建产物

**验收标准**:
- [ ] Git 标签已创建
- [ ] PyPI 发布成功
- [ ] GitHub Release 已创建
- [ ] 用户可以安装: `pip install forgeai==1.1.0`

**预计时间**: 15 分钟

---

## 📊 执行统计

**总任务数**: 6
**预计总时间**: 2-3 小时

**Wave 1**: 45 分钟 (基础设施)
**Wave 2**: 50 分钟 (验证)
**Wave 3**: 35 分钟 (发布)

---

## 🎯 成功标准

### 必须达成
- [ ] 所有自动化检查通过
- [ ] 手动测试全部成功
- [ ] 版本号已更新到 1.1.0
- [ ] CHANGELOG.md 已更新
- [ ] README.md 已更新
- [ ] Git 标签已创建
- [ ] PyPI 发布成功

### 期望达成
- [ ] GitHub Release 已创建
- [ ] 文档示例全部可运行
- [ ] 无遗留问题

---

## 🚫 风险和缓解

### 风险 1: 测试失败
**影响**: 阻塞发布
**缓解**: 优先修复测试失败，确保所有测试通过

### 风险 2: PyPI 发布失败
**影响**: 用户无法安装
**缓解**: 
- 提前验证 PyPI 凭据
- 使用 `twine check dist/*` 验证包
- 准备回滚方案

### 风险 3: 版本号不一致
**影响**: 用户困惑
**缓解**: 
- 使用脚本检查所有版本号
- 确保一致性后再发布

---

## 📝 执行顺序

1. **Wave 1**: 创建基础设施（检查脚本和清单）
2. **Wave 2**: 执行质量保证（自动化检查和手动测试）
3. **Wave 3**: 执行发布（更新版本和创建发布）

**注意**: Wave 2 必须全部通过才能进入 Wave 3

---

## 🎉 完成标志

Phase 5 完成后，应该达到以下状态：

- ✅ v1.1.0 成功发布到 PyPI
- ✅ 用户可以通过 `pip install forgeai` 安装
- ✅ 所有文档已更新
- ✅ GitHub Release 已创建
- ✅ 项目进入稳定状态
