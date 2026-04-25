#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立审查模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from forgeai_modules.independent_reviewer import IndependentReviewer


class TestIndependentReviewer:
    """IndependentReviewer测试"""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()
        
        # 创建必要的目录
        content_dir = project / "4-正文"
        content_dir.mkdir(parents=True)
        
        forgeai_dir = project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        
        summaries_dir = forgeai_dir / "summaries"
        summaries_dir.mkdir(parents=True)
        
        # 创建测试章节文件
        chapter_file = content_dir / "第009章 测试章节.md"
        chapter_file.write_text("上一章内容", encoding="utf-8")
        
        chapter_file2 = content_dir / "第010章 当前章节.md"
        chapter_file2.write_text("当前章节内容", encoding="utf-8")
        
        return project
    
    @pytest.fixture
    def mock_config(self, temp_project):
        """创建模拟配置"""
        config = Mock()
        config.project_root = temp_project
        return config
    
    @pytest.fixture
    def reviewer(self, mock_config):
        """创建IndependentReviewer实例"""
        with patch('forgeai_modules.independent_reviewer.StateManager') as mock_sm, \
             patch('forgeai_modules.independent_reviewer.RAGAdapter') as mock_rag:
            
            mock_sm_instance = Mock()
            mock_sm_instance.load.return_value = {
                "chapter_meta": {
                    "0009": {
                        "ending": {
                            "location": "青州城",
                            "characters": ["李天", "王强"]
                        }
                    }
                }
            }
            mock_sm.return_value = mock_sm_instance
            
            mock_rag.return_value = Mock()
            
            return IndependentReviewer(config=mock_config)
    
    def test_init(self, mock_config):
        """测试初始化"""
        with patch('forgeai_modules.independent_reviewer.StateManager') as mock_sm, \
             patch('forgeai_modules.independent_reviewer.RAGAdapter') as mock_rag:
            
            reviewer = IndependentReviewer(config=mock_config)
            
            assert reviewer.config == mock_config
            mock_sm.assert_called_once_with(mock_config)
            mock_rag.assert_called_once_with(mock_config)
    
    def test_prepare_minimal_context(self, reviewer, temp_project):
        """测试准备最小化上下文"""
        context = reviewer.prepare_minimal_context(
            current_chapter=10,
            project_root=temp_project
        )
        
        assert "previous_chapter" in context
        assert "current_chapter" in context
        
        # 检查上一章信息
        if context["previous_chapter"]:
            assert context["previous_chapter"]["number"] == 9
            assert "content" in context["previous_chapter"]
        
        # 检查当前章节信息
        if context["current_chapter"]:
            assert context["current_chapter"]["number"] == 10
            assert "content" in context["current_chapter"]
    
    def test_prepare_minimal_context_first_chapter(self, reviewer, temp_project):
        """测试第一章时准备上下文"""
        context = reviewer.prepare_minimal_context(
            current_chapter=1,
            project_root=temp_project
        )
        
        # 第一章没有上一章
        assert context["previous_chapter"] is None
    
    def test_generate_review_prompt(self, reviewer):
        """测试生成审查提示词"""
        context = {
            "previous_chapter": {
                "number": 9,
                "content": "上一章内容" * 100,
                "summary": "上一章摘要",
                "ending_state": {"location": "青州城"}
            },
            "current_chapter": {
                "number": 10,
                "content": "当前章节内容"
            }
        }
        
        prompt = reviewer.generate_review_prompt(context)
        
        assert "上一章内容" in prompt
        assert "当前章节内容" in prompt
        assert "第9章" in prompt
        assert "第10章" in prompt
        assert "审查任务" in prompt
        assert "人物位置瞬移" in prompt
        assert "时间线是否连贯" in prompt
    
    def test_generate_review_prompt_missing_chapters(self, reviewer):
        """测试缺少章节时生成提示词"""
        context = {
            "previous_chapter": None,
            "current_chapter": None
        }
        
        prompt = reviewer.generate_review_prompt(context)
        
        assert "错误" in prompt
    
    def test_conduct_independent_review(self, reviewer, temp_project):
        """测试执行独立审查"""
        result = reviewer.conduct_independent_review(
            current_chapter=10,
            project_root=temp_project
        )
        
        assert result["status"] == "ok"
        assert result["mode"] == "independent"
        assert result["chapter"] == 10
        assert "review_prompt" in result
        assert "instructions" in result
    
    def test_conduct_independent_review_instructions(self, reviewer, temp_project):
        """测试独立审查的指导说明"""
        result = reviewer.conduct_independent_review(
            current_chapter=10,
            project_root=temp_project
        )
        
        instructions = result["instructions"]
        
        assert len(instructions) > 0
        assert any("新对话窗口" in inst for inst in instructions)
    
    def test_save_review_context(self, reviewer, temp_project):
        """测试保存审查上下文"""
        output_file = reviewer.save_review_context(
            current_chapter=10,
            project_root=temp_project
        )
        
        assert output_file.exists()
        assert "ch010_review_prompt.md" in str(output_file)
        
        # 验证文件内容
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0


class TestIndependentReviewerEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def temp_project_empty(self, tmp_path):
        """创建空的临时项目"""
        project = tmp_path / "empty_project"
        project.mkdir()
        return project
    
    @pytest.fixture
    def reviewer_empty(self, temp_project_empty):
        """创建空项目的审查器"""
        config = Mock()
        config.project_root = temp_project_empty
        
        with patch('forgeai_modules.independent_reviewer.StateManager') as mock_sm, \
             patch('forgeai_modules.independent_reviewer.RAGAdapter') as mock_rag:
            
            mock_sm_instance = Mock()
            mock_sm_instance.load.return_value = {"chapter_meta": {}}
            mock_sm.return_value = mock_sm_instance
            
            mock_rag.return_value = Mock()
            
            return IndependentReviewer(config=config)
    
    def test_prepare_context_missing_chapters(self, reviewer_empty, temp_project_empty):
        """测试章节文件不存在时的处理"""
        context = reviewer_empty.prepare_minimal_context(
            current_chapter=10,
            project_root=temp_project_empty
        )
        
        # 应该返回错误信息而不是None
        assert "error" in context
        assert "找不到第10章" in context["error"]
        assert "hint" in context
    
    def test_generate_prompt_with_empty_ending_state(self, reviewer_empty):
        """测试空结束状态时生成提示词"""
        context = {
            "previous_chapter": {
                "number": 9,
                "content": "上一章内容",
                "summary": "",
                "ending_state": {}
            },
            "current_chapter": {
                "number": 10,
                "content": "当前章节内容"
            }
        }
        
        prompt = reviewer_empty.generate_review_prompt(context)
        
        # 应该能正常生成
        assert "上一章内容" in prompt
    
    def test_generate_prompt_with_error_context(self, reviewer_empty):
        """测试错误上下文时生成提示词"""
        error_context = {
            "error": "测试错误信息",
            "hint": "测试提示"
        }
        
        prompt = reviewer_empty.generate_review_prompt(error_context, current_chapter=10)
        
        # 应该返回错误信息
        assert "测试错误信息" in prompt
        assert "测试提示" in prompt
    
    def test_save_review_context_creates_directory(self, reviewer_empty, temp_project_empty):
        """测试保存时自动创建目录"""
        output_file = reviewer_empty.save_review_context(
            current_chapter=10,
            project_root=temp_project_empty
        )
        
        # 验证目录被创建
        assert output_file.parent.exists()
        assert output_file.exists()


