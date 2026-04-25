# Phase 5: 发布准备 - 上下文文档

**创建时间**: 2026-04-25
**阶段目标**: 准备 v1.1 版本发布

---

## 📋 项目现状

### 版本信息
- **当前版本**: v1.0.0
- **目标版本**: v1.1.0
- **版本文件位置**: 
  - `pyproject.toml` (line 7)
  - `system/scripts/forgeai_modules/__init__.py` (line 14)

### 发布文件状态
- ✅ `pyproject.toml` - 存在且配置完整
- ✅ `CHANGELOG.md` - 存在，需要更新 v1.1 内容
- ✅ `README.md` - 存在，需要更新
- ❌ `setup.py` - 不存在（使用现代 pyproject.toml）

### 测试状态
- **测试用例**: 987 个
- **测试覆盖率**: 103.45%
- **通过率**: 100%

### 已完成阶段
- ✅ Phase 1: Bug 修复和优化
- ✅ Phase 2: 文档完善
- ✅ Phase 3: 测试覆盖
- ✅ Phase 4: CLI 体验优化

---

## 🎯 核心决策

### 1. 发布检查清单

#### 1.1 自动化检查项目

**必须通过的检查**:
```bash
# 1. 测试套件
pytest tests/ -v --cov=forgeai_modules --cov-report=term-missing

# 2. 代码质量检查
flake8 system/scripts/forgeai_modules/ --max-line-length=100
black --check system/scripts/forgeai_modules/
mypy system/scripts/forgeai_modules/

# 3. 安全扫描
pip-audit                  # 检查依赖安全性漏洞
safety check              # 另一个安全检查工具
bandit -r system/scripts/ # 代码安全扫描
```

**检查失败处理**: 
- **阻塞策略**: 必须全部通过才能发布
- 不允许跳过检查
- 所有错误必须修复后才能继续

#### 1.2 手动测试流程

**基本功能验证** (必须执行):
```bash
# 1. 初始化项目
forgeai init 测试小说

# 2. 查看状态
forgeai status

# 3. 生成章节（如果配置了 API）
forgeai generate 1 --query "测试章节"
```

**完整工作流测试** (推荐):
1. 创建新项目
2. 配置 API 密钥
3. 生成章节
4. 审查章节
5. 导出小说

#### 1.3 文档完整性检查

**必须更新的文档**:
- [ ] `README.md` - 更新版本号、功能列表、安装说明
- [ ] `CHANGELOG.md` - 添加 v1.1 版本更新日志
- [ ] API 文档 - 更新 API 参考
- [ ] 用户指南 - 更新使用教程

**文档示例验证**:
- 所有代码示例必须可运行
- 所有命令示例必须有效
- 所有链接必须可访问

#### 1.4 依赖项检查

**依赖兼容性检查**:
```bash
# 检查 Python 版本兼容性
python -m pip install --upgrade pip
python -c "import sys; print(sys.version)"

# 检查依赖版本
pip list --outdated

# 检查依赖安全性
pip-audit
safety check
```

**跨版本兼容性**:
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

**跨平台兼容性**:
- Windows (已测试)
- Linux (需要测试)
- macOS (需要测试)

---

### 2. 发布检查执行策略

#### 2.1 执行模式

**混合模式**: 本地运行 + CI 验证

**本地检查** (开发者执行):
```bash
# 运行完整检查脚本
python scripts/pre-release-check.py

# 或分步执行
pytest tests/ -v
flake8 system/scripts/forgeai_modules/
black --check system/scripts/forgeai_modules/
mypy system/scripts/forgeai_modules/
pip-audit
```

**CI 验证** (GitHub Actions):
```yaml
# .github/workflows/release-check.yml
name: Release Check
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11, 3.12]
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e .[dev]
      - name: Run tests
        run: pytest tests/ -v
      - name: Run quality checks
        run: |
          flake8 system/scripts/forgeai_modules/
          black --check system/scripts/forgeai_modules/
          mypy system/scripts/forgeai_modules/
      - name: Security scan
        run: pip-audit
```

#### 2.2 检查失败处理

**阻塞策略**: 
- 所有检查必须通过
- 不允许跳过或忽略
- 失败时停止发布流程

**错误报告**:
- 详细记录失败原因
- 提供修复建议
- 自动创建 issue（可选）

---

### 3. 发布检查脚本

创建 `scripts/pre-release-check.py`:

