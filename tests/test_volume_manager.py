#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多卷大纲管理器测试"""

import pytest
import json
from pathlib import Path

from forgeai_modules.volume_manager import VolumeManager, VolumeInfo


class TestVolumeInfo:
    """卷信息数据类测试"""

    def test_create_volume_info(self):
        """创建卷信息"""
        volume = VolumeInfo(
            volume_id=1,
            name="第一卷",
            chapter_count=10,
            word_count=50000,
            status="writing"
        )

        assert volume.volume_id == 1
        assert volume.name == "第一卷"
        assert volume.chapter_count == 10
        assert volume.word_count == 50000
        assert volume.status == "writing"

    def test_volume_info_defaults(self):
        """默认值"""
        volume = VolumeInfo(volume_id=1, name="测试卷")

        assert volume.chapter_count == 0
        assert volume.word_count == 0
        assert volume.status == "draft"
        assert volume.created_at is not None
        assert volume.updated_at is not None

    def test_volume_info_to_dict(self):
        """转换为字典"""
        volume = VolumeInfo(
            volume_id=1,
            name="第一卷",
            chapter_count=10,
            word_count=50000,
            status="completed"
        )

        d = volume.to_dict()

        assert d["volume_id"] == 1
        assert d["name"] == "第一卷"
        assert d["chapter_count"] == 10
        assert d["word_count"] == 50000
        assert d["status"] == "completed"


class TestVolumeManagerInit:
    """管理器初始化测试"""

    def test_init_paths(self, temp_project):
        """初始化路径"""
        mgr = VolumeManager(temp_project)

        assert mgr.project_root == temp_project
        assert mgr.forgeai_dir == temp_project / ".forgeai"
        assert mgr.state_file == temp_project / ".forgeai" / "state.json"
        assert mgr.outline_dir == temp_project / "3-大纲"
        assert mgr.content_dir == temp_project / "4-正文"


class TestListVolumes:
    """列出卷测试"""

    def test_list_volumes_empty(self, temp_project):
        """空项目"""
        mgr = VolumeManager(temp_project)
        result = mgr.list_volumes()

        assert result["total_volumes"] == 0
        assert result["volumes"] == []

    def test_list_volumes_with_data(self, temp_project):
        """有卷数据"""
        # 创建大纲目录和卷
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)

        # 创建章节大纲
        (volume_dir / "第1章.md").write_text("大纲内容", encoding="utf-8")
        (volume_dir / "第2章.md").write_text("大纲内容", encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.list_volumes()

        assert result["total_volumes"] == 1
        assert len(result["volumes"]) == 1
        assert result["volumes"][0]["name"] == "第一卷"
        assert result["volumes"][0]["chapter_count"] == 2


class TestAddVolume:
    """添加卷测试"""

    def test_add_volume_first(self, temp_project):
        """添加第一卷"""
        # 创建必要目录
        outline_dir = temp_project / "3-大纲"
        outline_dir.mkdir(parents=True)

        # 创建状态文件
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({"progress": {}}), encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.add_volume()

        assert result["status"] == "ok"
        assert result["volume_id"] == 1
        assert (outline_dir / "第一卷").exists()

    def test_add_volume_with_name(self, temp_project):
        """添加指定名称的卷"""
        outline_dir = temp_project / "3-大纲"
        outline_dir.mkdir(parents=True)

        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({"progress": {}}), encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.add_volume(name="序章卷")

        assert result["status"] == "ok"
        assert result["name"] == "序章卷"
        assert (outline_dir / "序章卷").exists()


class TestGetVolumeStatus:
    """获取卷状态测试"""

    def test_get_volume_status_not_found(self, temp_project):
        """卷不存在"""
        mgr = VolumeManager(temp_project)
        result = mgr.get_volume_status(999)

        assert result is None

    def test_get_volume_status_basic(self, temp_project):
        """基本状态获取"""
        # 创建卷
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)

        # 创建章节
        (volume_dir / "第1章.md").write_text("大纲内容一", encoding="utf-8")
        (volume_dir / "第2章.md").write_text("大纲内容二", encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.get_volume_status(1)

        assert result is not None
        assert result["volume"]["volume_id"] == 1
        assert result["volume"]["chapter_count"] == 2
        assert len(result["chapters"]) == 2

    def test_get_volume_status_with_content(self, temp_project):
        """有正文的卷状态"""
        # 创建大纲卷
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)
        (volume_dir / "第1章.md").write_text("大纲", encoding="utf-8")

        # 创建正文卷
        content_dir = temp_project / "4-正文"
        content_volume_dir = content_dir / "第一卷"
        content_volume_dir.mkdir(parents=True)
        (content_volume_dir / "第1章.md").write_text("正文内容" * 100, encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.get_volume_status(1)

        assert result is not None
        assert result["chapters"][0]["written"] is True
        assert result["chapters"][0]["content_words"] > 0
        assert result["completion_rate"] == 100.0


class TestSetCurrentVolume:
    """设置当前卷测试"""

    def test_set_current_volume_success(self, temp_project):
        """成功设置"""
        # 创建卷
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)

        # 创建状态文件
        forgeai_dir = temp_project / ".forgeai"
        forgeai_dir.mkdir(parents=True)
        state_file = forgeai_dir / "state.json"
        state_file.write_text(json.dumps({"progress": {}}), encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.set_current_volume(1)

        assert result["status"] == "ok"
        assert result["volume_id"] == 1

    def test_set_current_volume_not_found(self, temp_project):
        """卷不存在"""
        mgr = VolumeManager(temp_project)
        result = mgr.set_current_volume(999)

        assert result["status"] == "error"
        assert "不存在" in result["message"]


class TestCompleteVolume:
    """完成卷测试"""

    def test_complete_volume_not_found(self, temp_project):
        """卷不存在"""
        mgr = VolumeManager(temp_project)
        result = mgr.complete_volume(999)

        assert result["status"] == "error"

    def test_complete_volume_incomplete(self, temp_project):
        """卷未完成"""
        # 创建卷（有章节但无正文）
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)
        (volume_dir / "第1章.md").write_text("大纲", encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.complete_volume(1)

        assert result["status"] == "error"
        assert "完成度" in result["message"]

    def test_complete_volume_success(self, temp_project):
        """成功完成卷"""
        # 创建大纲卷
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)
        (volume_dir / "第1章.md").write_text("大纲", encoding="utf-8")

        # 创建正文卷
        content_dir = temp_project / "4-正文"
        content_volume_dir = content_dir / "第一卷"
        content_volume_dir.mkdir(parents=True)
        (content_volume_dir / "第1章.md").write_text("正文内容" * 100, encoding="utf-8")

        mgr = VolumeManager(temp_project)
        result = mgr.complete_volume(1)

        assert result["status"] == "ok"
        assert (volume_dir / "VOLUME_COMPLETED.md").exists()


