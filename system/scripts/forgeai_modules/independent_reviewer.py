#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立审查模块

功能：
- 清除上下文，隔离审查环境
- 只传递【上一章】+【这一章】
- 模拟"新对话窗口"的客观审查
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig
from .state_manager import StateManager
from .rag_adapter import RAGAdapter
from .logger import get_logger

logger = get_logger(__name__)


class IndependentReviewer:
    """独立审查器（清除上下文，客观审查）"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.state_manager = StateManager(self.config)
        self.rag_adapter = RAGAdapter(self.config)

    def prepare_minimal_context(
        self, 
        current_chapter: int,
        project_root: Path
    ) -> Dict[str, Any]:
        """
        准备最小化上下文（只包含上一章+这一章）
        
        Args:
            current_chapter: 当前章节号
            project_root: 项目根目录
        
        Returns:
            {
                "previous_chapter": {
                    "number": 99,
                    "content": "上一章内容...",
                    "summary": "上一章摘要",
                    "ending_state": {...}
                },
                "current_chapter": {
                    "number": 100,
                    "content": "当前章节内容..."
                }
            }
        """
        logger.info(f"准备独立审查上下文：第{current_chapter}章")
        logger.debug(f"查找章节文件：4-正文/第{current_chapter:03d}章*.md")
        
        context = {
            "previous_chapter": None,
            "current_chapter": None
        }
        
        # 1. 读取上一章内容
        previous_chapter = current_chapter - 1
        if previous_chapter > 0:
            # 读取上一章正文
            previous_chapter_files = list(project_root.glob(f"4-正文/第{previous_chapter:03d}章*.md"))
            
            if not previous_chapter_files:
                logger.warning(f"未找到上一章文件：4-正文/第{previous_chapter:03d}章*.md")
                return {
                    "error": f"找不到第{previous_chapter}章文件，独立审查需要对比前后章节",
                    "hint": f"期望文件名格式：第{previous_chapter:03d}章*.md",
                    "previous_chapter": previous_chapter
                }
            
            previous_content = previous_chapter_files[0].read_text(encoding="utf-8")
            
            # 读取上一章摘要（如果存在）
            summary_file = project_root / ".forgeai" / "summaries" / f"ch{previous_chapter:03d}.md"
            summary = ""
            if summary_file.exists():
                summary = summary_file.read_text(encoding="utf-8")
            
            # 获取上一章的结束状态
            state = self.state_manager.load()
            chapter_meta = state.get("chapter_meta", {}).get(f"{previous_chapter:04d}", {})
            
            context["previous_chapter"] = {
                "number": previous_chapter,
                "content": previous_content,
                "summary": summary,
                "ending_state": chapter_meta.get("ending", {})
            }
        
        # 2. 读取当前章节内容
        current_chapter_files = list(project_root.glob(f"4-正文/第{current_chapter:03d}章*.md"))
        
        if not current_chapter_files:
            logger.warning(f"未找到章节文件：4-正文/第{current_chapter:03d}章*.md")
            return {
                "error": f"找不到第{current_chapter}章文件，请检查 4-正文/ 目录下是否存在匹配的文件",
                "hint": f"期望文件名格式：第{current_chapter:03d}章*.md",
                "current_chapter": current_chapter
            }
        
        current_content = current_chapter_files[0].read_text(encoding="utf-8")
        context["current_chapter"] = {
            "number": current_chapter,
            "content": current_content
        }
        
        logger.info(f"成功准备上下文：上一章={previous_chapter}, 当前章={current_chapter}")
        return context

    def generate_review_prompt(self, context: Dict[str, Any], current_chapter: int = None) -> str:
        """
        生成独立审查提示词
        
        Args:
            context: 最小化上下文
            current_chapter: 当前章节号（可选，用于错误信息）
        
        Returns:
            审查提示词
        """
        # 检查是否为错误上下文
        if isinstance(context, dict) and "error" in context:
            # 返回详细的错误信息
            error_msg = context["error"]
            if "hint" in context:
                error_msg += f"\n提示：{context['hint']}"
            logger.error(f"独立审查失败：{error_msg}")
            return error_msg
        
        previous = context.get("previous_chapter")
        current = context.get("current_chapter")
        
        if not previous or not current:
            error_msg = "错误：无法读取章节内容。请检查章节文件是否存在且格式正确。"
            logger.error(error_msg)
            return error_msg
        
        logger.info(f"成功生成独立审查提示词：第{current['number']}章")
        
        prompt = f"""你是严厉的资深编辑。请对比【上一章内容】和【这一章内容】。