class TestReviewPromptContent:
    """审查提示词内容测试"""
    
    @pytest.fixture
    def reviewer(self):
        """创建审查器"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        
        with patch('forgeai_modules.independent_reviewer.StateManager') as mock_sm, \
             patch('forgeai_modules.independent_reviewer.RAGAdapter') as mock_rag:
            
            mock_sm_instance = Mock()
            mock_sm_instance.load.return_value = {"chapter_meta": {}}
            mock_sm.return_value = mock_sm_instance
            
            mock_rag.return_value = Mock()
            
            return IndependentReviewer(config=config)
    
    def test_prompt_includes_all_check_types(self, reviewer):
        """测试提示词包含所有检查类型"""
        context = {
            "previous_chapter": {
                "number": 9,
                "content": "内容",
                "summary": "摘要",
                "ending_state": {}
            },
            "current_chapter": {
                "number": 10,
                "content": "内容"
            }
        }
        
        prompt = reviewer.generate_review_prompt(context)
        
        # 检查是否包含所有检查类型
        assert "人物位置瞬移" in prompt
        assert "物品道具消失" in prompt
        assert "说话语气是否符合人设" in prompt
        assert "时间线是否连贯" in prompt
        assert "状态变化是否合理" in prompt
    
    def test_prompt_includes_json_format(self, reviewer):
        """测试提示词包含JSON格式说明"""
        context = {
            "previous_chapter": {
                "number": 9,
                "content": "内容",
                "summary": "摘要",
                "ending_state": {}
            },
            "current_chapter": {
                "number": 10,
                "content": "内容"
            }
        }
        
        prompt = reviewer.generate_review_prompt(context)
        
        # 检查JSON格式说明
        assert "JSON" in prompt
        assert "issues" in prompt
        assert "severity" in prompt
        assert "description" in prompt
        assert "suggestion" in prompt
    
    def test_prompt_limits_content_length(self, reviewer):
        """测试提示词限制内容长度"""
        long_content = "很长的内容" * 1000
        
        context = {
            "previous_chapter": {
                "number": 9,
                "content": long_content,
                "summary": "摘要",
                "ending_state": {}
            },
            "current_chapter": {
                "number": 10,
                "content": "当前章节"
            }
        }
        
        prompt = reviewer.generate_review_prompt(context)
        
        # 提示词应该限制上一章内容长度
        assert len(prompt) < len(long_content) * 2


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def full_project(self, tmp_path):
        """创建完整的项目结构"""
        project = tmp_path / "full_project"
        project.mkdir()
        
        # 创建目录
        content_dir = project / "4-正文"
        content_dir.mkdir(parents=True)
        
        forgeai_dir = project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        
        summaries_dir = forgeai_dir / "summaries"
        summaries_dir.mkdir(parents=True)
        
        independent_reviews_dir = forgeai_dir / "independent_reviews"
        independent_reviews_dir.mkdir(parents=True)
        
        # 创建章节文件
        (content_dir / "第009章 测试.md").write_text(
            "李天站在青州城的城门口，看着远处的青云山。王强走过来，沉声说道：'我们该出发了。'",
            encoding="utf-8"
        )
        
        (content_dir / "第010章 继续测试.md").write_text(
            "李天和王强离开了青州城，向青云山进发。路上遇到了林雪儿。",
            encoding="utf-8"
        )
        
        # 创建摘要
        (summaries_dir / "ch009.md").write_text(
            "李天和王强准备前往青云山。",
            encoding="utf-8"
        )
        
        return project
    
    @pytest.fixture
    def reviewer(self, full_project):
        """创建审查器"""
        config = Mock()
        config.project_root = full_project
        
        with patch('forgeai_modules.independent_reviewer.StateManager') as mock_sm, \
             patch('forgeai_modules.independent_reviewer.RAGAdapter') as mock_rag:
            
            mock_sm_instance = Mock()
            mock_sm_instance.load.return_value = {
                "chapter_meta": {
                    "0009": {
                        "ending": {
                            "location": "青州城",
                            "characters": ["李天", "王强"]
                        }
                    }
                }
            }
            mock_sm.return_value = mock_sm_instance
            
            mock_rag.return_value = Mock()
            
            return IndependentReviewer(config=config)
    
    def test_full_review_workflow(self, reviewer, full_project):
        """测试完整审查工作流"""
        # 1. 准备上下文
        context = reviewer.prepare_minimal_context(
            current_chapter=10,
            project_root=full_project
        )
        
        assert context["previous_chapter"] is not None
        assert context["current_chapter"] is not None
        
        # 2. 生成提示词
        prompt = reviewer.generate_review_prompt(context)
        
        assert "李天" in prompt
        assert "青州城" in prompt
        
        # 3. 执行审查
        result = reviewer.conduct_independent_review(
            current_chapter=10,
            project_root=full_project
        )
        
        assert result["status"] == "ok"
        
        # 4. 保存审查上下文
        output_file = reviewer.save_review_context(
            current_chapter=10,
            project_root=full_project
        )
        
        assert output_file.exists()
