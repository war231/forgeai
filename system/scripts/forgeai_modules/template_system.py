#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板系统

支持自定义创作模板
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import get_config, ForgeAIConfig
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChapterTemplate:
    """章节模板"""
    name: str
    description: str
    genre: str = ""
    
    # 结构模板
    structure: Dict[str, Any] = field(default_factory=dict)
    
    # 钩子模板
    hooks: List[Dict[str, str]] = field(default_factory=list)
    
    # 爽点模板
    cool_points: List[Dict[str, str]] = field(default_factory=list)
    
    # 微兑现模板
    micro_payoffs: List[Dict[str, str]] = field(default_factory=list)
    
    # 写作指导
    writing_guidance: Dict[str, Any] = field(default_factory=dict)
    
    # 提示词模板
    prompt_template: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "structure": self.structure,
            "hooks": self.hooks,
            "cool_points": self.cool_points,
            "micro_payoffs": self.micro_payoffs,
            "writing_guidance": self.writing_guidance,
            "prompt_template": self.prompt_template,
        }


# 内置模板
BUILTIN_TEMPLATES = {
    "standard": ChapterTemplate(
        name="standard",
        description="标准章节模板",
        genre="通用",
        structure={
            "scenes": [
                {"name": "开场", "ratio": 0.3, "purpose": "建立场景，引入冲突"},
                {"name": "发展", "ratio": 0.4, "purpose": "推进情节，展开冲突"},
                {"name": "收尾", "ratio": 0.3, "purpose": "解决冲突，设置钩子"},
            ],
            "word_count": {"min": 2500, "max": 3500, "target": 3000},
        },
        hooks=[
            {"type": "悬念钩", "position": "章末", "description": "留下悬念，驱动下一章"},
        ],
        cool_points=[
            {"type": "装逼打脸", "probability": 0.6},
            {"type": "扮猪吃虎", "probability": 0.4},
        ],
        micro_payoffs=[
            {"type": "能力兑现", "probability": 0.5},
            {"type": "关系兑现", "probability": 0.3},
        ],
        writing_guidance={
            "pov": "第三人称",
            "tense": "过去时",
            "style": "网文风格，节奏紧凑",
        },
        prompt_template="",
    ),
    
    "climax": ChapterTemplate(
        name="climax",
        description="高潮章节模板",
        genre="通用",
        structure={
            "scenes": [
                {"name": "铺垫", "ratio": 0.2, "purpose": "建立紧张氛围"},
                {"name": "高潮", "ratio": 0.5, "purpose": "核心冲突爆发"},
                {"name": "余波", "ratio": 0.3, "purpose": "展示后果，收束线索"},
            ],
            "word_count": {"min": 3000, "max": 4000, "target": 3500},
        },
        hooks=[
            {"type": "危机钩", "position": "章内", "description": "危机感贯穿全章"},
            {"type": "渴望钩", "position": "章末", "description": "期待后续发展"},
        ],
        cool_points=[
            {"type": "越级反杀", "probability": 0.8},
            {"type": "身份掉马", "probability": 0.6},
            {"type": "打脸权威", "probability": 0.5},
        ],
        micro_payoffs=[
            {"type": "能力兑现", "probability": 0.7},
            {"type": "认可兑现", "probability": 0.6},
            {"type": "资源兑现", "probability": 0.5},
        ],
        writing_guidance={
            "pov": "第三人称",
            "tense": "过去时",
            "style": "高潮节奏，紧张刺激",
        },
        prompt_template="",
    ),
    
    "transition": ChapterTemplate(
        name="transition",
        description="过渡章节模板",
        genre="通用",
        structure={
            "scenes": [
                {"name": "回顾", "ratio": 0.3, "purpose": "回顾前情，承上启下"},
                {"name": "日常", "ratio": 0.4, "purpose": "日常互动，人物塑造"},
                {"name": "铺垫", "ratio": 0.3, "purpose": "铺垫未来，设置伏笔"},
            ],
            "word_count": {"min": 2000, "max": 3000, "target": 2500},
        },
        hooks=[
            {"type": "情绪钩", "position": "章内", "description": "情感互动"},
            {"type": "悬念钩", "position": "章末", "description": "暗示未来"},
        ],
        cool_points=[
            {"type": "甜蜜超预期", "probability": 0.5},
            {"type": "迪化误解", "probability": 0.4},
        ],
        micro_payoffs=[
            {"type": "关系兑现", "probability": 0.6},
            {"type": "情绪兑现", "probability": 0.5},
        ],
        writing_guidance={
            "pov": "第三人称",
            "tense": "过去时",
            "style": "轻松节奏，日常感强",
        },
        prompt_template="",
    ),
    
    "romance": ChapterTemplate(
        name="romance",
        description="感情章节模板",
        genre="言情",
        structure={
            "scenes": [
                {"name": "相遇", "ratio": 0.3, "purpose": "男女主相遇/互动"},
                {"name": "冲突", "ratio": 0.3, "purpose": "感情冲突/误会"},
                {"name": "和解", "ratio": 0.4, "purpose": "感情升温/甜蜜"},
            ],
            "word_count": {"min": 2500, "max": 3500, "target": 3000},
        },
        hooks=[
            {"type": "情绪钩", "position": "章内", "description": "情感波动"},
            {"type": "选择钩", "position": "章末", "description": "感情抉择"},
        ],
        cool_points=[
            {"type": "甜蜜超预期", "probability": 0.7},
            {"type": "身份掉马", "probability": 0.3},
        ],
        micro_payoffs=[
            {"type": "关系兑现", "probability": 0.7},
            {"type": "情绪兑现", "probability": 0.6},
            {"type": "认可兑现", "probability": 0.4},
        ],
        writing_guidance={
            "pov": "第三人称",
            "tense": "过去时",
            "style": "言情风格，细腻情感",
        },
        prompt_template="",
    ),
}


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self._templates: Dict[str, ChapterTemplate] = {}
        self._loaded = False
    
    def load(self) -> None:
        """加载模板"""
        if self._loaded:
            return
        
        # 加载内置模板
        self._templates = BUILTIN_TEMPLATES.copy()
        
        # 加载自定义模板
        self._load_custom_templates()
        
        self._loaded = True
    
    def _load_custom_templates(self) -> None:
        """加载自定义模板"""
        # 查找模板目录
        templates_dir = self._find_templates_dir()
        if not templates_dir:
            return
        
        # 加载 JSON 模板
        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, encoding="utf-8") as f:
                    data = json.load(f)
                
                template = ChapterTemplate(
                    name=data.get("name", template_file.stem),
                    description=data.get("description", ""),
                    genre=data.get("genre", ""),
                    structure=data.get("structure", {}),
                    hooks=data.get("hooks", []),
                    cool_points=data.get("cool_points", []),
                    micro_payoffs=data.get("micro_payoffs", []),
                    writing_guidance=data.get("writing_guidance", {}),
                    prompt_template=data.get("prompt_template", ""),
                )
                
                self._templates[template.name] = template
                logger.info(f"加载模板: {template.name}")
            
            except Exception as e:
                logger.warning(f"加载模板失败 {template_file}: {e}")
    
    def _find_templates_dir(self) -> Optional[Path]:
        """查找模板目录"""
        # 1. 项目目录下的 system/templates/
        if self.config.project_root:
            path = self.config.project_root.parent / "system" / "templates"
            if path.is_dir():
                return path
        
        # 2. ForgeAI 安装目录下的 system/templates/
        forgeai_root = Path(__file__).parent.parent.parent
        path = forgeai_root / "templates"
        if path.is_dir():
            return path
        
        return None
    
    def get_template(self, name: str) -> Optional[ChapterTemplate]:
        """获取模板"""
        if not self._loaded:
            self.load()
        
        return self._templates.get(name)
    
    def list_templates(self) -> List[str]:
        """列出所有模板"""
        if not self._loaded:
            self.load()
        
        return list(self._templates.keys())
    
    def create_template(self, template: ChapterTemplate) -> None:
        """创建模板"""
        if not self._loaded:
            self.load()
        
        self._templates[template.name] = template
    
    def save_template(self, name: str, output_dir: Path) -> Path:
        """保存模板到文件"""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"模板不存在: {name}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{name}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"模板已保存: {output_file}")
        
        return output_file
    
    def apply_template(self, 
                      template_name: str,
                      chapter_num: int,
                      context: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用模板
        
        Args:
            template_name: 模板名称
            chapter_num: 章节号
            context: 上下文
        
        Returns:
            应用模板后的配置
        """
        template = self.get_template(template_name)
        if not template:
            template = self.get_template("standard")
        
        if not template:
            return {}
        
        # 应用结构
        structure = template.structure.copy()
        
        # 应用钩子
        hooks = []
        for hook_template in template.hooks:
            hooks.append({
                "type": hook_template.get("type", "悬念钩"),
                "position": hook_template.get("position", "章末"),
                "description": hook_template.get("description", ""),
            })
        
        # 应用爽点
        cool_points = []
        import random
        for cp_template in template.cool_points:
            if random.random() < cp_template.get("probability", 0.5):
                cool_points.append({
                    "type": cp_template.get("type", "装逼打脸"),
                })
        
        # 应用微兑现
        micro_payoffs = []
        for mp_template in template.micro_payoffs:
            if random.random() < mp_template.get("probability", 0.5):
                micro_payoffs.append({
                    "type": mp_template.get("type", "能力兑现"),
                })
        
        return {
            "template_name": template.name,
            "structure": structure,
            "hooks": hooks,
            "cool_points": cool_points,
            "micro_payoffs": micro_payoffs,
            "writing_guidance": template.writing_guidance,
        }
    
    def generate_prompt_from_template(self,
                                     template_name: str,
                                     chapter_num: int,
                                     context: Dict[str, Any]) -> str:
        """从模板生成提示词"""
        template = self.get_template(template_name)
        if not template:
            return ""
        
        # 如果有自定义提示词模板，使用它
        if template.prompt_template:
            # 替换变量
            prompt = template.prompt_template
            prompt = prompt.replace("{chapter_num}", str(chapter_num))
            
            # 替换上下文变量
            for key, value in context.items():
                if isinstance(value, str):
                    prompt = prompt.replace(f"{{{key}}}", value)
            
            return prompt
        
        # 否则生成默认提示词
        applied = self.apply_template(template_name, chapter_num, context)
        
        lines = [
            f"# 第 {chapter_num} 章创作任务",
            "",
            f"## 模板: {template.name}",
            f"描述: {template.description}",
            "",
            "## 结构要求",
            "",
        ]
        
        for scene in applied["structure"].get("scenes", []):
            lines.append(f"- {scene['name']}: {scene['purpose']} ({scene['ratio']*100:.0f}%)")
        
        lines.append("")
        lines.append(f"目标字数: {applied['structure'].get('word_count', {}).get('target', 3000)}")
        lines.append("")
        
        if applied["hooks"]:
            lines.append("## 钩子设计")
            for hook in applied["hooks"]:
                lines.append(f"- {hook['type']} ({hook['position']}): {hook['description']}")
            lines.append("")
        
        if applied["cool_points"]:
            lines.append("## 爽点设计")
            for cp in applied["cool_points"]:
                lines.append(f"- {cp['type']}")
            lines.append("")
        
        if applied["micro_payoffs"]:
            lines.append("## 微兑现")
            for mp in applied["micro_payoffs"]:
                lines.append(f"- {mp['type']}")
            lines.append("")
        
        lines.append("## 写作指导")
        for key, value in applied["writing_guidance"].items():
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)


# 便捷函数
def get_template_manager(config: Optional[ForgeAIConfig] = None) -> TemplateManager:
    """获取模板管理器"""
    return TemplateManager(config)


def get_template(name: str, config: Optional[ForgeAIConfig] = None) -> Optional[ChapterTemplate]:
    """获取模板"""
    manager = TemplateManager(config)
    return manager.get_template(name)
