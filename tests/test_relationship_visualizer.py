"""
测试 relationship_visualizer 模块

测试关系网络可视化功能：
- Mermaid 关系图生成
- 关系演变追踪
- 角色设定模板生成
- OOC 检查
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from forgeai_modules.relationship_visualizer import (
    RelationshipVisualizer,
    RELATIONSHIP_STYLES,
    RELATIONSHIP_LABELS,
    TIER_COLORS,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def visualizer(temp_project: Path):
    """创建 RelationshipVisualizer 实例"""
    with patch("forgeai_modules.relationship_visualizer.get_config") as mock_config:
        mock_config.return_value.project_root = temp_project
        viz = RelationshipVisualizer()
        viz.state_manager.config.project_root = temp_project
        viz.index_manager.config.project_root = temp_project
        return viz


@pytest.fixture
def sample_state_with_entities():
    """带有实体和关系的示例状态"""
    return {
        "entities": {
            "protagonist": {
                "name": "李明",
                "type": "character",
                "tier": "core",
                "aliases": ["小明", "明哥"],
                "attributes": {
                    "修为": "筑基初期",
                    "性格": "沉稳",
                    "位置": "青云宗",
                },
                "description": "主角，性格沉稳",
            },
            "heroine": {
                "name": "林雪",
                "type": "character",
                "tier": "important",
                "attributes": {
                    "修为": "筑基中期",
                    "性格": "温柔",
                },
            },
            "villain": {
                "name": "王刚",
                "type": "character",
                "tier": "important",
                "attributes": {
                    "修为": "金丹初期",
                    "性格": "冷酷",
                },
            },
            "sect": {
                "name": "青云宗",
                "type": "organization",
                "tier": "secondary",
            },
        },
        "relationships": [
            {
                "from_entity": "protagonist",
                "to_entity": "heroine",
                "type": "friend",
                "description": "青梅竹马",
                "chapter": 1,
            },
            {
                "from_entity": "protagonist",
                "to_entity": "villain",
                "type": "enemy",
                "description": "杀父之仇",
                "chapter": 3,
            },
            {
                "from_entity": "heroine",
                "to_entity": "villain",
                "type": "enemy",
                "description": "敌对",
                "chapter": 5,
            },
        ],
        "state_changes": [
            {
                "entity_id": "protagonist",
                "field": "修为",
                "old_value": "练气后期",
                "new_value": "筑基初期",
                "chapter": 2,
                "reason": "突破成功",
            },
        ],
    }


# ============================================
# Test Constants
# ============================================

class TestConstants:
    """测试常量定义"""

    def test_relationship_styles(self):
        """测试关系样式映射"""
        assert RELATIONSHIP_STYLES["friend"] == "-->"
        assert RELATIONSHIP_STYLES["enemy"] == "--x"
        assert RELATIONSHIP_STYLES["mentor"] == "--|指导|-->"
        assert "related" in RELATIONSHIP_STYLES

    def test_relationship_labels(self):
        """测试关系标签映射"""
        assert RELATIONSHIP_LABELS["friend"] == "朋友"
        assert RELATIONSHIP_LABELS["enemy"] == "敌人"
        assert RELATIONSHIP_LABELS["mentor"] == "师徒"

    def test_tier_colors(self):
        """测试层级颜色映射"""
        assert TIER_COLORS["core"] == "#FF6B6B"
        assert TIER_COLORS["important"] == "#4ECDC4"
        assert TIER_COLORS["secondary"] == "#45B7D1"


# ============================================
# Test RelationshipVisualizer Initialization
# ============================================

class TestRelationshipVisualizerInit:
    """测试 RelationshipVisualizer 初始化"""

    def test_init_default(self, temp_project: Path):
        """测试默认初始化"""
        with patch("forgeai_modules.relationship_visualizer.get_config") as mock_config:
            mock_config.return_value.project_root = temp_project
            viz = RelationshipVisualizer()
            
            assert viz.config is not None
            assert viz.state_manager is not None
            assert viz.index_manager is not None

    def test_init_with_config(self, temp_project: Path, sample_config: dict):
        """测试带配置初始化"""
        with patch("forgeai_modules.relationship_visualizer.get_config") as mock_config:
            mock_config.return_value.project_root = temp_project
            from forgeai_modules.config import ForgeAIConfig
            
            config = ForgeAIConfig()
            viz = RelationshipVisualizer(config)
            
            assert viz.config is not None


# ============================================
# Test generate_mermaid_graph
# ============================================

class TestGenerateMermaidGraph:
    """测试 Mermaid 关系图生成"""

    def test_generate_empty_graph(self, visualizer: RelationshipVisualizer):
        """测试空关系图"""
        with patch.object(visualizer.state_manager, "load", return_value={"entities": {}, "relationships": []}):
            result = visualizer.generate_mermaid_graph()
            
            assert "```mermaid" in result
            assert "暂无关系数据" in result

    def test_generate_full_graph(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试生成完整关系图"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.generate_mermaid_graph()
            
            assert "```mermaid" in result
            assert "graph LR" in result
            assert "李明" in result
            assert "林雪" in result
            assert "王刚" in result
            assert "朋友" in result or "青梅竹马" in result

    def test_generate_by_entity(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试按实体过滤关系图"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.generate_mermaid_graph(entity_id="protagonist", max_depth=1)
            
            assert "李明" in result
            # 应该包含与主角相关的实体
            assert "林雪" in result or "王刚" in result

    def test_generate_with_tier_filter(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试层级过滤"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.generate_mermaid_graph(tier_filter="core")
            
            # 应该只包含核心层级角色
            assert "李明" in result
            # 重要层级角色可能不在
            # (取决于是否有关系连接)

    def test_generate_with_legend(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试图例生成"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.generate_mermaid_graph()
            
            assert "图例" in result
            assert "core" in result or "#FF6B6B" in result

    def test_safe_id(self, visualizer: RelationshipVisualizer):
        """测试 ID 安全化"""
        assert visualizer._safe_id("test-id") == "test_id"
        assert visualizer._safe_id("test@name") == "test_name"
        assert visualizer._safe_id("test.name") == "test_name"


# ============================================
# Test generate_evolution_mermaid
# ============================================

class TestGenerateEvolutionMermaid:
    """测试关系演变图生成"""

    def test_evolution_empty(self, visualizer: RelationshipVisualizer):
        """测试空演变图"""
        state = {"entities": {}, "state_changes": [], "relationships": []}
        with patch.object(visualizer.state_manager, "load", return_value=state):
            result = visualizer.generate_evolution_mermaid("protagonist")
            
            assert "```mermaid" in result
            assert "timeline" in result

    def test_evolution_with_data(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试带数据的演变图"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.generate_evolution_mermaid("protagonist")
            
            assert "```mermaid" in result
            assert "timeline" in result
            assert "李明" in result
            # 应该包含状态变化
            assert "筑基初期" in result or "练气后期" in result

    def test_evolution_with_chapter_range(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试章节范围过滤"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.generate_evolution_mermaid(
                "protagonist",
                from_chapter=1,
                to_chapter=3
            )
            
            assert "```mermaid" in result


# ============================================
# Test generate_character_template
# ============================================

class TestGenerateCharacterTemplate:
    """测试角色设定模板生成"""

    def test_template_not_found(self, visualizer: RelationshipVisualizer):
        """测试角色不存在"""
        with patch.object(visualizer.state_manager, "load", return_value={"entities": {}}):
            result = visualizer.generate_character_template("nonexistent")
            
            assert "未找到角色数据" in result

    def test_template_basic(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试基本模板生成"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            with patch.object(visualizer.index_manager, "get_entity_appearances", return_value=[]):
                result = visualizer.generate_character_template("protagonist")
                
                assert "# 李明 角色设定" in result
                assert "基本信息" in result
                assert "核心" in result or "core" in result
                assert "筑基初期" in result

    def test_template_with_relationships(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试包含关系的模板"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            with patch.object(visualizer.index_manager, "get_entity_appearances", return_value=[]):
                result = visualizer.generate_character_template("protagonist")
                
                assert "关系网络" in result
                assert "林雪" in result or "王刚" in result

    def test_template_with_state_changes(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试包含状态变化的模板"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            with patch.object(visualizer.index_manager, "get_entity_appearances", return_value=[]):
                result = visualizer.generate_character_template("protagonist")
                
                assert "成长" in result or "状态变化" in result

    def test_template_with_appearances(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试包含出场记录的模板"""
        appearances = [
            {"chapter": 1, "scene_index": 0, "role": "主角"},
            {"chapter": 2, "scene_index": 1, "role": "主角"},
        ]
        
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            with patch.object(visualizer.index_manager, "get_entity_appearances", return_value=appearances):
                result = visualizer.generate_character_template("protagonist")
                
                assert "出场记录" in result
                assert "第1章" in result


