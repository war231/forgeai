#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情节节奏分析模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from forgeai_modules.rhythm_analyzer import (
    RhythmPoint,
    RhythmReport,
    RhythmAnalyzer,
)


class TestRhythmPoint:
    """RhythmPoint数据类测试"""
    
    def test_rhythm_point_creation(self):
        """测试创建节奏点"""
        point = RhythmPoint(
            chapter=10,
            intensity=0.8,
            emotion="positive",
            event_type="battle",
            description="战斗为主，高潮密集，情绪积极"
        )
        
        assert point.chapter == 10
        assert point.intensity == 0.8
        assert point.emotion == "positive"
        assert point.event_type == "battle"
        assert point.description == "战斗为主，高潮密集，情绪积极"
    
    def test_rhythm_point_to_dict(self):
        """测试节奏点转换为字典"""
        point = RhythmPoint(
            chapter=5,
            intensity=0.5,
            emotion="neutral",
            event_type="dialogue",
            description="对话为主，节奏适中"
        )
        
        result = point.to_dict()
        
        assert result["chapter"] == 5
        assert result["intensity"] == 0.5
        assert result["emotion"] == "neutral"
        assert result["event_type"] == "dialogue"


class TestRhythmReport:
    """RhythmReport数据类测试"""
    
    def test_rhythm_report_creation(self):
        """测试创建节奏报告"""
        report = RhythmReport(
            start_chapter=1,
            end_chapter=10,
            total_chapters=10,
            avg_intensity=0.6
        )
        
        assert report.start_chapter == 1
        assert report.end_chapter == 10
        assert report.total_chapters == 10
        assert report.avg_intensity == 0.6
    
    def test_rhythm_report_with_points(self):
        """测试带节奏点的报告"""
        points = [
            RhythmPoint(1, 0.8, "positive", "battle", "战斗"),
            RhythmPoint(2, 0.4, "neutral", "dialogue", "对话")
        ]
        
        report = RhythmReport(
            start_chapter=1,
            end_chapter=2,
            total_chapters=2,
            avg_intensity=0.6,
            rhythm_curve=points
        )
        
        assert len(report.rhythm_curve) == 2
    
    def test_rhythm_report_to_dict(self):
        """测试报告转换为字典"""
        report = RhythmReport(
            start_chapter=1,
            end_chapter=5,
            total_chapters=5,
            avg_intensity=0.7,
            suggestions=["建议1", "建议2"]
        )
        
        result = report.to_dict()
        
        assert result["start_chapter"] == 1
        assert result["total_chapters"] == 5
        assert len(result["suggestions"]) == 2


