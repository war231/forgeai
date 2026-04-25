# Python API 文档

ForgeAI提供了完整的Python API，允许开发者以编程方式使用ForgeAI的所有功能。

## 安装

```bash
pip install forgeai
```

## 快速开始

```python
from forgeai import ForgeAI

# 初始化客户端
client = ForgeAI(api_key="your-api-key")

# 创建项目
project = client.create_project(
    name="我的小说",
    genre="都市",
    target_words=500000
)

# 生成章节
chapter = project.write_chapter(
    chapter_num=1,
    words=2500
)

# 审查章节
review = project.review_chapter(chapter_num=1)

# 导出成稿
project.export(format="markdown", output="我的小说.md")
```

---

## 核心类

### ForgeAI

主客户端类，用于初始化和项目管理。

```python
from forgeai import ForgeAI

# 初始化
client = ForgeAI(
    api_key="your-api-key",           # API密钥
    model="gpt-4",                    # 模型名称
    base_url="https://api.openai.com/v1"  # API基础URL
)
```

**方法：**

#### create_project()

创建新项目。

```python
project = client.create_project(
    name="我的小说",          # 项目名称
    genre="都市",             # 类型
    target_words=500000,     # 目标字数
    target_chapters=200,     # 目标章节数
    config={                 # 配置选项
        "words_per_chapter": 2500,
        "style": "轻松幽默",
        "perspective": "第三人称"
    }
)
```

**参数：**
- `name` (str): 项目名称
- `genre` (str): 小说类型
- `target_words` (int): 目标字数
- `target_chapters` (int): 目标章节数
- `config` (dict): 配置选项

**返回：** `Project` 对象

#### load_project()

加载现有项目。

```python
project = client.load_project(
    path="path/to/project"   # 项目路径
)
```

**参数：**
- `path` (str): 项目路径

**返回：** `Project` 对象

#### list_projects()

列出所有项目。

```python
projects = client.list_projects()
```

**返回：** `List[Project]` 项目列表

---

### Project

项目类，用于项目操作和章节管理。

```python
project = client.create_project(name="我的小说")
```

**属性：**
- `name` (str): 项目名称
- `genre` (str): 小说类型
- `target_words` (int): 目标字数
- `target_chapters` (int): 目标章节数
- `current_chapter` (int): 当前章节数
- `config` (dict): 项目配置

**方法：**

#### write_chapter()

生成章节内容。

```python
chapter = project.write_chapter(
    chapter_num=1,           # 章节号
    words=2500,              # 字数
    style="轻松幽默",        # 风格
    perspective="李明",      # 視角
    scene="公司办公室",      # 场景
    plot_point="李明入职"    # 情节点
)
```

**参数：**
- `chapter_num` (int): 章节号
- `words` (int): 目标字数（可选）
- `style` (str): 写作风格（可选）
- `perspective` (str): 叙事视角（可选）
- `scene` (str): 场景设定（可选）
- `plot_point` (str): 情节点（可选）

**返回：** `Chapter` 对象

#### review_chapter()

审查章节。

```python
review = project.review_chapter(
    chapter_num=1,           # 章节号
    agents=["ooc-checker"],  # 使用的Agent
    severity="moderate"      # 问题严重度阈值
)
```

**参数：**
- `chapter_num` (int): 章节号
- `agents` (List[str]): 使用的Agent列表（可选）
- `severity` (str): 问题严重度阈值（可选）

**返回：** `Review` 对象

#### fix_chapter()

修复章节问题。

```python
result = project.fix_chapter(
    chapter_num=1,           # 章节号
    issue_ids=[1, 2],        # 问题ID列表
    auto=True                # 自动修复
)
```

**参数：**
- `chapter_num` (int): 章节号
- `issue_ids` (List[int]): 问题ID列表（可选）
- `auto` (bool): 是否自动修复（可选）

**返回：** `FixResult` 对象

#### export()

导出成稿。

```python
output_path = project.export(
    format="markdown",       # 格式
    output="我的小说.md",    # 输出路径
    toc=True,                # 包含目录
    cover="cover.jpg"        # 封面图片
)
```

**参数：**
- `format` (str): 导出格式（markdown/docx/pdf/epub/txt）
- `output` (str): 输出路径
- `toc` (bool): 是否包含目录（可选）
- `cover` (str): 封面图片路径（可选）

**返回：** `str` 输出路径

#### add_character()

添加角色。

```python
character = project.add_character(
    name="李明",             # 角色名
    age=25,                  # 年龄
    gender="男",             # 性别
    occupation="程序员",     # 职业
    personality={            # 性格特征
        "traits": ["谨慎", "聪明"],
        "strengths": ["逻辑思维强"],
        "weaknesses": ["社交能力弱"]
    },
    background="..."         # 背景故事
)
```

