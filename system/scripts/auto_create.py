#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ForgeAI 一键创作助手
自动执行完整的创作流程
"""
import sys
import json
import asyncio
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from forgeai_modules.config import get_config
from forgeai_modules.pipeline import Pipeline
from forgeai_modules.context_extractor import ContextExtractor
from forgeai_modules.consistency_checker import ConsistencyChecker


class AutoCreationAssistant:
    """一键创作助手"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.config = get_config(self.project_root)
        self.pipeline = Pipeline(self.config)
        
    def create_chapter(self, chapter: int, text_file: str, 
                      auto_review: bool = True,
                      auto_consistency: bool = False) -> dict:
        """
        一键创作流程
        
        Args:
            chapter: 章节号
            text_file: 正文文件路径
            auto_review: 是否自动审查
            auto_consistency: 是否自动一致性检查
            
        Returns:
            完整流程结果
        """
        results = {"chapter": chapter, "steps": {}}
        
        # Step 1: 写前检查
        print(f"\n{'='*60}")
        print(f"📝 第{chapter}章创作流程")
        print(f"{'='*60}\n")
        
        print("1️⃣ 写前检查...")
        pre_check = self.pipeline.pre_write_check(chapter)
        results["steps"]["pre_check"] = pre_check
        
        if pre_check.get("alerts"):
            print("⚠️ 发现以下提醒：")
            for alert in pre_check["alerts"]:
                print(f"  [{alert['level']}] {alert['message']}")
        else:
            print("✅ 写前检查通过")
        
        # Step 2: 提取上下文
        print("\n2️⃣ 提取上下文...")
        extractor = ContextExtractor(self.config)
        context = asyncio.run(extractor.extract_with_rag(chapter))
        formatted_context = extractor.format_context_for_prompt(context)
        results["steps"]["context"] = {
            "status": "ok",
            "length": len(formatted_context),
            "entities": len(context.entities),
            "foreshadowing": len(context.foreshadowing)
        }
        print(f"✅ 上下文提取完成（{len(formatted_context)}字符）")
        
        # Step 3: 读取正文
        print(f"\n3️⃣ 读取正文: {text_file}")
        text_path = Path(text_file)
        if not text_path.exists():
            results["steps"]["error"] = f"文件不存在: {text_file}"
            return results
        
        text = text_path.read_text(encoding="utf-8")
        print(f"✅ 正文读取完成（{len(text)}字符）")
        
        # Step 4: 写后流水线（自动）
        print("\n4️⃣ 执行写后流水线...")
        post_result = asyncio.run(
            self.pipeline.post_write(
                chapter=chapter,
                text=text,
                source_file=str(text_path),
                score_ai=True,
                extract_llm=False
            )
        )
        results["steps"]["post_write"] = post_result["steps"]
        
        print("✅ 写后流水线完成：")
        for step, result in post_result["steps"].items():
            status = "✅" if result.get("status") == "ok" else "❌"
            print(f"  {status} {step}")
        
        # Step 5: 自动审查（可选）
        if auto_review:
            print("\n5️⃣ 执行章节审查...")
            # 这里可以调用审查逻辑
            results["steps"]["review"] = {"status": "skipped", "message": "请手动执行 forgeai check review"}
            print("⚠️ 审查需要手动执行: forgeai check review " + str(chapter))
        
        # Step 6: 一致性检查（可选）
        if auto_consistency:
            print("\n6️⃣ 执行一致性检查...")
            checker = ConsistencyChecker(self.project_root)
            report = checker.check_chapter(chapter, "full")
            results["steps"]["consistency"] = {
                "status": "ok",
                "total_issues": report.total_issues,
                "errors": report.errors,
                "warnings": report.warnings
            }
            print(f"✅ 一致性检查完成（{report.total_issues}个问题）")
        
        # 总结
        print(f"\n{'='*60}")
        print("📊 创作流程总结")
        print(f"{'='*60}")
        print(f"章节: 第{chapter}章")
        print(f"字数: {len(text)}")
        print(f"索引: {post_result['steps'].get('index', {}).get('chunks', 0)} 个分块")
        print(f"实体: {post_result['steps'].get('extract', {}).get('entities', 0)} 个")
        print(f"状态变更: {post_result['steps'].get('extract', {}).get('state_changes', 0)} 个")
        print(f"AI味评分: {post_result['steps'].get('score', {}).get('score', 0):.2f}")
        print(f"下一章提醒: {len(post_result['steps'].get('pre_check_next', {}).get('alerts', []))} 条")
        print(f"{'='*60}\n")
        
        return results


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ForgeAI 一键创作助手")
    parser.add_argument("chapter", type=int, help="章节号")
    parser.add_argument("text_file", help="正文文件路径")
    parser.add_argument("--project-root", help="项目根目录", default=".")
    parser.add_argument("--auto-review", action="store_true", help="自动审查")
    parser.add_argument("--auto-consistency", action="store_true", help="自动一致性检查")
    
    args = parser.parse_args()
    
    assistant = AutoCreationAssistant(args.project_root)
    result = assistant.create_chapter(
        chapter=args.chapter,
        text_file=args.text_file,
        auto_review=args.auto_review,
        auto_consistency=args.auto_consistency
    )
    
    # 保存结果
    output_file = Path(args.text_file).parent / f".forgeai/chapter_{args.chapter}_result.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📄 结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
