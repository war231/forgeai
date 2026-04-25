#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文提取器测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from forgeai_modules.context_extractor import ContextExtractor


class TestContextExtractor:
    """ContextExtractor测试"""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()
        
        # 创建必要的目录
        (project / "4-正文").mkdir(parents=True)
        (project / ".forgeai").mkdir(parents=True)
        
        return project
    
    @pytest.fixture
    def mock_config(self, temp_project):
        """创建模拟配置"""
        config = Mock()
        config.project_root = temp_project
        return config
    
    @pytest.fixture
    def extractor(self, mock_config):
        """创建ContextExtractor实例"""
        with patch('forgeai_modules.context_extractor.StateManager') as mock_sm, \
             patch('forgeai_modules.context_extractor.IndexManager') as mock_im, \
             patch('forgeai_modules.context_extractor.RAGAdapter') as mock_rag:
            
            mock_sm_instance = Mock()
            mock_sm_instance.load.return_value = {
                "project": {"name": "测试项目", "genre": "玄幻"},
                "progress": {"current_chapter": 10, "phase": "writing"},
                "foreshadowing": {"active": []},
                "strands": {"quest": [], "fire": [], "constellation": []},
                "reading_power": {"debt": 0.0},
                "state_changes": [],
                "relationships": [],
            }
            mock_sm_instance.get_entities.return_value = {}
            mock_sm_instance.get_overdue_foreshadowing.return_value = []
            mock_sm.return_value = mock_sm_instance
            
            mock_im_instance = Mock()
            mock_im_instance.get_chapter.return_value = None
            mock_im_instance.get_reading_power_trend.return_value = []
            mock_im.return_value = mock_im_instance
            
            mock_rag.return_value = Mock()
            
            extractor = ContextExtractor(config=mock_config)
            return extractor
    
    def test_init(self, mock_config):
        """测试初始化"""
        with patch('forgeai_modules.context_extractor.StateManager') as mock_sm, \
             patch('forgeai_modules.context_extractor.IndexManager') as mock_im, \
             patch('forgeai_modules.context_extractor.RAGAdapter') as mock_rag:
            
            extractor = ContextExtractor(config=mock_config)
            
            assert extractor.config == mock_config
            mock_sm.assert_called_once_with(mock_config)
            mock_im.assert_called_once_with(mock_config)
            mock_rag.assert_called_once_with(mock_config)
    
    def test_extract_full_context(self, extractor):
        """测试提取完整上下文"""
        context = extractor.extract_full_context(current_chapter=10)
        
        assert "project" in context
        assert "progress" in context
        assert "previous_chapters" in context
        assert "active_entities" in context
        assert "active_foreshadowing" in context
        assert "overdue_foreshadowing" in context
        assert "strand_balance" in context
        assert "reading_power_trend" in context
        assert "narrative_debt" in context
        assert "recent_state_changes" in context
        assert "relationships_snapshot" in context
    
    @pytest.mark.asyncio
    async def test_extract_with_rag(self, extractor):
        """测试带RAG的上下文提取"""
        # Mock RAG adapter
        extractor.rag_adapter.extract_context = Mock(return_value={
            "relevant_chunks": [{"text": "测试内容", "score": 0.8}],
            "degraded_mode": False
        })
        
        # 需要将同步mock改为异步mock
        async def mock_extract_context(*args, **kwargs):
            return {
                "relevant_chunks": [{"text": "测试内容", "score": 0.8}],
                "degraded_mode": False
            }
        
        extractor.rag_adapter.extract_context = mock_extract_context
        
        context = await extractor.extract_with_rag(current_chapter=10, query="测试查询")
        
        assert "rag_results" in context
        assert context["rag_degraded"] == False
    
    def test_get_previous_chapters(self, extractor):
        """测试获取前文章节"""
        # Mock章节元数据
        extractor.index_manager.get_chapter = Mock(return_value={
            "number": 9,
            "title": "第九章",
            "word_count": 2000
        })
        
        chapters = extractor._get_previous_chapters(current_chapter=10, lookback=2)
        
        assert len(chapters) == 2
        assert chapters[0]["number"] == 9
    
    def test_get_active_entities(self, extractor):
        """测试获取活跃实体"""
        extractor.state_manager.get_entities.return_value = {
            "char1": {
                "name": "李天",
                "tier": "core",
                "last_appearance": 8,
                "type": "character"
            },
            "char2": {
                "name": "路人甲",
                "tier": "decorative",
                "last_appearance": 1,
                "type": "character"
            }
        }
        
        active = extractor._get_active_entities(current_chapter=10, lookback=5)
        
        # 只有char1在最近5章出场过
        assert len(active) == 1
        assert active[0]["name"] == "李天"
    
    def test_get_active_entities_sorted_by_tier(self, extractor):
        """测试活跃实体按tier排序"""
        extractor.state_manager.get_entities.return_value = {
            "char1": {"name": "A", "tier": "decorative", "last_appearance": 9, "type": "character"},
            "char2": {"name": "B", "tier": "core", "last_appearance": 9, "type": "character"},
            "char3": {"name": "C", "tier": "important", "last_appearance": 9, "type": "character"},
        }
        
        active = extractor._get_active_entities(current_chapter=10, lookback=5)
        
        # 按tier排序: core > important > decorative
        assert active[0]["tier"] == "core"
        assert active[1]["tier"] == "important"
        assert active[2]["tier"] == "decorative"
    
    def test_get_active_foreshadowing(self, extractor):
        """测试获取活跃伏笔"""
        extractor.state_manager.load.return_value = {
            "foreshadowing": {
                "active": [
                    {"id": "fs1", "description": "测试伏笔"}
                ]
            }
        }
        
        state = extractor.state_manager.load()
        foreshadowing = extractor._get_active_foreshadowing(state)
        
        assert len(foreshadowing) == 1
        assert foreshadowing[0]["id"] == "fs1"
    
    def test_get_strand_balance_balanced(self, extractor):
        """测试节奏平衡（平衡状态）"""
        state = {
            "strands": {
                "quest": list(range(6)),  # 6个
                "fire": list(range(2)),   # 2个
                "constellation": list(range(2))  # 2个
            }
        }
        
        balance = extractor._get_strand_balance(state)
        
        assert balance["quest_ratio"] == 0.6
        assert balance["fire_ratio"] == 0.2
        assert balance["constellation_ratio"] == 0.2
        assert balance["balanced"] == True
    
    def test_get_strand_balance_unbalanced(self, extractor):
        """测试节奏平衡（失衡状态）"""
        state = {
            "strands": {
                "quest": list(range(10)),  # 10个
                "fire": [],                # 0个
                "constellation": []        # 0个
            }
        }
        
        balance = extractor._get_strand_balance(state)
        
        assert balance["quest_ratio"] == 1.0
        assert balance["fire_ratio"] == 0.0
        assert balance["balanced"] == False
    
    def test_get_strand_balance_empty(self, extractor):
        """测试节奏平衡（空状态）"""
        state = {"strands": {"quest": [], "fire": [], "constellation": []}}
        
        balance = extractor._get_strand_balance(state)
        
        assert balance["total"] == 0
        assert balance["balanced"] == True
    
    def test_get_reading_power_trend(self, extractor):
        """测试获取追读力趋势"""
        extractor.index_manager.get_reading_power_trend.return_value = [
            {"chapter": 1, "score": 8.5},
            {"chapter": 2, "score": 8.7}
        ]
        
        trend = extractor._get_reading_power_trend(last_n=10)
        
        assert len(trend) == 2
    
    def test_get_recent_changes(self, extractor):
        """测试获取最近状态变化"""
        extractor.state_manager.load.return_value = {
            "state_changes": [
                {"chapter": 9, "change": "test1"},
                {"chapter": 5, "change": "test2"},
                {"chapter": 3, "change": "test3"}
            ]
        }
        
        state = extractor.state_manager.load()
        changes = extractor._get_recent_changes(state, current_chapter=10, lookback=5)
        
        # 只保留章节 >= 5 的变化
        assert len(changes) == 2
    
    def test_get_relationships_snapshot(self, extractor):
        """测试获取关系快照"""
        extractor.state_manager.load.return_value = {
            "relationships": [
                {"chapter": 9, "relation": "test1"},
                {"chapter": 5, "relation": "test2"},
                {"chapter": 1, "relation": "test3"}
            ]
        }
        
        rels = extractor._get_relationships_snapshot(current_chapter=20)
        
        # 只保留章节 >= 0 的关系（current_chapter - 20 = 0）
        assert len(rels) == 3
    
    def test_format_context_for_prompt(self, extractor):
        """测试格式化上下文为prompt"""
        context = {
            "project": {"name": "测试项目", "genre": "玄幻", "mode": "standard"},
            "progress": {"current_chapter": 10, "total_chapters": 100, "phase": "writing", "word_count": 20000},
            "active_entities": [
                {"name": "李天", "tier": "core", "last_appearance": 9}
            ],
            "active_foreshadowing": [
                {"id": "fs1", "description": "测试伏笔", "chapter_planted": 5}
            ],
            "overdue_foreshadowing": [],
            "narrative_debt": 0.0,
            "strand_balance": {"balanced": True}
        }
        
        prompt = extractor.format_context_for_prompt(context)
        
        assert "测试项目" in prompt
        assert "第10章" in prompt
        assert "李天" in prompt
        assert "测试伏笔" in prompt


class TestContextExtractorEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建基本extractor"""
        config = Mock()
        config.project_root = Path("/tmp/test")
        
        with patch('forgeai_modules.context_extractor.StateManager') as mock_sm, \
             patch('forgeai_modules.context_extractor.IndexManager') as mock_im, \
             patch('forgeai_modules.context_extractor.RAGAdapter') as mock_rag:
            
            mock_sm_instance = Mock()
            mock_sm_instance.load.return_value = {}
            mock_sm_instance.get_entities.return_value = {}
            mock_sm_instance.get_overdue_foreshadowing.return_value = []
            mock_sm.return_value = mock_sm_instance
            
            mock_im_instance = Mock()
            mock_im_instance.get_chapter.return_value = None
            mock_im_instance.get_reading_power_trend.return_value = []
            mock_im.return_value = mock_im_instance
            
            mock_rag.return_value = Mock()
            
            return ContextExtractor(config=config)
    
    def test_extract_full_context_empty_state(self, extractor):
        """测试空状态时提取上下文"""
        context = extractor.extract_full_context(current_chapter=1)
        
        assert context["project"] == {}
        assert context["progress"] == {}
        assert context["previous_chapters"] == []
        assert context["active_entities"] == []
    
    def test_get_previous_chapters_first_chapter(self, extractor):
        """测试第一章时获取前文"""
        chapters = extractor._get_previous_chapters(current_chapter=1)
        
        assert len(chapters) == 0
    
    def test_get_active_entities_no_recent_appearance(self, extractor):
        """测试没有最近出场的实体"""
        extractor.state_manager.get_entities.return_value = {
            "char1": {"name": "A", "tier": "core", "last_appearance": 1, "type": "character"}
        }
        
        active = extractor._get_active_entities(current_chapter=100, lookback=5)
        
        assert len(active) == 0
    
    def test_format_context_with_warnings(self, extractor):
        """测试格式化带警告的上下文"""
        context = {
            "project": {"name": "测试", "genre": "玄幻", "mode": "standard"},
            "progress": {"current_chapter": 10, "total_chapters": 100, "phase": "writing", "word_count": 20000},
            "active_entities": [],
            "active_foreshadowing": [],
            "overdue_foreshadowing": [{"id": "fs1"}],
            "narrative_debt": 5.0,
            "strand_balance": {"balanced": False, "quest_ratio": 0.9, "fire_ratio": 0.1, "constellation_ratio": 0.0}
        }
        
        prompt = extractor.format_context_for_prompt(context)
        
        assert "超期伏笔" in prompt
        assert "叙事债务" in prompt
        assert "节奏失衡" in prompt
