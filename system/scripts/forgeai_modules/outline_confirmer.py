#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大纲确认模块

功能：
- Context Agent生成创作执行包后，显示给用户确认
- 提供 y/n/edit 选项
- 支持修改后重新确认
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig


class OutlineConfirmer:
    """大纲确认器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()

    def display_execution_package(self, package: Dict[str, Any]) -> str:
        """
        格式化显示创作执行包
        
        Args:
            package: 创作执行包
        
        Returns:
            格式化的字符串
        """
        lines = []
        lines.append("=" * 80)
        lines.append("📋 创作执行包已生成")
        lines.append("=" * 80)
        lines.append("")
        
        # 1. 任务书（7板块）
        if "任务书" in package:
            task_book = package["任务书"]
            lines.append("## 📝 任务书")
            lines.append("")
            
            # 板块1：本章核心任务
            if "本章核心任务" in task_book:
                lines.append("### 板块1：本章核心任务")
                for key, value in task_book["本章核心任务"].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            # 板块2：接住上章
            if "接住上章" in task_book:
                lines.append("### 板块2：接住上章")
                for key, value in task_book["接住上章"].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            # 板块3：出场角色
            if "出场角色" in task_book:
                lines.append("### 板块3：出场角色")
                for character in task_book["出场角色"].get("角色清单", []):
                    lines.append(f"- {character.get('姓名', '')}: {character.get('当前状态', '')}")
                lines.append("")
            
            # 板块4：场景与力量约束
            if "场景与力量约束" in task_book:
                lines.append("### 板块4：场景与力量约束")
                for key, value in task_book["场景与力量约束"].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            # 板块5：时间约束
            if "时间约束" in task_book:
                lines.append("### 板块5：时间约束")
                for key, value in task_book["时间约束"].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            # 板块6：风格指导
            if "风格指导" in task_book:
                lines.append("### 板块6：风格指导")
                for key, value in task_book["风格指导"].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            # 板块7：连续性与伏笔
            if "连续性与伏笔" in task_book:
                lines.append("### 板块7：连续性与伏笔")
                for key, value in task_book["连续性与伏笔"].items():
                    if isinstance(value, list):
                        lines.append(f"- **{key}**: {', '.join(value)}")
                    else:
                        lines.append(f"- **{key}**: {value}")
                lines.append("")
        
        # 2. Context Contract
        if "Context Contract" in package:
            lines.append("## 📜 Context Contract（硬约束）")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(package["Context Contract"], ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        
        # 3. 章节节拍
        if "章节节拍" in package:
            lines.append("## 🎵 章节节拍")
            lines.append("")
            lines.append(package["章节节拍"])
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("")
        
        return "\n".join(lines)

    def prompt_user_confirmation(self) -> str:
        """
        提示用户确认
        
        Returns:
            用户选择（y/n/edit）
        """
        lines = []
        lines.append("📌 请确认是否继续写作：")
        lines.append("")
        lines.append("  y      - 确认无误，开始写作")
        lines.append("  n      - 发现问题，中止流程")
        lines.append("  edit   - 修改执行包后重新确认")
        lines.append("")
        lines.append("请输入选择 (y/n/edit): ")
        
        return "\n".join(lines)

    def process_user_input(self, user_input: str, package: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入（y/n/edit）
            package: 创作执行包
        
        Returns:
            {
                "action": "proceed" / "abort" / "edit",
                "package": package  # 如果edit，可能包含修改后的package
            }
        """
        user_input = user_input.strip().lower()
        
        if user_input == "y":
            return {
                "action": "proceed",
                "message": "✅ 确认通过，开始写作",
                "package": package
            }
        elif user_input == "n":
            return {
                "action": "abort",
                "message": "❌ 已中止，请检查大纲和设定",
                "package": package
            }
        elif user_input == "edit":
            return {
                "action": "edit",
                "message": "✏️ 请修改以下字段（输入字段名=新值，多个用逗号分隔）：",
                "editable_fields": self._get_editable_fields(package),
                "package": package
            }
        else:
            return {
                "action": "invalid",
                "message": "⚠️ 无效输入，请输入 y/n/edit",
                "package": package
            }

    def _get_editable_fields(self, package: Dict[str, Any]) -> List[str]:
        """获取可编辑字段列表"""
        editable = []
        
        if "任务书" in package:
            task_book = package["任务书"]
            
            if "本章核心任务" in task_book:
                editable.extend([
                    "任务书.本章核心任务.目标",
                    "任务书.本章核心任务.阻力",
                    "任务书.本章核心任务.代价"
                ])
            
            if "时间约束" in task_book:
                editable.extend([
                    "任务书.时间约束.本章时间锚点",
                    "任务书.时间约束.本章允许推进"
                ])
        
        return editable

    def apply_edits(self, package: Dict[str, Any], edits: Dict[str, str]) -> Dict[str, Any]:
        """
        应用用户编辑
        
        Args:
            package: 原始创作执行包
            edits: 用户编辑 {字段路径: 新值}
        
        Returns:
            修改后的创作执行包
        """
        modified_package = package.copy()
        
        for field_path, new_value in edits.items():
            # 解析路径
            parts = field_path.split(".")
            
            # 定位到目标字段
            target = modified_package
            for part in parts[:-1]:
                if part in target:
                    target = target[part]
                else:
                    break
            
            # 修改值
            final_key = parts[-1]
            if final_key in target:
                target[final_key] = new_value
        
        return modified_package

    def save_execution_package(
        self, 
        package: Dict[str, Any],
        chapter: int,
        project_root: Path
    ) -> Path:
        """
        保存创作执行包到文件
        
        Args:
            package: 创作执行包
            chapter: 章节号
            project_root: 项目根目录
        
        Returns:
            保存的文件路径
        """
        output_dir = project_root / ".forgeai" / "execution_packages"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"ch{chapter:03d}_execution_package.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(package, f, ensure_ascii=False, indent=2)
        
        return output_file
