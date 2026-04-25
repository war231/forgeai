#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 管理器

功能：
1. Token 计数（支持中文）
2. 上下文截断
3. RAG 内容截断
4. Prompt 拼接优化
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional, Tuple
from .env_loader import get_token_limits


def estimate_tokens(text: str) -> int:
    """
    估算文本的 Token 数量（中文优化）
    
    规则：
    - 中文字符：约 1.5 tokens/字
    - 英文单词：约 1 token/词
    - 标点符号：约 1 token/个
    
    Args:
        text: 待估算的文本
    
    Returns:
        估算的 Token 数量
    """
    if not text:
        return 0
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    
    # 统计英文单词
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    
    # 统计数字
    numbers = len(re.findall(r'\d+', text))
    
    # 统计标点符号
    punctuation = len(re.findall(r'[^\w\s]', text))
    
    # 估算总 tokens
    total_tokens = int(
        chinese_chars * 1.5 +  # 中文字符
        english_words * 1.0 +  # 英文单词
        numbers * 0.5 +        # 数字
        punctuation * 1.0      # 标点符号
    )
    
    return max(total_tokens, 1)


def truncate_text(text: str, max_tokens: int) -> Tuple[str, int]:
    """
    截断文本到指定 Token 数量
    
    Args:
        text: 待截断的文本
        max_tokens: 最大 Token 数量
    
    Returns:
        (截断后的文本, 实际 Token 数量)
    """
    if not text:
        return "", 0
    
    # 估算当前 tokens
    current_tokens = estimate_tokens(text)
    
    if current_tokens <= max_tokens:
        return text, current_tokens
    
    # 需要截断
    # 按句子分割（优先保留完整句子）
    sentences = re.split(r'([。！？\n])', text)
    
    # 重新组合句子
    combined_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            combined_sentences.append(sentences[i] + sentences[i + 1])
        else:
            combined_sentences.append(sentences[i])
    
    # 从后向前截断（保留开头）
    result_text = ""
    result_tokens = 0
    
    for sentence in combined_sentences:
        sentence_tokens = estimate_tokens(sentence)
        if result_tokens + sentence_tokens <= max_tokens:
            result_text += sentence
            result_tokens += sentence_tokens
        else:
            break
    
    return result_text, result_tokens


def truncate_rag_content(
    rag_results: List[Dict[str, Any]],
    max_tokens: int,
    keep_first: int = 1
) -> Tuple[List[Dict[str, Any]], int]:
    """
    截断 RAG 召回内容
    
    Args:
        rag_results: RAG 召回结果列表
        max_tokens: 最大 Token 数量
        keep_first: 保留前 N 个结果（不截断）
    
    Returns:
        (截断后的结果列表, 实际 Token 数量)
    """
    if not rag_results:
        return [], 0
    
    truncated_results = []
    total_tokens = 0
    
    for i, result in enumerate(rag_results):
        content = result.get("content", "")
        content_tokens = estimate_tokens(content)
        
        if i < keep_first:
            # 保留前 N 个结果
            truncated_results.append(result)
            total_tokens += content_tokens
        else:
            # 检查是否还有剩余空间
            remaining_tokens = max_tokens - total_tokens
            
            if remaining_tokens <= 0:
                break
            
            if content_tokens <= remaining_tokens:
                # 可以完整保留
                truncated_results.append(result)
                total_tokens += content_tokens
            else:
                # 需要截断
                truncated_content, actual_tokens = truncate_text(content, remaining_tokens)
                if truncated_content:
                    truncated_results.append({
                        **result,
                        "content": truncated_content,
                        "truncated": True
                    })
                    total_tokens += actual_tokens
                break
    
    return truncated_results, total_tokens


