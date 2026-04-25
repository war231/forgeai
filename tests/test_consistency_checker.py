#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一致性检查器测试"""

import pytest
import json
from pathlib import Path

from forgeai_modules.consistency_checker import (
    ConsistencyChecker, ConsistencyIssue, ConsistencyReport
)


class TestConsistencyIssue:
    """一致性问题数据类测试"""

    def test_create_issue(self):
        """创建问题"""
        issue = ConsistencyIssue(
            issue_type="timeline",
            severity="error",
            chapter=10,
            description="时间回跳",
            details={"prev": 100, "curr": 90},
            suggestion="添加闪回标注"
        )

        assert issue.issue_type == "timeline"
        assert issue.severity == "error"
        assert issue.chapter == 10
        assert issue.details["prev"] == 100


class TestConsistencyReport:
    """一致性报告测试"""

    def test_create_report(self):
        """创建报告"""
        report = ConsistencyReport(
            target_chapter=10,
            check_time="2024-01-01T00:00:00",
            total_issues=0,
            errors=0,
            warnings=0
        )

        assert report.target_chapter == 10
        assert report.total_issues == 0
        assert len(report.issues) == 0

    def test_report_to_dict(self):
        """转换为字典"""
        report = ConsistencyReport(
            target_chapter=10,
            check_time="2024-01-01T00:00:00",
            total_issues=1,
            errors=1,
            warnings=0
        )
        report.issues.append(ConsistencyIssue(
            issue_type="timeline",
            severity="error",
            chapter=10,
            description="测试问题"
        ))

        d = report.to_dict()

        assert d["target_chapter"] == 10
        assert d["total_issues"] == 1
        assert len(d["issues"]) == 1


class TestConsistencyCheckerInit:
    """检查器初始化测试"""

    def test_init_paths(self, temp_project):
        """初始化路径"""
        checker = ConsistencyChecker(temp_project)

        assert checker.project_root == temp_project
        assert checker.forgeai_dir == temp_project / ".forgeai"
        assert checker.state_file == temp_project / ".forgeai" / "state.json"


class TestCheckChapter:
    """章节检查测试"""

    def test_check_chapter_empty_state(self, temp_project):
        """空状态检查"""
        checker = ConsistencyChecker(temp_project)
        report = checker.check_chapter(1)

        assert report.target_chapter == 1
        assert report.total_issues == 0

    def test_check_chapter_timeline_scope(self, temp_project):
        """仅检查时间线"""
        checker = ConsistencyChecker(temp_project)
        report = checker.check_chapter(1, check_scope="timeline")

        assert report.target_chapter == 1

    def test_check_chapter_full_scope(self, temp_project):
        """完整检查"""
        checker = ConsistencyChecker(temp_project)
        report = checker.check_chapter(1, check_scope="full")

        assert report.target_chapter == 1


class TestCheckTimelineConsistency:
    """时间线一致性检查测试"""

    def test_check_timeline_large_span(self, temp_project):
        """大跨度时间警告"""
        # 创建状态文件
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({
            "timeline": {
                "anchors": [
                    {"chapter": 1, "anchor": "末世第1天"},
                    {"chapter": 2, "anchor": "末世第20天"}
                ],
                "countdowns": []
            }
        }), encoding="utf-8")

        checker = ConsistencyChecker(temp_project)
        issues = checker._check_timeline_consistency(2)

        assert len(issues) > 0
        assert any(i.issue_type == "timeline" for i in issues)

    def test_check_timeline_countdown_inconsistent(self, temp_project):
        """倒计时不一致"""
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({
            "timeline": {
                "anchors": [],
                "countdowns": [
                    {
                        "name": "物资耗尽",
                        "start_chapter": 1,
                        "end_chapter": 20,
                        "value": "D-5"
                    }
                ]
            }
        }), encoding="utf-8")

        checker = ConsistencyChecker(temp_project)
        issues = checker._check_timeline_consistency(10)

        # D-5 意味着5天后到期，但实际在第20章才到期
        assert any(i.severity == "error" for i in issues)


class TestParseTimeAnchor:
    """时间锚点解析测试"""

    def test_parse_time_anchor_basic(self):
        """基本解析"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_time_anchor("末世第1天") == 1
        assert checker._parse_time_anchor("末世第100天") == 100
        assert checker._parse_time_anchor("第50天") == 50

    def test_parse_time_anchor_none(self):
        """无法解析"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_time_anchor("清晨") is None
        assert checker._parse_time_anchor("") is None


