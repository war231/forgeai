#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能实体提取模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from forgeai_modules.entity_extractor_v3_ner import (
    Entity,
    SmartEntityExtractor,
    LAC_AVAILABLE,
    HANLP_AVAILABLE,
    JIEBA_AVAILABLE,
)


class TestEntity:
    """Entity数据类测试"""
    
    def test_entity_creation(self):
        """测试创建实体"""
        entity = Entity(
            name="李天",
            type="PER",
            confidence=0.95,
            start=0,
            end=2,
            source="lac"
        )
        
        assert entity.name == "李天"
        assert entity.type == "PER"
        assert entity.confidence == 0.95
        assert entity.start == 0
        assert entity.end == 2
        assert entity.source == "lac"
    
    def test_entity_to_dict(self):
        """测试实体转换为字典"""
        entity = Entity(
            name="青州城",
            type="LOC",
            confidence=0.9,
            start=10,
            end=13,
            source="rule"
        )
        
        result = entity.to_dict()
        
        assert result["name"] == "青州城"
        assert result["type"] == "LOC"
        assert result["confidence"] == 0.9
        assert result["start"] == 10
        assert result["end"] == 13
        assert result["source"] == "rule"


class TestSmartEntityExtractor:
    """SmartEntityExtractor测试"""
    
    def test_init_auto_engine(self):
        """测试自动选择引擎初始化"""
        with patch('forgeai_modules.entity_extractor_v3_ner.LAC_AVAILABLE', True):
            with patch('forgeai_modules.entity_extractor_v3_ner.LAC') as mock_lac:
                mock_lac.return_value = Mock()
                
                extractor = SmartEntityExtractor(preferred_engine="auto")
                
                assert extractor.preferred_engine == "auto"
    
    def test_init_specific_engine(self):
        """测试指定引擎初始化"""
        extractor = SmartEntityExtractor(preferred_engine="jieba")
        
        assert extractor.preferred_engine == "jieba"
    
    def test_extract_with_rules(self):
        """测试使用规则提取实体"""
        extractor = SmartEntityExtractor(preferred_engine="rule")
        
        text = "李天看着眼前的王强，沉声说道：'我们要快点找到林雪儿。'张伟在一旁点头，他们正站在青州城的城门口。"
        
        entities = extractor.extract(text, engine="rule")
        
        # 应该能提取到角色名和地名
        assert len(entities) > 0
        
        # 检查是否包含角色
        per_entities = [e for e in entities if e.type == "PER"]
        assert len(per_entities) > 0
    
    def test_extract_characters(self):
        """测试提取角色"""
        extractor = SmartEntityExtractor(preferred_engine="rule")
        
        text = "李天是一个修仙者，王强是他的朋友。"
        
        characters = extractor.extract_characters(text)
        
        assert isinstance(characters, list)
        # 如果提取到角色，检查格式
        if len(characters) > 0:
            assert "name" in characters[0]
            assert "type" in characters[0]
    
    def test_extract_locations(self):
        """测试提取地点"""
        extractor = SmartEntityExtractor(preferred_engine="rule")
        
        text = "他们来到了青州城，准备前往青云山。"
        
        locations = extractor.extract_locations(text)
        
        assert isinstance(locations, list)
    
    def test_extract_all(self):
        """测试提取所有实体"""
        extractor = SmartEntityExtractor(preferred_engine="rule")
        
        text = "李天在青州城遇到了王强。"
        
        result = extractor.extract_all(text)
        
        assert "characters" in result
        assert "locations" in result
        assert "organizations" in result
        assert "items" in result
    
    def test_get_engine_info(self):
        """测试获取引擎信息"""
        extractor = SmartEntityExtractor(preferred_engine="auto")
        
        info = extractor.get_engine_info()
        
        assert info["preferred_engine"] == "auto"
        assert "available_engines" in info
        assert "loaded_engines" in info
        assert "lac" in info["available_engines"]
        assert "hanlp" in info["available_engines"]
        assert "jieba" in info["available_engines"]