```python
#!/usr/bin/env python3
"""发布前检查脚本"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并报告结果"""
    print(f"\n{'='*60}")
    print(f"检查: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 失败: {description}")
        print(result.stdout)
        print(result.stderr)
        return False
    else:
        print(f"✅ 通过: {description}")
        return True

def main():
    """运行所有检查"""
    checks = [
        ("pytest tests/ -v --tb=short", "测试套件"),
        ("flake8 system/scripts/forgeai_modules/ --max-line-length=100", "代码风格检查"),
        ("black --check system/scripts/forgeai_modules/", "代码格式检查"),
        ("mypy system/scripts/forgeai_modules/", "类型检查"),
        ("pip-audit", "依赖安全检查"),
    ]
    
    results = []
    for cmd, desc in checks:
        results.append(run_command(cmd, desc))
    
    print(f"\n{'='*60}")
    print("检查结果汇总")
    print(f"{'='*60}")
    
    for (cmd, desc), passed in zip(checks, results):
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {desc}")
    
    if all(results):
        print("\n🎉 所有检查通过！可以发布。")
        return 0
    else:
        print("\n⚠️  部分检查失败，请修复后再发布。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

### 4. 发布检查清单模板

创建 `RELEASE_CHECKLIST.md`:

```markdown
# v1.1.0 发布检查清单

## 自动化检查

- [ ] 所有测试通过 (pytest)
- [ ] 代码风格检查通过 (flake8)
- [ ] 代码格式检查通过 (black)
- [ ] 类型检查通过 (mypy)
- [ ] 依赖安全检查通过 (pip-audit)

## 手动测试

- [ ] 初始化项目成功 (forgeai init)
- [ ] 查看状态成功 (forgeai status)
- [ ] 生成章节成功 (forgeai generate)
- [ ] CLI 帮助系统正常 (forgeai help)
- [ ] 版本信息正确 (forgeai version)

## 文档检查

- [ ] README.md 已更新
- [ ] CHANGELOG.md 已更新
- [ ] API 文档已更新
- [ ] 用户指南已更新
- [ ] 所有示例可运行

## 跨版本测试

- [ ] Python 3.8 兼容性测试
- [ ] Python 3.9 兼容性测试
- [ ] Python 3.10 兼容性测试
- [ ] Python 3.11 兼容性测试
- [ ] Python 3.12 兼容性测试

## 跨平台测试

- [ ] Windows 测试通过
- [ ] Linux 测试通过
- [ ] macOS 测试通过

## 发布准备

- [ ] 版本号已更新 (pyproject.toml, __init__.py)
- [ ] Git 标签已创建
- [ ] GitHub Release 已创建
- [ ] PyPI 发布成功
```

---

## 📝 实现任务

基于以上决策，Phase 5 的实现任务如下：

### Task 5.1: 创建发布检查脚本
- 创建 `scripts/pre-release-check.py`
- 实现所有自动化检查
- 添加详细错误报告

### Task 5.2: 创建发布检查清单
- 创建 `RELEASE_CHECKLIST.md`
- 列出所有检查项目
- 提供检查方法说明

### Task 5.3: 配置 CI/CD
- 创建 `.github/workflows/release-check.yml`
- 配置跨版本测试
- 配置跨平台测试

### Task 5.4: 执行发布检查
- 运行所有自动化检查
- 执行手动测试
- 验证文档完整性

### Task 5.5: 更新版本和文档
- 更新版本号到 v1.1.0
- 更新 CHANGELOG.md
- 更新 README.md

### Task 5.6: 创建发布
- 创建 Git 标签
- 创建 GitHub Release
- 发布到 PyPI

---

## 🚫 范围边界

**包含在 Phase 5**:
- 发布检查脚本和清单
- CI/CD 配置
- 版本号更新
- 文档更新
- PyPI 发布

**不包含在 Phase 5** (延后到 v2.0):
- VSCode 扩展发布 (npm)
- 文档网站部署
- 社交媒体公告
- 用户迁移指南

---

## 🎯 成功标准

- [ ] 所有自动化检查通过
- [ ] 手动测试全部成功
- [ ] 文档完整且示例可运行
- [ ] 跨版本兼容性测试通过
- [ ] 跨平台兼容性测试通过
- [ ] v1.1.0 成功发布到 PyPI
- [ ] 用户可以通过 `pip install forgeai` 安装

---

## 📚 参考资料

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Keep a Changelog](https://keepachangelog.com/)
