"""
自动修复建议生成模块
基于LLM生成一致性问题的修复建议
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class AutoFixer:
    """自动修复建议生成器"""
    
    def __init__(self, project_root: Path, llm_client=None):
        """
        Args:
            project_root: 项目根目录
            llm_client: LLM客户端（可选，用于生成修复文本）
        """
        self.project_root = project_root
        self.forgeai_dir = project_root / ".forgeai"
        self.llm_client = llm_client
        
    def generate_fix_suggestion(self, issue: Dict[str, Any], context: Optional[str] = None) -> str:
        """生成修复建议
        
        Args:
            issue: 一致性问题
            context: 上下文文本（可选）
        
        Returns:
            修复建议文本
        """
        issue_type = issue.get("issue_type", "")
        severity = issue.get("severity", "")
        description = issue.get("description", "")
        details = issue.get("details", {})
        chapter = issue.get("chapter", 0)
        
        # 根据问题类型生成不同建议
        if issue_type == "timeline":
            return self._generate_timeline_fix(issue, context)
        elif issue_type == "character":
            return self._generate_character_fix(issue, context)
        elif issue_type == "worldview":
            return self._generate_worldview_fix(issue, context)
        elif issue_type == "ooc":
            return self._generate_ooc_fix(issue, context)
        else:
            return f"建议：检查并修复{description}"
    
    def _generate_timeline_fix(self, issue: Dict[str, Any], context: Optional[str]) -> str:
        """生成时间线修复建议"""
        description = issue.get("description", "")
        details = issue.get("details", {})
        chapter = issue.get("chapter", 0)
        
        # 时间跨度问题
        if "时间跨度过大" in description:
            days_diff = details.get("days_diff", 0)
            prev_anchor = details.get("prev_anchor", "")
            current_anchor = details.get("current_anchor", "")
            
            # 生成过渡文本
            transition_text = self._generate_time_transition(days_diff)
            
            suggestion = f"[FIX] 时间跨度修复建议\n\n"
            suggestion += f"**问题**：{description}\n\n"
            suggestion += f"**建议**：在第{chapter}章开头添加时间过渡段落\n\n"
            suggestion += f"**生成文本**：\n"
            suggestion += f"```text\n{transition_text}\n```\n\n"
            suggestion += f"**手动调整提示**：\n"
            suggestion += f"- 确认这{days_diff}天内主角的主要活动\n"
            suggestion += f"- 如果有重要事件，建议单独成章\n"
            suggestion += f"- 如果是修炼、赶路等日常，可简略带过\n"
            
            return suggestion
        
        # 倒计时问题
        if "倒计时不一致" in description:
            countdown_name = details.get("countdown_name", "")
            expected_end = details.get("expected_end", 0)
            actual_end = details.get("actual_end", 0)
            
            suggestion = f"[FIX] 倒计时修复建议\n\n"
            suggestion += f"**问题**：{description}\n\n"
            
            if actual_end > expected_end:
                # 延后了
                suggestion += f"**方案1**：调整倒计时值\n"
                suggestion += f"  - 将\"{countdown_name}\"改为D-{actual_end - chapter}\n\n"
                suggestion += f"**方案2**：添加延后原因\n"
                suggestion += f"  - 在第{expected_end}章提及：\"因{countdown_name}受到干扰，推迟了{actual_end - expected_end}章\"\n"
            else:
                # 提前了
                suggestion += f"**方案1**：调整倒计时值\n"
                suggestion += f"  - 将\"{countdown_name}\"改为D-{actual_end - chapter}\n\n"
                suggestion += f"**方案2**：调整剧情节奏\n"
                suggestion += f"  - 在第{actual_end}章之前添加缓冲事件，延长剧情\n"
            
            return suggestion
        
        return f"建议：检查时间线设置，确保时间连续性"
    
    def _generate_character_fix(self, issue: Dict[str, Any], context: Optional[str]) -> str:
        """生成角色修复建议"""
        description = issue.get("description", "")
        details = issue.get("details", {})
        chapter = issue.get("chapter", 0)
        
        # 修为倒退
        if "修为等级异常倒退" in description:
            entity = details.get("entity", "")
            prev_level = details.get("prev_level", 0)
            current_level = details.get("current_level", 0)
            
            suggestion = f"[FIX] 修为倒退修复建议\n\n"
            suggestion += f"**问题**：{description}\n\n"
            suggestion += f"**方案1**：合理解释修为倒退\n"
            suggestion += f"  - 添加：\"{entity}因{self._get_reason_for_level_drop()}，修为从{prev_level}降至{current_level}\"\n"
            suggestion += f"  - 常见原因：重伤、封印、献祭、压制等\n\n"
            suggestion += f"**方案2**：修正为正常修为\n"
            suggestion += f"  - 将第{chapter}章的修为描述改回{prev_level}\n\n"
            suggestion += f"**方案3**：添加恢复剧情\n"
            suggestion += f"  - 在后续章节添加恢复修为的剧情线\n"
            
            return suggestion
        
        # 角色消失
        if "未出场" in description:
            entity = details.get("entity", "")
            chapters_absent = details.get("chapters_absent", 0)
            
            suggestion = f"[FIX] 角色消失修复建议\n\n"
            suggestion += f"**问题**：{description}\n\n"
            suggestion += f"**方案1**：提及角色去向\n"
            suggestion += f"  - 添加：\"{entity}在...（说明原因）\"\n"
            suggestion += f"  - 例如：\"{entity}去闭关修炼了\"\n\n"
            suggestion += f"**方案2**：安排角色出场\n"
            suggestion += f"  - 在下一章安排{entity}出场\n"
            suggestion += f"  - 可以是短暂出现或提及\n\n"
            suggestion += f"**方案3**：说明角色离开\n"
            suggestion += f"  - 明确交代{entity}离开的原因\n"
            suggestion += f"  - 例如：\"{entity}已返回宗门\"\n"
            
            return suggestion
        
        return f"建议：检查角色状态设置"
    
    def _generate_worldview_fix(self, issue: Dict[str, Any], context: Optional[str]) -> str:
        """生成世界观修复建议"""
        description = issue.get("description", "")
        details = issue.get("details", {})
        chapter = issue.get("chapter", 0)
        
        # 伏笔超期
        if "伏笔" in description and "超期" in description:
            fs_id = details.get("foreshadowing_id", "")
            fs_desc = details.get("description", "")
            expected_payoff = details.get("expected_payoff", 0)
            overdue_chapters = details.get("overdue_chapters", 0)
            
            suggestion = f"[FIX] 伏笔回收修复建议\n\n"
            suggestion += f"**问题**：{description}\n\n"
            suggestion += f"**方案1**：立即回收伏笔\n"
            suggestion += f"  - 在第{chapter}章回收：\"{fs_desc}\"\n"
            suggestion += f"  - 生成回收文本：\n"
            suggestion += f"  ```text\n  {self._generate_foreshadowing_payoff(fs_desc, chapter)}\n  ```\n\n"
            suggestion += f"**方案2**：调整预期回收章节\n"
            suggestion += f"  - 将预期章节改为第{chapter + 5}章\n"
            suggestion += f"  - 命令：forgeai foreshadowing update --id {fs_id} --payoff {chapter + 5}\n\n"
            suggestion += f"**方案3**：放弃该伏笔\n"
            suggestion += f"  - 如果伏笔已不合适，可以放弃\n"
            suggestion += f"  - 命令：forgeai foreshadowing resolve --id {fs_id} --chapter {chapter}\n"
            
            return suggestion
        
        return f"建议：检查世界观设定一致性"
    
    def _generate_ooc_fix(self, issue: Dict[str, Any], context: Optional[str]) -> str:
        """生成OOC修复建议"""
        description = issue.get("description", "")
        details = issue.get("details", {})
        chapter = issue.get("chapter", 0)
        
        entity = details.get("entity", "")
        dialogue = details.get("dialogue", "")
        
        suggestion = f"[FIX] OOC修复建议\n\n"
        suggestion += f"**问题**：{description}\n\n"
        suggestion += f"**方案1**：修改对话内容\n"
        suggestion += f"  - 将\"{dialogue}\"修改为符合角色人设的表达\n"
        suggestion += f"  - 建议风格：沉稳、简洁、理性\n\n"
        suggestion += f"**方案2**：添加情绪状态说明\n"
        suggestion += f"  - 如果角色情绪特殊，可以添加心理描写\n"
        suggestion += f"  - 例如：\"{entity}此刻心急如焚，忍不住脱口而出...\"\n\n"
        suggestion += f"**方案3**：调整场景设置\n"
        suggestion += f"  - 如果对话在特殊场合，可以调整场景\n"
        suggestion += f"  - 使对话更符合当时情境\n"
        
        return suggestion
    
    def _generate_time_transition(self, days: int) -> str:
        """生成时间过渡文本"""
        if days <= 3:
            return f"接下来的几天里，李天专心修炼，修为稳步提升。"
        elif days <= 7:
            return f"随后的{days}天，李天闭关修炼，沉浸在灵气流转之中。" \
                   f"期间只短暂外出补充物资，便又回到修炼状态。"
        else:
            return f"转眼间，{days}天过去了。\n\n" \
                   f"这{days}天里，李天经历了{self._get_events_during_days(days)}。" \
                   f"修为从练气2层提升到了练气3层，实力大增。\n\n" \
                   f"当他再次睁开眼时，已经是末世第{days}天了。"
    
    def _get_reason_for_level_drop(self) -> str:
        """获取修为倒退原因"""
        reasons = [
            "在战斗中受到重伤，元气大伤",
            "为救人献祭了部分修为",
            "被封印压制，暂时无法发挥",
            "修炼出错，走火入魔",
            "施展禁术消耗了修为",
        ]
        import random
        return random.choice(reasons)
    
    def _get_events_during_days(self, days: int) -> str:
        """获取期间发生的事件"""
        if days <= 3:
            return "刻苦修炼"
        elif days <= 7:
            return "修炼和小规模战斗"
        else:
            return "修炼、探索遗迹、击杀妖兽"
    
    def _generate_foreshadowing_payoff(self, fs_desc: str, chapter: int) -> str:
        """生成伏笔回收文本"""
        # 简化版本，实际应该用LLM生成
        if "玉佩" in fs_desc:
            return f"李天握紧玉佩，感受到其中蕴含的古老传承。" \
                   f"\"原来，这就是玉佩的秘密...\" 他喃喃自语。"
        elif "失踪" in fs_desc:
            return f"终于，李天找到了关于林雪儿失踪的线索。" \
                   f"\"原来她被...\" 他眼神一凝。"
        else:
            return f"这一刻，李天终于明白了{fs_desc}的真相。"
    
    def auto_fix_chapter(self, chapter: int, issues: List[Dict[str, Any]]) -> str:
        """生成章节的完整修复方案
        
        Args:
            chapter: 章节号
            issues: 问题列表
        
        Returns:
            完整修复方案（Markdown格式）
        """
        if not issues:
            return f"# 第{chapter}章修复方案\n\n✅ 未发现一致性问题，无需修复。"
        
        md = f"# 第{chapter}章修复方案\n\n"
        md += f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**问题总数**：{len(issues)}\n\n"
        md += "---\n\n"
        
        for i, issue in enumerate(issues, 1):
            md += f"## 问题{i}：{issue.get('description', '未知问题')}\n\n"
            md += self.generate_fix_suggestion(issue)
            md += "\n---\n\n"
        
        return md
