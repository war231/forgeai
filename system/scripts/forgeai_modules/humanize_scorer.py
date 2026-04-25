#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去AI味评分器

基于 Humanize 的进化竞争机制：
1. baseline → 生成 challenger
2. 双引擎打分（规则引擎 + LLM）
3. 更像人的保留，更像AI的淘汰
4. 迭代直到结果更自然

规则引擎：检测24种AI写作特征 + 武行网文宪法
LLM评分：调用LLM判断"更像人"还是"更像AI"
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .config import get_config, ForgeAIConfig

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


# ---- AI 写作特征规则 ----

AI_PATTERNS = {
    # 通用 AI 特征（来自 Humanize / Wikipedia）
    "exaggerated_symbolism": {
        "name": "夸大象征意义",
        "patterns": [
            r"这不仅是.{2,10}更是.{2,10}的象征",
            r"象征着.{2,20}的深刻内涵",
            r"隐喻着.{2,20}的深层含义",
        ],
        "weight": 1.0,
    },
    "promotional_language": {
        "name": "宣传广告式语言",
        "patterns": [
            r"令人.{2,4}的是",
            r"不可.{2,4}的",
            r"前所未有的",
            r"颠覆性的",
            r"革命性的",
        ],
        "weight": 0.8,
    },
    "vague_attribution": {
        "name": "模糊归因",
        "patterns": [
            r"有人说",
            r"众所周知",
            r"专家认为",
            r"研究表明",
            r"据统计",
        ],
        "weight": 0.7,
    },
    "rule_of_three": {
        "name": "三段式法则",
        "patterns": [
            r"(.{2,10})[、，](.{2,10})[、，](?:乃至|更是|甚至)(.{2,10})",
        ],
        "weight": 0.6,
    },
    "filler_phrases": {
        "name": "填充短语",
        "patterns": [
            r"值得注意的是",
            r"需要指出的是",
            r"毋庸置疑",
            r"不言而喻",
            r"显而易见",
            r"总而言之",
            r"综上所述",
        ],
        "weight": 0.9,
    },
    "negative_parallelism": {
        "name": "否定式排比",
        "patterns": [
            r"不仅.{2,15}更.{2,15}",
            r"不是.{2,10}而是.{2,10}",
            r"并非.{2,10}而是.{2,10}",
        ],
        "weight": 0.7,
    },
    "fawning_tone": {
        "name": "谄媚语气",
        "patterns": [
            r"您说得(完全|非常|太)正确",
            r"真是一个好问题",
            r"非常感谢您的(提问|分享)",
        ],
        "weight": 1.0,
    },
    "generic_positive_conclusion": {
        "name": "通用积极结论",
        "patterns": [
            r"必将.{2,10}更加美好",
            r"让我们(一起|共同)期待",
            r"未来(一定|必将)更加",
            r"前景(广阔|光明|可期)",
        ],
        "weight": 0.8,
    },
    "collaboration_traces": {
        "name": "协作痕迹",
        "patterns": [
            r"希望这(对您|对你|能).{0,10}帮助",
            r"如有(任何|其他).{0,5}问题",
            r"随时(可以|欢迎).{0,10}询问",
            r"我是.{2,20}(助手|模型)",
        ],
        "weight": 1.0,
    },
    "ai_high_freq_words": {
        "name": "AI高频词",
        "patterns": [
            r"此外",
            r"至关重要",
            r"不可或缺",
            r"举足轻重",
            r"息息相关",
            r"相辅相成",
            r"层出不穷",
            r"纷至沓来",
        ],
        "weight": 0.6,
    },

    # 网文特有 AI 特征（来自武行宪法）
    "cliché_expressions": {
        "name": "陈词滥调",
        "patterns": [
            r"倒吸一口凉气",
            r"嘴角勾起一抹.{1,4}",
            r"眼中闪过一丝.{1,6}",
            r"心头一震",
            r"如遭雷击",
            r"虎躯一震",
            r"不禁.{1,4}起来",
        ],
        "weight": 1.0,
    },
    "micro_expressions": {
        "name": "神态微动作堆砌",
        "patterns": [
            r"眉.{0,2}一.{0,2}[皱挑扬]",
            r"嘴角.{0,3}[勾扬抿扯]",
            r"眼.{0,3}[神光波][闪动转]",
        ],
        "weight": 0.8,
        "consecutive_threshold": 3,  # 连续3个以上算AI味
    },
    "translation_tone": {
        "name": "翻译腔",
        "patterns": [
            r"哦[，,].{1,5}[啊呀哇]",
            r"我的.{1,5}[老天上帝天啊]",
            r"他(想|觉得|认为)自己",
            r"似乎在说",
            r"仿佛在.{1,5}(说|表达|暗示)",
        ],
        "weight": 1.0,
    },
    "over_methaphor": {
        "name": "滥用比喻",
        "patterns": [
            r"像一.{1,5}的.{1,5}一样",
            r"如同.{2,10}般",
            r"宛如.{2,10}似的",
        ],
        "weight": 0.7,
        "consecutive_threshold": 2,
    },
    "logic_padding": {
        "name": "逻辑废话",
        "patterns": [
            r"他(相信|知道|明白|意识到).{2,20}(是因为|毕竟|其实)",
            r"正因如此",
            r"之所以.{2,15}是因为",
        ],
        "weight": 0.6,
    },
    "over_description": {
        "name": "过度环境描写",
        "patterns": [
            r"(阳光|月光|星光|微风|清风).{5,30}(洒在|照在|拂过|掠过).{5,30}(映出|折射|泛起).{5,20}",
        ],
        "weight": 0.7,
    },
    "dash_overuse": {
        "name": "破折号过度使用",
        "patterns": [
            r"——.{5,30}——.{5,30}——",
        ],
        "weight": 0.5,
    },
}


