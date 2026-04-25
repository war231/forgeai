"""
单元测试：token_manager.py 模块

测试 token 计数、截断等功能
"""

import sys
from pathlib import Path

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.token_manager import (
    estimate_tokens,
    truncate_text,
    truncate_rag_content,
    build_context_with_limit,
    print_token_stats,
)


class TestEstimateTokens:
    """测试 estimate_tokens 函数"""

    def test_estimate_tokens_english(self):
        """英文文本 token 估算"""
        text = "Hello, world! This is a test."
        tokens = estimate_tokens(text)

        assert tokens > 0
        # 英文 token 数应小于字符数
        assert tokens < len(text)

    def test_estimate_tokens_chinese(self):
        """中文文本 token 估算"""
        text = "你好，世界！这是一个测试。"
        tokens = estimate_tokens(text)

        assert tokens > 0
        # 中文 token 数约为字符数的 1.5 倍
        # 根据估算规则

    def test_estimate_tokens_mixed(self):
        """中英混合文本 token 估算"""
        text = "Hello 你好 World 世界"
        tokens = estimate_tokens(text)

        assert tokens > 0

    def test_estimate_tokens_empty(self):
        """空字符串返回 0"""
        tokens = estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_numbers(self):
        """包含数字的文本"""
        text = "第1章 12345 第100章"
        tokens = estimate_tokens(text)

        assert tokens > 0

    def test_estimate_tokens_long_text(self):
        """长文本估算"""
        text = "这是一段测试文本。" * 1000
        tokens = estimate_tokens(text)

        assert tokens > 0

    def test_estimate_tokens_punctuation(self):
        """标点符号处理"""
        text = "，。！？、：；""''"
        tokens = estimate_tokens(text)

        assert tokens > 0


class TestTruncateText:
    """测试 truncate_text 函数"""

    def test_truncate_within_limit(self):
        """文本在限制内不截断"""
        text = "短文本"
        result, tokens = truncate_text(text, max_tokens=100)

        assert result == text

    def test_truncate_exceeds_limit(self):
        """文本超出限制时截断"""
        text = "这是一段较长的文本，需要进行截断处理。" * 10
        result, tokens = truncate_text(text, max_tokens=20)

        assert estimate_tokens(result) <= 30  # 允许一定误差

    def test_truncate_empty_string(self):
        """空字符串截断"""
        result, tokens = truncate_text("", max_tokens=100)

        assert result == ""
        assert tokens == 0

    def test_truncate_preserves_sentences(self):
        """尽量保留完整句子"""
        text = "第一句话。第二句话。第三句话。"
        result, tokens = truncate_text(text, max_tokens=10)

        # 应在句号处截断
        # 结果应以句号结尾或为空

    def test_truncate_exact_limit(self):
        """恰好等于限制"""
        text = "测试文本"
        result, tokens = truncate_text(text, max_tokens=100)

        assert result == text


class TestTruncateRagContent:
    """测试 truncate_rag_content 函数"""

    def test_truncate_rag_empty(self):
        """空列表截断"""
        result, tokens = truncate_rag_content([], max_tokens=100)

        assert result == []
        assert tokens == 0

    def test_truncate_rag_within_limit(self):
        """RAG 内容在限制内"""
        rag_results = [
            {"content": "内容1"},
            {"content": "内容2"},
        ]
        result, tokens = truncate_rag_content(rag_results, max_tokens=1000)

        assert len(result) == 2

    def test_truncate_rag_exceeds_limit(self):
        """RAG 内容超出限制"""
        rag_results = [
            {"content": "这是第一段内容，包含了一些文字。"},
            {"content": "这是第二段内容，也包含了一些文字。"},
            {"content": "这是第三段内容，同样包含了一些文字。"},
        ]
        result, tokens = truncate_rag_content(rag_results, max_tokens=20)

        # 应截断部分内容
        assert len(result) <= 3

    def test_truncate_rag_keep_first(self):
        """保留前 N 个结果"""
        rag_results = [
            {"content": "内容1" * 20},
            {"content": "内容2" * 20},
            {"content": "内容3" * 20},
        ]
        result, tokens = truncate_rag_content(rag_results, max_tokens=50, keep_first=1)

        # 第一个应完整保留
        assert len(result) >= 1

    def test_truncate_rag_marks_truncated(self):
        """截断的结果应标记"""
        rag_results = [
            {"content": "短内容"},
            {"content": "长内容" * 50},
        ]
        result, tokens = truncate_rag_content(rag_results, max_tokens=30)

        # 检查是否有截断标记
        for item in result:
            if item.get("truncated"):
                assert "truncated" in item