## 上一章内容（第{previous['number']}章）

```
{previous['content'][:2000]}  # 限制长度，避免token过多
```

## 上一章结束状态

```json
{json.dumps(previous.get('ending_state', {}), ensure_ascii=False, indent=2)}
```

## 这一章内容（第{current['number']}章）

```
{current['content']}
```

---

## 审查任务

请检查是否存在以下矛盾：

### 1. 人物位置瞬移
- 上一章结束位置 → 这一章开始位置
- 是否有合理的移动描述？

### 2. 物品道具消失/出现
- 上一章持有的物品 → 这一章是否还在？
- 新出现的物品是否有交代？

### 3. 说话语气是否符合人设
- 角色对话是否与其性格一致？
- 是否有OOC（Out of Character）行为？

### 4. 时间线是否连贯
- 时间锚点是否匹配？
- 倒计时是否正确递减？
- 是否有时间回跳（无闪回标注）？

### 5. 状态变化是否合理
- 主角境界是否突然提升（无突破描写）？
- 角色状态是否突然变化（无解释）？

---

## 输出格式

请以JSON格式输出：

```json
{{
  "issues": [
    {{
      "type": "人物位置瞬移|物品道具消失|说话语气偏离|时间线矛盾|状态变化异常",
      "severity": "critical|high|medium",
      "location": "第X段",
      "description": "具体问题描述",
      "suggestion": "修改建议"
    }}
  ],
  "highlights": [
    "找出可取之处"
  ],
  "overall_assessment": "整体评价"
}}
```

请开始审查："""
        
        return prompt

    def conduct_independent_review(
        self, 
        current_chapter: int,
        project_root: Path
    ) -> Dict[str, Any]:
        """
        执行独立审查（清除上下文）
        
        Args:
            current_chapter: 当前章节号
            project_root: 项目根目录
        
        Returns:
            {
                "status": "ok",
                "context": {...},
                "review_prompt": "...",
                "instructions": "请将review_prompt发送到新的对话窗口"
            }
        """
        # 1. 准备最小化上下文
        context = self.prepare_minimal_context(current_chapter, project_root)
        
        # 2. 生成审查提示词
        review_prompt = self.generate_review_prompt(context)
        
        # 3. 返回结果
        return {
            "status": "ok",
            "mode": "independent",
            "chapter": current_chapter,
            "context_prepared": {
                "previous_chapter": context["previous_chapter"]["number"] if context["previous_chapter"] else None,
                "current_chapter": context["current_chapter"]["number"] if context["current_chapter"] else None
            },
            "review_prompt": review_prompt,
            "instructions": [
                "1. 复制上述审查提示词",
                "2. 打开一个新的对话窗口",
                "3. 粘贴提示词到新窗口",
                "4. 获取独立的审查结果",
                "5. 根据审查结果修改章节内容"
            ],
            "tip": "新对话窗口可以避免上下文干扰，提供更客观的审查结果"
        }

    def save_review_context(
        self, 
        current_chapter: int,
        project_root: Path
    ) -> Path:
        """
        保存审查上下文到文件（方便复制）
        
        Args:
            current_chapter: 当前章节号
            project_root: 项目根目录
        
        Returns:
            保存的文件路径
        """
        context = self.prepare_minimal_context(current_chapter, project_root)
        review_prompt = self.generate_review_prompt(context)
        
        # 保存到文件
        output_dir = project_root / ".forgeai" / "independent_reviews"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"ch{current_chapter:03d}_review_prompt.md"
        output_file.write_text(review_prompt, encoding="utf-8")
        
        return output_file
