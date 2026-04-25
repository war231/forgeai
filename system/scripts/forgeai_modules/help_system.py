"""
Help System - 命令行帮助系统

提供详细的命令帮助、示例和快速入门指南。
"""

from typing import Dict, List, Optional
from .cli_formatter import console, print_header, print_list, print_table, print_panel


class CommandHelp:
    """命令帮助信息"""
    
    def __init__(
        self,
        name: str,
        description: str,
        usage: str,
        examples: List[str],
        options: Optional[Dict[str, str]] = None,
        see_also: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.usage = usage
        self.examples = examples
        self.options = options or {}
        self.see_also = see_also or []
    
    def print(self) -> None:
        """打印帮助信息"""
        # 标题
        print_header(f"命令: {self.name}")
        
        # 描述
        console.print(f"\n{self.description}\n", style="bold white")
        
        # 用法
        console.print("用法:", style="bold cyan")
        console.print(f"  {self.usage}\n", style="white")
        
        # 选项
        if self.options:
            console.print("选项:", style="bold cyan")
            for opt, desc in self.options.items():
                console.print(f"  {opt:<20} {desc}", style="white")
            console.print()
        
        # 示例
        if self.examples:
            console.print("示例:", style="bold cyan")
            for i, example in enumerate(self.examples, 1):
                console.print(f"  {i}. {example}", style="dim white")
            console.print()
        
        # 相关命令
        if self.see_also:
            console.print("相关命令:", style="bold cyan")
            console.print(f"  {', '.join(self.see_also)}\n", style="white")


class HelpSystem:
    """帮助系统"""
    
    # 命令帮助库
    COMMANDS: Dict[str, CommandHelp] = {
        "init": CommandHelp(
            name="init",
            description="初始化新的小说项目，创建必要的目录结构和配置文件。",
            usage="forgeai init [项目名称] [选项]",
            examples=[
                "forgeai init 我的小说",
                "forgeai init 我的小说 --template fantasy",
                "forgeai init 我的小说 --author 作者名",
            ],
            options={
                "--template": "项目模板 (fantasy, scifi, romance, mystery)",
                "--author": "作者名称",
                "--output": "输出目录 (默认: 当前目录)",
            },
            see_also=["config", "generate"],
        ),
        
        "generate": CommandHelp(
            name="generate",
            description="生成小说章节内容，支持单章节和批量生成。",
            usage="forgeai generate [章节号] [选项]",
            examples=[
                "forgeai generate 1",
                "forgeai generate 1-5",
                "forgeai generate 1 --words 3000",
                "forgeai generate --all",
            ],
            options={
                "--words": "目标字数 (默认: 2000)",
                "--context": "上下文章节数 (默认: 3)",
                "--theme": "主题指导",
                "--all": "生成所有未完成章节",
                "--batch": "批量生成模式",
            },
            see_also=["optimize", "status"],
        ),
        
        "optimize": CommandHelp(
            name="optimize",
            description="优化已生成的章节内容，提升质量和一致性。",
            usage="forgeai optimize [章节号] [选项]",
            examples=[
                "forgeai optimize 1",
                "forgeai optimize 1-5",
                "forgeai optimize --all",
                "forgeai optimize 1 --focus consistency",
            ],
            options={
                "--focus": "优化重点 (consistency, style, pacing)",
                "--iterations": "优化迭代次数 (默认: 2)",
                "--all": "优化所有章节",
            },
            see_also=["generate", "validate"],
        ),
        
        "validate": CommandHelp(
            name="validate",
            description="验证章节内容的一致性和质量。",
            usage="forgeai validate [章节号] [选项]",
            examples=[
                "forgeai validate 1",
                "forgeai validate 1-10",
                "forgeai validate --all",
                "forgeai validate --strict",
            ],
            options={
                "--strict": "严格模式，检查所有细节",
                "--all": "验证所有章节",
                "--report": "生成详细报告",
            },
            see_also=["optimize", "status"],
        ),
        
        "status": CommandHelp(
            name="status",
            description="查看项目状态和进度统计。",
            usage="forgeai status [选项]",
            examples=[
                "forgeai status",
                "forgeai status --detailed",
                "forgeai status --json",
            ],
            options={
                "--detailed": "显示详细信息",
                "--json": "输出JSON格式",
            },
            see_also=["generate", "validate"],
        ),
        
        "config": CommandHelp(
            name="config",
            description="配置项目设置和API密钥。",
            usage="forgeai config <操作> [参数]",
            examples=[
                "forgeai config set api_key YOUR_KEY",
                "forgeai config get api_key",
                "forgeai config list",
                "forgeai config set model gpt-4",
            ],
            options={
                "set": "设置配置项",
                "get": "获取配置项",
                "list": "列出所有配置",
                "reset": "重置为默认值",
            },
            see_also=["init"],
        ),
        
        "export": CommandHelp(
            name="export",
            description="导出小说为各种格式。",
            usage="forgeai export [格式] [选项]",
            examples=[
                "forgeai export txt",
                "forgeai export epub --output 小说.epub",
                "forgeai export pdf --chapters 1-10",
            ],
            options={
                "--output": "输出文件名",
                "--chapters": "导出章节范围",
                "--template": "导出模板",
            },
            see_also=["status"],
        ),
        
        "help": CommandHelp(
            name="help",
            description="显示帮助信息。",
            usage="forgeai help [命令名]",
            examples=[
                "forgeai help",
                "forgeai help generate",
                "forgeai help config",
            ],
            see_also=["init", "generate", "optimize"],
        ),
    }
    
    @classmethod
    def show_help(cls, command_name: Optional[str] = None) -> None:
        """
        显示帮助信息
        
        Args:
            command_name: 命令名称，None 表示显示总体帮助
        """
        if command_name:
            # 显示特定命令帮助
            if command_name in cls.COMMANDS:
                cls.COMMANDS[command_name].print()
            else:
                console.print(f"\n错误: 未知命令 '{command_name}'\n", style="bold red")
                console.print("可用命令:", style="bold cyan")
                print_list(list(cls.COMMANDS.keys()))
        else:
            # 显示总体帮助
            cls._show_overview()
    
    @classmethod
    def _show_overview(cls) -> None:
        """显示总体帮助概览"""
        print_header("ForgeAI - AI小说生成工具")
        
        # 简介
        console.print("\nForgeAI 是一个基于AI的小说生成工具，帮助作者快速创作高质量小说。\n", style="white")
        
        # 快速开始
        console.print("快速开始:", style="bold cyan")
        steps = [
            "forgeai init 我的小说        # 初始化项目",
            "forgeai config set api_key  # 配置API密钥",
            "forgeai generate 1          # 生成第一章",
            "forgeai status              # 查看状态",
        ]
        for step in steps:
            console.print(f"  {step}", style="dim white")
        console.print()
        
        # 命令列表
        console.print("可用命令:", style="bold cyan")
        commands_data = [
            {"命令": cmd, "说明": help.description}
            for cmd, help in cls.COMMANDS.items()
        ]
        print_table(commands_data, ["命令", "说明"])
        
        # 更多帮助
        console.print("\n使用 'forgeai help <命令>' 查看详细帮助\n", style="dim white")
    
    @classmethod
    def show_version(cls) -> None:
        """显示版本信息"""
        print_panel(
            "ForgeAI v1.1.0\n"
            "AI小说生成工具\n\n"
            "作者: ForgeAI Team\n"
            "许可: MIT",
            title="版本信息",
            style="green"
        )
    
    @classmethod
    def show_quick_start(cls) -> None:
        """显示快速入门指南"""
        print_header("快速入门指南")
        
        console.print("\n欢迎使用 ForgeAI！按照以下步骤开始创作：\n", style="white")
        
        steps = [
            ("初始化项目", "forgeai init 我的小说"),
            ("配置API密钥", "forgeai config set api_key YOUR_KEY"),
            ("生成第一章", "forgeai generate 1"),
            ("查看状态", "forgeai status"),
            ("优化内容", "forgeai optimize 1"),
            ("导出小说", "forgeai export txt"),
        ]
        
        for i, (desc, cmd) in enumerate(steps, 1):
            console.print(f"{i}. {desc}", style="bold cyan")
            console.print(f"   {cmd}\n", style="dim white")
        
        console.print("💡 提示: 使用 'forgeai help <命令>' 获取详细帮助\n", style="yellow")


# 示例用法
if __name__ == "__main__":
    # 显示总体帮助
    HelpSystem.show_help()
    
    print("\n" + "="*60 + "\n")
    
    # 显示特定命令帮助
    HelpSystem.show_help("generate")
    
    print("\n" + "="*60 + "\n")
    
    # 显示快速入门
    HelpSystem.show_quick_start()
