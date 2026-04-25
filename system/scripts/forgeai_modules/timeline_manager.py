#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间线管理模块

功能：
- 时间锚点提取（规则+LLM）
- 时间跨度计算
- 倒计时追踪
- 时间线一致性检查
- 时间线可视化（Mermaid）
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .config import get_config, ForgeAIConfig


class TimelineManager:
    """时间线管理器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()

    # ==================== 时间锚点提取 ====================

    def extract_time_anchor(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取时间锚点
        
        Returns:
            {
                "anchor": "末世第100天",
                "type": "absolute",  # absolute / relative / implicit
                "confidence": 0.95,
                "evidence": "正文第5段：'末世降临已经整整100天了'"
            }
        """
        # 1. 绝对时间（末世第N天、修炼第N年、N月N日）
        absolute_patterns = [
            r"末世第(\d+)天",
            r"修炼第(\d+)年",
            r"(\d+)年(\d+)月(\d+)日",
            r"第(\d+)天",
        ]
        
        for pattern in absolute_patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    "anchor": match.group(0),
                    "type": "absolute",
                    "confidence": 0.95,
                    "evidence": f"匹配规则：{pattern}"
                }
        
        # 2. 相对时间（三天后、两小时后、半个月后）
        relative_patterns = [
            (r"(\d+)天后", "天"),
            (r"(\d+)小时后", "小时"),
            (r"半个月后", "天"),
            (r"第二天清晨", "天"),
            (r"第二天", "天"),
        ]
        
        for pattern, unit in relative_patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    "anchor": match.group(0),
                    "type": "relative",
                    "confidence": 0.90,
                    "evidence": f"匹配规则：{pattern}"
                }
        
        # 3. 隐含时间（通过事件推断）
        implicit_patterns = [
            r"清晨",
            r"黄昏",
            r"夜晚",
            r"黎明",
            r"正午",
        ]
        
        for pattern in implicit_patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    "anchor": match.group(0),
                    "type": "implicit",
                    "confidence": 0.70,
                    "evidence": f"匹配规则：{pattern}"
                }
        
        # 未找到时间锚点
        return {
            "anchor": None,
            "type": "none",
            "confidence": 0.0,
            "evidence": "未找到时间标识"
        }

    # ==================== 时间跨度计算 ====================

    def calculate_time_span(
        self, 
        previous_anchor: str, 
        current_anchor: str
    ) -> Dict[str, Any]:
        """
        计算两个时间锚点之间的跨度
        
        Returns:
            {
                "span_days": 3,
                "span_type": "reasonable",  # reasonable / large / invalid
                "needs_transition": true,
                "transition_suggestion": "需要补充：主角修炼3天的过渡段落"
            }
        """
        # 提取数字
        prev_num = self._extract_number(previous_anchor)
        curr_num = self._extract_number(current_anchor)
        
        if prev_num is None or curr_num is None:
            return {
                "span_days": 0,
                "span_type": "unknown",
                "needs_transition": False,
                "transition_suggestion": ""
            }
        
        # 计算跨度
        span_days = curr_num - prev_num
        
        # 判断跨度类型
        if span_days < 0:
            # 时间回跳
            return {
                "span_days": span_days,
                "span_type": "invalid",
                "needs_transition": False,
                "transition_suggestion": f"⚠️ 时间回跳：{previous_anchor} → {current_anchor}，需要闪回标注"
            }
        elif span_days == 0:
            # 同一天
            return {
                "span_days": 0,
                "span_type": "reasonable",
                "needs_transition": False,
                "transition_suggestion": ""
            }
        elif span_days <= 1:
            # 合理跨度（≤1天）
            return {
                "span_days": span_days,
                "span_type": "reasonable",
                "needs_transition": False,
                "transition_suggestion": ""
            }
        else:
            # 大跨度（>1天）
            return {
                "span_days": span_days,
                "span_type": "large",
                "needs_transition": True,
                "transition_suggestion": f"需要补充：经过{span_days}天的过渡段落，如'{span_days}天后，李天缓缓睁开双眼'"
            }

    def _extract_number(self, anchor: str) -> Optional[int]:
        """从时间锚点中提取数字"""
        match = re.search(r"\d+", anchor)
        if match:
            return int(match.group(0))
        return None

    # ==================== 倒计时追踪 ====================

    def update_countdowns(
        self, 
        countdowns: List[Dict[str, Any]], 
        span_days: int
    ) -> List[Dict[str, Any]]:
        """
        更新倒计时状态
        
        Args:
            countdowns: 倒计时列表 [{"name": "物资耗尽", "current_value": "D-10", "initial_value": "D-10"}]
            span_days: 时间跨度（天数）
        
        Returns:
            更新后的倒计时列表
        """
        updated = []
        
        for countdown in countdowns:
            # 提取当前值
            match = re.search(r"D-(\d+)", countdown.get("current_value", ""))
            if not match:
                updated.append(countdown)
                continue
            
            current_num = int(match.group(1))
            new_num = current_num - span_days
            
            # 更新倒计时
            updated_countdown = countdown.copy()
            updated_countdown["current_value"] = f"D-{new_num}"
            
            # 检查是否到期
            if new_num <= 0:
                updated_countdown["status"] = "expired"
                updated_countdown["warning"] = f"⚠️ 倒计时已到期：{countdown['name']}"
            else:
                updated_countdown["status"] = "active"
            
            updated.append(updated_countdown)
        
        return updated

    # ==================== 时间线一致性检查 ====================

    def check_timeline_consistency(
        self,
        previous_anchor: str,
        current_anchor: str,
        countdowns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        检查时间线一致性
        
        Returns:
            警告列表 [{"type": "time_jump_back", "severity": "critical", "message": "..."}]
        """
        warnings = []
        
        # 1. 计算时间跨度
        span_result = self.calculate_time_span(previous_anchor, current_anchor)
        
        # 2. 检查时间回跳
        if span_result["span_type"] == "invalid":
            warnings.append({
                "type": "time_jump_back",
                "severity": "critical",
                "message": f"时间回跳：{previous_anchor} → {current_anchor}，缺少闪回标注",
                "suggestion": "请添加闪回标注，如'回忆起三天前的一幕'"
            })
        
        # 3. 检查大跨度无过渡
        if span_result["span_type"] == "large":
            warnings.append({
                "type": "large_span_no_transition",
                "severity": "high",
                "message": f"时间跨度{span_result['span_days']}天，缺少过渡说明",
                "suggestion": span_result["transition_suggestion"]
            })
        
        # 4. 检查倒计时
        updated_countdowns = self.update_countdowns(countdowns, span_result["span_days"])
        for countdown in updated_countdowns:
            if countdown.get("status") == "expired":
                warnings.append({
                    "type": "countdown_expired",
                    "severity": "high",
                    "message": countdown.get("warning", f"倒计时已到期：{countdown['name']}"),
                    "suggestion": "请处理倒计时事件"
                })
        
        return warnings

    # ==================== 时间线可视化 ====================

    def generate_timeline_visualization(
        self, 
        timeline_data: Dict[str, Any],
        from_chapter: Optional[int] = None,
        to_chapter: Optional[int] = None
    ) -> str:
        """
        生成时间线可视化（Mermaid格式）
        
        Args:
            timeline_data: 时间线数据
            from_chapter: 起始章节（可选）
            to_chapter: 结束章节（可选）
        
        Returns:
            Mermaid图表字符串
        """
        anchors = timeline_data.get("anchors", [])
        countdowns = timeline_data.get("countdowns", [])
        
        # 过滤章节范围
        if from_chapter is not None and to_chapter is not None:
            anchors = [a for a in anchors if from_chapter <= a.get("chapter", 0) <= to_chapter]
        
        # 生成Mermaid图表
        lines = ["```mermaid", "timeline", f"    title 时间线（第{anchors[0]['chapter']}章-{anchors[-1]['chapter']}章）"]
        
        # 按时间分组
        current_section = None
        for anchor in anchors:
            anchor_text = anchor.get("anchor", "")
            event = anchor.get("event", "")
            chapter = anchor.get("chapter", 0)
            
            # 每个时间锚点一个section
            lines.append(f"    section {anchor_text}")
            lines.append(f"        {event} : 第{chapter}章")
        
        # 添加倒计时
        if countdowns:
            lines.append("    section 倒计时")
            for countdown in countdowns:
                name = countdown.get("name", "")
                value = countdown.get("current_value", "")
                lines.append(f"        {name} : {value}")
        
        lines.append("```")
        
        return "\n".join(lines)

    # ==================== 时间线查询 ====================

    def get_timeline_status(self, state: Dict[str, Any]) -> str:
        """
        生成时间线状态报告
        
        Returns:
            格式化的状态报告
        """
        timeline = state.get("timeline", {})
        current_anchor = timeline.get("current_anchor", "未设置")
        anchors = timeline.get("anchors", [])
        countdowns = timeline.get("countdowns", [])
        warnings = timeline.get("warnings", [])
        
        lines = [
            f"当前时间：{current_anchor}",
        ]
        
        # 上一章时间
        if len(anchors) >= 2:
            prev_anchor = anchors[-2].get("anchor", "")
            curr_anchor = anchors[-1].get("anchor", "")
            span_result = self.calculate_time_span(prev_anchor, curr_anchor)
            lines.append(f"上一章：{prev_anchor}（+{span_result['span_days']}天）")
        
        lines.append("")
        
        # 倒计时
        if countdowns:
            lines.append("倒计时：")
            for countdown in countdowns:
                name = countdown.get("name", "")
                value = countdown.get("current_value", "")
                status = countdown.get("status", "active")
                status_icon = "⚠️" if status == "expired" else "✅"
                lines.append(f"  {status_icon} {name}：{value}")
        
        lines.append("")
        
        # 警告
        if warnings:
            lines.append("时间线警告：")
            for warning in warnings:
                severity = warning.get("severity", "medium")
                message = warning.get("message", "")
                severity_icon = "🔴" if severity == "critical" else "🟡" if severity == "high" else "🟢"
                lines.append(f"  {severity_icon} {message}")
        
        return "\n".join(lines)
