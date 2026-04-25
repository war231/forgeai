"""
跨章节一致性检查模块
支持时间线、角色行为、世界观一致性检查
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    issue_type: str  # timeline/character/worldview/ooc
    severity: str    # error/warning/info
    chapter: int
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""


@dataclass
class ConsistencyReport:
    """一致性检查报告"""
    target_chapter: int
    check_time: str
    total_issues: int
    errors: int
    warnings: int
    issues: List[ConsistencyIssue] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_chapter": self.target_chapter,
            "check_time": self.check_time,
            "total_issues": self.total_issues,
            "errors": self.errors,
            "warnings": self.warnings,
            "issues": [asdict(issue) for issue in self.issues],
        }


class ConsistencyChecker:
    """跨章节一致性检查器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.forgeai_dir = project_root / ".forgeai"
        self.state_file = self.forgeai_dir / "state.json"
        self.index_dir = self.forgeai_dir / "index"
        self.outline_dir = project_root / "3-大纲"
        self.content_dir = project_root / "4-正文"
        
    def _load_state(self) -> Dict[str, Any]:
        """加载状态文件"""
        if not self.state_file.exists():
            return {}
        return json.loads(self.state_file.read_text(encoding="utf-8"))
    
    def _search_index(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索索引（简化版，实际使用BM25）"""
        # 这里简化实现，实际应该调用index_manager的search功能
        results = []
        
        # 扫描所有chunk文件
        if not self.index_dir.exists():
            return results
        
        for chunk_file in self.index_dir.glob("chunk_*.json"):
            chunk_data = json.loads(chunk_file.read_text(encoding="utf-8"))
            text = chunk_data.get("text", "")
            
            # 简单关键词匹配
            if query.lower() in text.lower():
                results.append({
                    "chunk_id": chunk_data.get("chunk_id"),
                    "chapter": chunk_data.get("chapter"),
                    "text": text[:200],  # 截取前200字
                    "score": 1.0,
                })
                
                if len(results) >= top_k:
                    break
        
        return results
    
    def check_chapter(self, chapter: int, check_scope: str = "full") -> ConsistencyReport:
        """检查单章节一致性
        
        Args:
            chapter: 章节号
            check_scope: 检查范围（timeline/character/worldview/ooc/full）
        """
        report = ConsistencyReport(
            target_chapter=chapter,
            check_time=datetime.now().isoformat(),
            total_issues=0,
            errors=0,
            warnings=0,
        )
        
        # 执行各类检查
        if check_scope in ["timeline", "full"]:
            issues = self._check_timeline_consistency(chapter)
            report.issues.extend(issues)
        
        if check_scope in ["character", "full"]:
            issues = self._check_character_consistency(chapter)
            report.issues.extend(issues)
        
        if check_scope in ["worldview", "full"]:
            issues = self._check_worldview_consistency(chapter)
            report.issues.extend(issues)
        
        if check_scope in ["ooc", "full"]:
            issues = self._check_ooc(chapter)
            report.issues.extend(issues)
        
        # 统计问题数量
        report.total_issues = len(report.issues)
        report.errors = sum(1 for issue in report.issues if issue.severity == "error")
        report.warnings = sum(1 for issue in report.issues if issue.severity == "warning")
        
        return report
    
    def _check_timeline_consistency(self, chapter: int) -> List[ConsistencyIssue]:
        """检查时间线一致性"""
        issues = []
        state = self._load_state()
        
        # 1. 检查时间锚点连续性
        timeline = state.get("timeline", {})
        anchors = timeline.get("anchors", [])
        
        # 找到当前章节的时间锚点
        current_anchor = None
        prev_anchor = None
        
        for anchor in anchors:
            if anchor.get("chapter") == chapter:
                current_anchor = anchor
            elif anchor.get("chapter") < chapter:
                prev_anchor = anchor
        
        # 检查时间跳跃是否合理
        if current_anchor and prev_anchor:
            current_time = self._parse_time_anchor(current_anchor.get("anchor", ""))
            prev_time = self._parse_time_anchor(prev_anchor.get("anchor", ""))
            
            if current_time is not None and prev_time is not None:
                time_diff = current_time - prev_time
                
                # 如果时间跨度超过10天，发出警告
                if time_diff > 10:
                    issues.append(ConsistencyIssue(
                        issue_type="timeline",
                        severity="warning",
                        chapter=chapter,
                        description=f"时间跨度过大：从第{prev_anchor.get('chapter')}章到第{chapter}章跨越了{time_diff}天",
                        details={
                            "prev_chapter": prev_anchor.get("chapter"),
                            "prev_anchor": prev_anchor.get("anchor"),
                            "current_anchor": current_anchor.get("anchor"),
                            "days_diff": time_diff,
                        },
                        suggestion="考虑补充过渡章节或明确说明时间跳跃",
                    ))
        
        # 2. 检查倒计时一致性
        countdowns = timeline.get("countdowns", [])
        for countdown in countdowns:
            start_chapter = countdown.get("start_chapter", 0)
            end_chapter = countdown.get("end_chapter", 0)
            countdown_value = countdown.get("value", "")
            
            # 解析倒计时值（如：D-10）
            if countdown_value.startswith("D-"):
                try:
                    days = int(countdown_value[2:])
                    expected_end_chapter = start_chapter + days
                    
                    if end_chapter > 0 and abs(end_chapter - expected_end_chapter) > 2:
                        issues.append(ConsistencyIssue(
                            issue_type="timeline",
                            severity="error",
                            chapter=chapter,
                            description=f"倒计时不一致：{countdown.get('name')}预期在第{expected_end_chapter}章到期，实际在第{end_chapter}章",
                            details={
                                "countdown_name": countdown.get("name"),
                                "expected_end": expected_end_chapter,
                                "actual_end": end_chapter,
                            },
                            suggestion="调整倒计时值或章节安排",
                        ))
                except ValueError:
                    pass
        
        return issues
    
    def _parse_time_anchor(self, anchor: str) -> Optional[int]:
        """解析时间锚点（返回天数）
        
        Examples:
            "末世第1天" -> 1
            "末世第100天" -> 100
        """
        match = re.search(r"第(\d+)天", anchor)
        if match:
            return int(match.group(1))
        return None
    
    def _check_character_consistency(self, chapter: int) -> List[ConsistencyIssue]:
        """检查角色一致性"""
        issues = []
        state = self._load_state()
        
        # 1. 检查角色状态变化合理性
        entities = state.get("entities", {})
        state_changes = state.get("state_changes", [])
        
        # 按实体分组状态变化
        entity_changes = {}
        for change in state_changes:
            entity_id = change.get("entity_id", "")
            if entity_id not in entity_changes:
                entity_changes[entity_id] = []
            entity_changes[entity_id].append(change)
        
        # 检查每个角色的状态变化序列
        for entity_id, changes in entity_changes.items():
            # 按章节排序
            sorted_changes = sorted(changes, key=lambda x: x.get("chapter", 0))
            
            # 检查修为等级是否倒退
            prev_level = None
            for change in sorted_changes:
                current_level = self._parse_cultivation_level(change.get("new_state", ""))
                
                if prev_level is not None and current_level is not None:
                    if current_level < prev_level - 10:  # 允许小幅度波动
                        issues.append(ConsistencyIssue(
                            issue_type="character",
                            severity="warning",
                            chapter=change.get("chapter", 0),
                            description=f"角色{entity_id}修为等级异常倒退：从{prev_level}降至{current_level}",
                            details={
                                "entity": entity_id,
                                "prev_level": prev_level,
                                "current_level": current_level,
                            },
                            suggestion="检查是否有合理解释（如重伤、封印等）",
                        ))
                
                prev_level = current_level
        
        # 2. 检查角色消失问题
        for entity_id, entity in entities.items():
            last_appearance = entity.get("last_appearance")
            
            # 如果角色超过5章未出场，发出提醒
            if last_appearance and (chapter - last_appearance) > 5:
                issues.append(ConsistencyIssue(
                    issue_type="character",
                    severity="info",
                    chapter=chapter,
                    description=f"角色{entity_id}已{chapter - last_appearance}章未出场",
                    details={
                        "entity": entity_id,
                        "last_appearance": last_appearance,
                        "chapters_absent": chapter - last_appearance,
                    },
                    suggestion="考虑在后续章节中提及或安排出场",
                ))
        
        return issues
    
    def _check_worldview_consistency(self, chapter: int) -> List[ConsistencyIssue]:
        """检查世界观一致性"""
        issues = []
        state = self._load_state()
        
        # 1. 检查伏笔回收
        foreshadowings = state.get("foreshadowings", {})
        active_foreshadowings = foreshadowings.get("active", [])
        
        for fs in active_foreshadowings:
            expected_payoff = fs.get("expected_payoff_chapter", 0)
            
            # 如果超过预期回收章节5章，发出警告
            if expected_payoff > 0 and chapter > expected_payoff + 5:
                issues.append(ConsistencyIssue(
                    issue_type="worldview",
                    severity="warning",
                    chapter=chapter,
                    description=f"伏笔\"{fs.get('description')}\"已超期{chapter - expected_payoff}章未回收",
                    details={
                        "foreshadowing_id": fs.get("id"),
                        "description": fs.get("description"),
                        "expected_payoff": expected_payoff,
                        "overdue_chapters": chapter - expected_payoff,
                    },
                    suggestion="考虑尽快回收或调整预期章节",
                ))
        
        # 2. 检查设定冲突（简化版，实际需要更复杂的规则引擎）
        # 这里可以扩展为检查修仙体系、势力关系等世界观设定的一致性
        
        return issues
    
    def _check_ooc(self, chapter: int) -> List[ConsistencyIssue]:
        """检查角色OOC（Out of Character）"""
        issues = []
        state = self._load_state()
        
        # 读取当前章节内容
        content_file = self.content_dir / f"第{chapter:03d}章*.md"
        content_files = list(self.content_dir.glob(f"第{chapter:03d}章*.md"))
        
        if not content_files:
            return issues
        
        content = content_files[0].read_text(encoding="utf-8")
        
        # 1. 检查角色对话是否符合人设（简化版）
        entities = state.get("entities", {})
        
        for entity_id, entity in entities.items():
            if entity.get("type") != "character":
                continue
            
            # 这里简化实现，实际应该用LLM分析对话风格
            # 或者用规则引擎检查关键词
            
            # 示例：检查主角是否出现不符合身份的对话
            if entity.get("tier") == "protagonist":
                # 搜索主角对话
                dialogues = re.findall(rf"{entity_id}说[：:]\s*\"([^\"]+)\"", content)
                
                for dialogue in dialogues:
                    # 检查是否出现明显不符合主角人设的词汇
                    ooc_keywords = ["卧槽", "妈的", "他妈的"]  # 示例，实际需要根据人设定制
                    
                    if any(keyword in dialogue for keyword in ooc_keywords):
                        issues.append(ConsistencyIssue(
                            issue_type="ooc",
                            severity="warning",
                            chapter=chapter,
                            description=f"角色{entity_id}可能存在OOC对话",
                            details={
                                "entity": entity_id,
                                "dialogue": dialogue,
                            },
                            suggestion="检查对话是否符合角色人设",
                        ))
        
        return issues
    
    def batch_check(self, start_chapter: int, end_chapter: int) -> Dict[str, Any]:
        """批量检查多章节一致性"""
        reports = []
        
        for chapter in range(start_chapter, end_chapter + 1):
            report = self.check_chapter(chapter)
            reports.append(report.to_dict())
        
        # 统计总体情况
        total_issues = sum(r["total_issues"] for r in reports)
        total_errors = sum(r["errors"] for r in reports)
        total_warnings = sum(r["warnings"] for r in reports)
        
        return {
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "total_chapters": end_chapter - start_chapter + 1,
            "total_issues": total_issues,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "reports": reports,
        }
    
    def generate_report(self, report: ConsistencyReport, output_format: str = "markdown") -> str:
        """生成一致性检查报告"""
        if output_format == "markdown":
            return self._generate_markdown_report(report)
        else:
            return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    
    def _generate_markdown_report(self, report: ConsistencyReport) -> str:
        """生成Markdown格式报告"""
        md = f"# 一致性检查报告\n\n"
        md += f"**检查章节**：第{report.target_chapter}章\n"
        md += f"**检查时间**：{report.check_time}\n"
        md += f"**问题总数**：{report.total_issues}\n"
        md += f"**错误**：{report.errors}，**警告**：{report.warnings}\n\n"
        
        if not report.issues:
            md += "✅ **未发现一致性问题**\n"
            return md
        
        # 按严重程度分组
        errors = [issue for issue in report.issues if issue.severity == "error"]
        warnings = [issue for issue in report.issues if issue.severity == "warning"]
        infos = [issue for issue in report.issues if issue.severity == "info"]
        
        if errors:
            md += "## 🔴 错误\n\n"
            for i, issue in enumerate(errors, 1):
                md += f"### {i}. {issue.description}\n\n"
                md += f"- **类型**：{issue.issue_type}\n"
                md += f"- **章节**：第{issue.chapter}章\n"
                if issue.details:
                    md += f"- **详情**：\n"
                    for key, value in issue.details.items():
                        md += f"  - {key}: {value}\n"
                if issue.suggestion:
                    md += f"- **建议**：{issue.suggestion}\n"
                md += "\n"
        
        if warnings:
            md += "## 🟡 警告\n\n"
            for i, issue in enumerate(warnings, 1):
                md += f"### {i}. {issue.description}\n\n"
                md += f"- **类型**：{issue.issue_type}\n"
                md += f"- **章节**：第{issue.chapter}章\n"
                if issue.details:
                    md += f"- **详情**：\n"
                    for key, value in issue.details.items():
                        md += f"  - {key}: {value}\n"
                if issue.suggestion:
                    md += f"- **建议**：{issue.suggestion}\n"
                md += "\n"
        
        if infos:
            md += "## 🔵 提示\n\n"
            for i, issue in enumerate(infos, 1):
                md += f"{i}. {issue.description}\n"
                if issue.suggestion:
                    md += f"   - 建议：{issue.suggestion}\n"
        
        return md
    
    def _parse_cultivation_level(self, state_str: str) -> Optional[int]:
        """解析修为等级（数值化）
        
        Examples:
            "练气1层" -> 10
            "练气2层" -> 20
            "筑基初期" -> 100
        """
        if not state_str:
            return None
        
        # 练气期
        match = re.search(r"练气(\d+)层", state_str)
        if match:
            return int(match.group(1)) * 10
        
        # 筑基期
        if "筑基" in state_str:
            return 100
        
        # 金丹期
        if "金丹" in state_str:
            return 200
        
        # 元婴期
        if "元婴" in state_str:
            return 1000
        
        return None