**参数：**
- `name` (str): 角色名
- `age` (int): 年龄
- `gender` (str): 性别
- `occupation` (str): 职业
- `personality` (dict): 性格特征
- `background` (str): 背景故事

**返回：** `Character` 对象

#### add_setting()

添加世界设定。

```python
setting = project.add_setting(
    name="世界观",           # 设定名称
    content={                # 设定内容
        "time_period": "2024年",
        "technology_level": "现代",
        "locations": {
            "北京": {...}
        }
    }
)
```

**参数：**
- `name` (str): 设定名称
- `content` (dict): 设定内容

**返回：** `Setting` 对象

---

### Chapter

章节类，用于章节内容管理。

```python
chapter = project.write_chapter(chapter_num=1)
```

**属性：**
- `chapter_num` (int): 章节号
- `content` (str): 章节内容
- `words` (int): 字数
- `created_at` (datetime): 创建时间

**方法：**

#### save()

保存章节。

```python
chapter.save()
```

#### edit()

编辑章节内容。

```python
chapter.edit(new_content="...")
```

**参数：**
- `new_content` (str): 新内容

#### regenerate()

重新生成章节。

```python
chapter.regenerate(
    style="更紧张悬疑"       # 新风格
)
```

**参数：**
- `style` (str): 写作风格（可选）

---

### Review

审查结果类。

```python
review = project.review_chapter(chapter_num=1)
```

**属性：**
- `chapter_num` (int): 章节号
- `issues` (List[Issue]): 问题列表
- `score` (float): 质量评分
- `created_at` (datetime): 审查时间

**方法：**

#### show()

显示审查结果。

```python
review.show(verbose=True)  # 详细显示
```

**参数：**
- `verbose` (bool): 是否详细显示

#### export()

导出审查结果。

```python
review.export(output="review.json")
```

**参数：**
- `output` (str): 输出路径

---

### Character

角色类。

```python
character = project.add_character(name="李明")
```

**属性：**
- `name` (str): 角色名
- `age` (int): 年龄
- `gender` (str): 性别
- `occupation` (str): 职业
- `personality` (dict): 性格特征
- `background` (str): 背景故事

**方法：**

#### update()

更新角色信息。

```python
character.update(
    age=26,                  # 新年龄
    occupation="技术经理"    # 新职业
)
```

#### add_relationship()

添加角色关系。

```python
character.add_relationship(
    target="王芳",           # 目标角色
    type="朋友",             # 关系类型
    closeness=7              # 亲密度
)
```

**参数：**
- `target` (str): 目标角色名
- `type` (str): 关系类型
- `closeness` (int): 亲密度（1-10）

---

## 审查Agent

### 使用审查Agent

```python
from forgeai import ForgeAI
from forgeai.agents import (
    ConsistencyChecker,
    OOCChecker,
    ContinuityChecker,
    ReaderPullChecker,
    HighPointChecker,
    PacingChecker
)

client = ForgeAI(api_key="your-api-key")
project = client.load_project("path/to/project")

# 使用单个Agent
ooc_checker = OOCChecker()
result = ooc_checker.check(project, chapter_num=1)

# 使用多个Agent
agents = [
    ConsistencyChecker(),
    OOCChecker(),
    ContinuityChecker(),
    ReaderPullChecker()
]

for agent in agents:
    result = agent.check(project, chapter_num=1)
    print(result.summary)
```

### Agent基类

所有审查Agent继承自 `BaseAgent`。

```python
from forgeai.agents import BaseAgent

class CustomAgent(BaseAgent):
    def check(self, project, chapter_num):
        # 自定义审查逻辑
        issues = []
        
        # 检测问题...
        
        return ReviewResult(
            agent_name="custom-agent",
            issues=issues,
            score=8.5
        )
```

---

## 工具函数

### forgeai.utils

```python
from forgeai.utils import (
    count_words,           # 统计字数
    split_chapters,        # 分割章节
    merge_chapters,        # 合并章节
    format_output,         # 格式化输出
    validate_config        # 验证配置
)

# 统计字数
words = count_words(text="...")

# 分割章节
chapters = split_chapters(
    text="...",
    split_by="word_count",
    chunk_size=2500
)

# 合并章节
merged = merge_chapters(chapters=[...])

# 格式化输出
formatted = format_output(
    text="...",
    format="markdown"
)

# 验证配置
is_valid = validate_config(config={...})
```

---

## 配置管理

### forgeai.config

