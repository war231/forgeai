#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目初始化模块

创建 ForgeAI 项目结构：
- .forgeai/       数据目录
- 1-边界/            样板书与分析结果
- 2-设定/            设定案
- 3-大纲/            大纲文件
- 4-正文/            正文草稿
- 5-审查/            审查报告
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_config, ForgeAIConfig
from .state_manager import StateManager
from .index_manager import IndexManager


# 需要创建的目录结构
PROJECT_DIRS = {
    ".forgeai": "数据目录（状态/索引/配置）",
    "1-边界": "样板书与分析结果",
    "2-设定": "设定案（世界观/金手指/角色）",
    "3-大纲": "总纲/卷纲/章纲",
    "4-正文": "正文草稿",
    "5-审查": "审查报告",
}

# 需要创建的子目录
PROJECT_SUBDIRS = {
    ".forgeai/backups": "自动备份",
    "1-边界/样板书": "对标作品原文",
    "1-边界/分析": "样板书分析结果",
    "2-设定/世界观": "世界观设定",
    "2-设定/金手指": "金手指/系统设定",
    "2-设定/角色": "角色设定",
    "2-设定/势力": "势力/阵营设定",
    "3-大纲/总纲": "全书大纲",
    "3-大纲/卷纲": "卷级大纲",
    "3-大纲/章纲": "章节大纲",
    "4-正文/草稿": "草稿",
    "4-正文/定稿": "定稿",
    "5-审查/六维审查": "六维审查报告",
    "5-审查/去AI味": "去AI味记录",
}


class ProjectInitializer:
    """项目初始化器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self.state_manager = StateManager(self.config)
        self.index_manager = IndexManager(self.config)

    def init(self, project_root: Path | str, project_name: str = "",
             genre: str = "", mode: str = "standard") -> Dict:
        """
        初始化项目

        Args:
            project_root: 项目根目录(ForgeAI根目录)
            project_name: 项目名称
            genre: 题材
            mode: 启动模式 (standard/flexible/reference)

        Returns:
            初始化结果
        """
        root = Path(project_root).resolve()
        
        # 如果提供了项目名称,在 projects/ 目录下创建
        # 但如果 root 已经是以项目名结尾的路径,则直接使用
        if project_name:
            # 检查 root 是否已经包含了项目名
            if root.name == project_name or (root / project_name).exists():
                # root 已经指向项目目录,直接使用
                root.mkdir(exist_ok=True)
            else:
                # 在 root/projects/ 下创建
                projects_dir = root / "projects"
                projects_dir.mkdir(exist_ok=True)
                root = projects_dir / project_name
                root.mkdir(exist_ok=True)
        
        created_dirs = []
        created_files = []

        # 1. 创建目录结构
        for dir_path, desc in PROJECT_DIRS.items():
            full_path = root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_path)

        for dir_path, desc in PROJECT_SUBDIRS.items():
            full_path = root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_path)

        # 2. 创建 SOLOENT.md（项目总控文件）
        soloent_path = root / "SOLOENT.md"
        if not soloent_path.exists():
            soloent_content = self._generate_soloent(project_name, genre, mode)
            soloent_path.write_text(soloent_content, encoding="utf-8")
            created_files.append("SOLOENT.md")

        # 3. 创建 .gitignore
        gitignore_path = root / ".gitignore"
        if not gitignore_path.exists():
            gitignore_content = """# ForgeAI
.forgeai/*.db
.forgeai/*.lock
.forgeai/backups/
*.tmp
"""
            gitignore_path.write_text(gitignore_content, encoding="utf-8")
            created_files.append(".gitignore")

        # 4. 初始化配置
        self.config.set_project_root(root)
        self.config.save_config()
        created_files.append(".forgeai/config.json")

        # 5. 初始化 state.json
        state = self.state_manager.load()
        state["project"]["name"] = project_name or root.name
        state["project"]["genre"] = genre
        state["project"]["mode"] = mode
        state["project"]["created_at"] = datetime.now().isoformat()
        self.state_manager.save(state)
        created_files.append(".forgeai/state.json")

        # 6. 初始化 index.db
        self.index_manager.init_db()
        created_files.append(".forgeai/index.db")

        return {
            "status": "success",
            "project_root": str(root),
            "created_dirs": created_dirs,
            "created_files": created_files,
            "mode": mode,
        }

    def _generate_soloent(self, name: str, genre: str, mode: str) -> str:
        """生成 SOLOENT.md 模板"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""# SOLOENT.md - ForgeAI 项目总控

> 生成时间: {now}
> 项目: {name or "未命名"}
> 题材: {genre or "未设定"}
> 模式: {mode}

---

## §1 项目信息

- **项目名称**: {name or "未命名"}
- **题材类型**: {genre or "未设定"}
- **启动模式**: {mode} (standard=标准 / flexible=灵活 / reference=参考)
- **目标字数**: 待定
- **创建日期**: {now}

## §2 创作进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| 样板书分析 | ⬜ 待开始 | - |
| 方向定义 | ⬜ 待开始 | - |
| 创意脑暴 | ⬜ 待开始 | - |
| 大纲规划 | ⬜ 待开始 | - |
| 正文写作 | ⬜ 待开始 | 第0章 |
| 审查润色 | ⬜ 待开始 | - |

## §3 核心设定摘要

### 世界观
> 待填写

### 金手指
> 待填写

### 主角
> 待填写

## §4 卷章结构

| 卷 | 名称 | 章节范围 | 状态 |
|----|------|---------|------|
| 1 | 待定 | 第1-?章 | ⬜ |

## §5 角色状态追踪

> 写作过程中自动更新

## §6 伏笔追踪

> 写作过程中自动更新

| ID | 伏笔描述 | 埋设章节 | 预期回收 | 状态 |
|----|---------|---------|---------|------|
| - | - | - | - | - |

## §7 Strand 节奏追踪

> 写作过程中自动更新

- Quest（主线60%）: 0个
- Fire（爽点20%）: 0个
- Constellation（情感20%）: 0个

## §8 追读力趋势

> 写作过程中自动更新

## §9 审查记录

> 写作过程中自动更新

---

*此文件由 ForgeAI 自动生成并维护，请勿手动修改 §5-§9*
"""
