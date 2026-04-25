#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态变更确认模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from forgeai_modules.state_change_confirmer import StateChangeConfirmer


class TestStateChangeConfirmer:
    """StateChangeConfirmer测试"""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()
        
        forgeai_dir = project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        
        change_logs_dir = forgeai_dir / "change_logs"
        change_logs_dir.mkdir(parents=True)
        
        return project
    
    @pytest.fixture
    def mock_config(self, temp_project):
        """创建模拟配置"""
        config = Mock()
        config.project_root = temp_project
        return config
    
    @pytest.fixture
    def confirmer(self, mock_config):
        """创建StateChangeConfirmer实例"""
        return StateChangeConfirmer(config=mock_config)
    
    @pytest.fixture
    def sample_changes(self):
        """创建示例状态变更列表"""
        return [
            {
                "entity": "李天",
                "field": "location",
                "old_value": "青州城",
                "new_value": "青云山",
                "chapter": 10,
                "evidence": "李天离开青州城，前往青云山",
                "severity": "medium",
                "change_type": "location"
            },
            {
                "entity": "李天",
                "field": "cultivation_level",
                "old_value": "筑基中期",
                "new_value": "筑基后期",
                "chapter": 10,
                "evidence": "李天突破境界",
                "severity": "high",
                "change_type": "power"
            },
            {
                "entity": "李天",
                "field": "inventory",
                "old_value": "无",
                "new_value": "灵石x10",
                "chapter": 10,
                "evidence": "李天获得战利品",
                "severity": "low",
                "change_type": "inventory"
            }
        ]
    
    def test_init(self, mock_config):
        """测试初始化"""
        confirmer = StateChangeConfirmer(config=mock_config)
        
        assert confirmer.config == mock_config
    
    def test_display_state_changes(self, confirmer, sample_changes):
        """测试显示状态变更"""
        output = confirmer.display_state_changes(sample_changes)
        
        assert "检测到状态变更" in output
        assert "李天" in output
        assert "青州城" in output
        assert "青云山" in output
        assert "筑基中期" in output
        assert "筑基后期" in output
    
    def test_display_state_changes_with_type_hints(self, confirmer, sample_changes):
        """测试显示带类型提示的状态变更"""
        output = confirmer.display_state_changes(sample_changes)
        
        # 检查变更类型提示
        assert "位置变更" in output
        assert "境界变更" in output
        assert "物品变更" in output
    
    def test_display_state_changes_empty(self, confirmer):
        """测试显示空变更列表"""
        output = confirmer.display_state_changes([])
        
        # 应该能正常处理空列表
        assert "检测到状态变更" in output
    
    def test_prompt_user_confirmation(self, confirmer, sample_changes):
        """测试提示用户确认"""
        prompt = confirmer.prompt_user_confirmation(sample_changes)
        
        assert "请确认是否写入" in prompt
        assert "all" in prompt
        assert "none" in prompt
        assert "select" in prompt
        assert "review" in prompt
        assert "3 个状态变更" in prompt
    
    def test_process_user_input_all(self, confirmer, sample_changes):
        """测试处理用户输入 'all'"""
        result = confirmer.process_user_input("all", sample_changes)
        
        assert result["action"] == "write_all"
        assert "写入全部" in result["message"]
        assert result["changes_to_write"] == sample_changes
        assert result["changes_to_skip"] == []
    
    def test_process_user_input_none(self, confirmer, sample_changes):
        """测试处理用户输入 'none'"""
        result = confirmer.process_user_input("none", sample_changes)
        
        assert result["action"] == "skip_all"
        assert "跳过全部" in result["message"]
        assert result["changes_to_write"] == []
        assert result["changes_to_skip"] == sample_changes
    
    def test_process_user_input_select(self, confirmer, sample_changes):
        """测试处理用户输入 'select'"""
        result = confirmer.process_user_input("select", sample_changes)
        
        assert result["action"] == "selective"
        assert "选择性确认模式" in result["message"]
    
    def test_process_user_input_review(self, confirmer, sample_changes):
        """测试处理用户输入 'review'"""
        result = confirmer.process_user_input("review", sample_changes)
        
        assert result["action"] == "review"
        assert "详细变更" in result["message"]
        assert "detailed_changes" in result
    
    def test_process_user_input_invalid(self, confirmer, sample_changes):
        """测试处理无效用户输入"""
        result = confirmer.process_user_input("invalid", sample_changes)
        
        assert result["action"] == "invalid"
        assert "无效输入" in result["message"]
    
    def test_process_user_input_case_insensitive(self, confirmer, sample_changes):
        """测试用户输入不区分大小写"""
        result1 = confirmer.process_user_input("ALL", sample_changes)
        result2 = confirmer.process_user_input("NONE", sample_changes)
        
        assert result1["action"] == "write_all"
        assert result2["action"] == "skip_all"
    
    def test_selective_confirmation(self, confirmer, sample_changes):
        """测试选择性确认"""
        result = confirmer.selective_confirmation(sample_changes)
        
        assert "changes_to_write" in result
        assert "changes_to_skip" in result
        assert "note" in result
    
    def test_generate_detailed_report(self, confirmer, sample_changes):
        """测试生成详细报告"""
        report = confirmer._generate_detailed_report(sample_changes)
        
        assert "状态变更详细报告" in report
        assert "LOCATION" in report or "location" in report.lower()
        assert "POWER" in report or "power" in report.lower()
    
    def test_generate_detailed_report_grouped(self, confirmer, sample_changes):
        """测试详细报告按类型分组"""
        report = confirmer._generate_detailed_report(sample_changes)
        
        # 应该按变更类型分组显示
        assert "变更" in report
    
    def test_generate_summary(self, confirmer, sample_changes):
        """测试生成变更摘要"""
        summary = confirmer.generate_summary(sample_changes)
        
        assert "3 个状态变更" in summary
        assert "location" in summary.lower() or "位置" in summary
    
    def test_generate_summary_empty(self, confirmer):
        """测试空变更摘要"""
        summary = confirmer.generate_summary([])
        
        assert "无状态变更" in summary
    
    def test_save_change_log(self, confirmer, sample_changes, temp_project):
        """测试保存变更日志"""
        output_file = confirmer.save_change_log(
            changes=sample_changes,
            chapter=10,
            project_root=temp_project
        )
        
        assert output_file.exists()
        assert "ch010_changes.json" in str(output_file)
        
        # 验证文件内容
        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data["chapter"] == 10
        assert len(saved_data["changes"]) == 3


class TestStateChangeConfirmerEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def confirmer(self):
        """创建确认器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        return StateChangeConfirmer(config=config)
    
    def test_display_changes_with_missing_fields(self, confirmer):
        """测试显示缺少字段的状态变更"""
        changes = [
            {
                "entity": "未知实体",
                # 缺少其他字段
            }
        ]
        
        output = confirmer.display_state_changes(changes)
        
        # 应该能正常处理，不抛出异常
        assert "未知实体" in output
    
    def test_process_user_input_whitespace(self, confirmer):
        """测试处理带空格的用户输入"""
        changes = []
        
        result = confirmer.process_user_input("  all  ", changes)
        
        assert result["action"] == "write_all"
    
    def test_generate_detailed_report_empty(self, confirmer):
        """测试空变更的详细报告"""
        report = confirmer._generate_detailed_report([])
        
        assert "状态变更详细报告" in report
    
    def test_generate_summary_single_change(self, confirmer):
        """测试单个变更的摘要"""
        changes = [
            {
                "entity": "李天",
                "change_type": "location"
            }
        ]
        
        summary = confirmer.generate_summary(changes)
        
        assert "1 个状态变更" in summary


class TestChangeTypes:
    """变更类型测试"""
    
    @pytest.fixture
    def confirmer(self):
        """创建确认器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        return StateChangeConfirmer(config=config)
    
    def test_location_change_hint(self, confirmer):
        """测试位置变更提示"""
        changes = [{
            "entity": "李天",
            "field": "location",
            "change_type": "location"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "位置变更" in output
        assert "移动路径" in output
    
    def test_power_change_hint(self, confirmer):
        """测试境界变更提示"""
        changes = [{
            "entity": "李天",
            "field": "cultivation",
            "change_type": "power"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "境界变更" in output
        assert "突破描写" in output
    
    def test_inventory_change_hint(self, confirmer):
        """测试物品变更提示"""
        changes = [{
            "entity": "李天",
            "field": "items",
            "change_type": "inventory"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "物品变更" in output
        assert "来源" in output or "去向" in output
    
    def test_relationship_change_hint(self, confirmer):
        """测试关系变更提示"""
        changes = [{
            "entity": "李天",
            "field": "relationship",
            "change_type": "relationship"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "关系变更" in output


class TestSeverityLevels:
    """严重度级别测试"""
    
    @pytest.fixture
    def confirmer(self):
        """创建确认器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        return StateChangeConfirmer(config=config)
    
    def test_display_critical_severity(self, confirmer):
        """测试显示critical严重度"""
        changes = [{
            "entity": "李天",
            "severity": "critical",
            "change_type": "power"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "critical" in output.lower()
    
    def test_display_high_severity(self, confirmer):
        """测试显示high严重度"""
        changes = [{
            "entity": "李天",
            "severity": "high",
            "change_type": "location"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "high" in output.lower()
    
    def test_display_medium_severity(self, confirmer):
        """测试显示medium严重度"""
        changes = [{
            "entity": "李天",
            "severity": "medium",
            "change_type": "inventory"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        assert "medium" in output.lower()


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def full_project(self, tmp_path):
        """创建完整项目"""
        project = tmp_path / "full_project"
        project.mkdir()
        
        forgeai_dir = project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        
        return project
    
    @pytest.fixture
    def confirmer(self, full_project):
        """创建确认器"""
        config = Mock()
        config.project_root = full_project
        return StateChangeConfirmer(config=config)
    
    @pytest.fixture
    def full_changes(self):
        """创建完整变更列表"""
        return [
            {
                "entity": "李天",
                "field": "location",
                "old_value": "青州城",
                "new_value": "青云山",
                "chapter": 10,
                "evidence": "李天前往青云山",
                "severity": "medium",
                "change_type": "location"
            },
            {
                "entity": "李天",
                "field": "cultivation_level",
                "old_value": "筑基中期",
                "new_value": "筑基后期",
                "chapter": 10,
                "evidence": "突破成功",
                "severity": "high",
                "change_type": "power"
            },
            {
                "entity": "李天",
                "field": "inventory",
                "old_value": "无",
                "new_value": "灵石x10",
                "chapter": 10,
                "evidence": "战利品",
                "severity": "low",
                "change_type": "inventory"
            }
        ]
    
    def test_full_confirmation_workflow(self, confirmer, full_changes, full_project):
        """测试完整确认工作流"""
        # 1. 显示状态变更
        display = confirmer.display_state_changes(full_changes)
        assert len(display) > 0
        
        # 2. 提示确认
        prompt = confirmer.prompt_user_confirmation(full_changes)
        assert "请确认" in prompt
        
        # 3. 处理用户输入
        result = confirmer.process_user_input("all", full_changes)
        assert result["action"] == "write_all"
        
        # 4. 保存变更日志
        output_file = confirmer.save_change_log(
            changes=full_changes,
            chapter=10,
            project_root=full_project
        )
        assert output_file.exists()
    
    def test_selective_workflow(self, confirmer, full_changes, full_project):
        """测试选择性确认工作流"""
        # 1. 用户选择选择性确认
        result = confirmer.process_user_input("select", full_changes)
        assert result["action"] == "selective"
        
        # 2. 进入选择性确认
        select_result = confirmer.selective_confirmation(full_changes)
        assert "changes_to_write" in select_result
        
        # 3. 保存部分变更
        output_file = confirmer.save_change_log(
            changes=select_result["changes_to_write"],
            chapter=10,
            project_root=full_project
        )
        assert output_file.exists()
    
    def test_review_workflow(self, confirmer, full_changes):
        """测试查看详细变更工作流"""
        # 1. 用户选择查看详细变更
        result = confirmer.process_user_input("review", full_changes)
        assert result["action"] == "review"
        
        # 2. 显示详细报告
        detailed = result["detailed_changes"]
        assert len(detailed) > 0
        
        # 3. 生成摘要
        summary = confirmer.generate_summary(full_changes)
        assert "状态变更" in summary


class TestOutputFormatting:
    """输出格式化测试"""
    
    @pytest.fixture
    def confirmer(self):
        """创建确认器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        return StateChangeConfirmer(config=config)
    
    def test_display_format_structure(self, confirmer):
        """测试显示格式结构"""
        changes = [{
            "entity": "李天",
            "field": "location",
            "old_value": "A",
            "new_value": "B",
            "chapter": 10,
            "evidence": "证据",
            "severity": "medium",
            "change_type": "location"
        }]
        
        output = confirmer.display_state_changes(changes)
        
        # 检查输出结构
        assert "=" in output  # 分隔线
        assert "变更 1/1" in output  # 变更计数
        assert "实体" in output
        assert "字段" in output
        assert "旧值" in output
        assert "新值" in output
        assert "章节" in output
        assert "证据" in output
        assert "严重度" in output
    
    def test_summary_format(self, confirmer):
        """测试摘要格式"""
        changes = [
            {"change_type": "location"},
            {"change_type": "power"},
            {"change_type": "location"}
        ]
        
        summary = confirmer.generate_summary(changes)
        
        # 检查摘要格式
        assert "共检测到" in summary
        assert "3 个状态变更" in summary