class TestRhythmAnalyzer:
    """RhythmAnalyzer测试"""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()
        
        content_dir = project / "4-正文"
        content_dir.mkdir(parents=True)
        
        return project
    
    @pytest.fixture
    def analyzer(self, temp_project):
        """创建RhythmAnalyzer实例"""
        return RhythmAnalyzer(project_root=temp_project)
    
    @pytest.fixture
    def project_with_chapters(self, tmp_path):
        """创建带章节的项目"""
        project = tmp_path / "chapter_project"
        project.mkdir()
        
        content_dir = project / "4-正文"
        content_dir.mkdir(parents=True)
        
        # 创建测试章节
        (content_dir / "第001章 战斗.md").write_text(
            "李天与王强展开激烈的战斗，厮杀声震天。攻击、防御、闪避，招招致命。",
            encoding="utf-8"
        )
        
        (content_dir / "第002章 修炼.md").write_text(
            "李天闭关修炼，突破境界。领悟新的功法，提升实力。",
            encoding="utf-8"
        )
        
        (content_dir / "第003章 对话.md").write_text(
            "李天与林雪儿说道：'我们要小心。'她回答道：'我知道。'",
            encoding="utf-8"
        )
        
        (content_dir / "第004章 探索.md").write_text(
            "李天探索青州城，寻找线索。发现了一个秘密通道。",
            encoding="utf-8"
        )
        
        (content_dir / "第005章 休息.md").write_text(
            "李天休息调息，恢复灵力。疗伤后安顿下来。",
            encoding="utf-8"
        )
        
        return project
    
    def test_init(self, temp_project):
        """测试初始化"""
        analyzer = RhythmAnalyzer(project_root=temp_project)
        
        assert analyzer.project_root == temp_project
        assert analyzer.content_dir == temp_project / "4-正文"
    
    def test_count_keywords(self, analyzer):
        """测试关键词计数"""
        text = "战斗战斗战斗，攻击攻击，防御"
        
        count = analyzer._count_keywords(text, ["战斗", "攻击", "防御"])
        
        assert count == 5  # 3 + 2 + 1
    
    def test_calculate_intensity(self, analyzer):
        """测试计算情节强度"""
        event_counts = {
            "battle": 5,
            "upgrade": 3,
            "dialogue": 2,
            "exploration": 1,
            "rest": 0
        }
        
        intensity = analyzer._calculate_intensity(event_counts)
        
        assert 0 <= intensity <= 1
        # 战斗权重最高，强度应该较高
        assert intensity > 0.3
    
    def test_calculate_intensity_all_rest(self, analyzer):
        """测试全休息章节的强度"""
        event_counts = {
            "battle": 0,
            "upgrade": 0,
            "dialogue": 0,
            "exploration": 0,
            "rest": 5
        }
        
        intensity = analyzer._calculate_intensity(event_counts)
        
        # 休息权重最低，强度应该较低
        assert intensity < 0.5
    
    def test_analyze_emotion_positive(self, analyzer):
        """测试分析正面情绪"""
        text = "李天笑了，充满希望和期待。成功了！"
        
        emotion = analyzer._analyze_emotion(text)
        
        assert emotion == "positive"
    
    def test_analyze_emotion_negative(self, analyzer):
        """测试分析负面情绪"""
        text = "李天愤怒，绝望和恐惧。失败了，死亡逼近。"
        
        emotion = analyzer._analyze_emotion(text)
        
        assert emotion == "negative"
    
    def test_analyze_emotion_neutral(self, analyzer):
        """测试分析中性情绪"""
        text = "李天继续前进，没有特别的情绪波动。"
        
        emotion = analyzer._analyze_emotion(text)
        
        assert emotion == "neutral"
    
    def test_generate_description(self, analyzer):
        """测试生成节奏描述"""
        description = analyzer._generate_description(
            intensity=0.8,
            event_type="battle",
            emotion="positive"
        )
        
        assert "战斗" in description
        assert "高潮密集" in description
        assert "情绪积极" in description
    
    def test_generate_description_low_intensity(self, analyzer):
        """测试生成低强度描述"""
        description = analyzer._generate_description(
            intensity=0.2,
            event_type="rest",
            emotion="neutral"
        )
        
        assert "休整恢复" in description
        assert "节奏平缓" in description
    
    def test_analyze_chapter(self, project_with_chapters):
        """测试分析单章节"""
        analyzer = RhythmAnalyzer(project_root=project_with_chapters)
        
        point = analyzer.analyze_chapter(1)
        
        assert point is not None
        assert point.chapter == 1
        assert 0 <= point.intensity <= 1
        assert point.emotion in ["positive", "negative", "neutral"]
        assert point.event_type in ["battle", "upgrade", "dialogue", "exploration", "rest"]
    
    def test_analyze_chapter_not_found(self, analyzer):
        """测试章节不存在"""
        point = analyzer.analyze_chapter(999)
        
        assert point is None
    
    def test_analyze_range(self, project_with_chapters):
        """测试分析章节范围"""
        analyzer = RhythmAnalyzer(project_root=project_with_chapters)
        
        report = analyzer.analyze_range(1, 5)
        
        assert report.start_chapter == 1
        assert report.end_chapter == 5
        assert report.total_chapters == 5
        assert len(report.rhythm_curve) == 5
        assert 0 <= report.avg_intensity <= 1
    
    def test_analyze_range_partial(self, project_with_chapters):
        """测试分析部分章节范围"""
        analyzer = RhythmAnalyzer(project_root=project_with_chapters)
        
        report = analyzer.analyze_range(1, 3)
        
        assert report.total_chapters == 3
        assert len(report.rhythm_curve) == 3


