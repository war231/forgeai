#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时间线管理器测试"""

import pytest
from pathlib import Path

from forgeai_modules.timeline_manager import TimelineManager


class TestExtractTimeAnchor:
    """时间锚点提取测试"""

    def test_extract_absolute_time_末世(self):
        """提取末世第N天"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("末世降临已经整整100天了")
        assert result["anchor"] == "末世第100天"
        assert result["type"] == "absolute"
        assert result["confidence"] >= 0.9

    def test_extract_absolute_time_修炼(self):
        """提取修炼第N年"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("修炼第5年，他终于突破了")
        assert result["anchor"] == "修炼第5年"
        assert result["type"] == "absolute"

    def test_extract_absolute_time_date(self):
        """提取具体日期"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("2024年3月15日，天气晴朗")
        assert "2024年3月15日" in result["anchor"]
        assert result["type"] == "absolute"

    def test_extract_relative_time_days(self):
        """提取相对时间（N天后）"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("三天后，他终于醒来了")
        assert result["anchor"] == "三天后"
        assert result["type"] == "relative"

    def test_extract_relative_time_hours(self):
        """提取相对时间（N小时后）"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("两小时后，战斗结束了")
        assert result["anchor"] == "两小时后"
        assert result["type"] == "relative"

    def test_extract_relative_time_第二天(self):
        """提取第二天"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("第二天清晨，阳光洒落")
        assert result["anchor"] == "第二天清晨"
        assert result["type"] == "relative"

    def test_extract_implicit_time_清晨(self):
        """提取隐含时间（清晨）"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("清晨，他开始了修炼")
        assert result["anchor"] == "清晨"
        assert result["type"] == "implicit"
        assert result["confidence"] < 0.9

    def test_extract_implicit_time_黄昏(self):
        """提取隐含时间（黄昏）"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("黄昏时分，战斗结束")
        assert result["anchor"] == "黄昏"
        assert result["type"] == "implicit"

    def test_extract_no_time(self):
        """无时间锚点"""
        mgr = TimelineManager()

        result = mgr.extract_time_anchor("他挥剑斩向敌人")
        assert result["anchor"] is None
        assert result["type"] == "none"
        assert result["confidence"] == 0.0


class TestCalculateTimeSpan:
    """时间跨度计算测试"""

    def test_calculate_span_same_day(self):
        """同一天"""
        mgr = TimelineManager()

        result = mgr.calculate_time_span("末世第100天", "末世第100天")
        assert result["span_days"] == 0
        assert result["span_type"] == "reasonable"
        assert result["needs_transition"] is False

    def test_calculate_span_one_day(self):
        """一天跨度"""
        mgr = TimelineManager()

        result = mgr.calculate_time_span("末世第100天", "末世第101天")
        assert result["span_days"] == 1
        assert result["span_type"] == "reasonable"
        assert result["needs_transition"] is False

    def test_calculate_span_large(self):
        """大跨度"""
        mgr = TimelineManager()

        result = mgr.calculate_time_span("末世第100天", "末世第110天")
        assert result["span_days"] == 10
        assert result["span_type"] == "large"
        assert result["needs_transition"] is True
        assert "过渡段落" in result["transition_suggestion"]

    def test_calculate_span_invalid_backwards(self):
        """时间回跳"""
        mgr = TimelineManager()

        result = mgr.calculate_time_span("末世第100天", "末世第90天")
        assert result["span_days"] == -10
        assert result["span_type"] == "invalid"
        assert "时间回跳" in result["transition_suggestion"]

    def test_calculate_span_no_numbers(self):
        """无数字"""
        mgr = TimelineManager()

        result = mgr.calculate_time_span("清晨", "黄昏")
        assert result["span_days"] == 0
        assert result["span_type"] == "unknown"


class TestUpdateCountdowns:
    """倒计时更新测试"""

    def test_update_countdown_basic(self):
        """基本倒计时更新"""
        mgr = TimelineManager()

        countdowns = [
            {"name": "物资耗尽", "current_value": "D-10", "initial_value": "D-10"}
        ]

        updated = mgr.update_countdowns(countdowns, span_days=3)

        assert updated[0]["current_value"] == "D-7"
        assert updated[0]["status"] == "active"

    def test_update_countdown_expired(self):
        """倒计时到期"""
        mgr = TimelineManager()

        countdowns = [
            {"name": "物资耗尽", "current_value": "D-2", "initial_value": "D-10"}
        ]

        updated = mgr.update_countdowns(countdowns, span_days=5)

        assert updated[0]["current_value"] == "D--3"
        assert updated[0]["status"] == "expired"
        assert "warning" in updated[0]

    def test_update_countdown_multiple(self):
        """多个倒计时"""
        mgr = TimelineManager()

        countdowns = [
            {"name": "物资耗尽", "current_value": "D-10", "initial_value": "D-10"},
            {"name": "敌人来袭", "current_value": "D-5", "initial_value": "D-5"},
        ]

        updated = mgr.update_countdowns(countdowns, span_days=3)

        assert updated[0]["current_value"] == "D-7"
        assert updated[1]["current_value"] == "D-2"

    def test_update_countdown_invalid_format(self):
        """无效格式保持不变"""
        mgr = TimelineManager()

        countdowns = [
            {"name": "测试", "current_value": "无效格式", "initial_value": "无效格式"}
        ]

        updated = mgr.update_countdowns(countdowns, span_days=3)

        assert updated[0]["current_value"] == "无效格式"


