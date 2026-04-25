"""
共享 pytest fixtures for ForgeAI Kit tests

提供测试所需的通用 fixtures：
- 临时项目目录
- 模拟环境变量
- 示例配置
- 模拟 API 响应
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import MagicMock

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))


# ============================================
# 项目结构 Fixtures
# ============================================

@pytest.fixture
def temp_project() -> Generator[Path, None, None]:
    """
    创建临时项目目录，包含标准结构

    测试结束后自动清理
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # 创建标准目录结构
        (project_path / ".forgeai").mkdir()
        (project_path / ".forgeai" / "memory").mkdir()
        (project_path / "1-边界").mkdir()
        (project_path / "2-设定").mkdir()
        (project_path / "3-大纲").mkdir()
        (project_path / "4-正文").mkdir()
        (project_path / "5-审查").mkdir()

        # 创建最小配置文件
        config = {
            "version": "1.0",
            "llm_params": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 4096,
            },
            "rag": {
                "chunk_size": 500,
                "chunk_overlap": 100,
            },
        }
        with open(project_path / ".forgeai" / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f)

        # 创建最小状态文件
        state = {
            "version": "1.0.0",
            "project": {"name": "test-project", "genre": "玄幻"},
            "progress": {"current_chapter": 0, "phase": "init"},
            "entities": {},
            "foreshadowing": {"active": [], "resolved": []},
        }
        with open(project_path / ".forgeai" / "state.json", "w", encoding="utf-8") as f:
            json.dump(state, f)

        yield project_path


@pytest.fixture
def temp_project_with_chapters(temp_project: Path) -> Path:
    """
    带有示例章节的临时项目
    """
    chapters_dir = temp_project / "4-正文"

    # 创建示例章节文件
    for i in range(1, 4):
        chapter_file = chapters_dir / f"第{i}章.txt"
        chapter_file.write_text(f"这是第{i}章的内容。\n\n李明站在山顶，望着远方。", encoding="utf-8")

    return temp_project


# ============================================
# 环境变量 Fixtures
# ============================================

@pytest.fixture
def mock_env() -> Generator[Dict[str, str], None, None]:
    """
    设置测试用环境变量

    测试结束后恢复原始环境
    """
    test_env = {
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-4o-mini",
        "LLM_API_KEY": "test-api-key-12345",
        "LLM_BASE_URL": "https://api.test.com/v1",
        "LLM_TEMPERATURE": "0.7",
        "LLM_TOP_P": "0.9",
        "LLM_MAX_TOKENS": "4096",
        "EMBED_MODEL": "text-embedding-3-small",
        "EMBED_API_KEY": "test-embed-key",
        "EMBED_BASE_URL": "https://api.test.com/v1",
        "RERANK_PROVIDER": "qwen",
        "RERANK_API_KEY": "test-rerank-key",
        "RERANK_BASE_URL": "https://rerank.test.com/v1",
        "LOG_LEVEL": "DEBUG",
    }

    # 保存原始环境
    original = {}
    for key in test_env:
        original[key] = os.environ.get(key)

    # 设置测试环境
    os.environ.update(test_env)

    yield test_env

    # 恢复原始环境
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """
    清理所有 ForgeAI 相关环境变量
    """
    env_keys = [k for k in os.environ if k.startswith(("LLM_", "EMBED_", "RERANK_", "LOG_"))]
    original = {k: os.environ.get(k) for k in env_keys}

    for k in env_keys:
        os.environ.pop(k, None)

    yield

    for k, v in original.items():
        if v is not None:
            os.environ[k] = v


# ============================================
# 配置 Fixtures
# ============================================

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """
    示例配置字典
    """
    return {
        "version": "1.0",
        "llm_params": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 4096,
            "retry_attempts": 3,
            "timeout": 60,
            "temperature_outline": 0.4,
            "temperature_writing": 1.0,
            "temperature_review": 0.3,
        },
        "embedding_params": {
            "batch_size": 32,
            "dimension": 1536,
        },
        "rerank_params": {
            "top_n": 5,
        },
        "rag": {
            "chunk_size": 500,
            "chunk_overlap": 100,
            "top_k": 10,
            "bm25_weight": 0.3,
            "vector_weight": 0.7,
        },
        "humanize": {
            "max_rounds": 3,
            "score_threshold": 0.6,
        },
    }


