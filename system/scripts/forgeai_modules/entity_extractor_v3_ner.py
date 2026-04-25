"""
智能实体提取模块 V3 - 集成NER模型
支持LAC、HanLP、Jieba等多种NER引擎
"""
import re
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# 尝试导入NER库
try:
    from LAC import LAC
    LAC_AVAILABLE = True
except ImportError:
    LAC_AVAILABLE = False

try:
    import hanlp
    HANLP_AVAILABLE = True
except ImportError:
    HANLP_AVAILABLE = False

try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


@dataclass
class Entity:
    """实体"""
    name: str
    type: str  # PER/LOC/ORG/ITEM
    confidence: float
    start: int
    end: int
    source: str  # lac/hanlp/jieba/rule
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "confidence": self.confidence,
            "start": self.start,
            "end": self.end,
            "source": self.source,
        }


class SmartEntityExtractor:
    """智能实体提取器（多引擎支持）"""
    
    # 三国时期地名词典（州郡城市）
    LOCATION_DICT = {
        # 州名
        "兖州", "豫州", "徐州", "青州", "冀州", "荆州", "扬州", "益州", "凉州", "并州",
        "幽州", "交州", "司隶",
        # 郡名/城市名
        "许昌", "洛阳", "长安", "邺城", "许都", "濮阳", "陈留", "颍川", "汝南", "南阳",
        "襄阳", "江陵", "长沙", "武陵", "零陵", "桂阳", "江夏", "南郡", "宛城", "下邳",
        "小沛", "徐州城", "寿春", "合肥", "建业", "吴郡", "会稽", "丹阳", "豫章", "庐江",
        "江东", "荆州城", "成都", "汉中", "天水", "安定", "陇西", "西凉", "并州城",
        "幽州城", "辽东", "北海", "平原", "北海国", "东郡", "陈国", "梁国", "沛国",
    }
    
    def __init__(self, preferred_engine: str = "auto", config: Optional[Dict] = None):
        """
        Args:
            preferred_engine: lac/hanlp/jieba/auto
            config: 配置字典（包含缓存配置）
        """
        self.preferred_engine = preferred_engine
        self.lac = None
        self.hanlp = None
        
        # 缓存配置
        self.config = config or {}
        cache_config = self.config.get("humanize", {}).get("entity_cache", {})
        self.cache_enabled = cache_config.get("enabled", True)
        self.cache_ttl = cache_config.get("ttl", 300)
        
        # 初始化缓存
        self._cache = {} if self.cache_enabled else None
        self._cache_timestamps = {} if self.cache_enabled else None
        
        # 初始化引擎
        self._init_engines()
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_from_cache(self, text: str) -> Optional[List[Entity]]:
        """从缓存获取结果"""
        if not self.cache_enabled:
            return None
        
        key = self._get_cache_key(text)
        if key in self._cache:
            if time.time() - self._cache_timestamps[key] < self.cache_ttl:
                print(f"[缓存命中] {key[:8]}")
                return self._cache[key]
        return None
    
    def _save_to_cache(self, text: str, result: List[Entity]):
        """保存结果到缓存"""
        if not self.cache_enabled:
            return
        
        key = self._get_cache_key(text)
        self._cache[key] = result
        self._cache_timestamps[key] = time.time()
        print(f"[缓存保存] {key[:8]}")
    
    def _init_engines(self):
        """初始化NER引擎"""
        if self.preferred_engine == "lac" or self.preferred_engine == "auto":
            if LAC_AVAILABLE:
                try:
                    self.lac = LAC(mode='lac')
                    print("✅ LAC引擎加载成功")
                except Exception as e:
                    print(f"⚠️ LAC加载失败: {e}")
        
        if self.preferred_engine == "hanlp" or self.preferred_engine == "auto":
            if HANLP_AVAILABLE:
                try:
                    # 使用HanLP的预训练模型
                    self.hanlp = hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)
                    print("✅ HanLP引擎加载成功")
                except Exception as e:
                    print(f"⚠️ HanLP加载失败: {e}")
    
    def extract(self, text: str, engine: Optional[str] = None) -> List[Entity]:
        """提取实体
        
        Args:
            text: 待提取文本
            engine: 指定引擎（lac/hanlp/jieba/rule），None则使用preferred_engine
        
        Returns:
            实体列表
        """
        start_time = time.time()
        
        # 检查缓存
        cached = self._get_from_cache(text)
        if cached:
            elapsed = time.time() - start_time
            print(f"[实体提取] 耗时 {elapsed:.2f}s（缓存），提取 {len(cached)} 个实体")
            return cached
        
        # 执行提取
        engine = engine or self.preferred_engine
        
        if engine == "lac" and self.lac:
            entities = self._extract_with_lac(text)
        elif engine == "hanlp" and self.hanlp:
            entities = self._extract_with_hanlp(text)
        elif engine == "jieba" and JIEBA_AVAILABLE:
            entities = self._extract_with_jieba(text)
        elif engine == "rule":
            entities = self._extract_with_rules(text)
        else:
            # 自动选择最佳引擎
            if self.lac:
                entities = self._extract_with_lac(text)
            elif self.hanlp:
                entities = self._extract_with_hanlp(text)
            elif JIEBA_AVAILABLE:
                entities = self._extract_with_jieba(text)
            else:
                entities = self._extract_with_rules(text)
        
        # 去重
        entities = self._deduplicate_entities(entities)
        
        # 后处理：修正实体类型
        entities = self._post_process_entities(entities, text)
        
        # 保存缓存
        self._save_to_cache(text, entities)
        
        # 性能日志
        elapsed = time.time() - start_time
        print(f"[实体提取] 耗时 {elapsed:.2f}s，提取 {len(entities)} 个实体")
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """去重实体列表"""
        seen = set()
        unique_entities = []
        
        for entity in entities:
            # 使用实体名称和类型作为唯一标识
            key = f"{entity.name}_{entity.type}"
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
            else:
                print(f"[去重实体] {key}")
        
        return unique_entities
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """后处理：修正实体类型
        
        规则:
        1. 地名词典匹配 → LOC
        2. 上下文包含"城"、"郡"、"县"等 → LOC
        3. 上下文包含"公"、"侯"、"将军"等 → PER
        """
        processed = []
        
        for entity in entities:
            # 规则1: 地名词典匹配
            if entity.name in self.LOCATION_DICT and entity.type != "LOC":
                print(f"[修正] {entity.name}: {entity.type} → LOC (词典匹配)")
                entity = Entity(
                    name=entity.name,
                    type="LOC",
                    confidence=0.95,
                    start=entity.start,
                    end=entity.end,
                    source=entity.source + "+dict"
                )
            
            # 规则2: 上下文检查（地名后缀）
            elif entity.type == "PER":
                # 检查实体后面是否跟着地名后缀（需要独立成词）
                context_end = min(entity.end + 3, len(text))
                suffix = text[entity.end:context_end]
                
                # 更严格的规则：后缀必须紧跟实体，且实体长度>=2
                if len(entity.name) >= 2 and any(s in suffix for s in ["城", "郡", "县", "州", "都", "镇", "村"]):
                    # 排除误判：如果后缀是"城中"、"城外"等，可能是误判
                    if not any(w in suffix for w in ["城中", "城外", "城中"]):
                        print(f"[修正] {entity.name}: PER → LOC (上下文: {suffix})")
                        entity = Entity(
                            name=entity.name,
                            type="LOC",
                            confidence=0.85,
                            start=entity.start,
                            end=entity.end,
                            source=entity.source + "+context"
                        )
            
            processed.append(entity)
        
        return processed
    
    def _extract_with_lac(self, text: str) -> List[Entity]:
        """使用LAC提取实体"""
        entities = []
        
        try:
            result = self.lac.run(text)
            words, tags = result
            
            current_pos = 0
            for word, tag in zip(words, tags):
                start = current_pos
                end = current_pos + len(word)
                current_pos = end
                
                # 映射LAC标签到实体类型
                entity_type = None
                confidence = 0.9
                
                if tag == "PER":
                    entity_type = "PER"
                elif tag == "LOC":
                    entity_type = "LOC"
                elif tag == "ORG":
                    entity_type = "ORG"
                elif tag == "nw":  # 新词
                    entity_type = "ITEM"
                    confidence = 0.7
                
                if entity_type and len(word) >= 2:
                    entities.append(Entity(
                        name=word,
                        type=entity_type,
                        confidence=confidence,
                        start=start,
                        end=end,
                        source="lac",
                    ))
        
        except Exception as e:
            print(f"LAC提取失败: {e}")
        
        return entities
    
    def _extract_with_hanlp(self, text: str) -> List[Entity]:
        """使用HanLP提取实体"""
        entities = []
        
        try:
            result = self.hanlp(text)
            
            for entity_info in result:
                name, ner_tag, start, end = entity_info
                
                # 映射HanLP标签
                entity_type = None
                if "PER" in ner_tag or "NR" in ner_tag:
                    entity_type = "PER"
                elif "LOC" in ner_tag or "NS" in ner_tag:
                    entity_type = "LOC"
                elif "ORG" in ner_tag or "NT" in ner_tag:
                    entity_type = "ORG"
                
                if entity_type and len(name) >= 2:
                    entities.append(Entity(
                        name=name,
                        type=entity_type,
                        confidence=0.95,
                        start=start,
                        end=end,
                        source="hanlp",
                    ))
        
        except Exception as e:
            print(f"HanLP提取失败: {e}")
        
        return entities
    
    def _extract_with_jieba(self, text: str) -> List[Entity]:
        """使用Jieba词性标注提取实体"""
        entities = []
        
        try:
            words = pseg.cut(text)
            
            current_pos = 0
            for word, flag in words:
                start = current_pos
                end = current_pos + len(word)
                current_pos = end
                
                entity_type = None
                
                if flag == "nr":  # 人名
                    entity_type = "PER"
                elif flag == "ns":  # 地名
                    entity_type = "LOC"
                elif flag == "nt":  # 机构团体
                    entity_type = "ORG"
                elif flag == "nz":  # 其他专名
                    entity_type = "ITEM"
                
                if entity_type and len(word) >= 2:
                    entities.append(Entity(
                        name=word,
                        type=entity_type,
                        confidence=0.75,
                        start=start,
                        end=end,
                        source="jieba",
                    ))
        
        except Exception as e:
            print(f"Jieba提取失败: {e}")
        
        return entities
    
    def _extract_with_rules(self, text: str) -> List[Entity]:
        """使用规则提取实体（fallback）"""
        entities = []
        
        # 规则1：对话提取角色名
        dialogue_patterns = [
            re.compile(r'我叫([\u4e00-\u9fff]{2,3})'),
            re.compile(r'([\u4e00-\u9fff]{2,3})(?:冷冷说道?|沉声说道?|淡淡说道?)'),
        ]
        
        for pattern in dialogue_patterns:
            for match in pattern.finditer(text):
                name = match.group(1)
                if len(name) >= 2:
                    entities.append(Entity(
                        name=name,
                        type="PER",
                        confidence=0.8,
                        start=match.start(),
                        end=match.end(),
                        source="rule",
                    ))
        
        # 规则2：地名提取
        location_pattern = re.compile(r'([\u4e00-\u9fff]{2,6})(?:城|镇|村|山|河|湖|海)')
        for match in location_pattern.finditer(text):
            name = match.group(1) + match.group(0)[-1]
            entities.append(Entity(
                name=name,
                type="LOC",
                confidence=0.7,
                start=match.start(),
                end=match.end(),
                source="rule",
            ))
        
        # 去重
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.name not in seen:
                seen.add(entity.name)
                unique_entities.append(entity)
        
        return unique_entities
    
    def extract_characters(self, text: str) -> List[Dict[str, Any]]:
        """提取所有角色名"""
        entities = self.extract(text)
        characters = [e for e in entities if e.type == "PER"]
        return [e.to_dict() for e in characters]
    
    def extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """提取所有地名"""
        entities = self.extract(text)
        locations = [e for e in entities if e.type == "LOC"]
        return [e.to_dict() for e in locations]
    
    def extract_all(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """提取所有实体（分类）"""
        entities = self.extract(text)
        
        result = {
            "characters": [],
            "locations": [],
            "organizations": [],
            "items": [],
        }
        
        for entity in entities:
            if entity.type == "PER":
                result["characters"].append(entity.to_dict())
            elif entity.type == "LOC":
                result["locations"].append(entity.to_dict())
            elif entity.type == "ORG":
                result["organizations"].append(entity.to_dict())
            elif entity.type == "ITEM":
                result["items"].append(entity.to_dict())
        
        return result
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取当前引擎信息"""
        return {
            "preferred_engine": self.preferred_engine,
            "available_engines": {
                "lac": LAC_AVAILABLE,
                "hanlp": HANLP_AVAILABLE,
                "jieba": JIEBA_AVAILABLE,
            },
            "loaded_engines": {
                "lac": self.lac is not None,
                "hanlp": self.hanlp is not None,
                "jieba": JIEBA_AVAILABLE,
            },
        }


def install_ner_dependencies():
    """安装NER依赖"""
    print("安装NER模型依赖：")
    print()
    print("方案1：安装LAC（推荐，百度开源）")
    print("  pip install lac")
    print()
    print("方案2：安装HanLP（更强大，但模型较大）")
    print("  pip install hanlp")
    print()
    print("方案3：安装Jieba（轻量级，已包含posseg）")
    print("  pip install jieba")
    print()
    print("建议：首选LAC，速度快且准确率高。")


if __name__ == "__main__":
    # 测试代码
    test_text = """
    李天看着眼前的王强，沉声说道："我们要快点找到林雪儿。"
    张伟在一旁点头，他们正站在青州城的城门口。
    远处的青云山若隐若现。
    """
    
    print("=" * 60)
    print("智能实体提取测试")
    print("=" * 60)
    
    # 自动选择引擎
    extractor = SmartEntityExtractor(preferred_engine="auto")
    
    print(f"\n引擎信息: {extractor.get_engine_info()}")
    
    print("\n提取结果:")
    result = extractor.extract_all(test_text)
    
    print(f"\n角色: {len(result['characters'])}个")
    for char in result['characters']:
        print(f"  - {char['name']} (置信度: {char['confidence']:.2f})")
    
    print(f"\n地点: {len(result['locations'])}个")
    for loc in result['locations']:
        print(f"  - {loc['name']} (置信度: {loc['confidence']:.2f})")
