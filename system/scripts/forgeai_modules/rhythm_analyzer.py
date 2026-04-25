"""
情节节奏分析模块
分析章节的情绪曲线、冲突密度、节奏变化
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class RhythmPoint:
    """节奏点"""
    chapter: int
    intensity: float  # 0-1，情节强度
    emotion: str      # positive/negative/neutral
    event_type: str   # battle/dialogue/upgrade/exploration/rest
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RhythmReport:
    """节奏分析报告"""
    start_chapter: int
    end_chapter: int
    total_chapters: int
    avg_intensity: float
    rhythm_curve: List[RhythmPoint] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_chapter": self.start_chapter,
            "end_chapter": self.end_chapter,
            "total_chapters": self.total_chapters,
            "avg_intensity": self.avg_intensity,
            "rhythm_curve": [p.to_dict() for p in self.rhythm_curve],
            "suggestions": self.suggestions,
        }


class RhythmAnalyzer:
    """情节节奏分析器"""
    
    # 情节关键词
    BATTLE_KEYWORDS = [
        "战斗", "交手", "对决", "击杀", "厮杀", "对峙",
        "攻击", "防御", "闪避", "反击", "爆发",
    ]
    
    UPGRADE_KEYWORDS = [
        "突破", "修炼", "提升", "进阶", "觉醒",
        "领悟", "感悟", "融合", "吸收",
    ]
    
    DIALOGUE_KEYWORDS = [
        "说道", "问道", "回答", "开口", "沉声道",
        "笑道", "冷声道", "低声道", "点头道",
    ]
    
    EXPLORATION_KEYWORDS = [
        "探索", "寻找", "搜索", "发现", "进入",
        "穿过", "到达", "离开", "前往",
    ]
    
    REST_KEYWORDS = [
        "休息", "闭关", "睡觉", "打坐", "调息",
        "恢复", "疗伤", "安顿",
    ]
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.content_dir = project_root / "4-正文"
        
    def analyze_chapter(self, chapter: int) -> Optional[RhythmPoint]:
        """分析单章节节奏
        
        Args:
            chapter: 章节号
        
        Returns:
            节奏点数据
        """
        # 读取章节内容
        content_files = list(self.content_dir.glob(f"第{chapter:03d}章*.md"))
        
        if not content_files:
            return None
        
        content = content_files[0].read_text(encoding="utf-8")
        
        # 分析情节类型
        event_counts = {
            "battle": self._count_keywords(content, self.BATTLE_KEYWORDS),
            "upgrade": self._count_keywords(content, self.UPGRADE_KEYWORDS),
            "dialogue": self._count_keywords(content, self.DIALOGUE_KEYWORDS),
            "exploration": self._count_keywords(content, self.EXPLORATION_KEYWORDS),
            "rest": self._count_keywords(content, self.REST_KEYWORDS),
        }
        
        # 找出主要事件类型
        main_event = max(event_counts.items(), key=lambda x: x[1])[0]
        
        # 计算情节强度（0-1）
        intensity = self._calculate_intensity(event_counts)
        
        # 分析情绪倾向
        emotion = self._analyze_emotion(content)
        
        # 生成描述
        description = self._generate_description(intensity, main_event, emotion)
        
        return RhythmPoint(
            chapter=chapter,
            intensity=intensity,
            emotion=emotion,
            event_type=main_event,
            description=description,
        )
    
    def analyze_range(self, start_chapter: int, end_chapter: int) -> RhythmReport:
        """分析章节范围的节奏
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
        
        Returns:
            节奏分析报告
        """
        rhythm_points = []
        
        for chapter in range(start_chapter, end_chapter + 1):
            point = self.analyze_chapter(chapter)
            if point:
                rhythm_points.append(point)
        
        # 计算平均强度
        avg_intensity = sum(p.intensity for p in rhythm_points) / len(rhythm_points) if rhythm_points else 0
        
        # 生成建议
        suggestions = self._generate_suggestions(rhythm_points)
        
        return RhythmReport(
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            total_chapters=len(rhythm_points),
            avg_intensity=avg_intensity,
            rhythm_curve=rhythm_points,
            suggestions=suggestions,
        )
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """统计关键词出现次数"""
        count = 0
        for keyword in keywords:
            count += len(re.findall(keyword, text))
        return count
    
    def _calculate_intensity(self, event_counts: Dict[str, int]) -> float:
        """计算情节强度（0-1）
        
        战斗强度最高，休息强度最低
        """
        # 权重
        weights = {
            "battle": 1.0,
            "upgrade": 0.8,
            "exploration": 0.6,
            "dialogue": 0.4,
            "rest": 0.2,
        }
        
        total_weight = sum(weights[event_type] * count for event_type, count in event_counts.items())
        max_weight = sum(weights.values()) * max(event_counts.values()) if event_counts else 1
        
        return min(total_weight / max_weight, 1.0) if max_weight > 0 else 0.5
    
    def _analyze_emotion(self, text: str) -> str:
        """分析情绪倾向"""
        # 正面情绪词
        positive_words = ["笑", "喜", "乐", "兴奋", "期待", "希望", "成功"]
        # 负面情绪词
        negative_words = ["怒", "悲", "恐", "焦虑", "绝望", "失败", "死亡"]
        
        positive_count = sum(len(re.findall(word, text)) for word in positive_words)
        negative_count = sum(len(re.findall(word, text)) for word in negative_words)
        
        if positive_count > negative_count * 1.5:
            return "positive"
        elif negative_count > positive_count * 1.5:
            return "negative"
        else:
            return "neutral"
    
    def _generate_description(self, intensity: float, event_type: str, emotion: str) -> str:
        """生成节奏描述"""
        type_names = {
            "battle": "战斗",
            "upgrade": "修炼升级",
            "dialogue": "对话交流",
            "exploration": "探索发现",
            "rest": "休整恢复",
        }
        
        intensity_desc = "高潮密集" if intensity > 0.7 else "节奏平缓" if intensity < 0.3 else "节奏适中"
        emotion_desc = "情绪积极" if emotion == "positive" else "情绪低落" if emotion == "negative" else "情绪平稳"
        
        return f"{type_names[event_type]}为主，{intensity_desc}，{emotion_desc}"
    
    def _generate_suggestions(self, rhythm_points: List[RhythmPoint]) -> List[str]:
        """生成节奏建议"""
        suggestions = []
        
        if len(rhythm_points) < 3:
            return ["章节较少，暂无节奏建议"]
        
        # 分析节奏变化
        intensities = [p.intensity for p in rhythm_points]
        avg_intensity = sum(intensities) / len(intensities)
        
        # 建议1：高潮密度
        high_intensity_count = sum(1 for i in intensities if i > 0.7)
        if high_intensity_count > len(intensities) * 0.6:
            suggestions.append("[WARN] 高潮密度过高（>60%），读者可能疲劳。建议添加休整章节或降低部分章节强度。")
        elif high_intensity_count < len(intensities) * 0.2:
            suggestions.append("[WARN] 高潮密度过低（<20%），读者可能无聊。建议增加冲突或战斗章节。")
        else:
            suggestions.append("[OK] 高潮密度合理，节奏把控良好。")
        
        # 建议2：连续低潮
        low_streak = 0
        max_low_streak = 0
        for intensity in intensities:
            if intensity < 0.3:
                low_streak += 1
                max_low_streak = max(max_low_streak, low_streak)
            else:
                low_streak = 0
        
        if max_low_streak >= 3:
            suggestions.append(f"[WARN] 连续{max_low_streak}章节奏平缓，建议插入冲突或转折。")
        
        # 建议3：情绪变化
        emotions = [p.emotion for p in rhythm_points]
        positive_ratio = emotions.count("positive") / len(emotions)
        
        if positive_ratio < 0.2:
            suggestions.append("[WARN] 负面情绪占主导，建议添加积极事件平衡读者情绪。")
        elif positive_ratio > 0.8:
            suggestions.append("[WARN] 正面情绪占主导，建议添加挑战或危机增加张力。")
        
        # 建议4：事件类型多样性
        event_types = [p.event_type for p in rhythm_points]
        unique_events = len(set(event_types))
        
        if unique_events < 3:
            suggestions.append(f"[WARN] 事件类型单一（仅{unique_events}种），建议增加多样性（如加入探索、对话等）。")
        else:
            suggestions.append(f"[OK] 事件类型丰富（{unique_events}种），情节多样。")
        
        return suggestions
    
    def predict_reader_emotion(self, chapter: int) -> Dict[str, Any]:
        """预测读者情绪反应
        
        Args:
            chapter: 章节号
        
        Returns:
            读者情绪预测
        """
        point = self.analyze_chapter(chapter)
        
        if not point:
            return {"error": f"第{chapter}章不存在"}
        
        # 基于情节强度和事件类型预测读者情绪
        expectation = 0.5
        satisfaction = 0.5
        frustration = 0.5
        
        # 战斗章节
        if point.event_type == "battle":
            expectation = 0.7
            satisfaction = 0.8 if point.intensity > 0.6 else 0.6
            frustration = 0.3
        
        # 修炼升级
        elif point.event_type == "upgrade":
            expectation = 0.6
            satisfaction = 0.9
            frustration = 0.2
        
        # 对话交流
        elif point.event_type == "dialogue":
            expectation = 0.5
            satisfaction = 0.6
            frustration = 0.4
        
        # 探索发现
        elif point.event_type == "exploration":
            expectation = 0.8
            satisfaction = 0.7
            frustration = 0.3
        
        # 休整恢复
        elif point.event_type == "rest":
            expectation = 0.3
            satisfaction = 0.5
            frustration = 0.6 if point.intensity < 0.3 else 0.4
        
        # 生成建议
        suggestions = []
        
        if expectation > 0.7:
            suggestions.append("读者期待值高，建议在后续章节满足期待（如伏笔回收、真相揭示）")
        
        if frustration > 0.5:
            suggestions.append("读者挫败感强，建议添加积极事件或降低难度")
        
        if satisfaction > 0.7:
            suggestions.append("读者满意度高，可以继续当前节奏")
        
        return {
            "chapter": chapter,
            "expectation": expectation,
            "satisfaction": satisfaction,
            "frustration": frustration,
            "main_event": point.event_type,
            "intensity": point.intensity,
            "suggestions": suggestions,
        }