class TestCheckCharacterConsistency:
    """角色一致性检查测试"""

    def test_check_character_level_regression(self, temp_project):
        """修为等级倒退"""
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({
            "entities": {},
            "state_changes": [
                {"entity_id": "李天", "chapter": 1, "new_state": "练气5层"},
                {"entity_id": "李天", "chapter": 2, "new_state": "练气1层"}
            ]
        }), encoding="utf-8")

        checker = ConsistencyChecker(temp_project)
        issues = checker._check_character_consistency(2)

        assert len(issues) > 0
        assert any("倒退" in i.description for i in issues)

    def test_check_character_absent(self, temp_project):
        """角色长期未出场"""
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({
            "entities": {
                "张三": {"last_appearance": 1}
            },
            "state_changes": []
        }), encoding="utf-8")

        checker = ConsistencyChecker(temp_project)
        issues = checker._check_character_consistency(10)

        assert any(i.severity == "info" for i in issues)


class TestCheckWorldviewConsistency:
    """世界观一致性检查测试"""

    def test_check_foreshadowing_overdue(self, temp_project):
        """伏笔超期未回收"""
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({
            "foreshadowings": {
                "active": [
                    {
                        "id": "fs1",
                        "description": "神秘玉佩",
                        "expected_payoff_chapter": 5
                    }
                ]
            }
        }), encoding="utf-8")

        checker = ConsistencyChecker(temp_project)
        issues = checker._check_worldview_consistency(15)

        assert len(issues) > 0
        assert any("超期" in i.description for i in issues)


class TestParseCultivationLevel:
    """修为等级解析测试"""

    def test_parse_cultivation_lingqi(self):
        """练气期"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_cultivation_level("练气1层") == 10
        assert checker._parse_cultivation_level("练气5层") == 50
        assert checker._parse_cultivation_level("练气10层") == 100

    def test_parse_cultivation_zhuji(self):
        """筑基期"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_cultivation_level("筑基初期") == 100
        assert checker._parse_cultivation_level("筑基中期") == 100

    def test_parse_cultivation_jindan(self):
        """金丹期"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_cultivation_level("金丹期") == 200

    def test_parse_cultivation_yuanying(self):
        """元婴期"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_cultivation_level("元婴期") == 1000

    def test_parse_cultivation_none(self):
        """无法解析"""
        checker = ConsistencyChecker.__new__(ConsistencyChecker)

        assert checker._parse_cultivation_level("") is None
        assert checker._parse_cultivation_level("未知") is None


class TestBatchCheck:
    """批量检查测试"""

    def test_batch_check_basic(self, temp_project):
        """基本批量检查"""
        checker = ConsistencyChecker(temp_project)
        result = checker.batch_check(1, 3)

        assert result["start_chapter"] == 1
        assert result["end_chapter"] == 3
        assert result["total_chapters"] == 3
        assert len(result["reports"]) == 3


class TestGenerateReport:
    """报告生成测试"""

    def test_generate_markdown_report(self, temp_project):
        """生成 Markdown 报告"""
        checker = ConsistencyChecker(temp_project)

        report = ConsistencyReport(
            target_chapter=10,
            check_time="2024-01-01T00:00:00",
            total_issues=1,
            errors=1,
            warnings=0
        )
        report.issues.append(ConsistencyIssue(
            issue_type="timeline",
            severity="error",
            chapter=10,
            description="测试错误",
            suggestion="测试建议"
        ))

        md = checker.generate_report(report, output_format="markdown")

        assert "# 一致性检查报告" in md
        assert "测试错误" in md
        assert "测试建议" in md

    def test_generate_json_report(self, temp_project):
        """生成 JSON 报告"""
        checker = ConsistencyChecker(temp_project)

        report = ConsistencyReport(
            target_chapter=10,
            check_time="2024-01-01T00:00:00",
            total_issues=0,
            errors=0,
            warnings=0
        )

        json_str = checker.generate_report(report, output_format="json")

        assert "target_chapter" in json_str
        assert "10" in json_str

    def test_generate_report_no_issues(self, temp_project):
        """无问题报告"""
        checker = ConsistencyChecker(temp_project)

        report = ConsistencyReport(
            target_chapter=10,
            check_time="2024-01-01T00:00:00",
            total_issues=0,
            errors=0,
            warnings=0
        )

        md = checker._generate_markdown_report(report)

        assert "未发现一致性问题" in md