class TestRuleBasedExtraction:
    """基于规则的提取测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建使用规则引擎的提取器"""
        return SmartEntityExtractor(preferred_engine="rule")
    
    def test_extract_dialogue_pattern(self, extractor):
        """测试对话模式提取角色"""
        text = "李天沉声说道：'我们必须小心。'"
        
        entities = extractor.extract(text, engine="rule")
        
        # 应该能从对话模式中提取角色名
        per_entities = [e for e in entities if e.type == "PER"]
        assert len(per_entities) > 0
    
    def test_extract_location_pattern(self, extractor):
        """测试地名模式提取"""
        text = "他们来到了青州城，又去了青云山。"
        
        entities = extractor.extract(text, engine="rule")
        
        loc_entities = [e for e in entities if e.type == "LOC"]
        assert len(loc_entities) > 0
    
    def test_extract_multiple_entities(self, extractor):
        """测试提取多个实体"""
        text = """
        李天看着眼前的王强，沉声说道："我们要快点找到林雪儿。"
        张伟在一旁点头，他们正站在青州城的城门口。
        远处的青云山若隐若现。
        """
        
        entities = extractor.extract(text, engine="rule")
        
        # 应该提取到多个实体
        assert len(entities) >= 2
        
        # 检查去重
        names = [e.name for e in entities]
        assert len(names) == len(set(names))
    
    def test_entity_position(self, extractor):
        """测试实体位置信息"""
        text = "李天是一个修仙者。"
        
        entities = extractor.extract(text, engine="rule")
        
        if len(entities) > 0:
            entity = entities[0]
            # 验证位置信息
            assert entity.start >= 0
            assert entity.end > entity.start
            assert entity.end <= len(text)


class TestJiebaExtraction:
    """Jieba提取测试"""
    
    @pytest.mark.skipif(not JIEBA_AVAILABLE, reason="Jieba未安装")
    def test_extract_with_jieba(self):
        """测试使用Jieba提取"""
        extractor = SmartEntityExtractor(preferred_engine="jieba")
        
        text = "李天在青州城遇到了王强。"
        
        entities = extractor.extract(text, engine="jieba")
        
        assert isinstance(entities, list)
    
    @pytest.mark.skipif(not JIEBA_AVAILABLE, reason="Jieba未安装")
    def test_jieba_entity_types(self):
        """测试Jieba提取的实体类型"""
        extractor = SmartEntityExtractor(preferred_engine="jieba")
        
        text = "李天去了北京。"
        
        entities = extractor.extract(text, engine="jieba")
        
        # 检查实体类型是否正确
        for entity in entities:
            assert entity.type in ["PER", "LOC", "ORG", "ITEM"]
            assert entity.source == "jieba"


class TestLACExtraction:
    """LAC提取测试"""
    
    @pytest.mark.skipif(not LAC_AVAILABLE, reason="LAC未安装")
    def test_extract_with_lac(self):
        """测试使用LAC提取"""
        with patch('forgeai_modules.entity_extractor_v3_ner.LAC') as mock_lac:
            mock_instance = Mock()
            mock_instance.run.return_value = (
                ["李天", "在", "青州城"],
                ["PER", "p", "LOC"]
            )
            mock_lac.return_value = mock_instance
            
            extractor = SmartEntityExtractor(preferred_engine="lac")
            
            text = "李天在青州城"
            
            entities = extractor.extract(text, engine="lac")
            
            assert isinstance(entities, list)


class TestHanLPExtraction:
    """HanLP提取测试"""
    
    @pytest.mark.skipif(not HANLP_AVAILABLE, reason="HanLP未安装")
    def test_extract_with_hanlp(self):
        """测试使用HanLP提取"""
        with patch('forgeai_modules.entity_extractor_v3_ner.hanlp') as mock_hanlp:
            mock_model = Mock()
            mock_model.return_value = [
                ["李天", "PER", 0, 2],
                ["青州城", "LOC", 3, 6]
            ]
            mock_hanlp.load.return_value = mock_model
            mock_hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH = "mock_model"
            
            extractor = SmartEntityExtractor(preferred_engine="hanlp")
            
            text = "李天在青州城"
            
            entities = extractor.extract(text, engine="hanlp")
            
            assert isinstance(entities, list)