def build_context_with_limit(
    system_prompt: str,
    user_prompt: str,
    rag_content: Optional[str] = None,
    previous_chapters: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> Tuple[str, int]:
    """
    构建上下文（自动截断）
    
    Args:
        system_prompt: 系统提示
        user_prompt: 用户提示
        rag_content: RAG 召回内容
        previous_chapters: 前文章节
        max_tokens: 最大 Token 数量（默认从配置读取）
    
    Returns:
        (构建的上下文, 实际 Token 数量)
    """
    # 获取 Token 限制
    token_limits = get_token_limits()
    max_tokens = max_tokens or token_limits["max_input_tokens"]
    
    # 计算各部分 tokens
    system_tokens = estimate_tokens(system_prompt)
    user_tokens = estimate_tokens(user_prompt)
    rag_tokens = estimate_tokens(rag_content) if rag_content else 0
    prev_tokens = estimate_tokens(previous_chapters) if previous_chapters else 0
    
    total_tokens = system_tokens + user_tokens + rag_tokens + prev_tokens
    
    # 检查是否需要截断
    if total_tokens <= max_tokens:
        # 无需截断，直接拼接
        context = ""
        if system_prompt:
            context += system_prompt + "\n\n"
        if rag_content:
            context += rag_content + "\n\n"
        if previous_chapters:
            context += previous_chapters + "\n\n"
        if user_prompt:
            context += user_prompt
        
        return context.strip(), total_tokens
    
    # 需要截断
    # 优先级：system_prompt > user_prompt > rag_content > previous_chapters
    
    # 1. 保留 system_prompt 和 user_prompt
    reserved_tokens = system_tokens + user_tokens
    remaining_tokens = max_tokens - reserved_tokens
    
    if remaining_tokens <= 0:
        # 连 system_prompt + user_prompt 都超了，只能截断 user_prompt
        truncated_user, _ = truncate_text(user_prompt, max_tokens - system_tokens)
        context = f"{system_prompt}\n\n{truncated_user}"
        return context, estimate_tokens(context)
    
    # 2. 分配剩余 tokens 给 rag_content 和 previous_chapters
    # RAG 内容优先级更高（更相关）
    rag_ratio = 0.7  # RAG 占 70%
    prev_ratio = 0.3  # 前文占 30%
    
    rag_max_tokens = int(remaining_tokens * rag_ratio)
    prev_max_tokens = int(remaining_tokens * prev_ratio)
    
    # 截断 RAG 内容
    truncated_rag = ""
    if rag_content:
        truncated_rag, _ = truncate_text(rag_content, rag_max_tokens)
    
    # 截断前文
    truncated_prev = ""
    if previous_chapters:
        truncated_prev, _ = truncate_text(previous_chapters, prev_max_tokens)
    
    # 拼接最终上下文
    context = ""
    if system_prompt:
        context += system_prompt + "\n\n"
    if truncated_rag:
        context += truncated_rag + "\n\n"
    if truncated_prev:
        context += truncated_prev + "\n\n"
    if user_prompt:
        context += user_prompt
    
    return context.strip(), estimate_tokens(context)


def print_token_stats(
    system_prompt: str,
    user_prompt: str,
    rag_content: Optional[str] = None,
    previous_chapters: Optional[str] = None
) -> None:
    """
    打印 Token 统计信息
    
    Args:
        system_prompt: 系统提示
        user_prompt: 用户提示
        rag_content: RAG 召回内容
        previous_chapters: 前文章节
    """
    token_limits = get_token_limits()
    
    system_tokens = estimate_tokens(system_prompt)
    user_tokens = estimate_tokens(user_prompt)
    rag_tokens = estimate_tokens(rag_content) if rag_content else 0
    prev_tokens = estimate_tokens(previous_chapters) if previous_chapters else 0
    
    total_tokens = system_tokens + user_tokens + rag_tokens + prev_tokens
    
    print("=" * 60)
    print("Token 统计")
    print("=" * 60)
    print(f"系统提示: {system_tokens:,} tokens")
    print(f"用户提示: {user_tokens:,} tokens")
    print(f"RAG 内容: {rag_tokens:,} tokens")
    print(f"前文章节: {prev_tokens:,} tokens")
    print("-" * 60)
    print(f"总计: {total_tokens:,} tokens")
    print(f"最大限制: {token_limits['max_context_tokens']:,} tokens")
    print(f"预留空间: {token_limits['reserve_tokens']:,} tokens")
    print(f"可用空间: {token_limits['max_input_tokens']:,} tokens")
    
    if total_tokens > token_limits['max_input_tokens']:
        print(f"\n[警告] 超出限制 {total_tokens - token_limits['max_input_tokens']:,} tokens")
        print("建议：启用自动截断")
    else:
        print(f"\n[OK] 剩余空间 {token_limits['max_input_tokens'] - total_tokens:,} tokens")
    
    print("=" * 60)


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("Token 管理器测试")
    print("=" * 60)
    
    # 测试 Token 估算
    test_text = "这是一段测试文本，包含中文和 English words，以及数字 123。"
    tokens = estimate_tokens(test_text)
    print(f"\n测试文本: {test_text}")
    print(f"估算 Tokens: {tokens}")
    
    # 测试截断
    long_text = "这是一段很长的文本。" * 100
    truncated, actual_tokens = truncate_text(long_text, max_tokens=50)
    print(f"\n截断测试:")
    print(f"原文长度: {len(long_text)} 字符")
    print(f"截断后长度: {len(truncated)} 字符")
    print(f"实际 Tokens: {actual_tokens}")
    
    # 测试上下文构建
    system_prompt = "你是一位小说创作助手。"
    user_prompt = "请生成第1章大纲。"
    rag_content = "角色设定：李天，筑基初期。" * 10
    previous_chapters = "前文内容..." * 20
    
    print("\n")
    print_token_stats(system_prompt, user_prompt, rag_content, previous_chapters)
    
    context, tokens = build_context_with_limit(
        system_prompt,
        user_prompt,
        rag_content,
        previous_chapters,
        max_tokens=200
    )
    
    print(f"\n构建的上下文 ({tokens} tokens):")
    print(context[:200] + "...")