```python
from forgeai.config import Config

# 加载配置
config = Config.load("path/to/config.yaml")

# 获取配置项
api_key = config.get("api.key")
model = config.get("api.model")

# 设置配置项
config.set("api.model", "gpt-4")

# 保存配置
config.save("path/to/config.yaml")
```

---

## 数据管理

### forgeai.data

```python
from forgeai.data import (
    Timeline,              # 时间线管理
    Context,               # 上下文管理
    DataStore              # 数据存储
)

# 时间线管理
timeline = Timeline()
timeline.add_event(
    chapter=1,
    date="2024-01-01",
    event="李明入职"
)

# 上下文管理
context = Context()
context.update_character(
    name="李明",
    location="北京",
    mood="平静"
)

# 数据存储
store = DataStore(path=".forgeai")
store.save("timeline", timeline)
store.save("context", context)
```

---

## 异常处理

```python
from forgeai import ForgeAI
from forgeai.exceptions import (
    ForgeAIError,          # 基础异常
    APIError,              # API错误
    ConfigError,           # 配置错误
    ValidationError,       # 验证错误
    ReviewError            # 审查错误
)

try:
    client = ForgeAI(api_key="invalid-key")
    project = client.create_project(name="测试")
except APIError as e:
    print(f"API错误: {e}")
except ConfigError as e:
    print(f"配置错误: {e}")
except ForgeAIError as e:
    print(f"ForgeAI错误: {e}")
```

---

## 异步支持

ForgeAI支持异步操作。

```python
import asyncio
from forgeai import AsyncForgeAI

async def main():
    client = AsyncForgeAI(api_key="your-api-key")
    
    # 异步创建项目
    project = await client.create_project(name="我的小说")
    
    # 异步生成章节
    chapter = await project.write_chapter(chapter_num=1)
    
    # 异步审查章节
    review = await project.review_chapter(chapter_num=1)
    
    print(review.summary)

asyncio.run(main())
```

---

## 完整示例

### 示例1：创建项目并生成章节

```python
from forgeai import ForgeAI

# 初始化客户端
client = ForgeAI(api_key="your-api-key")

# 创建项目
project = client.create_project(
    name="我的小说",
    genre="都市",
    target_words=500000,
    target_chapters=200
)

# 添加角色
project.add_character(
    name="李明",
    age=25,
    gender="男",
    occupation="程序员",
    personality={
        "traits": ["谨慎", "聪明", "内向"],
        "strengths": ["逻辑思维强"],
        "weaknesses": ["社交能力弱"]
    }
)

# 添加世界设定
project.add_setting(
    name="世界观",
    content={
        "time_period": "2024年",
        "technology_level": "现代"
    }
)

# 生成章节
for i in range(1, 11):
    chapter = project.write_chapter(chapter_num=i)
    print(f"第{i}章生成完成，字数：{chapter.words}")

# 导出成稿
project.export(format="markdown", output="我的小说.md")
```

### 示例2：审查和优化章节

```python
from forgeai import ForgeAI

client = ForgeAI(api_key="your-api-key")
project = client.load_project("path/to/project")

# 审查章节
review = project.review_chapter(
    chapter_num=1,
    agents=["ooc-checker", "continuity-checker"]
)

# 显示审查结果
print(f"质量评分：{review.score}")
print(f"问题数量：{len(review.issues)}")

# 修复问题
if review.issues:
    result = project.fix_chapter(
        chapter_num=1,
        auto=True
    )
    print(f"修复了{result.fixed_count}个问题")

# 重新审查
review = project.review_chapter(chapter_num=1)
print(f"修复后评分：{review.score}")
```

### 示例3：批量处理

```python
from forgeai import ForgeAI

client = ForgeAI(api_key="your-api-key")
project = client.load_project("path/to/project")

# 批量生成章节
chapters = []
for i in range(1, 21):
    chapter = project.write_chapter(chapter_num=i)
    chapters.append(chapter)
    print(f"第{i}章生成完成")

# 批量审查章节
reviews = []
for i in range(1, 21):
    review = project.review_chapter(chapter_num=i)
    reviews.append(review)
    
    # 自动修复问题
    if review.issues:
        project.fix_chapter(chapter_num=i, auto=True)

# 生成统计报告
total_issues = sum(len(r.issues) for r in reviews)
avg_score = sum(r.score for r in reviews) / len(reviews)

print(f"总问题数：{total_issues}")
print(f"平均评分：{avg_score:.2f}")
```

---

## API参考

完整的API参考文档请访问：https://forgeai.readthedocs.io/api/

---

## 相关文档

- [CLI命令](CLI命令.md) - 命令行工具使用
- [配置文件](配置文件.md) - 配置文件详解
- [数据结构](数据结构.md) - 数据结构说明
