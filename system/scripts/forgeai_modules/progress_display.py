"""
Progress Display - 进度显示模块

提供进度条、状态跟踪和实时更新功能。
"""

from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

from .cli_formatter import console


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(
        self,
        total: int,
        description: str = "处理中",
        show_time: bool = True,
    ):
        self.total = total
        self.description = description
        self.show_time = show_time
        self.current = 0
        self.progress: Optional[Progress] = None
        self.task_id = None
    
    def start(self) -> None:
        """开始进度跟踪"""
        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ]
        
        if self.show_time:
            columns.append(TimeRemainingColumn())
        
        self.progress = Progress(*columns, console=console)
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=self.total)
    
    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        """更新进度"""
        if self.progress and self.task_id is not None:
            self.current += advance
            update_kwargs = {"advance": advance}
            if description:
                update_kwargs["description"] = description
            self.progress.update(self.task_id, **update_kwargs)
    
    def complete(self) -> None:
        """完成进度"""
        if self.progress:
            self.progress.stop()
    
    @contextmanager
    def track(self):
        """上下文管理器模式"""
        self.start()
        try:
            yield self
        finally:
            self.complete()


class MultiProgressTracker:
    """多任务进度跟踪器"""
    
    def __init__(self, tasks: List[Dict[str, Any]]):
        """
        Args:
            tasks: 任务列表，每个任务包含 name, total, description
        """
        self.tasks = tasks
        self.progress: Optional[Progress] = None
        self.task_ids: Dict[str, int] = {}
    
    def start(self) -> None:
        """开始跟踪"""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        )
        self.progress.start()
        
        for task in self.tasks:
            task_id = self.progress.add_task(
                task.get("description", task["name"]),
                total=task["total"],
            )
            self.task_ids[task["name"]] = task_id
    
    def update(self, task_name: str, advance: int = 1, description: Optional[str] = None) -> None:
        """更新任务进度"""
        if self.progress and task_name in self.task_ids:
            update_kwargs = {"advance": advance}
            if description:
                update_kwargs["description"] = description
            self.progress.update(self.task_ids[task_name], **update_kwargs)
    
    def complete(self) -> None:
        """完成跟踪"""
        if self.progress:
            self.progress.stop()
    
    @contextmanager
    def track(self):
        """上下文管理器模式"""
        self.start()
        try:
            yield self
        finally:
            self.complete()


class StatusDisplay:
    """状态显示器"""
    
    def __init__(self, title: str = "项目状态"):
        self.title = title
        self.status_data: Dict[str, Any] = {}
    
    def update(self, key: str, value: Any) -> None:
        """更新状态数据"""
        self.status_data[key] = value
    
    def display(self) -> None:
        """显示状态"""
        table = Table(title=self.title, show_header=True, header_style="bold cyan")
        table.add_column("项目", style="white")
        table.add_column("状态", style="green")
        
        for key, value in self.status_data.items():
            table.add_row(str(key), str(value))
        
        console.print(table)


class ChapterProgress:
    """章节进度管理"""
    
    def __init__(self, total_chapters: int):
        self.total_chapters = total_chapters
        self.completed_chapters: List[int] = []
        self.current_chapter: Optional[int] = None
    
    def start_chapter(self, chapter: int) -> None:
        """开始章节"""
        self.current_chapter = chapter
        console.print(f"\n[开始] 章节 {chapter}/{self.total_chapters}", style="bold cyan")
    
    def complete_chapter(self, chapter: int, success: bool = True) -> None:
        """完成章节"""
        if success:
            self.completed_chapters.append(chapter)
            console.print(f"[完成] 章节 {chapter} ✓", style="bold green")
        else:
            console.print(f"[失败] 章节 {chapter} ✗", style="bold red")
        
        self.current_chapter = None
    
    def show_summary(self) -> None:
        """显示摘要"""
        completed = len(self.completed_chapters)
        total = self.total_chapters
        percentage = (completed / total * 100) if total > 0 else 0
        
        panel = Panel(
            f"已完成章节: {completed}/{total} ({percentage:.1f}%)\n"
            f"完成章节: {', '.join(map(str, self.completed_chapters)) if self.completed_chapters else '无'}",
            title="进度摘要",
            border_style="green",
        )
        console.print(panel)


def create_spinner(message: str = "处理中") -> Progress:
    """创建旋转加载器"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


@contextmanager
def show_progress(description: str, total: int):
    """简单的进度上下文管理器"""
    tracker = ProgressTracker(total, description)
    tracker.start()
    try:
        yield tracker
    finally:
        tracker.complete()


@contextmanager
def show_spinner(message: str = "处理中"):
    """旋转加载器上下文管理器"""
    progress = create_spinner(message)
    progress.start()
    task_id = progress.add_task(message, total=None)
    try:
        yield progress
    finally:
        progress.stop()


# 示例用法
if __name__ == "__main__":
    import time
    
    # 示例1: 基本进度跟踪
    print("示例1: 基本进度跟踪")
    with show_progress("生成章节", 10) as tracker:
        for i in range(10):
            time.sleep(0.1)
            tracker.update(1)
    
    # 示例2: 章节进度
    print("\n示例2: 章节进度")
    chapter_progress = ChapterProgress(5)
    for i in range(1, 6):
        chapter_progress.start_chapter(i)
        time.sleep(0.2)
        chapter_progress.complete_chapter(i)
    
    chapter_progress.show_summary()
    
    # 示例3: 状态显示
    print("\n示例3: 状态显示")
    status = StatusDisplay("项目状态")
    status.update("总章节", 10)
    status.update("已完成", 5)
    status.update("进行中", 2)
    status.update("待生成", 3)
    status.display()
    
    # 示例4: 旋转加载器
    print("\n示例4: 旋转加载器")
    with show_spinner("加载配置文件..."):
        time.sleep(1)
