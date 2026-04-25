#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大纲确认模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from forgeai_modules.outline_confirmer import OutlineConfirmer


class TestOutlineConfirmer:
    """OutlineConfirmer测试"""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()
        
        forgeai_dir = project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        
        execution_packages_dir = forgeai_dir / "execution_packages"
        execution_packages_dir.mkdir(parents=True)
        
        return project
    
    @pytest.fixture
    def mock_config(self, temp_project):
        """创建模拟配置"""
        config = Mock()
        config.project_root = temp_project
        return config
    
    @pytest.fixture
    def confirmer(self, mock_config):
        """创建OutlineConfirmer实例"""
        return OutlineConfirmer(config=mock_config)
    
    @pytest.fixture
    def sample_package(self):
        """创建示例创作执行包"""
        return {
            "任务书": {
                "本章核心任务": {
                    "目标": "李天突破境界",
                    "阻力": "心魔干扰",
                    "代价": "消耗大量灵力"
                },
                "接住上章": {
                    "起始场景": "青州城",
                    "起始状态": "李天准备闭关"
                },
                "出场角色": {
                    "角色清单": [
                        {"姓名": "李天", "当前状态": "筑基中期"},
                        {"姓名": "王强", "当前状态": "筑基初期"}
                    ]
                },
                "场景与力量约束": {
                    "主要场景": "青州城修炼室",
                    "力量上限": "筑基后期"
                },
                "时间约束": {
                    "本章时间锚点": "天元历1024年春",
                    "本章允许推进": "3天"
                },
                "风格指导": {
                    "叙事风格": "紧凑",
                    "情感基调": "紧张"
                },
                "连续性与伏笔": {
                    "待回收伏笔": ["伏笔1", "伏笔2"],
                    "状态变更": ["李天境界提升"]
                }
            },
            "Context Contract": {
                "hard_constraints": {
                    "location": "青州城",
                    "time": "天元历1024年春"
                }
            },
            "章节节拍": "开篇→修炼→突破→收尾"
        }
    
    def test_init(self, mock_config):
        """测试初始化"""
        confirmer = OutlineConfirmer(config=mock_config)
        
        assert confirmer.config == mock_config
    
    def test_display_execution_package(self, confirmer, sample_package):
        """测试显示创作执行包"""
        output = confirmer.display_execution_package(sample_package)
        
        assert "创作执行包已生成" in output
        assert "任务书" in output
        assert "本章核心任务" in output
        assert "李天突破境界" in output
        assert "出场角色" in output
        assert "李天" in output
        assert "Context Contract" in output
        assert "章节节拍" in output
    
    def test_display_execution_package_with_all_sections(self, confirmer, sample_package):
        """测试显示包含所有板块的执行包"""
        output = confirmer.display_execution_package(sample_package)
        
        # 检查所有7个板块
        assert "板块1：本章核心任务" in output
        assert "板块2：接住上章" in output
        assert "板块3：出场角色" in output
        assert "板块4：场景与力量约束" in output
        assert "板块5：时间约束" in output
        assert "板块6：风格指导" in output
        assert "板块7：连续性与伏笔" in output
    
    def test_prompt_user_confirmation(self, confirmer):
        """测试提示用户确认"""
        prompt = confirmer.prompt_user_confirmation()
        
        assert "请确认是否继续写作" in prompt
        assert "y" in prompt
        assert "n" in prompt
        assert "edit" in prompt
    
    def test_process_user_input_yes(self, confirmer, sample_package):
        """测试处理用户输入 'y'"""
        result = confirmer.process_user_input("y", sample_package)
        
        assert result["action"] == "proceed"
        assert "确认通过" in result["message"]
        assert result["package"] == sample_package
    
    def test_process_user_input_no(self, confirmer, sample_package):
        """测试处理用户输入 'n'"""
        result = confirmer.process_user_input("n", sample_package)
        
        assert result["action"] == "abort"
        assert "中止" in result["message"]
        assert result["package"] == sample_package
    
    def test_process_user_input_edit(self, confirmer, sample_package):
        """测试处理用户输入 'edit'"""
        result = confirmer.process_user_input("edit", sample_package)
        
        assert result["action"] == "edit"
        assert "修改" in result["message"]
        assert "editable_fields" in result
    
    def test_process_user_input_invalid(self, confirmer, sample_package):
        """测试处理无效用户输入"""
        result = confirmer.process_user_input("invalid", sample_package)
        
        assert result["action"] == "invalid"
        assert "无效输入" in result["message"]
    
    def test_process_user_input_case_insensitive(self, confirmer, sample_package):
        """测试用户输入不区分大小写"""
        result1 = confirmer.process_user_input("Y", sample_package)
        result2 = confirmer.process_user_input("N", sample_package)
        result3 = confirmer.process_user_input("EDIT", sample_package)
        
        assert result1["action"] == "proceed"
        assert result2["action"] == "abort"
        assert result3["action"] == "edit"
    
    def test_get_editable_fields(self, confirmer, sample_package):
        """测试获取可编辑字段"""
        editable = confirmer._get_editable_fields(sample_package)
        
        assert len(editable) > 0
        assert any("本章核心任务" in field for field in editable)
        assert any("时间约束" in field for field in editable)
    
    def test_apply_edits(self, confirmer, sample_package):
        """测试应用编辑"""
        edits = {
            "任务书.本章核心任务.目标": "新目标",
            "任务书.时间约束.本章时间锚点": "新时间"
        }
        
        modified = confirmer.apply_edits(sample_package, edits)
        
        assert modified["任务书"]["本章核心任务"]["目标"] == "新目标"
        assert modified["任务书"]["时间约束"]["本章时间锚点"] == "新时间"
    
    def test_apply_edits_preserves_other_fields(self, confirmer, sample_package):
        """测试应用编辑保留其他字段"""
        original_goal = sample_package["任务书"]["本章核心任务"]["目标"]
        
        edits = {
            "任务书.时间约束.本章时间锚点": "新时间"
        }
        
        modified = confirmer.apply_edits(sample_package, edits)
        
        # 未修改的字段应该保持不变
        assert modified["任务书"]["本章核心任务"]["目标"] == original_goal
    
    def test_apply_edits_invalid_path(self, confirmer, sample_package):
        """测试应用编辑到无效路径"""
        edits = {
            "invalid.path.field": "值"
        }
        
        # 不应该抛出异常，只是忽略无效路径
        modified = confirmer.apply_edits(sample_package, edits)
        
        assert modified == sample_package
    
    def test_save_execution_package(self, confirmer, sample_package, temp_project):
        """测试保存创作执行包"""
        output_file = confirmer.save_execution_package(
            package=sample_package,
            chapter=10,
            project_root=temp_project
        )
        
        assert output_file.exists()
        assert "ch010_execution_package.json" in str(output_file)
        
        # 验证文件内容
        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data == sample_package


class TestOutlineConfirmerEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def confirmer(self):
        """创建确认器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        return OutlineConfirmer(config=config)
    
    def test_display_empty_package(self, confirmer):
        """测试显示空执行包"""
        output = confirmer.display_execution_package({})
        
        # 应该能正常处理，不抛出异常
        assert "创作执行包已生成" in output
    
    def test_display_package_missing_sections(self, confirmer):
        """测试显示缺少部分板块的执行包"""
        package = {
            "任务书": {
                "本章核心任务": {"目标": "测试"}
            }
        }
        
        output = confirmer.display_execution_package(package)
        
        # 应该只显示存在的板块
        assert "本章核心任务" in output
    
    def test_process_user_input_whitespace(self, confirmer):
        """测试处理带空格的用户输入"""
        package = {}
        
        result = confirmer.process_user_input("  y  ", package)
        
        assert result["action"] == "proceed"
    
    def test_get_editable_fields_empty_package(self, confirmer):
        """测试空包的可编辑字段"""
        editable = confirmer._get_editable_fields({})
        
        assert editable == []
    
    def test_apply_edits_empty_edits(self, confirmer):
        """测试应用空编辑"""
        package = {"test": "value"}
        
        modified = confirmer.apply_edits(package, {})
        
        assert modified == package


class TestPackageFormatting:
    """执行包格式化测试"""
    
    @pytest.fixture
    def confirmer(self):
        """创建确认器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        return OutlineConfirmer(config=config)
    
    def test_format_characters_list(self, confirmer):
        """测试格式化角色列表"""
        package = {
            "任务书": {
                "出场角色": {
                    "角色清单": [
                        {"姓名": "李天", "当前状态": "筑基中期"},
                        {"姓名": "王强", "当前状态": "筑基初期"}
                    ]
                }
            }
        }
        
        output = confirmer.display_execution_package(package)
        
        assert "李天" in output
        assert "筑基中期" in output
        assert "王强" in output
    
    def test_format_foreshadowing_list(self, confirmer):
        """测试格式化伏笔列表"""
        package = {
            "任务书": {
                "连续性与伏笔": {
                    "待回收伏笔": ["伏笔A", "伏笔B"],
                    "状态变更": ["变更1"]
                }
            }
        }
        
        output = confirmer.display_execution_package(package)
        
        assert "伏笔A" in output
        assert "伏笔B" in output
    
    def test_format_context_contract(self, confirmer):
        """测试格式化Context Contract"""
        package = {
            "Context Contract": {
                "hard_constraints": {
                    "location": "青州城",
                    "time": "天元历1024年"
                },
                "soft_constraints": {
                    "mood": "紧张"
                }
            }
        }
        
        output = confirmer.display_execution_package(package)
        
        assert "Context Contract" in output
        assert "青州城" in output


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
        return OutlineConfirmer(config=config)
    
    @pytest.fixture
    def full_package(self):
        """创建完整执行包"""
        return {
            "任务书": {
                "本章核心任务": {
                    "目标": "李天突破境界",
                    "阻力": "心魔干扰",
                    "代价": "消耗大量灵力"
                },
                "接住上章": {
                    "起始场景": "青州城",
                    "起始状态": "李天准备闭关"
                },
                "出场角色": {
                    "角色清单": [
                        {"姓名": "李天", "当前状态": "筑基中期"}
                    ]
                },
                "场景与力量约束": {
                    "主要场景": "青州城修炼室",
                    "力量上限": "筑基后期"
                },
                "时间约束": {
                    "本章时间锚点": "天元历1024年春",
                    "本章允许推进": "3天"
                },
                "风格指导": {
                    "叙事风格": "紧凑",
                    "情感基调": "紧张"
                },
                "连续性与伏笔": {
                    "待回收伏笔": ["伏笔1"],
                    "状态变更": ["李天境界提升"]
                }
            },
            "Context Contract": {
                "hard_constraints": {
                    "location": "青州城"
                }
            },
            "章节节拍": "开篇→修炼→突破→收尾"
        }
    
    def test_full_confirmation_workflow(self, confirmer, full_package, full_project):
        """测试完整确认工作流"""
        # 1. 显示执行包
        display = confirmer.display_execution_package(full_package)
        assert len(display) > 0
        
        # 2. 提示确认
        prompt = confirmer.prompt_user_confirmation()
        assert "请确认" in prompt
        
        # 3. 处理用户输入
        result = confirmer.process_user_input("y", full_package)
        assert result["action"] == "proceed"
        
        # 4. 保存执行包
        output_file = confirmer.save_execution_package(
            package=full_package,
            chapter=10,
            project_root=full_project
        )
        assert output_file.exists()
    
    def test_edit_and_confirm_workflow(self, confirmer, full_package, full_project):
        """测试编辑后确认工作流"""
        # 1. 用户选择编辑
        result = confirmer.process_user_input("edit", full_package)
        assert result["action"] == "edit"
        
        # 2. 应用编辑
        edits = {
            "任务书.本章核心任务.目标": "修改后的目标"
        }
        modified = confirmer.apply_edits(full_package, edits)
        assert modified["任务书"]["本章核心任务"]["目标"] == "修改后的目标"
        
        # 3. 再次确认
        result = confirmer.process_user_input("y", modified)
        assert result["action"] == "proceed"
        
        # 4. 保存
        output_file = confirmer.save_execution_package(
            package=modified,
            chapter=10,
            project_root=full_project
        )
        assert output_file.exists()