class TestRhythmSuggestions:
    """节奏建议测试"""
    
    @pytest.fixture
    def analyzer(self, tmp_path):
        """创建分析器"""
        project = tmp_path / "test"
        project.mkdir()
        return RhythmAnalyzer(project_root=project)
    
    def test_generate_suggestions_high_intensity(self, analyzer):
        """测试高潮密度过高的建议"""
        points = [
            RhythmPoint(i, 0.8, "positive", "battle", "战斗") for i in range(1, 11)
        ]
        
        suggestions = analyzer._generate_suggestions(points)
        
        assert any("高潮密度过高" in s for s in suggestions)
    
    def test_generate_suggestions_low_intensity(self, analyzer):
        """测试高潮密度过低的建议"""
        points = [
            RhythmPoint(i, 0.2, "neutral", "rest", "休息") for i in range(1, 11)
        ]
        
        suggestions = analyzer._generate_suggestions(points)
        
        assert any("高潮密度过低" in s for s in suggestions)
    
    def test_generate_suggestions_continuous_low(self, analyzer):
        """测试连续低潮的建议"""
        points = [
            RhythmPoint(1, 0.8, "positive", "battle", "战斗"),
            RhythmPoint(2, 0.2, "neutral", "rest", "休息"),
            RhythmPoint(3, 0.2, "neutral", "rest", "休息"),
            RhythmPoint(4, 0.2, "neutral", "rest", "休息"),
            RhythmPoint(5, 0.8, "positive", "battle", "战斗"),
        ]
        
        suggestions = analyzer._generate_suggestions(points)
        
        assert any("连续" in s and "节奏平缓" in s for s in suggestions)
    
    def test_generate_suggestions_negative_emotion(self, analyzer):
        """测试负面情绪主导的建议"""
        points = [
            RhythmPoint(i, 0.5, "negative", "battle", "战斗") for i in range(1, 11)
        ]
        
        suggestions = analyzer._generate_suggestions(points)
        
        assert any("负面情绪占主导" in s for s in suggestions)
    
    def test_generate_suggestions_single_event_type(self, analyzer):
        """测试事件类型单一的建议"""
        points = [
            RhythmPoint(i, 0.5, "neutral", "dialogue", "对话") for i in range(1, 6)
        ]
        
        suggestions = analyzer._generate_suggestions(points)
        
        assert any("事件类型单一" in s for s in suggestions)
    
    def test_generate_suggestions_insufficient_data(self, analyzer):
        """测试数据不足时的建议"""
        points = [RhythmPoint(1, 0.5, "neutral", "dialogue", "对话")]
        
        suggestions = analyzer._generate_suggestions(points)
        
        assert any("章节较少" in s for s in suggestions)


class TestReaderEmotionPrediction:
    """读者情绪预测测试"""
    
    @pytest.fixture
    def project_with_chapter(self, tmp_path):
        """创建带章节的项目"""
        project = tmp_path / "emotion_project"
        project.mkdir()
        
        content_dir = project / "4-正文"
        content_dir.mkdir(parents=True)
        
        (content_dir / "第001章 战斗.md").write_text(
            "激烈的战斗爆发，攻击防御闪避。",
            encoding="utf-8"
        )
        
        return project
    
    @pytest.fixture
    def analyzer(self, project_with_chapter):
        """创建分析器"""
        return RhythmAnalyzer(project_root=project_with_chapter)
    
    def test_predict_reader_emotion_battle(self, analyzer):
        """测试战斗章节的读者情绪预测"""
        prediction = analyzer.predict_reader_emotion(1)
        
        assert "chapter" in prediction
        assert "expectation" in prediction
        assert "satisfaction" in prediction
        assert "frustration" in prediction
        assert "suggestions" in prediction
        
        # 战斗章节期待值较高
        assert prediction["expectation"] > 0.5
    
    def test_predict_reader_emotion_not_found(self, analyzer):
        """测试章节不存在时的预测"""
        prediction = analyzer.predict_reader_emotion(999)
        
        assert "error" in prediction
    
    def test_predict_reader_emotion_suggestions(self, project_with_chapter):
        """测试读者情绪预测建议"""
        # 创建高期待章节
        content_dir = project_with_chapter / "4-正文"
        (content_dir / "第002章 探索.md").write_text(
            "李天探索神秘的遗迹，发现重要线索。",
            encoding="utf-8"
        )
        
        analyzer = RhythmAnalyzer(project_root=project_with_chapter)
        prediction = analyzer.predict_reader_emotion(2)
        
        # 探索章节期待值高，应该有建议
        if prediction["expectation"] > 0.7:
            assert len(prediction["suggestions"]) > 0


