---
wave: 2
depends_on: [01]
files_modified:
  - system/scripts/forgeai_modules/entity_extractor_v3_ner.py
  - system/scripts/forgeai_modules/config.py
autonomous: true
requirements_addressed: [REQ-006]
---

<objective>
优化实体提取性能，添加缓存机制和去重逻辑
</objective>

<tasks>
<task id="1" type="execute">
<read_first>
- system/scripts/forgeai_modules/entity_extractor_v3_ner.py (file being modified)
- system/scripts/forgeai_modules/config.py (config module)
</read_first>

<action>
添加实体提取结果缓存：

1. 在 `config.py` 中添加缓存配置：
```python
# 实体提取缓存配置
ENTITY_CACHE_ENABLED = True
ENTITY_CACHE_TTL = 300  # 5分钟
```

2. 在 `entity_extractor_v3_ner.py` 中添加缓存装饰器：
```python
from functools import lru_cache
import hashlib
from config import ENTITY_CACHE_ENABLED, ENTITY_CACHE_TTL

class EntityExtractor:
    def __init__(self):
        self._cache = {} if ENTITY_CACHE_ENABLED else None
        self._cache_timestamps = {} if ENTITY_CACHE_ENABLED else None
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_from_cache(self, text: str):
        """从缓存获取结果"""
        if not ENTITY_CACHE_ENABLED:
            return None
        
        key = self._get_cache_key(text)
        if key in self._cache:
            import time
            if time.time() - self._cache_timestamps[key] < ENTITY_CACHE_TTL:
                logger.debug(f"缓存命中：{key[:8]}")
                return self._cache[key]
        return None
    
    def _save_to_cache(self, text: str, result):
        """保存结果到缓存"""
        if not ENTITY_CACHE_ENABLED:
            return
        
        key = self._get_cache_key(text)
        import time
        self._cache[key] = result
        self._cache_timestamps[key] = time.time()
        logger.debug(f"缓存保存：{key[:8]}")
```

3. 修改 `extract` 方法使用缓存：
```python
def extract(self, text: str) -> dict:
    # 检查缓存
    cached = self._get_from_cache(text)
    if cached:
        return cached
    
    # 执行提取
    result = self._extract_impl(text)
    
    # 保存缓存
    self._save_to_cache(text, result)
    
    return result
```
</action>

<acceptance_criteria>
- `config.py contains "ENTITY_CACHE_ENABLED"`
- `config.py contains "ENTITY_CACHE_TTL"`
- `entity_extractor_v3_ner.py contains "_get_cache_key"`
- `entity_extractor_v3_ner.py contains "_get_from_cache"`
- `entity_extractor_v3_ner.py contains "_save_to_cache"`
</acceptance_criteria>
</task>

<task id="2" type="execute">
<read_first>
- system/scripts/forgeai_modules/entity_extractor_v3_ner.py (file being modified)
</read_first>

<action>
添加实体去重逻辑：

```python
def _deduplicate_entities(self, entities: list) -> list:
    """去重实体列表"""
    seen = set()
    unique_entities = []
    
    for entity in entities:
        # 使用实体名称和类型作为唯一标识
        key = f"{entity.get('name', '')}_{entity.get('type', '')}"
        if key not in seen:
            seen.add(key)
            unique_entities.append(entity)
        else:
            logger.debug(f"去重实体：{key}")
    
    return unique_entities

def _extract_impl(self, text: str) -> dict:
    """实际提取实现"""
    # ... 现有提取逻辑 ...
    
    # 添加去重步骤
    entities = self._deduplicate_entities(entities)
    
    return {
        "entities": entities,
        "count": len(entities)
    }
```
</action>

<acceptance_criteria>
- `entity_extractor_v3_ner.py contains "_deduplicate_entities"`
- `entity_extractor_v3_ner.py contains "seen = set()"`
- `entity_extractor_v3_ner.py contains "logger.debug(f\"去重实体"`
</acceptance_criteria>
</task>

<task id="3" type="execute">
<read_first>
- system/scripts/forgeai_modules/entity_extractor_v3_ner.py (file being modified)
</read_first>

<action>
添加性能监控日志：

```python
import time

def extract(self, text: str) -> dict:
    start_time = time.time()
    
    # ... 现有逻辑 ...
    
    elapsed = time.time() - start_time
    logger.info(f"实体提取完成：耗时 {elapsed:.2f}s，提取 {len(result.get('entities', []))} 个实体")
    
    return result
```
</action>

<acceptance_criteria>
- `entity_extractor_v3_ner.py contains "start_time = time.time()"`
- `entity_extractor_v3_ner.py contains "实体提取完成：耗时"`
</acceptance_criteria>
</task>
</tasks>

<verification>
1. 运行实体提取命令，检查缓存是否生效
2. 检查日志输出的性能数据
3. 验证去重功能（重复实体应被过滤）
</verification>

<must_haves>
- 缓存必须可配置（开关、TTL）
- 去重逻辑必须正确
- 必须添加性能日志
- 不能破坏现有提取功能
</must_haves>