@pytest.fixture
def sample_state() -> Dict[str, Any]:
    """
    示例状态字典
    """
    return {
        "version": "1.0.0",
        "project": {
            "name": "测试小说",
            "genre": "玄幻",
            "mode": "standard",
        },
        "progress": {
            "phase": "write",
            "current_chapter": 5,
            "total_chapters": 100,
            "word_count": 15000,
        },
        "entities": {
            "protagonist": {
                "name": "李明",
                "type": "character",
                "tier": "core",
                "last_appearance": 5,
                "state": {"power": "筑基初期", "location": "青云宗"},
            }
        },
        "foreshadowing": {
            "active": [
                {"id": "fs_1", "description": "神秘玉佩", "chapter_planted": 1, "expected_payoff": 10}
            ],
            "resolved": [],
        },
        "reading_power": {
            "history": [
                {"chapter": 1, "score": 0.8},
                {"chapter": 2, "score": 0.75},
            ],
            "debt": 0.5,
        },
    }


# ============================================
# Mock Fixtures
# ============================================

@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """
    模拟 LLM API 响应
    """
    return {
        "id": "chatcmpl-test123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "这是一个测试响应。李明挥剑斩向敌人，剑光闪烁。"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def mock_embedding_response() -> Dict[str, Any]:
    """
    模拟 Embedding API 响应
    """
    return {
        "data": [
            {
                "embedding": [0.1] * 1536,
                "index": 0
            }
        ],
        "model": "text-embedding-3-small",
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 10
        }
    }


@pytest.fixture
def mock_llm_client():
    """
    模拟 CloudLLMClient
    """
    mock = MagicMock()
    mock.chat.return_value = "测试响应内容"
    mock.embed.return_value = [[0.1] * 1536]
    return mock


# ============================================
# 示例数据 Fixtures
# ============================================

@pytest.fixture
def sample_chapter_text() -> str:
    """
    示例章节文本
    """
    return """
    第一章 开始

    李明站在山顶上，望着远方的城市。风吹过他的脸庞，带来一丝凉意。

    "终于到了，"他自言自语道。

    他回想起这一路走来的艰辛。从一个小村庄出发，历经千辛万苦，终于来到了这座传说中的城市。

    街道上人来人往，各种叫卖声此起彼伏。李明感到一阵迷茫，不知道该往哪里走。

    就在这时，一个声音传来："你是新来的吧？"

    李明转过身，看到一个身穿青衫的少女正微笑着看着他。

    "我是林雪，"少女说道，"你是来参加宗门选拔的吗？"

    李明点了点头，心中却暗暗警惕。这个少女虽然看起来和善，但他能感觉到她身上淡淡的灵力波动。
    """.strip()


@pytest.fixture
def sample_ai_text() -> str:
    """
    带有 AI 写作特征的示例文本
    """
    return """
    李明站在山顶，心中不禁倒吸一口凉气。

    这个场景不仅令人震撼，更是他命运的转折点的象征。众所周知，这座山有着不为人知的秘密。

    值得注意的是，他的眼中闪过一丝复杂的情绪。虎躯一震，他感到一股前所未有的力量涌入体内。

    如遭雷击，他不禁想起了自己的师父。这是一个举足轻重的时刻，他与师父的命运息息相关。

    让我们一起期待，李明将会迎来怎样光明的未来。
    """.strip()


@pytest.fixture
def sample_entities() -> Dict[str, list]:
    """
    示例提取实体
    """
    return {
        "characters": ["李明", "林雪"],
        "locations": ["山顶", "城市", "青云宗"],
        "items": ["玉佩", "长剑"],
        "organizations": ["青云宗"],
    }


# ============================================
# 异步 Fixtures
# ============================================

@pytest.fixture
def event_loop_policy():
    """配置 asyncio 事件循环策略"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
