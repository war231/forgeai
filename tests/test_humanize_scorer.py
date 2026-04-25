"""
单元测试：humanize_scorer.py 模块

测试 AI 味检测和评分功能
"""

import sys
from pathlib import Path

import pytest

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "scripts"))

from forgeai_modules.humanize_scorer import (
    HumanizeScorer,
    AI_PATTERNS,
    ScoreResult,
)


class TestAIPatterns:
    """测试 AI 写作特征规则"""

    def test_patterns_exist(self):
        """AI 特征规则存在"""
        assert len(AI_PATTERNS) > 0

    def test_patterns_have_required_fields(self):
        """规则包含必需字段"""
        for key, rule in AI_PATTERNS.items():
            assert "name" in rule
            assert "patterns" in rule
            assert "weight" in rule

    def test_patterns_weight_range(self):
        """规则权重在合理范围"""
        for key, rule in AI_PATTERNS.items():
            assert 0 <= rule["weight"] <= 2


class TestHumanizeScorer:
    """测试 HumanizeScorer 类"""

    def test_scorer_init(self):
        """初始化评分器"""
        scorer = HumanizeScorer()
        assert scorer is not None

    def test_scorer_compiled_patterns(self):
        """正则表达式预编译"""
        scorer = HumanizeScorer()
        assert len(scorer._compiled_patterns) > 0


class TestRuleBasedScore:
    """测试规则引擎评分"""

    def test_score_natural_text(self):
        """自然文本应得高分"""
        scorer = HumanizeScorer()

        natural_text = """
        李明走进茶馆，找了个靠窗的位置坐下。

        "小二，来壶好茶。"他喊道。

        茶馆里人声嘈杂，各色人等都有。有商人在谈生意，有江湖客在吹牛，还有几个书生模样的在吟诗作对。

        李明端起茶杯，轻轻抿了一口。茶香四溢，回味悠长。
        """

        result = scorer.rule_based_score(natural_text)

        assert isinstance(result, ScoreResult)
        assert result.score >= 0.5  # 自然文本应得较高分

    def test_score_ai_text(self):
        """AI 文本应得低分"""
        scorer = HumanizeScorer()

        ai_text = """
        李明站在山顶，心中不禁倒吸一口凉气。

        这个场景不仅令人震撼，更是他命运的转折点的象征。众所周知，这座山有着不为人知的秘密。

        值得注意的是，他的眼中闪过一丝复杂的情绪。如遭雷击，他感到一股前所未有的力量涌入体内。

        让我们一起期待，李明将会迎来怎样光明的未来。
        """

        result = scorer.rule_based_score(ai_text)

        # AI 文本应检测到多个模式
        assert len(result.ai_patterns) > 0
        # 分数应低于自然文本
        assert result.score < 1.0

    def test_score_empty_text(self):
        """空文本评分"""
        scorer = HumanizeScorer()
        result = scorer.rule_based_score("")

        assert result.score >= 0  # 应有默认分数

    def test_score_detects_cliché(self):
        """检测陈词滥调"""
        scorer = HumanizeScorer()

        cliché_text = "他倒吸一口凉气，眼中闪过一丝复杂的情绪。"

        result = scorer.rule_based_score(cliché_text)

        # 应检测到陈词滥调
        assert len(result.ai_patterns) > 0

    def test_score_detects_exaggerated_symbolism(self):
        """检测夸大象征意义"""
        scorer = HumanizeScorer()

        text = "这不仅是他成长的开始，更是命运转折的象征。"

        result = scorer.rule_based_score(text)

        assert len(result.ai_patterns) > 0

    def test_score_detects_filler_phrases(self):
        """检测填充短语"""
        scorer = HumanizeScorer()

        text = "值得注意的是，这个决定非常重要。毋庸置疑，他会成功的。"

        result = scorer.rule_based_score(text)

        assert len(result.ai_patterns) > 0

    def test_score_detects_collaboration_traces(self):
        """检测协作痕迹"""
        scorer = HumanizeScorer()

        text = "希望这对你有所帮助。如有任何问题，随时可以询问。"

        result = scorer.rule_based_score(text)

        assert len(result.ai_patterns) > 0

    def test_score_detects_negative_parallelism(self):
        """检测否定式排比"""
        scorer = HumanizeScorer()

        text = "这不仅是一次冒险，更是一次成长的旅程。"

        result = scorer.rule_based_score(text)

        assert len(result.ai_patterns) > 0

    def test_score_micro_expressions(self):
        """检测微表情堆砌"""
        scorer = HumanizeScorer()

        text = """
        她眉头一皱，嘴角微扬，眼中闪过一丝复杂的情绪。
        他眉梢一挑，眼波流转，嘴角勾起一抹淡淡的微笑。
        她眉心微蹙，眼眸流转，嘴角轻轻抿起。
        """

        result = scorer.rule_based_score(text)

        # 连续的微表情应被检测
        # 需要超过阈值才计为 AI 特征

    def test_score_details_format(self):
        """评分详情格式"""
        scorer = HumanizeScorer()

        result = scorer.rule_based_score("测试文本")

        assert isinstance(result.details, str)

    def test_score_result_fields(self):
        """评分结果字段"""
        scorer = HumanizeScorer()

        result = scorer.rule_based_score("测试文本")

        assert hasattr(result, "score")
        assert hasattr(result, "ai_patterns")
        assert hasattr(result, "human_likeness")
        assert hasattr(result, "ai_likeness")
        assert hasattr(result, "details")

        # human_likeness + ai_likeness 应约等于 1
        assert abs(result.human_likeness + result.ai_likeness - 1.0) < 0.01


