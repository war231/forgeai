# Contributing to ForgeAI

感谢你对ForgeAI的兴趣！我们欢迎所有形式的贡献。

## 🤔 如何贡献

### 报告Bug

如果你发现了bug，请：

1. 检查[Issues](https://github.com/forgeai/forgeai/issues)是否已有相同问题
2. 如果没有，创建新Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤
   - 预期行为
   - 实际行为
   - 环境信息（Python版本、操作系统等）

### 提出新功能

如果你有新功能建议：

1. 检查[Issues](https://github.com/forgeai/forgeai/issues)是否已有类似建议
2. 创建新Issue，包含：
   - 功能描述
   - 使用场景
   - 预期效果

### 提交代码

#### 1. Fork仓库

```bash
# Fork后克隆你的仓库
git clone https://github.com/your-username/forgeai.git
cd forgeai
```

#### 2. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

#### 3. 安装开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -e ".[dev]"
```

#### 4. 编写代码

- 遵循PEP 8代码规范
- 添加必要的注释
- 编写单元测试

#### 5. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_token_manager.py

# 查看测试覆盖率
pytest --cov=forgeai_modules
```

#### 6. 代码格式化

```bash
# 使用black格式化
black system/scripts/

# 使用flake8检查
flake8 system/scripts/
```

#### 7. 提交更改

```bash
git add .
git commit -m "feat: add new feature"
# 或
git commit -m "fix: fix bug in token manager"
```

提交信息格式：
- `feat:` 新功能
- `fix:` Bug修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

#### 8. 推送分支

```bash
git push origin feature/your-feature-name
```

#### 9. 创建Pull Request

1. 访问你fork的仓库
2. 点击"New Pull Request"
3. 填写PR描述：
   - 更改内容
   - 相关Issue
   - 测试结果

## 📝 代码规范

### Python代码

- 遵循PEP 8
- 使用4空格缩进
- 行长度不超过100字符
- 使用有意义的变量名
- 添加docstring

### 示例

```python
def calculate_token_budget(
    total_tokens: int,
    reserve_ratio: float = 0.1
) -> dict:
    """
    计算token预算分配。
    
    Args:
        total_tokens: 总token数
        reserve_ratio: 保留比例
        
    Returns:
        包含各部分token预算的字典
        
    Raises:
        ValueError: 如果total_tokens小于0
    """
    if total_tokens < 0:
        raise ValueError("total_tokens must be non-negative")
    
    reserve = int(total_tokens * reserve_ratio)
    available = total_tokens - reserve
    
    return {
        "total": total_tokens,
        "reserve": reserve,
        "available": available
    }
```

## 🧪 测试规范

### 单元测试

```python
import pytest
from forgeai_modules.token_manager import TokenManager

class TestTokenManager:
    """TokenManager测试类"""
    
    def test_init(self):
        """测试初始化"""
        tm = TokenManager(max_context=1000)
        assert tm.max_context == 1000
        
    def test_build_context(self):
        """测试上下文构建"""
        tm = TokenManager(max_context=1000)
        context = tm.build_context_with_limit(
            system_prompt="System",
            recent_chapters=["Chapter 1"],
            max_input_tokens=500
        )
        assert len(context) > 0
```

## 📚 文档规范

### Markdown文档

- 使用清晰的标题层级
- 添加代码示例
- 包含截图或图表（如适用）

### API文档

```python
def function_name(param1: str, param2: int) -> bool:
    """
    简短描述。
    
    详细描述。
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        返回值说明
        
    Raises:
        ExceptionType: 异常说明
        
    Examples:
        >>> function_name("test", 10)
        True
    """
    pass
```

## 🔍 代码审查

所有PR都会经过代码审查：

1. 代码质量
2. 测试覆盖率
3. 文档完整性
4. 性能影响

## 📋 检查清单

提交PR前，请确认：

- [ ] 代码遵循PEP 8规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交信息清晰
- [ ] 没有引入新的警告

## 💬 获取帮助

- GitHub Issues: 提问和讨论
- 文档: https://forgeai.readthedocs.io

## 🙏 感谢

感谢你的贡献！每一份贡献都让ForgeAI变得更好。
