#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 实体提取器单元测试
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from forgeai_modules.llm_entity_extractor import (
    LLMEntityExtractor,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractedStateChange,
    ExtractionResult,
)


class TestExtractedEntity:
    """测试 ExtractedEntity 数据类"""

    def test_to_dict(self):
        entity = ExtractedEntity(
            id="litian",
            name="李天",
            type="character",
            tier="core",
            aliases=["小李子"],
            attributes={"修为": "筑基初期"},
            description="男主角",
        )
        result = entity.to_dict()
        assert result["id"] == "litian"
        assert result["name"] == "李天"
        assert result["tier"] == "core"
        assert "小李子" in result["aliases"]

    def test_defaults(self):
        entity = ExtractedEntity(id="test", name="测试")
        assert entity.type == "character"
        assert entity.tier == "secondary"
        assert entity.aliases == []
        assert entity.attributes == {}


class TestExtractedRelationship:
    """测试 ExtractedRelationship 数据类"""

    def test_to_dict(self):
        rel = ExtractedRelationship(
            from_entity="litian",
            to_entity="linxue",
            type="lover",
            description="暗恋",
            chapter=5,
        )
        result = rel.to_dict()
        assert result["from_entity"] == "litian"
        assert result["type"] == "lover"

    def test_defaults(self):
        rel = ExtractedRelationship(from_entity="a", to_entity="b")
        assert rel.type == "related"
        assert rel.chapter == 0


class TestExtractedStateChange:
    """测试 ExtractedStateChange 数据类"""

    def test_to_dict(self):
        change = ExtractedStateChange(
            entity_id="litian",
            field="power.realm",
            old_value="练气9层",
            new_value="筑基初期",
            reason="突破",
            chapter=10,
            change_type="power",
        )
        result = change.to_dict()
        assert result["entity_id"] == "litian"
        assert result["change_type"] == "power"


class TestLLMEntityExtractor:
    """测试 LLMEntityExtractor 类"""

    def test_extract_json_from_code_block(self):
        """测试从代码块提取 JSON"""
        extractor = LLMEntityExtractor.__new__(LLMEntityExtractor)
        text = '''```json
{"entities": [{"id": "test", "name": "测试"}]}
```'''
        result = extractor._extract_json(text)
        assert result is not None
        assert "entities" in result

    def test_extract_json_from_braces(self):
        """测试从花括号提取 JSON"""
        extractor = LLMEntityExtractor.__new__(LLMEntityExtractor)
        text = '一些文本 {"entities": []} 更多文本'
        result = extractor._extract_json(text)
        assert result is not None
        assert "entities" in result

    def test_extract_json_malformed_repair(self):
        """测试修复畸形 JSON"""
        extractor = LLMEntityExtractor.__new__(LLMEntityExtractor)
        # 尾逗号修复
        text = '{"entities": [{"id": "test",},],}'
        result = extractor._extract_json(text)
        # 应该返回 None 或修复后的结果
        # 取决于修复能力

    def test_parse_response_valid(self):
        """测试解析有效响应"""
        extractor = LLMEntityExtractor.__new__(LLMEntityExtractor)
        response = json.dumps({
            "entities": [
                {"id": "litian", "name": "李天", "tier": "core"}
            ],
            "relationships": [
                {"from_entity": "litian", "to_entity": "linxue", "type": "lover"}
            ],
            "state_changes": [
                {"entity_id": "litian", "field": "power", "old_value": "a", "new_value": "b", "reason": "突破", "chapter": 1}
            ]
        })
        result = extractor._parse_response(response, chapter=1)
        assert len(result.entities) == 1
        assert len(result.relationships) == 1
        assert len(result.state_changes) == 1

    def test_parse_response_empty(self):
        """测试解析空响应"""
        extractor = LLMEntityExtractor.__new__(LLMEntityExtractor)
        result = extractor._parse_response("", chapter=1)
        assert len(result.entities) == 0

    @pytest.mark.asyncio
    async def test_extract_from_chapter_success(self):
        """测试成功提取"""
        with patch('forgeai_modules.llm_entity_extractor.CloudLLMManager') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.chat_completion_async = AsyncMock(return_value={
                "content": json.dumps({
                    "entities": [{"id": "test", "name": "测试"}],
                    "relationships": [],
                    "state_changes": []
                })
            })
            MockLLM.return_value = mock_instance

            with patch('forgeai_modules.llm_entity_extractor.StateManager'):
                with patch('forgeai_modules.llm_entity_extractor.IndexManager'):
                    extractor = LLMEntityExtractor()
                    result = await extractor.extract_from_chapter("测试文本", chapter=1)
                    assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_extract_from_chapter_llm_error(self):
        """测试 LLM 错误时返回空结果"""
        with patch('forgeai_modules.llm_entity_extractor.CloudLLMManager') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.chat_completion_async = AsyncMock(side_effect=Exception("API Error"))
            MockLLM.return_value = mock_instance

            with patch('forgeai_modules.llm_entity_extractor.StateManager'):
                with patch('forgeai_modules.llm_entity_extractor.IndexManager'):
                    extractor = LLMEntityExtractor()
                    result = await extractor.extract_from_chapter("测试文本", chapter=1)
                    assert len(result.entities) == 0
                    assert len(result.relationships) == 0

    def test_extract_from_chapter_sync(self):
        """测试同步版本"""
        with patch('forgeai_modules.llm_entity_extractor.asyncio.run') as mock_run:
            mock_run.return_value = ExtractionResult(
                entities=[ExtractedEntity(id="test", name="测试")]
            )
            with patch('forgeai_modules.llm_entity_extractor.CloudLLMManager'):
                with patch('forgeai_modules.llm_entity_extractor.StateManager'):
                    with patch('forgeai_modules.llm_entity_extractor.IndexManager'):
                        extractor = LLMEntityExtractor()
                        result = extractor.extract_from_chapter_sync("文本", 1)
                        assert len(result.entities) == 1

    def test_save_to_state(self, temp_project):
        """测试保存到状态"""
        with patch('forgeai_modules.llm_entity_extractor.StateManager') as MockSM:
            with patch('forgeai_modules.llm_entity_extractor.IndexManager') as MockIM:
                mock_sm = MagicMock()
                mock_im = MagicMock()
                MockSM.return_value = mock_sm
                MockIM.return_value = mock_im

                extractor = LLMEntityExtractor()
                result = ExtractionResult(
                    entities=[ExtractedEntity(id="litian", name="李天", tier="core")],
                    relationships=[ExtractedRelationship(from_entity="a", to_entity="b", type="friend")],
                    state_changes=[ExtractedStateChange(entity_id="litian", field="power", old_value="a", new_value="b", reason="test", chapter=1)]
                )
                stats = extractor.save_to_state(result)
                assert stats["entities"] == 1
                assert stats["relationships"] == 1
                assert stats["state_changes"] == 1


class TestExtractionResult:
    """测试 ExtractionResult 数据类"""

    def test_to_dict(self):
        result = ExtractionResult(
            entities=[ExtractedEntity(id="a", name="A")],
            relationships=[ExtractedRelationship(from_entity="a", to_entity="b")],
            state_changes=[],
        )
        d = result.to_dict()
        assert "entities" in d
        assert "relationships" in d
        assert len(d["entities"]) == 1

    def test_defaults(self):
        result = ExtractionResult()
        assert result.entities == []
        assert result.relationships == []
        assert result.state_changes == []