class TestGetVolumeSummary:
    """卷大纲汇总测试"""

    def test_get_summary_not_found(self, temp_project):
        """卷不存在"""
        mgr = VolumeManager(temp_project)
        result = mgr.get_volume_summary(999)

        assert result is None

    def test_get_summary_basic(self, temp_project):
        """基本汇总"""
        # 创建卷
        outline_dir = temp_project / "3-大纲"
        volume_dir = outline_dir / "第一卷"
        volume_dir.mkdir(parents=True)

        (volume_dir / "第1章.md").write_text("## 第1章大纲\n\n主角出场。", encoding="utf-8")
        (volume_dir / "第2章.md").write_text("## 第2章大纲\n\n主角修炼。", encoding="utf-8")

        mgr = VolumeManager(temp_project)
        summary = mgr.get_volume_summary(1)

        assert summary is not None
        assert "第一卷" in summary
        assert "第1章" in summary
        assert "第2章" in summary
        assert "主角出场" in summary


class TestScanVolumes:
    """扫描卷测试"""

    def test_scan_volumes_multiple(self, temp_project):
        """扫描多个卷"""
        outline_dir = temp_project / "3-大纲"

        # 创建多个卷
        for i in range(1, 4):
            volume_dir = outline_dir / f"第{i}卷"
            volume_dir.mkdir(parents=True)
            (volume_dir / "第1章.md").write_text("大纲", encoding="utf-8")

        mgr = VolumeManager(temp_project)
        volumes = mgr._scan_volumes()

        assert len(volumes) == 3
        assert 1 in volumes
        assert 2 in volumes
        assert 3 in volumes

    def test_scan_volumes_ignores_invalid(self, temp_project):
        """忽略无效目录"""
        outline_dir = temp_project / "3-大纲"

        # 创建有效卷
        (outline_dir / "第一卷").mkdir(parents=True)

        # 创建无效目录
        (outline_dir / "其他目录").mkdir(parents=True)
        (outline_dir / "草稿").mkdir(parents=True)

        mgr = VolumeManager(temp_project)
        volumes = mgr._scan_volumes()

        assert len(volumes) == 1
        assert 1 in volumes
