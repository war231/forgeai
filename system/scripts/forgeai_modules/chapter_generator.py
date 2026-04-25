#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节生成器

核心功能:
1. 生成章节大纲
2. 生成章节正文
3. 应用参考数据
4. 调用 LLM API
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .cloud_llm_client import CloudLLMManager
from .context_extractor import ContextExtractor
from .rag_adapter import RAGAdapter
from .state_manager import StateManager
from .reference_integrator import ReferenceIntegrator, IntegratedContext, BookAnalysisResult
from .genre_profile_loader import GenreProfileLoader
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChapterOutline:
    """章节大纲"""
    chapter_num: int
    title: str
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    hooks: List[Dict[str, str]] = field(default_factory=list)
    cool_points: List[Dict[str, str]] = field(default_factory=list)
    micro_payoffs: List[Dict[str, str]] = field(default_factory=list)
    word_count_target: int = 3000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_num": self.chapter_num,
            "title": self.title,
            "scenes": self.scenes,
            "hooks": self.hooks,
            "cool_points": self.cool_points,
            "micro_payoffs": self.micro_payoffs,
            "word_count_target": self.word_count_target,
        }


@dataclass
class GenerationResult:
    """生成结果"""
    chapter_num: int
    title: str = ""
    content: str = ""
    outline: Optional[ChapterOutline] = None
    word_count: int = 0
    context: Optional[IntegratedContext] = None
    llm_usage: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_num": self.chapter_num,
            "title": self.title,
            "content": self.content,
            "outline": self.outline.to_dict() if self.outline else None,
            "word_count": self.word_count,
            "context": self.context.to_dict() if self.context else None,
            "llm_usage": self.llm_usage,
            "success": self.success,
            "error_message": self.error_message,
        }


