#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态变更确认模块

功能：
- Data Agent检测到状态变更后，显示变更详情
- 让用户确认是否写入
- 支持选择性写入（部分确认）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_config, ForgeAIConfig


class StateChangeConfirmer:
    """状态变更确认器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()

    def display_state_changes(self, changes: List[Dict[str, Any]]) -> str:
        """
        格式化显示状态变更
        
        Args:
            changes: 状态变更列表
        
        Returns:
            格式化的字符串
        """
        lines = []
        lines.append("=" * 80)
        lines.append("🔄 检测到状态变更")
        lines.append("=" * 80)
        lines.append("")
        
        for i, change in enumerate(changes, 1):
            lines.append(f"## 变更 {i}/{len(changes)}")
            lines.append("")
            lines.append(f"- **实体**: {change.get('entity', '未知')}")
            lines.append(f"- **字段**: {change.get('field', '未知')}")
            lines.append(f"- **旧值**: {change.get('old_value', '无')}")
            lines.append(f"- **新值**: {change.get('new_value', '无')}")
            lines.append(f"- **章节**: 第{change.get('chapter', '未知')}章")
            lines.append(f"- **证据**: {change.get('evidence', '无')}")
            lines.append(f"- **严重度**: {change.get('severity', 'medium')}")
            lines.append("")
            
            # 变更类型提示
            change_type = change.get('change_type', 'update')
            if change_type == 'location':
                lines.append("📍 **位置变更**: 请确认移动路径是否合理")
            elif change_type == 'power':
                lines.append("⚔️ **境界变更**: 请确认是否有突破描写")
            elif change_type == 'inventory':
                lines.append("🎒 **物品变更**: 请确认物品来源/去向")
            elif change_type == 'relationship':
                lines.append("💕 **关系变更**: 请确认关系变化原因")
            
            lines.append("")
            lines.append("-" * 80)
            lines.append("")
        
        return "\n".join(lines)

    def prompt_user_confirmation(self, changes: List[Dict[str, Any]]) -> str:
        """
        提示用户确认
        
        Args:
            changes: 状态变更列表
        
        Returns:
            提示字符串
        """
        lines = []
        lines.append("📌 请确认是否写入这些状态变更：")
        lines.append("")
        lines.append("  all      - 全部写入")
        lines.append("  none     - 全部跳过")
        lines.append("  select   - 选择性写入（逐个确认）")
        lines.append("  review   - 查看详细变更")
        lines.append("")
        lines.append(f"共检测到 {len(changes)} 个状态变更")
        lines.append("")
        lines.append("请输入选择 (all/none/select/review): ")
        
        return "\n".join(lines)

    def process_user_input(
        self, 
        user_input: str, 
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            changes: 状态变更列表
        
        Returns:
            {
                "action": "write_all" / "skip_all" / "selective" / "review",
                "changes_to_write": [...],
                "changes_to_skip": [...]
            }
        """
        user_input = user_input.strip().lower()
        
        if user_input == "all":
            return {
                "action": "write_all",
                "message": f"✅ 将写入全部 {len(changes)} 个状态变更",
                "changes_to_write": changes,
                "changes_to_skip": []
            }
        elif user_input == "none":
            return {
                "action": "skip_all",
                "message": f"❌ 跳过全部 {len(changes)} 个状态变更",
                "changes_to_write": [],
                "changes_to_skip": changes
            }
        elif user_input == "select":
            return {
                "action": "selective",
                "message": "✏️ 进入选择性确认模式",
                "instructions": "将逐个显示变更，请确认每个变更（y/n）"
            }
        elif user_input == "review":
            return {
                "action": "review",
                "message": "📋 显示详细变更",
                "detailed_changes": self._generate_detailed_report(changes)
            }
        else:
            return {
                "action": "invalid",
                "message": "⚠️ 无效输入，请输入 all/none/select/review"
            }

    def selective_confirmation(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        逐个确认状态变更
        
        Args:
            changes: 状态变更列表
        
        Returns:
            {
                "changes_to_write": [...],
                "changes_to_skip": [...]
            }
        """
        changes_to_write = []
        changes_to_skip = []
        
        for i, change in enumerate(changes, 1):
            print(f"\n变更 {i}/{len(changes)}:")
            print(f"  实体: {change.get('entity', '未知')}")
            print(f"  字段: {change.get('field', '未知')}")
            print(f"  旧值: {change.get('old_value', '无')}")
            print(f"  新值: {change.get('new_value', '无')}")
            print(f"  证据: {change.get('evidence', '无')}")
            print()
            
            # 这里应该是交互式输入，但在模块中我们返回提示
            # 实际使用时，调用者需要处理用户输入
        
        return {
            "changes_to_write": changes_to_write,
            "changes_to_skip": changes_to_skip,
            "note": "请在调用者中处理逐个确认的用户输入"
        }

    def _generate_detailed_report(self, changes: List[Dict[str, Any]]) -> str:
        """生成详细变更报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 状态变更详细报告")
        lines.append("=" * 80)
        lines.append("")
        
        # 按变更类型分组
        by_type = {}
        for change in changes:
            change_type = change.get('change_type', 'other')
            if change_type not in by_type:
                by_type[change_type] = []
            by_type[change_type].append(change)
        
        # 显示分组统计
        for change_type, type_changes in by_type.items():
            lines.append(f"## {change_type.upper()} 变更 ({len(type_changes)}个)")
            lines.append("")
            
            for change in type_changes:
                lines.append(f"- 实体: {change.get('entity')}")
                lines.append(f"  字段: {change.get('field')}")
                lines.append(f"  变更: {change.get('old_value')} → {change.get('new_value')}")
                lines.append(f"  证据: {change.get('evidence')}")
                lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)

    def generate_summary(self, changes: List[Dict[str, Any]]) -> str:
        """
        生成变更摘要
        
        Args:
            changes: 状态变更列表
        
        Returns:
            摘要字符串
        """
        if not changes:
            return "无状态变更"
        
        summary_lines = []
        summary_lines.append(f"共检测到 {len(changes)} 个状态变更：")
        
        # 按变更类型分组
        by_type = {}
        for change in changes:
            change_type = change.get('change_type', 'other')
            if change_type not in by_type:
                by_type[change_type] = 0
            by_type[change_type] += 1
        
        for change_type, count in by_type.items():
            summary_lines.append(f"  - {change_type}: {count}个")
        
        return "\n".join(summary_lines)

    def save_change_log(
        self, 
        changes: List[Dict[str, Any]],
        chapter: int,
        project_root: Path
    ) -> Path:
        """
        保存变更日志到文件
        
        Args:
            changes: 状态变更列表
            chapter: 章节号
            project_root: 项目根目录
        
        Returns:
            保存的文件路径
        """
        output_dir = project_root / ".forgeai" / "change_logs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"ch{chapter:03d}_changes.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "chapter": chapter,
                "timestamp": str(Path.cwd()),
                "changes": changes
            }, f, ensure_ascii=False, indent=2)
        
        return output_file
