"""
CLI Formatter - 统一的命令行输出格式化工具

提供彩色输出、表格、面板等格式化功能，让 CLI 输出更易读。
"""

from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich import print as rprint


# 创建全局 Console 实例
console = Console()


def print_success(message: str) -> None:
    """打印成功消息（绿色）"""
    console.print(f"✓ {message}", style="bold green")


def print_error(message: str, suggestion: Optional[str] = None) -> None:
    """打印错误消息（红色）"""
    console.print(f"✗ {message}", style="bold red")
    if suggestion:
        console.print(f"  💡 建议: {suggestion}", style="yellow")


def print_warning(message: str) -> None:
    """打印警告消息（黄色）"""
    console.print(f"⚠ {message}", style="bold yellow")


def print_info(message: str) -> None:
    """打印信息消息（蓝色）"""
    console.print(f"ℹ {message}", style="bold blue")


def print_table(data: List[Dict], headers: List[str], title: Optional[str] = None) -> None:
    """打印表格"""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    
    # 添加列
    for header in headers:
        table.add_column(header, style="white")
    
    # 添加行
    for row in data:
        table.add_row(*[str(row.get(h, "")) for h in headers])
    
    console.print(table)


def print_panel(content: str, title: Optional[str] = None, style: str = "blue") -> None:
    """打印面板"""
    panel = Panel(content, title=title, border_style=style)
    console.print(panel)


def print_code(code: str, language: str = "python") -> None:
    """打印代码（带语法高亮）"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


def print_header(title: str) -> None:
    """打印标题头"""
    console.print(f"\n{'='*60}", style="bold blue")
    console.print(f"  {title}", style="bold blue")
    console.print(f"{'='*60}\n", style="bold blue")


def print_step(step: int, total: int, message: str) -> None:
    """打印步骤信息"""
    console.print(f"\n[{step}/{total}] {message}", style="bold cyan")


def print_list(items: List[str], title: Optional[str] = None) -> None:
    """打印列表"""
    if title:
        console.print(f"\n{title}:", style="bold white")
    for i, item in enumerate(items, 1):
        console.print(f"  {i}. {item}", style="white")


def print_dict(data: Dict, title: Optional[str] = None) -> None:
    """打印字典"""
    if title:
        console.print(f"\n{title}:", style="bold white")
    for key, value in data.items():
        console.print(f"  • {key}: {value}", style="white")


def create_progress(description: str = "处理中") -> Progress:
    """创建进度条"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    )


def clear_screen() -> None:
    """清屏"""
    console.clear()


# 示例用法
if __name__ == "__main__":
    print_header("ForgeAI CLI Formatter")
    
    print_success("操作成功完成！")
    print_error("操作失败", "请检查配置文件")
    print_warning("这是一个警告")
    print_info("这是一条信息")
    
    print_table(
        data=[
            {"名称": "项目A", "状态": "完成", "进度": "100%"},
            {"名称": "项目B", "状态": "进行中", "进度": "50%"},
        ],
        headers=["名称", "状态", "进度"],
        title="项目列表"
    )
    
    print_panel("这是一个面板内容", title="面板标题")
    
    print_list(["项目1", "项目2", "项目3"], title="项目列表")
    
    print_dict({"版本": "v1.1", "状态": "稳定", "测试覆盖率": "103.45%"}, title="项目信息")