class ChapterGenerator:
    """章节生成器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.llm_client = CloudLLMManager()
        self.context_extractor = ContextExtractor(self.config)
        self.rag_adapter = RAGAdapter(self.config)
        self.state_manager = StateManager(self.config)
        self.reference_integrator = ReferenceIntegrator(self.config)
        self.profile_loader = GenreProfileLoader(self.config)
    
    async def generate_chapter(self,
                               chapter_num: int,
                               genre: str = "",
                               query: str = "",
                               use_rag: bool = False,
                               book_analysis: Optional[Dict[str, Any]] = None,
                               max_chars: int = 8000) -> GenerationResult:
        """
        生成章节
        
        Args:
            chapter_num: 章节号
            genre: 题材
            query: 主题指导
            use_rag: 是否使用 RAG 增强
            book_analysis: 样板书分析结果
            max_chars: 最大上下文字数
        
        Returns:
            生成结果
        """
        result = GenerationResult(chapter_num=chapter_num)
        
        try:
            # 1. 提取上下文
            logger.info(f"提取第 {chapter_num} 章上下文...")
            if use_rag:
                context_data = await self.context_extractor.extract_with_rag(
                    chapter_num, query, top_k=5
                )
            else:
                context_data = self.context_extractor.extract_full_context(
                    chapter_num, query
                )
            
            # 2. 融合参考数据
            logger.info(f"融合参考数据...")
            analysis = None
            if book_analysis:
                analysis = BookAnalysisResult.from_dict(book_analysis)
            
            # 确定章节类型
            chapter_type = self._determine_chapter_type(chapter_num)
            
            integrated_context = self.reference_integrator.integrate(
                genre or self._get_genre_from_config(),
                chapter_num,
                analysis,
                chapter_type
            )
            result.context = integrated_context
            
            # 3. 生成章节大纲
            logger.info(f"生成章节大纲...")
            outline = await self.generate_outline(chapter_num, context_data, integrated_context)
            result.outline = outline
            
            # 4. 生成章节正文
            logger.info(f"生成章节正文...")
            content = await self.generate_content(outline, context_data, integrated_context)
            
            result.title = outline.title
            result.content = content
            result.word_count = len(content)
            result.success = True
            
            logger.info(f"第 {chapter_num} 章生成完成，字数: {result.word_count}")
            
        except Exception as e:
            logger.error(f"生成第 {chapter_num} 章失败: {e}")
            result.success = False
            result.error_message = str(e)
        
        return result
    
    async def generate_outline(self,
                               chapter_num: int,
                               context_data: Dict[str, Any],
                               integrated_context: IntegratedContext) -> ChapterOutline:
        """
        生成章节大纲
        
        Args:
            chapter_num: 章节号
            context_data: 上下文数据
            integrated_context: 融合上下文
        
        Returns:
            章节大纲
        """
        # 构建提示词
        prompt = self._build_outline_prompt(chapter_num, context_data, integrated_context)
        logger.info(f"大纲提示词长度: {len(prompt)} 字符")
        logger.debug(f"大纲提示词前200字: {prompt[:200]}...")
        
        # 调用 LLM
        logger.info("调用LLM生成大纲...")
        response = await self.llm_client.chat_completion_async(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )
        
        # 提取响应内容
        response_content = response.get("content", "") if isinstance(response, dict) else str(response)
        logger.info(f"LLM响应长度: {len(response_content)} 字符")
        logger.debug(f"LLM响应前200字: {response_content[:200]}...")
        
        # 解析响应
        outline_data = self._parse_outline_response(response_content)
        logger.info(f"解析后大纲: title={outline_data.get('title')}, scenes={len(outline_data.get('scenes', []))}")
        
        return ChapterOutline(
            chapter_num=chapter_num,
            title=outline_data.get("title", f"第{chapter_num}章"),
            scenes=outline_data.get("scenes", []),
            hooks=outline_data.get("hooks", []),
            cool_points=outline_data.get("cool_points", []),
            micro_payoffs=outline_data.get("micro_payoffs", []),
            word_count_target=integrated_context.rhythm_suggestion.get("target_word_count", 3000),
        )
    
    async def generate_content(self,
                               outline: ChapterOutline,
                               context_data: Dict[str, Any],
                               integrated_context: IntegratedContext) -> str:
        """
        生成章节正文
        
        Args:
            outline: 章节大纲
            context_data: 上下文数据
            integrated_context: 融合上下文
        
        Returns:
            章节正文
        """
        # 构建提示词
        prompt = self._build_content_prompt(outline, context_data, integrated_context)
        
        # 调用 LLM
        response = await self.llm_client.chat_completion_async(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4000,
        )
        
        content = response.get("content", "")
        
        # 清理内容
        content = self._clean_content(content)
        
        return content
    
    def _build_outline_prompt(self,
                              chapter_num: int,
                              context_data: Dict[str, Any],
                              integrated_context: IntegratedContext) -> str:
        """构建大纲生成提示词"""
        lines = [
            f"# 任务: 生成第 {chapter_num} 章大纲",
            "",
            "## 创作背景",
            "",
        ]
        
        # 项目信息
        project = context_data.get("project", {})
        lines.append(f"- 书名: {project.get('name', '未命名')}")
        lines.append(f"- 题材: {project.get('genre', '未设定')}")
        lines.append(f"- 当前进度: 第{chapter_num}章")
        lines.append("")
        
        # 前情提要
        previous = context_data.get("previous_chapters", [])
        if previous:
            lines.append("## 前情提要")
            for ch in previous[-3:]:
                lines.append(f"- 第{ch.get('chapter', 0)}章: {ch.get('summary', '无摘要')[:100]}")
            lines.append("")
        
        # 创作指导
        guidance = self.reference_integrator.format_context_for_prompt(integrated_context)
        lines.append(guidance)
        
        # 大纲要求
        lines.extend([
            "## 大纲要求",
            "",
            "请生成章节大纲，包含以下内容:",
            "",
            "1. **章节标题**: 吸引人的标题",
            "2. **场景设计**: 3-5个场景，每个场景包含:",
            "   - 场景描述",
            "   - 主要人物",
            "   - 冲突/目标",
            "   - 预期字数",
            "3. **钩子设计**: 1-2个钩子，包含:",
            "   - 钩子类型",
            "   - 钩子内容",
            "   - 放置位置 (章内/章末)",
            "4. **爽点设计**: 1-2个爽点，包含:",
            "   - 爽点类型",
            "   - 爽点描述",
            "   - 铺垫/兑现/余波",
            "5. **微兑现**: 1-2个微兑现，包含:",
            "   - 微兑现类型",
            "   - 微兑现内容",
            "",
            "请以 JSON 格式返回大纲:",
            "```json",
            "{",
            '  "title": "章节标题",',
            '  "scenes": [',
            "    {",
            '      "description": "场景描述",',
            '      "characters": ["人物1", "人物2"],',
            '      "conflict": "冲突/目标",',
            '      "word_count": 800',
            "    }",
            "  ],",
            '  "hooks": [',
            "    {",
            '      "type": "钩子类型",',
            '      "content": "钩子内容",',
            '      "position": "章末"',
            "    }",
            "  ],",
            '  "cool_points": [',
            "    {",
            '      "type": "爽点类型",',
            '      "description": "爽点描述"',
            "    }",
            "  ],",
            '  "micro_payoffs": [',
            "    {",
            '      "type": "微兑现类型",',
            '      "content": "微兑现内容"',
            "    }",
            "  ]",
            "}",
            "```",
        ])
        
        return "\n".join(lines)
    
    def _build_content_prompt(self,
                              outline: ChapterOutline,
                              context_data: Dict[str, Any],
                              integrated_context: IntegratedContext) -> str:
        """构建正文生成提示词"""
        lines = [
            f"# 任务: 撰写第 {outline.chapter_num} 章",
            "",
            f"## 章节标题: {outline.title}",
            "",
            "## 章节大纲",
            "",
        ]
        
        # 场景
        for i, scene in enumerate(outline.scenes, 1):
            lines.append(f"### 场景{i}: {scene.get('description', '')}")
            lines.append(f"- 人物: {', '.join(scene.get('characters', []))}")
            lines.append(f"- 冲突: {scene.get('conflict', '')}")
            lines.append(f"- 字数: {scene.get('word_count', 800)}")
            lines.append("")
        
        # 钩子
        if outline.hooks:
            lines.append("### 钩子设计")
            for hook in outline.hooks:
                lines.append(f"- {hook.get('type', '')} ({hook.get('position', '')}): {hook.get('content', '')}")
            lines.append("")
        
        # 爽点
        if outline.cool_points:
            lines.append("### 爽点设计")
            for cp in outline.cool_points:
                lines.append(f"- {cp.get('type', '')}: {cp.get('description', '')}")
            lines.append("")
        
        # 微兑现
        if outline.micro_payoffs:
            lines.append("### 微兑现")
            for mp in outline.micro_payoffs:
                lines.append(f"- {mp.get('type', '')}: {mp.get('content', '')}")
            lines.append("")
        
        # 创作指导
        guidance = self.reference_integrator.format_context_for_prompt(integrated_context)
        lines.append(guidance)
        
        # 写作要求
        lines.extend([
            "## 写作要求",
            "",
            f"1. 目标字数: {outline.word_count_target} 字",
            "2. 文风要求:",
            f"   - 句长: {integrated_context.style_reference.get('avg_sentence_length', 25):.0f} 字左右",
            f"   - 对白密度: {integrated_context.style_reference.get('dialogue_ratio', 30):.0f}%",
            f"   - 开头模式: {integrated_context.style_reference.get('preferred_opening', '场景切入')}",
            f"   - 结尾模式: {integrated_context.style_reference.get('preferred_ending', '悬念钩子')}",
            "",
            "3. 节奏控制:",
            f"   - 铺垫: {integrated_context.rhythm_suggestion.get('rhythm_ratio', {}).get('铺垫', 30)}%",
            f"   - 冲突: {integrated_context.rhythm_suggestion.get('rhythm_ratio', {}).get('冲突', 40)}%",
            f"   - 高潮: {integrated_context.rhythm_suggestion.get('rhythm_ratio', {}).get('高潮', 30)}%",
            "",
            "4. 禁忌:",
            "   - 避免过度使用形容词和副词",
            "   - 避免冗长的心理描写",
            "   - 避免AI写作特征（如'令人...的是'、'不可...的'）",
            "",
            "请直接输出章节正文，不要包含标题。",
        ])
        
        return "\n".join(lines)
    
    def _parse_outline_response(self, response: str) -> Dict[str, Any]:
        """解析大纲响应"""
        import re
        
        # 空响应检查
        if not response or not response.strip():
            logger.warning("LLM返回空响应，使用默认大纲")
            return self._get_default_outline()
        
        try:
            # 尝试提取 JSON 代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                try:
                    result = json.loads(json_str)
                    logger.info("成功解析JSON代码块格式的大纲")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON代码块解析失败: {e}")
                    # 尝试修复常见问题
                    result = self._try_fix_json(json_str)
                    if result:
                        return result
            
            # 尝试提取花括号内的JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                try:
                    result = json.loads(json_str)
                    logger.info("成功解析花括号格式的大纲")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"花括号JSON解析失败: {e}")
                    result = self._try_fix_json(json_str)
                    if result:
                        return result
            
            # 尝试直接解析
            result = json.loads(response)
            logger.info("成功直接解析JSON格式的大纲")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}，响应内容: {response[:200]}...")
            return self._get_default_outline()
        except Exception as e:
            logger.error(f"解析大纲响应时发生错误: {e}")
            return self._get_default_outline()
    
    def _try_fix_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """尝试修复JSON"""
        import re
        
        try:
            # 1. 移除代码块标记
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            # 2. 移除注释
            json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            
            # 3. 修复末尾逗号
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # 4. 修复未闭合的字符串（简单处理）
            # 统计引号数量，如果是奇数，尝试在末尾添加
            quote_count = json_str.count('"')
            if quote_count % 2 == 1:
                json_str = json_str + '"'
            
            # 5. 尝试解析
            result = json.loads(json_str)
            logger.info("JSON修复成功")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"JSON修复失败: {e}")
            
            # 6. 最后尝试：提取title字段
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_str)
            if title_match:
                title = title_match.group(1)
                logger.info(f"提取到标题: {title}")
                return {
                    "title": title,
                    "scenes": self._get_default_outline()["scenes"],
                    "hooks": [],
                    "cool_points": [],
                    "micro_payoffs": [],
                }
            
            return None
        except Exception as e:
            logger.error(f"JSON修复异常: {e}")
            return None
    
    def _get_default_outline(self) -> Dict[str, Any]:
        """获取默认大纲"""
        return {
            "title": "待定",
            "scenes": [
                {"description": "开场", "characters": [], "conflict": "", "word_count": 1000},
                {"description": "发展", "characters": [], "conflict": "", "word_count": 1000},
                {"description": "收尾", "characters": [], "conflict": "", "word_count": 1000},
            ],
            "hooks": [],
            "cool_points": [],
            "micro_payoffs": [],
        }
    
    def _clean_content(self, content: str) -> str:
        """清理内容"""
        # 移除可能的标题
        lines = content.split("\n")
        if lines and lines[0].startswith("#"):
            lines = lines[1:]
        
        # 移除代码块标记
        content = "\n".join(lines)
        content = content.replace("```", "")
        
        return content.strip()
    
    def _determine_chapter_type(self, chapter_num: int) -> str:
        """确定章节类型"""
        # 简化实现：每10章一个高潮
        if chapter_num % 10 == 0:
            return "climax"
        elif chapter_num % 10 in [3, 7]:
            return "transition"
        else:
            return "normal"
    
    def _get_genre_from_config(self) -> str:
        """从配置获取题材"""
        state = self.state_manager.load()
        return state.get("project", {}).get("genre", "shuangwen")


# 便捷函数
async def generate_chapter(chapter_num: int,
                          genre: str = "",
                          query: str = "",
                          use_rag: bool = False,
                          book_analysis: Optional[Dict[str, Any]] = None,
                          config: Optional[ForgeAIConfig] = None) -> GenerationResult:
    """生成章节"""
    generator = ChapterGenerator(config)
    return await generator.generate_chapter(
        chapter_num, genre, query, use_rag, book_analysis
    )
