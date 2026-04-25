"""
单元测试：book_analyzer.py 模块

测试样板书拆解分析功能：
- 章节解析（中文/英文/方括号格式）
- 结构分析（字数统计、节奏比例）
- 爽点分析（关键词匹配、密度计算）
- 文风分析（句长、对白比例、开头/结尾模式）
- 报告生成
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.book_analyzer import (
    BookAnalyzer, Chapter, TrophyPoint, AnalysisResult,
    TROPHY_TYPES, OPENING_PATTERNS, ENDING_PATTERNS,
)


# ========== 测试用文本 ==========

SAMPLE_CHINESE_NOVEL = """
第一章 开始

李明站在山顶上，望着远方的城市。风吹过他的脸庞，带来一丝凉意。

"终于到了，"他自言自语道。

他回想起这一路走来的艰辛。从一个小村庄出发，历经千辛万苦，终于来到了这座传说中的城市。

第二章 冲突

街道上人来人往，各种叫卖声此起彼伏。李明感到一阵迷茫。

就在这时，一个声音传来："你是新来的吧？"

李明转过身，看到少女正微笑着看着他。没想到她竟然是宗主的女儿。打脸了那些嘲笑他的人。

"我是林雪，"少女说道。她不屑地看了看旁边的长老。

第三章 战斗

李明心中不禁暗想，这次危机必须面对。他越级反杀了一只妖兽，震惊了所有人。

这场战斗爆发得非常突然。他竟然在不可能的情况下获得了胜利。

然而，究竟前方还有什么在等待着他？
"""

SAMPLE_ENGLISH_NOVEL = """
Chapter 1 The Beginning

Li Ming stood on the mountain top, looking at the distant city.

Chapter 2 The Conflict

The streets were bustling with people. Li Ming felt confused.

Chapter 3 The Battle

The battle erupted suddenly. He achieved victory against all odds.
"""

SAMPLE_NO_CHAPTERS = """
这是一段没有章节标记的文本。
只有普通的段落内容。
没有第X章的标记。
"""


class TestChapterParsing:
    """测试章节解析"""

    def test_parse_chinese_chapters(self):
        """解析中文章节格式"""
        analyzer = BookAnalyzer(verbose=False)
        chapters = analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)

        assert len(chapters) == 3
        assert chapters[0].title == "第一章 开始"
        assert chapters[1].title == "第二章 冲突"
        assert chapters[2].title == "第三章 战斗"

    def test_parse_english_chapters(self):
        """解析英文章节格式"""
        analyzer = BookAnalyzer(verbose=False)
        chapters = analyzer.load_chapters_from_text(SAMPLE_ENGLISH_NOVEL)

        assert len(chapters) == 3
        assert chapters[1].index == 2

    def test_parse_no_chapters(self):
        """无章节标记时作为单章处理"""
        analyzer = BookAnalyzer(verbose=False)
        chapters = analyzer.load_chapters_from_text(SAMPLE_NO_CHAPTERS)

        assert len(chapters) == 1
        assert chapters[0].index == 1

    def test_word_count_populated(self):
        """章节字数自动计算"""
        analyzer = BookAnalyzer(verbose=False)
        chapters = analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)

        for ch in chapters:
            assert ch.word_count > 0

    def test_load_from_file_not_found(self):
        """文件不存在时抛出异常"""
        analyzer = BookAnalyzer(verbose=False)
        with pytest.raises(FileNotFoundError):
            analyzer.load_chapters_from_file("/nonexistent/path.txt")

    def test_load_from_file(self, tmp_path: Path):
        """从文件加载章节"""
        novel_file = tmp_path / "test_novel.txt"
        novel_file.write_text(SAMPLE_CHINESE_NOVEL, encoding="utf-8")

        analyzer = BookAnalyzer(verbose=False)
        chapters = analyzer.load_chapters_from_file(str(novel_file))

        assert len(chapters) == 3


class TestStructureAnalysis:
    """测试结构分析"""

    def test_structure_basic_fields(self):
        """结构分析返回基本字段"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_structure()

        assert "chapter_count" in result
        assert "total_words" in result
        assert "avg_word_count" in result
        assert "min_word_count" in result
        assert "max_word_count" in result
        assert "rhythm" in result

    def test_chapter_count(self):
        """章节数正确"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_structure()

        assert result["chapter_count"] == 3

    def test_rhythm_keys(self):
        """节奏分析包含三个类型"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_structure()

        assert "铺垫" in result["rhythm"]
        assert "冲突" in result["rhythm"]
        assert "高潮" in result["rhythm"]

    def test_empty_chapters_structure(self):
        """空章节时返回空字典"""
        analyzer = BookAnalyzer(verbose=False)
        result = analyzer.analyze_structure()
        assert result == {}


