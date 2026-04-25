"""
样板书分析器
用于拆解样板书，提取结构、套路、节奏、文风
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import Counter
from datetime import datetime

# 爽点类型定义
TROPHY_TYPES = {
    "装逼打脸": ["打脸", "嘲讽", "不屑", "冷笑", "碾压", "震惊", "目瞪口呆"],
    "扮猪吃虎": ["隐藏", "低调", "扮猪", "吃虎", "没想到", "竟然", "原来"],
    "越级反杀": ["越级", "反杀", "不可能", "怎么做到", "境界", "实力"],
    "身份掉马": ["身份", "掉马", "暴露", "真面目", "原来是你", "竟然是"],
    "反派翻车": ["翻车", "自食其果", "搬起石头", "算计", "反噬"],
    "甜蜜超预期": ["甜蜜", "心动", "脸红", "害羞", "意外", "惊喜"],
    "迪化误解": ["误解", "以为", "其实", "迪化", "脑补", "自我攻略"],
    "打脸权威": ["权威", "长老", "宗主", "不屑", "质疑", "反驳"],
}

# 章节开头模式
OPENING_PATTERNS = {
    "场景切入": r"^(天|地|山|水|风|雨|雪|阳光|月光|夜|清晨|黄昏|房间|大厅)",
    "对话切入": r'^["「「『]',
    "心理切入": r"^(我|他|她|心想|暗道|不禁|不由得)",
    "动作切入": r"^(走|跑|跳|站|坐|躺|握|拿|放|推|拉)",
}

# 章节结尾模式
ENDING_PATTERNS = {
    "悬念钩子": r"(究竟|到底|会怎样|接下来|然而|却不知|就在这时)",
    "高潮截断": r"(轰|炸|碎|裂|冲|杀|战|斗|剑|刀|拳|掌)",
    "过渡收束": r"(这一夜|第二天|次日|天亮|离开|转身|回去)",
}


@dataclass
class Chapter:
    """章节数据"""
    index: int
    title: str
    content: str
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.content)


@dataclass
class TrophyPoint:
    """爽点"""
    chapter_index: int
    trophy_type: str
    context: str
    position: int  # 在章节中的位置


@dataclass
class AnalysisResult:
    """分析结果"""
    chapters: List[Chapter] = field(default_factory=list)
    trophy_points: List[TrophyPoint] = field(default_factory=list)

    # 结构数据
    avg_word_count: float = 0
    word_count_std: float = 0
    rhythm_ratio: Dict[str, float] = field(default_factory=dict)

    # 爽点数据
    trophy_density: float = 0
    trophy_distribution: Dict[str, int] = field(default_factory=dict)

    # 文风数据
    avg_sentence_length: float = 0
    dialogue_ratio: float = 0
    description_ratio: float = 0
    opening_modes: Dict[str, int] = field(default_factory=dict)
    ending_modes: Dict[str, int] = field(default_factory=dict)


class BookAnalyzer:
    """样板书分析器"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.result = AnalysisResult()

    def log(self, msg: str):
        if self.verbose:
            print(f"[BookAnalyzer] {msg}")

    def load_chapters_from_text(self, text: str) -> List[Chapter]:
        """从文本中解析章节"""
        chapters = []

        # 尝试多种章节分隔模式
        patterns = [
            r"第([零一二三四五六七八九十百千万\d]+)章[^\n]*",
            r"Chapter\s*(\d+)[^\n]*",
            r"【第([零一二三四五六七八九十百千万\d]+)章】",
        ]

        splits = []
        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                splits = [(m.group(), m.start()) for m in matches]
                break

        if not splits:
            # 无法识别章节，作为单章处理
            chapters.append(Chapter(1, "第1章", text.strip()))
        else:
            for i, (title, start) in enumerate(splits):
                end = splits[i + 1][1] if i + 1 < len(splits) else len(text)
                content = text[start:end].strip()
                chapters.append(Chapter(i + 1, title, content))

        self.result.chapters = chapters
        self.log(f"解析到 {len(chapters)} 个章节")
        return chapters

    def load_chapters_from_file(self, filepath: str) -> List[Chapter]:
        """从文件加载章节"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")

        text = path.read_text(encoding="utf-8")
        return self.load_chapters_from_text(text)

    def analyze_structure(self) -> Dict:
        """分析结构"""
        chapters = self.result.chapters
        if not chapters:
            return {}

        # 字数统计
        word_counts = [ch.word_count for ch in chapters]
        avg = sum(word_counts) / len(word_counts)
        std = (sum((x - avg) ** 2 for x in word_counts) / len(word_counts)) ** 0.5

        self.result.avg_word_count = avg
        self.result.word_count_std = std

        # 节奏分析（简化版：基于段落长度分布）
        rhythm = self._analyze_rhythm()

        result = {
            "chapter_count": len(chapters),
            "total_words": sum(word_counts),
            "avg_word_count": round(avg),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts),
            "word_count_std": round(std),
            "rhythm": rhythm,
        }

        self.log(f"结构分析完成: 平均章长 {round(avg)} 字")
        return result

    def _analyze_rhythm(self) -> Dict[str, float]:
        """分析章节节奏（铺垫/冲突/高潮比例）"""
        # 简化实现：基于关键词密度
        setup_keywords = ["平静", "日常", "修炼", "学习", "准备", "计划"]
        conflict_keywords = ["冲突", "争执", "矛盾", "危机", "威胁", "挑战"]
        climax_keywords = ["战斗", "决战", "爆发", "击杀", "胜利", "失败"]

        setup_count = conflict_count = climax_count = 0

        for ch in self.result.chapters:
            text = ch.content
            setup_count += sum(text.count(kw) for kw in setup_keywords)
            conflict_count += sum(text.count(kw) for kw in conflict_keywords)
            climax_count += sum(text.count(kw) for kw in climax_keywords)

        total = setup_count + conflict_count + climax_count or 1

        return {
            "铺垫": round(setup_count / total * 100, 1),
            "冲突": round(conflict_count / total * 100, 1),
            "高潮": round(climax_count / total * 100, 1),
        }

    def analyze_trophy_points(self) -> Dict:
        """分析爽点"""
        chapters = self.result.chapters
        trophy_points = []

        for ch in chapters:
            for trophy_type, keywords in TROPHY_TYPES.items():
                for keyword in keywords:
                    # 查找关键词位置
                    for match in re.finditer(keyword, ch.content):
                        point = TrophyPoint(
                            chapter_index=ch.index,
                            trophy_type=trophy_type,
                            context=ch.content[max(0, match.start() - 20):match.end() + 20],
                            position=match.start(),
                        )
                        trophy_points.append(point)

        self.result.trophy_points = trophy_points

        # 统计分布
        distribution = Counter(p.trophy_type for p in trophy_points)
        self.result.trophy_distribution = dict(distribution)

        # 密度计算
        density = len(trophy_points) / len(chapters) if chapters else 0
        self.result.trophy_density = density

        # 每章爽点数
        chapter_trophy_count = Counter(p.chapter_index for p in trophy_points)

        result = {
            "total_count": len(trophy_points),
            "density": round(density, 2),
            "distribution": dict(distribution),
            "chapter_distribution": dict(chapter_trophy_count),
            "high_density_chapters": [
                ch for ch, count in chapter_trophy_count.items() if count >= 3
            ],
            "low_density_chapters": [
                ch for ch in range(1, len(chapters) + 1)
                if chapter_trophy_count.get(ch, 0) == 0
            ],
        }

        self.log(f"爽点分析完成: 共 {len(trophy_points)} 个，密度 {round(density, 2)} 个/章")
        return result

    def analyze_style(self) -> Dict:
        """分析文风"""
        all_text = "\n".join(ch.content for ch in self.result.chapters)

        # 句长分析
        sentences = re.split(r"[。！？\n]", all_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        self.result.avg_sentence_length = avg_length

        # 对白比例
        dialogue_chars = len(re.findall(r'["「」『』]', all_text))
        dialogue_ratio = dialogue_chars / len(all_text) * 100 if all_text else 0
        self.result.dialogue_ratio = dialogue_ratio

        # 开头模式分析
        opening_modes = Counter()
        for ch in self.result.chapters:
            first_para = ch.content.split("\n")[0][:50]
            for mode, pattern in OPENING_PATTERNS.items():
                if re.search(pattern, first_para):
                    opening_modes[mode] += 1
                    break
        self.result.opening_modes = dict(opening_modes)

        # 结尾模式分析
        ending_modes = Counter()
        for ch in self.result.chapters:
            last_para = ch.content.split("\n")[-1][-100:]
            for mode, pattern in ENDING_PATTERNS.items():
                if re.search(pattern, last_para):
                    ending_modes[mode] += 1
                    break
        self.result.ending_modes = dict(ending_modes)

        result = {
            "avg_sentence_length": round(avg_length, 1),
            "dialogue_ratio": round(dialogue_ratio, 1),
            "opening_modes": dict(opening_modes),
            "ending_modes": dict(ending_modes),
        }

        self.log(f"文风分析完成: 平均句长 {round(avg_length, 1)} 字")
        return result

    def analyze_all(self, text: Optional[str] = None, filepath: Optional[str] = None) -> Dict:
        """完整分析"""
        # 加载章节
        if filepath:
            self.load_chapters_from_file(filepath)
        elif text:
            self.load_chapters_from_text(text)
        elif not self.result.chapters:
            raise ValueError("需要提供 text 或 filepath，或先调用 load_chapters_from_file/load_chapters_from_text")

        # 执行分析
        result = {
            "structure": self.analyze_structure(),
            "trophy": self.analyze_trophy_points(),
            "style": self.analyze_style(),
        }

        return result

    def generate_report(self, output_dir: str) -> Dict[str, str]:
        """生成分析报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        reports = {}

        # 生成结构分析报告
        structure_report = self._generate_structure_report()
        structure_path = output_path / "结构分析.md"
        structure_path.write_text(structure_report, encoding="utf-8")
        reports["结构分析"] = str(structure_path)

        # 生成爽点分析报告
        trophy_report = self._generate_trophy_report()
        trophy_path = output_path / "爽点分析.md"
        trophy_path.write_text(trophy_report, encoding="utf-8")
        reports["爽点分析"] = str(trophy_path)

        # 生成文风分析报告
        style_report = self._generate_style_report()
        style_path = output_path / "文风提取.md"
        style_path.write_text(style_report, encoding="utf-8")
        reports["文风提取"] = str(style_path)

        # 生成综合报告
        summary_report = self._generate_summary_report()
        summary_path = output_path / "分析报告.md"
        summary_path.write_text(summary_report, encoding="utf-8")
        reports["分析报告"] = str(summary_path)

        # 新增: 保存JSON格式的分析数据（便于程序读取）
        analysis_data = self._export_analysis_data()
        data_path = output_path / "analysis_data.json"
        data_path.write_text(
            json.dumps(analysis_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        reports["数据文件"] = str(data_path)

        self.log(f"报告已生成到 {output_dir}")
        return reports

    def _export_analysis_data(self) -> Dict[str, Any]:
        """导出分析数据为JSON格式"""
        s = self.result
        
        return {
            "structure": {
                "chapter_count": len(s.chapters),
                "total_words": sum(ch.word_count for ch in s.chapters),
                "avg_word_count": round(s.avg_word_count),
                "word_count_std": round(s.word_count_std),
                "rhythm_ratio": s.rhythm_ratio,
                "chapters": [
                    {
                        "index": ch.index,
                        "title": ch.title,
                        "word_count": ch.word_count,
                    }
                    for ch in s.chapters
                ],
            },
            "trophy": {
                "total_count": len(s.trophy_points),
                "density": round(s.trophy_density, 2),
                "distribution": s.trophy_distribution,
                "points": [
                    {
                        "chapter_index": p.chapter_index,
                        "trophy_type": p.trophy_type,
                        "context": p.context,
                        "position": p.position,
                    }
                    for p in s.trophy_points[:100]  # 最多保存100个
                ],
            },
            "style": {
                "avg_sentence_length": round(s.avg_sentence_length, 1),
                "dialogue_ratio": round(s.dialogue_ratio, 1),
                "opening_modes": s.opening_modes,
                "ending_modes": s.ending_modes,
            },
            "metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "version": "1.0",
            },
        }

    def _generate_structure_report(self) -> str:
        """生成结构分析报告"""
        s = self.result
        return f"""# 结构分析

## 章节统计

| 指标 | 数值 |
|-----|------|
| 章节数 | {len(s.chapters)} |
| 总字数 | {sum(ch.word_count for ch in s.chapters):,} |
| 平均章长 | {round(s.avg_word_count):,} 字 |
| 字数标准差 | {round(s.word_count_std):,} 字 |

## 节奏分布

| 类型 | 占比 |
|-----|------|
| 铺垫 | {s.rhythm_ratio.get('铺垫', 0)}% |
| 冲突 | {s.rhythm_ratio.get('冲突', 0)}% |
| 高潮 | {s.rhythm_ratio.get('高潮', 0)}% |

## 字数分布

| 章节 | 字数 |
|-----|------|
{chr(10).join(f"| 第{ch.index}章 | {ch.word_count:,} 字 |" for ch in s.chapters[:20])}
{"| ... | ... |" if len(s.chapters) > 20 else ""}
"""

    def _generate_trophy_report(self) -> str:
        """生成爽点分析报告"""
        s = self.result
        dist = s.trophy_distribution

        return f"""# 爽点分析

## 总体统计

| 指标 | 数值 |
|-----|------|
| 爽点总数 | {len(s.trophy_points)} |
| 平均密度 | {s.trophy_density:.2f} 个/章 |

## 爽点类型分布

| 类型 | 次数 | 占比 |
|-----|------|------|
{chr(10).join(f"| {t} | {c} | {c/len(s.trophy_points)*100:.1f}% |" for t, c in sorted(dist.items(), key=lambda x: -x[1]))}

## 章节爽点分布

| 章节 | 爽点数 | 强度 |
|-----|--------|------|
{self._generate_trophy_table()}
"""

    def _generate_trophy_table(self) -> str:
        """生成爽点表格"""
        chapter_count = Counter(p.chapter_index for p in self.result.trophy_points)
        lines = []
        for ch in self.result.chapters[:20]:
            count = chapter_count.get(ch.index, 0)
            intensity = "★" * min(count, 3) + "☆" * (3 - min(count, 3))
            lines.append(f"| 第{ch.index}章 | {count} | {intensity} |")
        return "\n".join(lines)

    def _generate_style_report(self) -> str:
        """生成文风分析报告"""
        s = self.result

        return f"""# 文风提取

## 语言特征

| 指标 | 数值 |
|-----|------|
| 平均句长 | {s.avg_sentence_length:.1f} 字 |
| 对白密度 | {s.dialogue_ratio:.1f}% |

## 章节开头模式

| 模式 | 次数 |
|-----|------|
{chr(10).join(f"| {m} | {c} |" for m, c in s.opening_modes.items())}

## 章节结尾模式

| 模式 | 次数 |
|-----|------|
{chr(10).join(f"| {m} | {c} |" for m, c in s.ending_modes.items())}
"""

    def _generate_summary_report(self) -> str:
        """生成综合报告"""
        s = self.result
        total_words = sum(ch.word_count for ch in s.chapters)

        return f"""# 样板书分析报告

## 基本信息

| 项目 | 内容 |
|-----|------|
| 分析章节 | {len(s.chapters)} 章 |
| 总字数 | {total_words:,} 字 |
| 平均章长 | {round(s.avg_word_count):,} 字 |

## 核心指标

| 指标 | 数值 |
|-----|------|
| 爽点密度 | {s.trophy_density:.2f} 个/章 |
| 对白密度 | {s.dialogue_ratio:.1f}% |
| 平均句长 | {s.avg_sentence_length:.1f} 字 |

## 主要爽点类型

{', '.join(t for t, _ in sorted(s.trophy_distribution.items(), key=lambda x: -x[1])[:5])}

## 分析结论

基于以上数据，该书的创作特点：

1. **节奏控制**：{s.rhythm_ratio.get('铺垫', 0)}% 铺垫 + {s.rhythm_ratio.get('冲突', 0)}% 冲突 + {s.rhythm_ratio.get('高潮', 0)}% 高潮
2. **爽点设计**：平均每章 {s.trophy_density:.1f} 个爽点，密度{'较高' if s.trophy_density > 2 else '适中' if s.trophy_density > 1 else '较低'}
3. **文风特征**：句长{s.avg_sentence_length:.0f}字，{'对白为主' if s.dialogue_ratio > 30 else '描写为主'}

---
*由 BookAnalyzer 自动生成*
"""


# CLI 入口
def main():
    import argparse

    parser = argparse.ArgumentParser(description="样板书分析器")
    parser.add_argument("input", help="输入文件路径")
    parser.add_argument("-o", "--output", default="./样板书分析", help="输出目录")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    analyzer = BookAnalyzer(verbose=args.verbose)
    analyzer.analyze_all(filepath=args.input)
    reports = analyzer.generate_report(args.output)

    print("\n生成的报告：")
    for name, path in reports.items():
        print(f"  - {name}: {path}")


if __name__ == "__main__":
    main()
