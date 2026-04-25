"""
测试 CLI entity 和 relationship 命令

测试命令行接口的实体和关系管理功能。
使用 mock 进行单元测试,不依赖完整的数据库初始化。
"""

import json
import sys
from argparse import Namespace
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))


@pytest.fixture
def captured_output():
    """捕获标准输出"""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    yield sys.stdout
    sys.stdout = old_stdout


@pytest.fixture
def sample_args():
    """创建模拟参数对象"""
    def make_args(**kwargs):
        return Namespace(**kwargs)
    return make_args


class TestCmdEntity:
    """测试 entity 命令"""

    def test_entity_list(self, sample_args, temp_project):
        """测试 entity list 调用 StateManager"""
        from forgeai import cmd_entity
        
        mock_sm = MagicMock()
        mock_sm.get_entities.return_value = {
            "protagonist": {"name": "李明", "type": "character", "tier": "core"},
        }
        
        args = sample_args(entity_action="list", type=None)
        
        # 捕获输出
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            with patch("forgeai._get_config") as mock_config:
                mock_config.return_value.project_root = temp_project
                with patch("forgeai.StateManager", return_value=mock_sm):
                    cmd_entity(args)
            
            output = sys.stdout.getvalue()
            result = json.loads(output)
            assert isinstance(result, list)
        finally:
            sys.stdout = old_stdout
        
        mock_sm.get_entities.assert_called_once()

    def test_entity_add(self, sample_args, temp_project):
        """测试 entity add 调用管理器"""
        from forgeai import cmd_entity
        
        mock_im = MagicMock()
        mock_sm = MagicMock()
        
        args = sample_args(
            entity_action="add",
            id="test",
            name="测试",
            type="character",
            tier="core",
        )
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            with patch("forgeai._get_config") as mock_config:
                mock_config.return_value.project_root = temp_project
                with patch("forgeai.IndexManager", return_value=mock_im):
                    with patch("forgeai.StateManager", return_value=mock_sm):
                        cmd_entity(args)
            
            output = sys.stdout.getvalue()
            result = json.loads(output)
            assert result["status"] == "ok"
        finally:
            sys.stdout = old_stdout
        
        mock_im.upsert_entity.assert_called_once()

    def test_entity_import_file_not_found(self, sample_args, temp_project):
        """测试导入不存在的文件"""
        from forgeai import cmd_entity
        
        args = sample_args(
            entity_action="import",
            input_file=str(temp_project / "nonexistent.md"),
        )
        
        with patch("forgeai._get_config") as mock_config:
            mock_config.return_value.project_root = temp_project
            with pytest.raises(SystemExit):
                cmd_entity(args)


class TestCmdRelationship:
    """测试 relationship 命令"""

    def test_relationship_list(self, sample_args, temp_project):
        """测试 relationship list"""
        from forgeai import _cmd_relationship
        
        mock_sm = MagicMock()
        mock_sm.load.return_value = {"relationships": []}
        mock_im = MagicMock()
        mock_im.get_stats.return_value = {"relationships": 0}
        
        args = sample_args(rel_action="list", entity=None)
        config = MagicMock()
        config.project_root = temp_project
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            with patch("forgeai.StateManager", return_value=mock_sm):
                with patch("forgeai.IndexManager", return_value=mock_im):
                    _cmd_relationship(args, config)
            
            output = sys.stdout.getvalue()
            result = json.loads(output)
            assert isinstance(result, list)
        finally:
            sys.stdout = old_stdout
        
        mock_sm.load.assert_called_once()

    def test_relationship_add(self, sample_args, temp_project):
        """测试 relationship add"""
        from forgeai import _cmd_relationship
        
        mock_sm = MagicMock()
        mock_im = MagicMock()
        
        args = sample_args(
            rel_action="add",
            from_entity="A",
            to_entity="B",
            rel_type="friend",
            description="朋友",
            chapter=1,
        )
        config = MagicMock()
        config.project_root = temp_project
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            with patch("forgeai.StateManager", return_value=mock_sm):
                with patch("forgeai.IndexManager", return_value=mock_im):
                    _cmd_relationship(args, config)
            
            output = sys.stdout.getvalue()
            result = json.loads(output)
            assert result["status"] == "ok"
        finally:
            sys.stdout = old_stdout
        
        mock_sm.add_relationship.assert_called_once()

    def test_relationship_graph(self, sample_args, temp_project):
        """测试 relationship graph"""
        from forgeai import _cmd_relationship
        
        mock_viz = MagicMock()
        mock_viz.generate_mermaid_graph.return_value = "```mermaid\ngraph LR\n```"
        
        args = sample_args(rel_action="graph", entity=None, tier_filter=None, output=None)
        config = MagicMock()
        config.project_root = temp_project
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            with patch("forgeai.RelationshipVisualizer", return_value=mock_viz):
                _cmd_relationship(args, config)
            
            output = sys.stdout.getvalue()
            assert "```mermaid" in output
        finally:
            sys.stdout = old_stdout
        
        mock_viz.generate_mermaid_graph.assert_called_once()