class TestTrophyAnalysis:
    """测试爽点分析"""

    def test_trophy_detection(self):
        """能检测到爽点关键词"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_trophy_points()

        assert result["total_count"] > 0

    def test_trophy_density(self):
        """爽点密度计算"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_trophy_points()

        assert result["density"] > 0
        assert isinstance(result["density"], float)

    def test_trophy_distribution(self):
        """爽点分布包含已知类型"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_trophy_points()

        assert isinstance(result["distribution"], dict)
        # 至少应该检测到一些类型
        for trophy_type in result["distribution"]:
            assert trophy_type in TROPHY_TYPES

    def test_high_low_density_chapters(self):
        """高/低密度章节列表"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_trophy_points()

        assert isinstance(result["high_density_chapters"], list)
        assert isinstance(result["low_density_chapters"], list)


class TestStyleAnalysis:
    """测试文风分析"""

    def test_style_basic_fields(self):
        """文风分析返回基本字段"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_style()

        assert "avg_sentence_length" in result
        assert "dialogue_ratio" in result
        assert "opening_modes" in result
        assert "ending_modes" in result

    def test_dialogue_ratio_positive(self):
        """有对白时对白比例大于0"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_style()

        assert result["dialogue_ratio"] > 0

    def test_sentence_length_positive(self):
        """句长大于0"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        result = analyzer.analyze_style()

        assert result["avg_sentence_length"] > 0


class TestAnalyzeAll:
    """测试完整分析"""

    def test_analyze_all_with_text(self):
        """用文本进行完整分析"""
        analyzer = BookAnalyzer(verbose=False)
        result = analyzer.analyze_all(text=SAMPLE_CHINESE_NOVEL)

        assert "structure" in result
        assert "trophy" in result
        assert "style" in result

    def test_analyze_all_with_file(self, tmp_path: Path):
        """用文件进行完整分析"""
        novel_file = tmp_path / "novel.txt"
        novel_file.write_text(SAMPLE_CHINESE_NOVEL, encoding="utf-8")

        analyzer = BookAnalyzer(verbose=False)
        result = analyzer.analyze_all(filepath=str(novel_file))

        assert "structure" in result

    def test_analyze_all_no_input(self):
        """不提供输入时抛出异常"""
        analyzer = BookAnalyzer(verbose=False)
        with pytest.raises(ValueError):
            analyzer.analyze_all()


class TestReportGeneration:
    """测试报告生成"""

    def test_generate_report_creates_files(self, tmp_path: Path):
        """报告生成创建文件"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        analyzer.analyze_all()

        output_dir = tmp_path / "analysis_output"
        reports = analyzer.generate_report(str(output_dir))

        assert "结构分析" in reports
        assert "爽点分析" in reports
        assert "文风提取" in reports
        assert "分析报告" in reports

        # 验证文件存在
        for name, path in reports.items():
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0

    def test_report_content_not_empty(self, tmp_path: Path):
        """报告内容非空"""
        analyzer = BookAnalyzer(verbose=False)
        analyzer.load_chapters_from_text(SAMPLE_CHINESE_NOVEL)
        analyzer.analyze_all()

        output_dir = tmp_path / "report_content_test"
        reports = analyzer.generate_report(str(output_dir))

        for name, path in reports.items():
            content = Path(path).read_text(encoding="utf-8")
            assert len(content) > 50  # 报告内容应足够长


class TestDataClasses:
    """测试数据类"""

    def test_chapter_word_count(self):
        """Chapter 自动计算字数"""
        ch = Chapter(index=1, title="第1章", content="这是测试内容")
        assert ch.word_count == len("这是测试内容")

    def test_trophy_point_fields(self):
        """TrophyPoint 字段正确"""
        tp = TrophyPoint(
            chapter_index=1,
            trophy_type="装逼打脸",
            context="上下文",
            position=10,
        )
        assert tp.chapter_index == 1
        assert tp.trophy_type == "装逼打脸"

    def test_analysis_result_defaults(self):
        """AnalysisResult 默认值"""
        result = AnalysisResult()
        assert result.chapters == []
        assert result.trophy_points == []
        assert result.avg_word_count == 0
        assert result.trophy_density == 0