class TestEventTypes:
    """事件类型测试"""
    
    @pytest.fixture
    def project(self, tmp_path):
        """创建项目"""
        project = tmp_path / "event_project"
        project.mkdir()
        (project / "4-正文").mkdir(parents=True)
        return project
    
    def test_detect_battle_event(self, project):
        """测试检测战斗事件"""
        content_dir = project / "4-正文"
        (content_dir / "第001章 战斗.md").write_text(
            "李天与敌人战斗，攻击防御闪避，击杀对手。",
            encoding="utf-8"
        )
        
        analyzer = RhythmAnalyzer(project_root=project)
        point = analyzer.analyze_chapter(1)
        
        assert point.event_type == "battle"
    
    def test_detect_upgrade_event(self, project):
        """测试检测修炼升级事件"""
        content_dir = project / "4-正文"
        (content_dir / "第001章 修炼.md").write_text(
            "李天闭关修炼，突破境界，领悟新功法。",
            encoding="utf-8"
        )
        
        analyzer = RhythmAnalyzer(project_root=project)
        point = analyzer.analyze_chapter(1)
        
        assert point.event_type == "upgrade"
    
    def test_detect_dialogue_event(self, project):
        """测试检测对话事件"""
        content_dir = project / "4-正文"
        (content_dir / "第001章 对话.md").write_text(
            "李天说道：'你好。'王强回答道：'你好。'",
            encoding="utf-8"
        )
        
        analyzer = RhythmAnalyzer(project_root=project)
        point = analyzer.analyze_chapter(1)
        
        assert point.event_type == "dialogue"
    
    def test_detect_exploration_event(self, project):
        """测试检测探索事件"""
        content_dir = project / "4-正文"
        (content_dir / "第001章 探索.md").write_text(
            "李天探索青州城，寻找线索，发现秘密。",
            encoding="utf-8"
        )
        
        analyzer = RhythmAnalyzer(project_root=project)
        point = analyzer.analyze_chapter(1)
        
        assert point.event_type == "exploration"
    
    def test_detect_rest_event(self, project):
        """测试检测休息事件"""
        content_dir = project / "4-正文"
        (content_dir / "第001章 休息.md").write_text(
            "李天休息调息，疗伤恢复，安顿下来。",
            encoding="utf-8"
        )
        
        analyzer = RhythmAnalyzer(project_root=project)
        point = analyzer.analyze_chapter(1)
        
        assert point.event_type == "rest"


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def full_project(self, tmp_path):
        """创建完整项目"""
        project = tmp_path / "full_project"
        project.mkdir()
        
        content_dir = project / "4-正文"
        content_dir.mkdir(parents=True)
        
        # 创建多个不同类型的章节
        chapters = [
            ("第001章 开篇.md", "李天站在青州城，看着远方。战斗的气息弥漫。"),
            ("第002章 冲突.md", "敌人来袭！李天与敌人展开激烈的战斗，攻击防御闪避。"),
            ("第003章 修炼.md", "战后，李天闭关修炼，突破境界，领悟新功法。"),
            ("第004章 对话.md", "李天与林雪儿说道：'我们成功了。'她笑道：'是的。'"),
            ("第005章 探索.md", "李天探索遗迹，寻找宝藏，发现秘密通道。"),
            ("第006章 休息.md", "李天休息调息，恢复灵力，疗伤安顿。"),
            ("第007章 高潮.md", "最终决战爆发！李天全力以赴，击杀强敌！"),
        ]
        
        for filename, content in chapters:
            (content_dir / filename).write_text(content, encoding="utf-8")
        
        return project
    
    def test_full_analysis_workflow(self, full_project):
        """测试完整分析工作流"""
        analyzer = RhythmAnalyzer(project_root=full_project)
        
        # 1. 分析单个章节
        point = analyzer.analyze_chapter(2)
        assert point is not None
        assert point.event_type == "battle"
        
        # 2. 分析章节范围
        report = analyzer.analyze_range(1, 7)
        assert report.total_chapters == 7
        assert len(report.rhythm_curve) == 7
        
        # 3. 预测读者情绪
        prediction = analyzer.predict_reader_emotion(7)
        assert "expectation" in prediction
        
        # 4. 检查建议
        assert len(report.suggestions) > 0
    
    def test_rhythm_curve_variation(self, full_project):
        """测试节奏曲线变化"""
        analyzer = RhythmAnalyzer(project_root=full_project)
        
        report = analyzer.analyze_range(1, 7)
        
        # 节奏应该有变化
        intensities = [p.intensity for p in report.rhythm_curve]
        
        # 不应该所有章节强度都一样
        assert len(set(intensities)) > 1
        
        # 应该有高潮和低谷
        assert max(intensities) > min(intensities)