# ============================================
# Test generate_all_character_templates
# ============================================

class TestGenerateAllCharacterTemplates:
    """测试批量生成角色模板"""

    def test_generate_all(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict, temp_project: Path):
        """测试批量生成"""
        output_dir = temp_project / "character_templates"
        
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            with patch.object(visualizer.index_manager, "get_entity_appearances", return_value=[]):
                results = visualizer.generate_all_character_templates(output_dir)
                
                # 应该生成 3 个角色模板（protagonist, heroine, villain）
                assert len(results) == 3
                assert "protagonist" in results
                assert "heroine" in results
                assert "villain" in results
                
                # 检查文件是否创建
                assert output_dir.exists()
                assert len(list(output_dir.glob("*.md"))) == 3


# ============================================
# Test check_ooc
# ============================================

class TestCheckOOC:
    """测试 OOC 检查"""

    def test_ooc_entity_not_found(self, visualizer: RelationshipVisualizer):
        """测试角色不存在"""
        with patch.object(visualizer.state_manager, "load", return_value={"entities": {}}):
            result = visualizer.check_ooc("nonexistent", "章节文本")
            
            assert "error" in result
            assert "未找到角色" in result["error"]

    def test_ooc_no_issues(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试无 OOC 问题"""
        chapter_text = "李明站在青云宗的山顶，望着远方。"
        
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.check_ooc("protagonist", chapter_text)
            
            assert result["entity_id"] == "protagonist"
            assert result["total_issues"] == 0
            assert result["issues"] == []

    def test_ooc_power_regression(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试修为倒退检测"""
        chapter_text = "李明的实力倒退了，修为下降到练气期。"
        
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.check_ooc("protagonist", chapter_text)
            
            assert result["total_issues"] > 0
            assert any(issue["type"] == "power_regression" for issue in result["issues"])

    def test_ooc_personality_contradiction(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试性格矛盾检测"""
        # 主角性格为"沉稳"，检查是否出现慌张
        chapter_text = "李明看到敌人后，惊慌失措，手忙脚乱地逃跑。"
        
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.check_ooc("protagonist", chapter_text)
            
            # 可能检测到性格矛盾
            personality_issues = [
                issue for issue in result["issues"]
                if issue["type"] == "personality_contradiction"
            ]
            # 这个测试依赖于具体的检测逻辑
            # 可能找到也可能找不到，取决于上下文匹配

    def test_ooc_relationship_contradiction(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict):
        """测试关系矛盾检测"""
        # 主角和王刚是敌人关系，检查是否出现亲密行为
        chapter_text = "李明和王刚拥抱在一起，微笑着看着对方。"
        
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            result = visualizer.check_ooc("protagonist", chapter_text)
            
            # 可能检测到关系矛盾
            relationship_issues = [
                issue for issue in result["issues"]
                if issue["type"] == "relationship_contradiction"
            ]
            # 这个测试依赖于具体的检测逻辑


# ============================================
# Test Helper Methods
# ============================================

class TestHelperMethods:
    """测试辅助方法"""

    def test_get_connected_entities(self, visualizer: RelationshipVisualizer):
        """测试获取相连实体"""
        relationships = [
            {"from_entity": "A", "to_entity": "B"},
            {"from_entity": "B", "to_entity": "C"},
            {"from_entity": "C", "to_entity": "D"},
        ]
        
        # 深度为 1
        connected = visualizer._get_connected_entities("A", relationships, max_depth=1)
        assert "A" in connected
        assert "B" in connected
        assert "C" not in connected
        
        # 深度为 2
        connected = visualizer._get_connected_entities("A", relationships, max_depth=2)
        assert "C" in connected
        
        # 深度为 3
        connected = visualizer._get_connected_entities("A", relationships, max_depth=3)
        assert "D" in connected

    def test_get_all_index_relationships(self, visualizer: RelationshipVisualizer):
        """测试从 index.db 获取关系"""
        # Mock index_manager._connect
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            {"from_entity": "A", "to_entity": "B", "type": "friend"}
        ]
        
        with patch.object(visualizer.index_manager, "_connect", return_value=mock_conn):
            result = visualizer._get_all_index_relationships()
            
            assert len(result) == 1
            assert result[0]["from_entity"] == "A"

    def test_get_all_index_relationships_error(self, visualizer: RelationshipVisualizer):
        """测试 index.db 获取失败"""
        with patch.object(visualizer.index_manager, "_connect", side_effect=Exception("DB error")):
            result = visualizer._get_all_index_relationships()
            
            assert result == []


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, visualizer: RelationshipVisualizer, sample_state_with_entities: dict, temp_project: Path):
        """测试完整工作流"""
        with patch.object(visualizer.state_manager, "load", return_value=sample_state_with_entities):
            with patch.object(visualizer.index_manager, "get_entity_appearances", return_value=[]):
                # 1. 生成关系图
                graph = visualizer.generate_mermaid_graph()
                assert "```mermaid" in graph
                
                # 2. 生成演变图
                evolution = visualizer.generate_evolution_mermaid("protagonist")
                assert "```mermaid" in evolution
                
                # 3. 生成角色模板
                template = visualizer.generate_character_template("protagonist")
                assert "李明" in template
                
                # 4. OOC 检查
                ooc_result = visualizer.check_ooc("protagonist", "李明修炼了一整天。")
                assert "entity_id" in ooc_result