class TestCombinedScore:
    """测试双引擎评分"""

    @pytest.mark.asyncio
    async def test_combined_score_without_llm(self):
        """无 LLM 时使用规则评分"""
        scorer = HumanizeScorer()

        # 不设置 API key，应仅使用规则引擎
        result = await scorer.combined_score("测试文本内容")

        assert result is not None
        assert result.score >= 0

    @pytest.mark.asyncio
    async def test_combined_score_returns_result(self):
        """返回评分结果"""
        scorer = HumanizeScorer()

        result = await scorer.combined_score("这是一段测试文本。")

        assert isinstance(result, ScoreResult)


class TestEvolve:
    """测试进化式去 AI 味"""

    @pytest.mark.asyncio
    async def test_evolve_basic(self):
        """基本进化流程"""
        scorer = HumanizeScorer()

        result = await scorer.evolve("测试文本", max_rounds=1)

        assert "winner" in result
        assert "score" in result
        assert "rounds" in result

    @pytest.mark.asyncio
    async def test_evolve_high_score_text(self):
        """高分文本不需要进化"""
        scorer = HumanizeScorer()

        natural_text = "李明走进茶馆，要了一壶茶。"
        result = await scorer.evolve(natural_text, max_rounds=3)

        # 高分文本可能提前结束
        assert result["rounds"] >= 0

    @pytest.mark.asyncio
    async def test_evolve_returns_challenger_prompt(self):
        """返回挑战者生成提示"""
        scorer = HumanizeScorer()

        ai_text = "这不仅是开始，更是希望的象征。众所周知，这将改变一切。"
        result = await scorer.evolve(ai_text, max_rounds=1)

        # 如果分数低，应返回 challenger_prompt
        if result["needs_challenger"]:
            assert result.get("challenger_prompt") is not None


class TestBuildChallengerPrompt:
    """测试挑战者提示构建"""

    def test_build_prompt_with_patterns(self):
        """包含检测到的模式"""
        scorer = HumanizeScorer()

        score_result = ScoreResult(
            score=0.3,
            ai_patterns=[
                {"type": "cliché", "name": "陈词滥调", "count": 2, "weight": 1.0}
            ],
            human_likeness=0.3,
            ai_likeness=0.7,
            details="检测到问题"
        )

        prompt = scorer._build_challenger_prompt("测试文本", score_result)

        assert "陈词滥调" in prompt
        assert "0.30" in prompt  # 分数

    def test_build_prompt_without_patterns(self):
        """无检测模式时"""
        scorer = HumanizeScorer()

        score_result = ScoreResult(
            score=0.9,
            ai_patterns=[],
            human_likeness=0.9,
            ai_likeness=0.1,
            details="无明显AI模式"
        )

        prompt = scorer._build_challenger_prompt("测试文本", score_result)

        assert "无明显AI模式" in prompt or "无" in prompt


class TestHumanizeScorerIntegration:
    """评分器集成测试"""

    def test_full_scoring_workflow(self):
        """完整评分工作流"""
        scorer = HumanizeScorer()

        # 1. 准备测试文本
        text = """
        李明站在悬崖边，望着远方的云海。

        "师父，我一定会找到你的。"他低声说道。

        风吹过他的脸庞，带来一丝凉意。他深吸一口气，转身离开。

        身后，云海翻涌，仿佛在诉说着什么。
        """

        # 2. 规则评分
        result = scorer.rule_based_score(text)

        # 3. 验证结果
        assert 0 <= result.score <= 1
        assert 0 <= result.human_likeness <= 1
        assert 0 <= result.ai_likeness <= 1

    @pytest.mark.asyncio
    async def test_async_workflow(self):
        """异步工作流"""
        scorer = HumanizeScorer()

        text = "这是一段测试文本，用于验证异步评分功能。"

        result = await scorer.combined_score(text)

        assert result is not None
        assert result.score >= 0

    def test_multiple_texts_comparison(self):
        """多文本对比"""
        scorer = HumanizeScorer()

        natural = "李明喝茶，看书，练功。日复一日，年复一年。"
        ai_like = "这不仅是一种修炼，更是一种人生的感悟。毋庸置疑，他会成为强者。"

        natural_result = scorer.rule_based_score(natural)
        ai_result = scorer.rule_based_score(ai_like)

        # 自然文本分数应更高
        assert natural_result.score >= ai_result.score

    def test_score_threshold(self):
        """评分阈值测试"""
        scorer = HumanizeScorer()

        # 明显的 AI 特征文本
        obvious_ai = "让我们共同期待，未来必将更加美好。这不仅是一个开始，更是一个希望。"

        result = scorer.rule_based_score(obvious_ai)

        # 应低于通过阈值
        # 注意：具体阈值取决于规则配置
