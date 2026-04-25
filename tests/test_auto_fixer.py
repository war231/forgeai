#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动修复建议模块测试"""

import pytest
from pathlib import Path

from forgeai_modules.auto_fixer import AutoFixer


class TestAutoFixerInit:
    """初始化测试"""

    def test_init_basic(self, temp_project):
        """基本初始化"""
        fixer = AutoFixer(temp_project)

        assert fixer.project_root == temp_project
        assert fixer.llm_client is None

    def test_init_with_llm(self, temp_project):
        """带 LLM 客户端"""
        mock_client = object()
        fixer = AutoFixer(temp_project, llm_client=mock_client)

        assert fixer.llm_client == mock_client


class TestGenerateFixSuggestion:
    """修复建议生成测试"""

    def test_timeline_suggestion(self, temp_project):
        """时间线问题建议"""
        fixer = AutoFixer(temp_project)

        issue = {
            "issue_type": "timeline",
            "severity": "warning",
            "chapter": 10,
            "description": "时间跨度过大",
            "details": {
                "days_diff": 15,
                "prev_anchor": "末世第1天",
                "current_anchor": "末世第16天"
            }
        }

        suggestion = fixer.generate_fix_suggestion(issue)

        assert "[FIX]" in suggestion
        assert "时间跨度" in suggestion

    def test_character_suggestion(self, temp_project):
        """角色问题建议"""
        fixer = AutoFixer(temp_project)

        issue = {
            "issue_type": "character",
            "severity": "warning",
            "chapter": 5,
            "description": "角色李天修为等级异常倒退",
            "details": {
                "entity": "李天",
                "prev_level": 50,
                "current_level": 10
            }
        }

        suggestion = fixer.generate_fix_suggestion(issue)

        assert "[FIX]" in suggestion
        assert "修为倒退" in suggestion

    def test_worldview_suggestion(self, temp_project):
        """世界观问题建议"""
        fixer = AutoFixer(temp_project)

        issue = {
            "issue_type": "worldview",
            "severity": "warning",
            "chapter": 20,
            "description": "伏笔\"神秘玉佩\"已超期10章未回收",
            "details": {
                "foreshadowing_id": "fs1",
                "description": "神秘玉佩",
                "expected_payoff": 10,
                "overdue_chapters": 10
            }
        }

        suggestion = fixer.generate_fix_suggestion(issue)

        assert "[FIX]" in suggestion
        assert "伏笔" in suggestion

    def test_ooc_suggestion(self, temp_project):
        """OOC 问题建议"""
        fixer = AutoFixer(temp_project)

        issue = {
            "issue_type": "ooc",
            "severity": "warning",
            "chapter": 5,
            "description": "角色李天可能存在OOC对话",
            "details": {
                "entity": "李天",
                "dialogue": "卧槽，这太离谱了"
            }
        }

        suggestion = fixer.generate_fix_suggestion(issue)

        assert "[FIX]" in suggestion
        assert "OOC" in suggestion

    def test_unknown_issue_type(self, temp_project):
        """未知问题类型"""
        fixer = AutoFixer(temp_project)

        issue = {
            "issue_type": "unknown",
            "description": "未知问题"
        }

        suggestion = fixer.generate_fix_suggestion(issue)

        assert "建议" in suggestion


class TestTimelineFix:
    """时间线修复测试"""

    def test_large_time_span_fix(self, temp_project):
        """大跨度时间修复"""
        fixer = AutoFixer(temp_project)

        issue = {
            "description": "时间跨度过大",
            "chapter": 10,
            "details": {
                "days_diff": 20,
                "prev_anchor": "末世第1天",
                "current_anchor": "末世第21天"
            }
        }

        suggestion = fixer._generate_timeline_fix(issue, None)

        assert "过渡段落" in suggestion
        assert "20天" in suggestion

    def test_countdown_inconsistent_fix(self, temp_project):
        """倒计时不一致修复"""
        fixer = AutoFixer(temp_project)

        issue = {
            "description": "倒计时不一致",
            "chapter": 10,
            "details": {
                "countdown_name": "物资耗尽",
                "expected_end": 5,
                "actual_end": 15
            }
        }

        suggestion = fixer._generate_timeline_fix(issue, None)

        assert "倒计时" in suggestion
        assert "方案" in suggestion