class TestCheckTimelineConsistency:
    """时间线一致性检查测试"""

    def test_check_consistency_valid(self):
        """正常时间线"""
        mgr = TimelineManager()

        warnings = mgr.check_timeline_consistency(
            "末世第100天",
            "末世第101天",
            []
        )

        assert len(warnings) == 0

    def test_check_consistency_time_jump_back(self):
        """时间回跳警告"""
        mgr = TimelineManager()

        warnings = mgr.check_timeline_consistency(
            "末世第100天",
            "末世第90天",
            []
        )

        assert len(warnings) > 0
        assert any(w["type"] == "time_jump_back" for w in warnings)
        assert any(w["severity"] == "critical" for w in warnings)

    def test_check_consistency_large_span(self):
        """大跨度警告"""
        mgr = TimelineManager()

        warnings = mgr.check_timeline_consistency(
            "末世第100天",
            "末世第110天",
            []
        )

        assert len(warnings) > 0
        assert any(w["type"] == "large_span_no_transition" for w in warnings)

    def test_check_consistency_countdown_expired(self):
        """倒计时到期警告"""
        mgr = TimelineManager()

        warnings = mgr.check_timeline_consistency(
            "末世第100天",
            "末世第110天",
            [{"name": "物资耗尽", "current_value": "D-5", "initial_value": "D-10"}]
        )

        assert any(w["type"] == "countdown_expired" for w in warnings)


class TestGenerateTimelineVisualization:
    """时间线可视化测试"""

    def test_generate_visualization_basic(self):
        """基本可视化生成"""
        mgr = TimelineManager()

        timeline_data = {
            "anchors": [
                {"chapter": 1, "anchor": "末世第1天", "event": "末世降临"},
                {"chapter": 2, "anchor": "末世第2天", "event": "首次战斗"},
                {"chapter": 3, "anchor": "末世第3天", "event": "获得物资"},
            ],
            "countdowns": [
                {"name": "物资耗尽", "current_value": "D-10"}
            ]
        }

        viz = mgr.generate_timeline_visualization(timeline_data)

        assert "```mermaid" in viz
        assert "timeline" in viz
        assert "末世第1天" in viz
        assert "末世降临" in viz
        assert "倒计时" in viz

    def test_generate_visualization_with_range(self):
        """带章节范围的可视化"""
        mgr = TimelineManager()

        timeline_data = {
            "anchors": [
                {"chapter": 1, "anchor": "末世第1天", "event": "事件1"},
                {"chapter": 2, "anchor": "末世第2天", "event": "事件2"},
                {"chapter": 3, "anchor": "末世第3天", "event": "事件3"},
                {"chapter": 4, "anchor": "末世第4天", "event": "事件4"},
            ],
            "countdowns": []
        }

        viz = mgr.generate_timeline_visualization(timeline_data, from_chapter=2, to_chapter=3)

        assert "末世第1天" not in viz
        assert "末世第2天" in viz
        assert "末世第3天" in viz
        assert "末世第4天" not in viz


class TestGetTimelineStatus:
    """时间线状态报告测试"""

    def test_get_status_basic(self):
        """基本状态报告"""
        mgr = TimelineManager()

        state = {
            "timeline": {
                "current_anchor": "末世第100天",
                "anchors": [
                    {"chapter": 1, "anchor": "末世第99天"},
                    {"chapter": 2, "anchor": "末世第100天"},
                ],
                "countdowns": [
                    {"name": "物资耗尽", "current_value": "D-10", "status": "active"}
                ],
                "warnings": []
            }
        }

        status = mgr.get_timeline_status(state)

        assert "末世第100天" in status
        assert "物资耗尽" in status

    def test_get_status_with_warnings(self):
        """带警告的状态报告"""
        mgr = TimelineManager()

        state = {
            "timeline": {
                "current_anchor": "末世第100天",
                "anchors": [],
                "countdowns": [],
                "warnings": [
                    {"severity": "critical", "message": "时间回跳警告"}
                ]
            }
        }

        status = mgr.get_timeline_status(state)

        assert "时间回跳警告" in status
        assert "🔴" in status

    def test_get_status_with_expired_countdown(self):
        """带过期倒计时的状态报告"""
        mgr = TimelineManager()

        state = {
            "timeline": {
                "current_anchor": "末世第100天",
                "anchors": [],
                "countdowns": [
                    {"name": "物资耗尽", "current_value": "D-0", "status": "expired"}
                ],
                "warnings": []
            }
        }

        status = mgr.get_timeline_status(state)

        assert "⚠️" in status


class TestExtractNumber:
    """数字提取测试"""

    def test_extract_number_basic(self):
        """基本数字提取"""
        mgr = TimelineManager()

        assert mgr._extract_number("末世第100天") == 100
        assert mgr._extract_number("修炼第5年") == 5
        assert mgr._extract_number("第10天") == 10

    def test_extract_number_none(self):
        """无数字"""
        mgr = TimelineManager()

        assert mgr._extract_number("清晨") is None
        assert mgr._extract_number("黄昏") is None
