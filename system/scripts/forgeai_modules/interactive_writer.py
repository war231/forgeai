#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式创作

支持用户确认和修改的交互式创作流程
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .config import get_config, ForgeAIConfig
from .chapter_generator import ChapterGenerator, GenerationResult
from .chapter_optimizer import ChapterOptimizer, OptimizationResult
from .review_feedback_loop import ReviewFeedbackLoop, FeedbackResult
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class InteractiveSession:
    """交互式会话"""
    session_id: str
    chapter_num: int
    status: str = "pending"  # pending/generating/reviewing/completed/aborted
    current_content: str = ""
    generation_result: Optional[GenerationResult] = None
    optimization_result: Optional[OptimizationResult] = None
    feedback_result: Optional[FeedbackResult] = None
    user_inputs: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "chapter_num": self.chapter_num,
            "status": self.status,
            "current_content_length": len(self.current_content),
            "user_inputs_count": len(self.user_inputs),
        }


class InteractiveWriter:
    """交互式创作器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.generator = ChapterGenerator(config)
        self.optimizer = ChapterOptimizer(config)
        self.feedback_loop = ReviewFeedbackLoop(config)
        
        # 用户交互回调
        self._confirm_callback: Optional[Callable] = None
        self._edit_callback: Optional[Callable] = None
    
    def set_callbacks(self,
                     confirm_callback: Optional[Callable] = None,
                     edit_callback: Optional[Callable] = None) -> None:
        """设置用户交互回调"""
        self._confirm_callback = confirm_callback
        self._edit_callback = edit_callback
    
    async def write_interactive(self,
                               chapter_num: int,
                               genre: str = "",
                               query: str = "",
                               use_rag: bool = False,
                               enable_optimization: bool = True,
                               enable_feedback: bool = True) -> InteractiveSession:
        """
        交互式创作
        
        Args:
            chapter_num: 章节号
            genre: 题材
            query: 主题指导
            use_rag: 是否使用 RAG
            enable_optimization: 是否启用优化
            enable_feedback: 是否启用反馈循环
        
        Returns:
            交互式会话
        """
        import uuid
        session = InteractiveSession(
            session_id=str(uuid.uuid4())[:8],
            chapter_num=chapter_num,
        )
        
        try:
            # Step 1: 生成章节
            session.status = "generating"
            logger.info(f"[Session {session.session_id}] 生成章节...")
            
            gen_result = await self.generator.generate_chapter(
                chapter_num, genre, query, use_rag
            )
            session.generation_result = gen_result
            session.current_content = gen_result.content
            
            if not gen_result.success:
                session.status = "aborted"
                logger.error(f"[Session {session.session_id}] 生成失败: {gen_result.error_message}")
                return session
            
            # Step 2: 用户确认
            confirmed = await self._confirm_generation(session)
            
            if not confirmed:
                session.status = "aborted"
                logger.info(f"[Session {session.session_id}] 用户取消")
                return session
            
            # Step 3: 优化（可选）
            if enable_optimization:
                session.status = "optimizing"
                logger.info(f"[Session {session.session_id}] 优化章节...")
                
                opt_result = await self.optimizer.optimize_chapter(
                    chapter_num, session.current_content
                )
                session.optimization_result = opt_result
                session.current_content = opt_result.final_content
                
                # 用户确认优化
                confirmed = await self._confirm_optimization(session)
                
                if not confirmed:
                    # 回滚到优化前
                    session.current_content = session.generation_result.content
            
            # Step 4: 反馈循环（可选）
            if enable_feedback:
                session.status = "reviewing"
                logger.info(f"[Session {session.session_id}] 应用反馈...")
                
                fb_result = await self.feedback_loop.apply_feedback(
                    chapter_num, session.current_content
                )
                session.feedback_result = fb_result
                session.current_content = fb_result.final_content
                
                # 用户确认修复
                confirmed = await self._confirm_feedback(session)
                
                if not confirmed:
                    # 回滚到反馈前
                    if session.optimization_result:
                        session.current_content = session.optimization_result.final_content
                    else:
                        session.current_content = session.generation_result.content
            
            # Step 5: 最终确认
            final_confirmed = await self._confirm_final(session)
            
            if final_confirmed:
                session.status = "completed"
                logger.info(f"[Session {session.session_id}] 完成")
            else:
                session.status = "aborted"
                logger.info(f"[Session {session.session_id}] 用户取消最终结果")
            
        except Exception as e:
            session.status = "aborted"
            logger.error(f"[Session {session.session_id}] 错误: {e}")
        
        return session
    
    async def _confirm_generation(self, session: InteractiveSession) -> bool:
        """确认生成结果"""
        if self._confirm_callback:
            return await self._confirm_callback(
                stage="generation",
                content=session.current_content,
                metadata={
                    "chapter_num": session.chapter_num,
                    "word_count": len(session.current_content),
                    "title": session.generation_result.title if session.generation_result else "",
                }
            )
        
        # 默认：总是确认
        return True
    
    async def _confirm_optimization(self, session: InteractiveSession) -> bool:
        """确认优化结果"""
        if self._confirm_callback:
            return await self._confirm_callback(
                stage="optimization",
                content=session.current_content,
                metadata={
                    "improvement": session.optimization_result.total_improvement if session.optimization_result else 0,
                    "rounds": len(session.optimization_result.rounds) if session.optimization_result else 0,
                }
            )
        
        # 默认：总是确认
        return True
    
    async def _confirm_feedback(self, session: InteractiveSession) -> bool:
        """确认反馈结果"""
        if self._confirm_callback:
            return await self._confirm_callback(
                stage="feedback",
                content=session.current_content,
                metadata={
                    "total_fixes": session.feedback_result.total_fixes if session.feedback_result else 0,
                    "remaining_issues": len(session.feedback_result.final_issues) if session.feedback_result else 0,
                }
            )
        
        # 默认：总是确认
        return True
    
    async def _confirm_final(self, session: InteractiveSession) -> bool:
        """确认最终结果"""
        if self._confirm_callback:
            return await self._confirm_callback(
                stage="final",
                content=session.current_content,
                metadata={
                    "chapter_num": session.chapter_num,
                    "word_count": len(session.current_content),
                    "status": session.status,
                }
            )
        
        # 默认：总是确认
        return True
    
    async def edit_content(self,
                          session: InteractiveSession,
                          edits: Dict[str, Any]) -> str:
        """
        编辑内容
        
        Args:
            session: 交互式会话
            edits: 编辑指令
        
        Returns:
            编辑后的内容
        """
        if self._edit_callback:
            return await self._edit_callback(session.current_content, edits)
        
        # 默认：应用简单替换
        content = session.current_content
        
        for key, value in edits.items():
            if key == "replace":
                # 替换文本
                old = value.get("old", "")
                new = value.get("new", "")
                content = content.replace(old, new)
            elif key == "append":
                # 追加文本
                content += value
            elif key == "prepend":
                # 前置文本
                content = value + content
        
        session.current_content = content
        session.user_inputs.append({"action": "edit", "edits": edits})
        
        return content


# CLI 交互式确认函数
async def cli_confirm(stage: str, content: str, metadata: Dict[str, Any]) -> bool:
    """CLI 交互式确认"""
    print(f"\n{'='*60}")
    print(f"[Confirm] {stage.upper()} 阶段")
    print(f"{'='*60}")
    
    # 显示元数据
    for key, value in metadata.items():
        print(f"{key}: {value}")
    
    # 显示内容预览
    print(f"\n[Preview] 内容预览（前300字）:")
    print("-" * 60)
    print(content[:300])
    if len(content) > 300:
        print("...")
    print("-" * 60)
    
    # 用户确认
    while True:
        response = input("\n确认继续? (y/n/edit): ").strip().lower()
        
        if response == "y":
            return True
        elif response == "n":
            return False
        elif response == "edit":
            # 简单编辑
            print("输入要替换的文本（空行结束）:")
            old_lines = []
            while True:
                line = input()
                if not line:
                    break
                old_lines.append(line)
            old_text = "\n".join(old_lines)
            
            if old_text:
                print("输入新文本（空行结束）:")
                new_lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    new_lines.append(line)
                new_text = "\n".join(new_lines)
                
                # 应用替换
                content = content.replace(old_text, new_text)
                print("已应用替换")
            else:
                print("取消编辑")
        else:
            print("无效输入，请输入 y/n/edit")


# 便捷函数
async def write_interactive(chapter_num: int,
                           genre: str = "",
                           query: str = "",
                           use_rag: bool = False,
                           config: Optional[ForgeAIConfig] = None) -> InteractiveSession:
    """交互式创作"""
    writer = InteractiveWriter(config)
    writer.set_callbacks(confirm_callback=cli_confirm)
    return await writer.write_interactive(chapter_num, genre, query, use_rag)
