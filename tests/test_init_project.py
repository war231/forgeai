#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目初始化模块测试"""

import pytest
import json
from pathlib import Path

from forgeai_modules.init_project import (
    ProjectInitializer, PROJECT_DIRS, PROJECT_SUBDIRS
)


class TestProjectDirs:
    """项目目录结构测试"""

    def test_project_dirs_defined(self):
        """项目目录已定义"""
        assert ".forgeai" in PROJECT_DIRS
        assert "1-边界" in PROJECT_DIRS
        assert "2-设定" in PROJECT_DIRS
        assert "3-大纲" in PROJECT_DIRS
        assert "4-正文" in PROJECT_DIRS
        assert "5-审查" in PROJECT_DIRS

    def test_project_subdirs_defined(self):
        """项目子目录已定义"""
        assert ".forgeai/backups" in PROJECT_SUBDIRS
        assert "2-设定/世界观" in PROJECT_SUBDIRS
        assert "3-大纲/总纲" in PROJECT_SUBDIRS


class TestProjectInitializerInit:
    """初始化器创建测试"""

    def test_init_basic(self, temp_project):
        """基本创建"""
        initializer = ProjectInitializer()

        assert initializer.config is not None
        assert initializer.state_manager is not None
        assert initializer.index_manager is not None


class TestProjectInit:
    """项目初始化测试"""

    def test_init_creates_dirs(self, temp_project):
        """创建目录结构"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project, "测试项目", "玄幻", "standard")

        assert result["status"] == "success"

        # 检查主要目录
        for dir_path in PROJECT_DIRS.keys():
            full_path = temp_project / dir_path
            assert full_path.exists(), f"目录 {dir_path} 未创建"

    def test_init_creates_subdirs(self, temp_project):
        """创建子目录"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project)

        # 检查子目录
        for dir_path in PROJECT_SUBDIRS.keys():
            full_path = temp_project / dir_path
            assert full_path.exists(), f"子目录 {dir_path} 未创建"

    def test_init_creates_soloent(self, temp_project):
        """创建 SOLOENT.md"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project, "我的小说", "都市", "standard")

        soloent_path = temp_project / "SOLOENT.md"
        assert soloent_path.exists()

        content = soloent_path.read_text(encoding="utf-8")
        assert "我的小说" in content
        assert "都市" in content

    def test_init_creates_gitignore(self, temp_project):
        """创建 .gitignore"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project)

        gitignore_path = temp_project / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text(encoding="utf-8")
        assert ".forgeai" in content

    def test_init_creates_state(self, temp_project):
        """创建状态文件"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project, "测试项目", "仙侠")

        state_path = temp_project / ".forgeai" / "state.json"
        assert state_path.exists()

        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["project"]["name"] == "测试项目"
        assert state["project"]["genre"] == "仙侠"

    def test_init_creates_index_db(self, temp_project):
        """创建索引数据库"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project)

        db_path = temp_project / ".forgeai" / "index.db"
        assert db_path.exists()

    def test_init_different_modes(self, temp_project):
        """不同启动模式"""
        initializer = ProjectInitializer()

        for mode in ["standard", "flexible", "reference"]:
            result = initializer.init(temp_project, mode=mode)
            assert result["mode"] == mode

    def test_init_existing_project(self, temp_project):
        """已存在项目不覆盖"""
        # 第一次初始化
        initializer = ProjectInitializer()
        result1 = initializer.init(temp_project, "项目1")

        # 修改 SOLOENT.md
        soloent_path = temp_project / "SOLOENT.md"
        original_content = soloent_path.read_text(encoding="utf-8")
        modified_content = original_content + "\n\n## 自定义内容"
        soloent_path.write_text(modified_content, encoding="utf-8")

        # 第二次初始化
        result2 = initializer.init(temp_project, "项目2")

        # SOLOENT.md 应该保持修改
        current_content = soloent_path.read_text(encoding="utf-8")
        assert "自定义内容" in current_content


class TestGenerateSoloent:
    """SOLOENT 生成测试"""

    def test_generate_soloent_basic(self, temp_project):
        """基本生成"""
        initializer = ProjectInitializer()

        content = initializer._generate_soloent("测试项目", "玄幻", "standard")

        assert "# SOLOENT.md" in content
        assert "测试项目" in content
        assert "玄幻" in content
        assert "standard" in content

    def test_generate_soloent_sections(self, temp_project):
        """包含必要章节"""
        initializer = ProjectInitializer()

        content = initializer._generate_soloent("测试", "都市", "flexible")

        assert "§1 项目信息" in content
        assert "§2 创作进度" in content
        assert "§3 核心设定摘要" in content
        assert "§4 卷章结构" in content

    def test_generate_soloent_empty_values(self, temp_project):
        """空值处理"""
        initializer = ProjectInitializer()

        content = initializer._generate_soloent("", "", "standard")

        assert "未命名" in content
        assert "未设定" in content


class TestInitResult:
    """初始化结果测试"""

    def test_result_structure(self, temp_project):
        """结果结构"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project, "测试")

        assert "status" in result
        assert "project_root" in result
        assert "created_dirs" in result
        assert "created_files" in result
        assert "mode" in result

    def test_result_created_files(self, temp_project):
        """创建的文件列表"""
        initializer = ProjectInitializer()
        result = initializer.init(temp_project)

        assert "SOLOENT.md" in result["created_files"]
        assert ".gitignore" in result["created_files"]
        assert ".forgeai/state.json" in result["created_files"]