class TestAutoEngineSelection:
    """自动引擎选择测试"""
    
    def test_auto_select_lac(self):
        """测试自动选择LAC引擎"""
        with patch('forgeai_modules.entity_extractor_v3_ner.LAC_AVAILABLE', True), \
             patch('forgeai_modules.entity_extractor_v3_ner.HANLP_AVAILABLE', False), \
             patch('forgeai_modules.entity_extractor_v3_ner.JIEBA_AVAILABLE', True), \
             patch('forgeai_modules.entity_extractor_v3_ner.LAC') as mock_lac:
            
            mock_lac.return_value = Mock()
            
            extractor = SmartEntityExtractor(preferred_engine="auto")
            
            # LAC应该被加载
            assert extractor.lac is not None
    
    def test_auto_select_jieba_fallback(self):
        """测试Jieba作为后备引擎"""
        with patch('forgeai_modules.entity_extractor_v3_ner.LAC_AVAILABLE', False), \
             patch('forgeai_modules.entity_extractor_v3_ner.HANLP_AVAILABLE', False), \
             patch('forgeai_modules.entity_extractor_v3_ner.JIEBA_AVAILABLE', True):
            
            extractor = SmartEntityExtractor(preferred_engine="auto")
            
            # 应该回退到Jieba或规则
            text = "李天是一个修仙者。"
            entities = extractor.extract(text)
            
            assert isinstance(entities, list)
    
    def test_auto_select_rule_fallback(self):
        """测试规则作为最后后备"""
        with patch('forgeai_modules.entity_extractor_v3_ner.LAC_AVAILABLE', False), \
             patch('forgeai_modules.entity_extractor_v3_ner.HANLP_AVAILABLE', False), \
             patch('forgeai_modules.entity_extractor_v3_ner.JIEBA_AVAILABLE', False):
            
            extractor = SmartEntityExtractor(preferred_engine="auto")
            
            text = "李天是一个修仙者。"
            entities = extractor.extract(text)
            
            # 应该使用规则引擎
            assert isinstance(entities, list)


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建提取器"""
        return SmartEntityExtractor(preferred_engine="rule")
    
    def test_empty_text(self, extractor):
        """测试空文本"""
        entities = extractor.extract("")
        
        assert entities == []
    
    def test_no_entities(self, extractor):
        """测试没有实体的文本"""
        text = "今天天气很好，阳光明媚。"
        
        entities = extractor.extract(text, engine="rule")
        
        # 可能没有提取到实体，或者提取到很少
        assert isinstance(entities, list)
    
    def test_short_entity_name(self, extractor):
        """测试短实体名（少于2字）"""
        text = "他说：'你好。'"
        
        entities = extractor.extract(text, engine="rule")
        
        # 规则引擎应该过滤掉单字实体
        for entity in entities:
            assert len(entity.name) >= 2
    
    def test_long_text(self, extractor):
        """测试长文本"""
        text = "李天" * 1000
        
        entities = extractor.extract(text, engine="rule")
        
        assert isinstance(entities, list)
    
    def test_special_characters(self, extractor):
        """测试特殊字符"""
        text = "李天@#$%王强"
        
        entities = extractor.extract(text, engine="rule")
        
        assert isinstance(entities, list)


class TestEntityConfidence:
    """实体置信度测试"""
    
    def test_rule_based_confidence(self):
        """测试规则提取的置信度"""
        extractor = SmartEntityExtractor(preferred_engine="rule")
        
        text = "李天沉声说道：'你好。'"
        
        entities = extractor.extract(text, engine="rule")
        
        for entity in entities:
            # 规则提取的置信度应该在合理范围内
            assert 0 < entity.confidence <= 1.0
    
    @pytest.mark.skipif(not JIEBA_AVAILABLE, reason="Jieba未安装")
    def test_jieba_confidence(self):
        """测试Jieba提取的置信度"""
        extractor = SmartEntityExtractor(preferred_engine="jieba")
        
        text = "李天去了北京。"
        
        entities = extractor.extract(text, engine="jieba")
        
        for entity in entities:
            assert 0 < entity.confidence <= 1.0