@dataclass
class ScoreResult:
    """评分结果"""
    score: float  # 0.0 (像AI) ~ 1.0 (像人)
    ai_patterns: List[Dict[str, Any]] = field(default_factory=list)
    human_likeness: float = 0.0
    ai_likeness: float = 0.0
    details: str = ""


class HumanizeScorer:
    """去AI味评分器"""

    def __init__(self, config: Optional[ForgeAIConfig] = None):
        self.config = config or get_config()
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """预编译正则表达式"""
        for key, rule in AI_PATTERNS.items():
            patterns = []
            for p in rule.get("patterns", []):
                try:
                    patterns.append(re.compile(p))
                except re.error:
                    pass
            self._compiled_patterns[key] = patterns

    def rule_based_score(self, text: str) -> ScoreResult:
        """规则引擎评分"""
        detected = []

        for key, rule in AI_PATTERNS.items():
            patterns = self._compiled_patterns.get(key, [])
            weight = rule.get("weight", 1.0)

            matches = []
            for pattern in patterns:
                found = pattern.findall(text)
                if found:
                    matches.extend(found)

            if matches:
                # 检查连续阈值
                threshold = rule.get("consecutive_threshold", 1)
                if threshold > 1 and len(matches) < threshold:
                    continue

                detected.append({
                    "type": key,
                    "name": rule["name"],
                    "weight": weight,
                    "count": len(matches),
                    "penalty": weight * min(len(matches), 5) / 5,  # 上限5次
                })

        # 计算扣分
        total_penalty = sum(d["penalty"] for d in detected)
        
        # 优化评分算法：更敏感的扣分机制
        # 1. 基础扣分：每个检测到的模式扣分
        # 2. 累积效应：检测到的模式越多,扣分越多
        # 3. 权重放大：将权重影响放大
        
        # 计算基础扣分（每个模式至少扣0.1分）
        base_penalty = len(detected) * 0.1
        
        # 计算加权扣分（考虑权重和出现次数）
        weighted_penalty = total_penalty * 1.5  # 放大权重影响
        
        # 总扣分
        total_deduction = base_penalty + weighted_penalty
        
        # 最终分数：0.0（像AI）~ 1.0（像人）
        score = max(0.0, 1.0 - min(total_deduction, 1.0))

        ai_likeness = 1.0 - score
        human_likeness = score

        return ScoreResult(
            score=score,
            ai_patterns=detected,
            human_likeness=human_likeness,
            ai_likeness=ai_likeness,
            details=self._format_detected(detected),
        )

    async def llm_based_score(self, text: str) -> Optional[ScoreResult]:
        """LLM 评分"""
        api_key = self.config.get_api_key("llm")
        base_url = self.config.get_base_url("llm") or "https://api.openai.com/v1"
        model = self.config.get("llm.model", "gpt-4o-mini")

        if not api_key or not AIOHTTP_AVAILABLE:
            return None

        prompt = f"""你是一个专业的文本分析专家。请评估以下中文文本是否像AI生成的。

评分标准（0.0=完全像AI, 1.0=完全像人类）：
- 语言自然度
- 表达多样性
- 是否有AI常见模式（翻译腔、三段式、填充短语等）
- 是否有人类写作的"不完美"特征

请以JSON格式返回：
{{"score": 0.0-1.0, "ai_patterns": ["模式1", "模式2"], "reason": "评分理由"}}

待评估文本：
---
{text[:2000]}
---"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 500,
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{base_url}/chat/completions"
                async with session.post(url, json=payload, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]

                    # 解析 JSON
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        result = json.loads(json_match.group())
                        score = float(result.get("score", 0.5))
                        return ScoreResult(
                            score=score,
                            ai_patterns=[{"type": "llm_detected", "name": n} 
                                         for n in result.get("ai_patterns", [])],
                            human_likeness=score,
                            ai_likeness=1.0 - score,
                            details=result.get("reason", ""),
                        )
        except Exception:
            pass

        return None

    async def combined_score(self, text: str) -> ScoreResult:
        """双引擎综合评分"""
        rule_result = self.rule_based_score(text)
        llm_result = await self.llm_based_score(text)

        if llm_result is None:
            return rule_result

        # 加权融合：规则 40% + LLM 60%
        rule_weight = 0.4
        llm_weight = 0.6

        combined_score = rule_result.score * rule_weight + llm_result.score * llm_weight

        return ScoreResult(
            score=combined_score,
            ai_patterns=rule_result.ai_patterns + llm_result.ai_patterns,
            human_likeness=combined_score,
            ai_likeness=1.0 - combined_score,
            details=f"[规则评分: {rule_result.score:.2f}] [LLM评分: {llm_result.score:.2f}]\n"
                    f"规则检测: {rule_result.details}\n"
                    f"LLM分析: {llm_result.details}",
        )

    # ---- 进化竞争 ----

    async def evolve(self, baseline: str, max_rounds: int = 0) -> Dict[str, Any]:
        """
        进化式去AI味：baseline → challenger → score → 保留更好的

        返回：{"winner": str, "score": float, "rounds": int, "history": [...]}
        """
        max_rounds = max_rounds or self.config.get("humanize.max_rounds", 3)
        threshold = self.config.get("humanize.score_threshold", 0.6)
        challenger_count = self.config.get("humanize.challenger_count", 2)

        current_text = baseline
        current_score = await self.combined_score(baseline)
        history = [{
            "round": 0,
            "text": baseline[:200] + "..." if len(baseline) > 200 else baseline,
            "score": current_score.score,
            "source": "baseline",
        }]

        for round_num in range(1, max_rounds + 1):
            # 生成 challenger（这里只记录 prompt，实际由 AI 执行）
            prompt = self._build_challenger_prompt(current_text, current_score)

            # 如果已经够好了，提前结束
            if current_score.score >= threshold:
                break

            history.append({
                "round": round_num,
                "prompt": prompt,
                "current_score": current_score.score,
                "source": "pending_challenger",
            })

            # 注意：实际的 challenger 生成由 AI 在调用方完成
            # 这里只提供评分和决策框架

        return {
            "winner": current_text,
            "score": current_score.score,
            "rounds": len(history) - 1,
            "history": history,
            "detected_patterns": current_score.ai_patterns,
            "needs_challenger": current_score.score < threshold,
            "challenger_prompt": self._build_challenger_prompt(current_text, current_score)
                                 if current_score.score < threshold else None,
        }

    def _build_challenger_prompt(self, text: str, score: ScoreResult) -> str:
        """构建挑战者生成 prompt"""
        patterns_desc = "\n".join(
            f"- {p.get('name', p.get('type', '未知'))}: 出现{p.get('count', 1)}次"
            for p in score.ai_patterns
        )

        return f"""请改写以下文本，消除AI写作痕迹，使其更像人类作家写的。

当前评分: {score.score:.2f}/1.0 (目标: ≥0.6)

检测到的AI模式:
{patterns_desc if patterns_desc else "无明显AI模式"}

改写要求:
1. 消除上述AI模式
2. 保持原文情节和意思不变
3. 使用更自然的中文表达
4. 适当加入"不完美"的人类写作特征
5. 网文风格：对话感强，节奏紧凑

原文:
---
{text[:3000]}
---

请输出改写后的文本:"""

    def _format_detected(self, detected: List[Dict]) -> str:
        """格式化检测结果"""
        if not detected:
            return "未检测到明显AI模式"
        return "\n".join(f"- {d['name']}: {d['count']}次 (权重{d['weight']})" for d in detected)
