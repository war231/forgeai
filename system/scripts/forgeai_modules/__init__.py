"""
ForgeAI Python Backend - 长篇小说创作套件后端

核心模块：
- config: 配置管理
- state_manager: 状态管理（state.json）
- index_manager: SQLite 索引（实体/场景/追读力）
- rag_adapter: RAG 检索（向量+BM25 混合）
- context_extractor: 上下文提取
- humanize_scorer: 去AI味评分器
- init_project: 项目初始化
"""

__version__ = "1.1.0"