class TestCharacterFix:
    """角色修复测试"""

    def test_level_drop_fix(self, temp_project):
        """修为倒退修复"""
        fixer = AutoFixer(temp_project)

        issue = {
            "description": "角色李天修为等级异常倒退",
            "chapter": 5,
            "details": {
                "entity": "李天",
                "prev_level": 50,
                "current_level": 10
            }
        }

        suggestion = fixer._generate_character_fix(issue, None)

        assert "修为倒退" in suggestion
        assert "方案" in suggestion

    def test_character_absent_fix(self, temp_project):
        """角色消失修复"""
        fixer = AutoFixer(temp_project)

        issue = {
            "description": "角色张三已10章未出场",
            "chapter": 15,
            "details": {
                "entity": "张三",
                "chapters_absent": 10
            }
        }

        suggestion = fixer._generate_character_fix(issue, None)

        assert "消失" in suggestion or "出场" in suggestion


class TestWorldviewFix:
    """世界观修复测试"""

    def test_foreshadowing_overdue_fix(self, temp_project):
        """伏笔超期修复"""
        fixer = AutoFixer(temp_project)

        issue = {
            "description": "伏笔\"神秘玉佩\"已超期10章未回收",
            "chapter": 20,
            "details": {
                "foreshadowing_id": "fs1",
                "description": "神秘玉佩",
                "expected_payoff": 10,
                "overdue_chapters": 10
            }
        }

        suggestion = fixer._generate_worldview_fix(issue, None)

        assert "伏笔" in suggestion
        assert "回收" in suggestion


class TestOOCFix:
    """OOC 修复测试"""

    def test_ooc_dialogue_fix(self, temp_project):
        """OOC 对话修复"""
        fixer = AutoFixer(temp_project)

        issue = {
            "description": "角色李天可能存在OOC对话",
            "chapter": 5,
            "details": {
                "entity": "李天",
                "dialogue": "卧槽"
            }
        }

        suggestion = fixer._generate_ooc_fix(issue, None)

        assert "OOC" in suggestion
        assert "修改对话" in suggestion


class TestTimeTransition:
    """时间过渡文本生成测试"""

    def test_short_transition(self, temp_project):
        """短时间过渡"""
        fixer = AutoFixer(temp_project)

        text = fixer._generate_time_transition(2)

        assert "修炼" in text or "天" in text

    def test_medium_transition(self, temp_project):
        """中等时间过渡"""
        fixer = AutoFixer(temp_project)

        text = fixer._generate_time_transition(5)

        assert "5天" in text or "天" in text

    def test_long_transition(self, temp_project):
        """长时间过渡"""
        fixer = AutoFixer(temp_project)

        text = fixer._generate_time_transition(15)

        assert "15天" in text or "天" in text


class TestForeshadowingPayoff:
    """伏笔回收文本生成测试"""

    def test_jade_pendant_payoff(self, temp_project):
        """玉佩伏笔"""
        fixer = AutoFixer(temp_project)

        text = fixer._generate_foreshadowing_payoff("神秘玉佩", 10)

        assert "玉佩" in text

    def test_missing_person_payoff(self, temp_project):
        """失踪伏笔"""
        fixer = AutoFixer(temp_project)

        text = fixer._generate_foreshadowing_payoff("林雪儿失踪", 10)

        assert "失踪" in text or "线索" in text

    def test_generic_payoff(self, temp_project):
        """通用伏笔"""
        fixer = AutoFixer(temp_project)

        text = fixer._generate_foreshadowing_payoff("某个秘密", 10)

        assert "真相" in text


class TestAutoFixChapter:
    """章节修复方案测试"""

    def test_auto_fix_no_issues(self, temp_project):
        """无问题"""
        fixer = AutoFixer(temp_project)

        md = fixer.auto_fix_chapter(1, [])

        assert "未发现一致性问题" in md

    def test_auto_fix_with_issues(self, temp_project):
        """有问题"""
        fixer = AutoFixer(temp_project)

        issues = [
            {
                "issue_type": "timeline",
                "description": "时间跨度过大",
                "chapter": 1,
                "details": {"days_diff": 10}
            }
        ]

        md = fixer.auto_fix_chapter(1, issues)

        assert "# 第1章修复方案" in md
        assert "问题总数" in md

    def test_auto_fix_multiple_issues(self, temp_project):
        """多个问题"""
        fixer = AutoFixer(temp_project)

        issues = [
            {"issue_type": "timeline", "description": "问题1", "chapter": 1, "details": {}},
            {"issue_type": "character", "description": "问题2", "chapter": 1, "details": {}},
        ]

        md = fixer.auto_fix_chapter(1, issues)

        assert "问题1" in md
        assert "问题2" in md