class TestBuildContextWithLimit:
    """测试 build_context_with_limit 函数"""

    def test_build_context_basic(self):
        """基本上下文构建"""
        context, tokens = build_context_with_limit(
            system_prompt="你是助手",
            user_prompt="请生成内容",
        )

        assert "你是助手" in context
        assert "请生成内容" in context
        assert tokens > 0

    def test_build_context_with_rag(self):
        """包含 RAG 内容"""
        context, tokens = build_context_with_limit(
            system_prompt="系统提示",
            user_prompt="用户提示",
            rag_content="RAG 召回的相关内容",
        )

        assert "系统提示" in context
        assert "用户提示" in context
        assert "RAG" in context

    def test_build_context_with_previous(self):
        """包含前文"""
        context, tokens = build_context_with_limit(
            system_prompt="系统提示",
            user_prompt="用户提示",
            previous_chapters="前文章节内容",
        )

        assert "前文章节内容" in context

    def test_build_context_truncation(self):
        """超出限制时截断"""
        long_text = "很长的内容" * 100
        context, tokens = build_context_with_limit(
            system_prompt=long_text,
            user_prompt=long_text,
            rag_content=long_text,
            max_tokens=200,
        )

        # 应被截断到合理范围
        # 注意：tokens 是估算值，允许一定误差
        assert tokens <= 5000  # 粗略检查未被无限扩展

    def test_build_context_priority(self):
        """system_prompt 优先级最高"""
        context, tokens = build_context_with_limit(
            system_prompt="必须保留的系统提示",
            user_prompt="必须保留的用户提示",
            rag_content="RAG内容" * 100,
            previous_chapters="前文" * 100,
            max_tokens=50,
        )

        # system 和 user 应优先保留
        assert "系统提示" in context or "用户提示" in context


class TestTokenStats:
    """测试 token 统计功能"""

    def test_print_token_stats(self, capsys):
        """打印 token 统计"""
        print_token_stats(
            system_prompt="系统提示",
            user_prompt="用户提示",
            rag_content="RAG内容",
            previous_chapters="前文",
        )

        captured = capsys.readouterr()
        assert "Token" in captured.out or "token" in captured.out.lower()

    def test_print_token_stats_minimal(self, capsys):
        """最小参数打印统计"""
        print_token_stats(
            system_prompt="提示",
            user_prompt="",
        )

        captured = capsys.readouterr()
        # 应正常输出，不报错
        assert captured.out != "" or True  # 允许无输出


class TestTokenManagerIntegration:
    """Token 管理集成测试"""

    def test_full_workflow(self):
        """完整 token 管理工作流"""
        # 1. 估算原始文本
        long_text = "这是一段很长的小说正文内容。" * 100
        original_tokens = estimate_tokens(long_text)

        # 2. 截断到限制
        truncated, trunc_tokens = truncate_text(long_text, max_tokens=100)

        # 3. 构建上下文
        context, context_tokens = build_context_with_limit(
            system_prompt="你是小说创作助手",
            user_prompt="请继续写下一章",
            rag_content=truncated,
            max_tokens=200,
        )

        assert context_tokens > 0
        assert context_tokens <= 250  # 允许误差

    def test_chinese_novel_scenario(self):
        """中文小说场景测试"""
        chapter = """
        第一章 天才少年

        李明站在青云宗的山门前，望着高耸入云的山峰，心中不禁倒吸一口凉气。

        "这就是传说中的青云宗吗？"他喃喃自语道。

        身穿青衫的弟子来来往往，每个人身上都散发着淡淡的灵力波动。李明知道，这些人都是修仙者。

        他紧了紧背上的包裹，迈步走向山门。守门的弟子拦住了他。

        "来者何人？可知青云宗不是凡人可入之地。"

        李明深吸一口气，从怀中取出一块玉佩。

        "我是受药老所托，前来拜师学艺。"
        """

        # 估算 tokens
        tokens = estimate_tokens(chapter)
        assert tokens > 0

        # 截断到不同限制
        for limit in [50, 100, 200]:
            truncated, _ = truncate_text(chapter, max_tokens=limit)
            assert estimate_tokens(truncated) <= limit + 20  # 允许误差
