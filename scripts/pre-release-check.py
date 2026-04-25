#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布前检查脚本

运行所有自动化检查，确保代码质量符合发布标准。
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# 添加颜色输出支持
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_header(title: str) -> None:
    """打印标题"""
    if HAS_RICH:
        console.print(f"\n{'='*60}", style="bold blue")
        console.print(f"  {title}", style="bold blue")
        console.print(f"{'='*60}\n", style="bold blue")
    else:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")


def print_success(message: str) -> None:
    """打印成功消息"""
    if HAS_RICH:
        console.print(f"✓ {message}", style="bold green")
    else:
        print(f"✓ {message}")


def print_error(message: str) -> None:
    """打印错误消息"""
    if HAS_RICH:
        console.print(f"✗ {message}", style="bold red")
    else:
        print(f"✗ {message}")


def print_warning(message: str) -> None:
    """打印警告消息"""
    if HAS_RICH:
        console.print(f"⚠ {message}", style="bold yellow")
    else:
        print(f"⚠ {message}")


def run_command(cmd: str, description: str, cwd: Path = None) -> Tuple[bool, str]:
    """
    运行命令并报告结果
    
    Args:
        cmd: 要运行的命令
        description: 检查描述
        cwd: 工作目录
    
    Returns:
        (是否成功, 输出内容)
    """
    print_header(f"检查: {description}")
    print(f"命令: {cmd}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300  # 5分钟超时
        )
        
        output = result.stdout + result.stderr
        
        if result.returncode != 0:
            print_error(f"失败: {description}")
            if output:
                print(output)
            return False, output
        else:
            print_success(f"通过: {description}")
            if output and "--verbose" in sys.argv:
                print(output)
            return True, output
    
    except subprocess.TimeoutExpired:
        print_error(f"超时: {description}")
        return False, "Command timed out"
    except Exception as e:
        print_error(f"异常: {description} - {str(e)}")
        return False, str(e)


def check_tests(project_root: Path) -> bool:
    """检查测试套件"""
    cmd = "python -m pytest tests/ -v --tb=short --cov=forgeai_modules --cov-report=term-missing"
    success, _ = run_command(cmd, "测试套件", project_root)
    return success


def check_code_style(project_root: Path) -> bool:
    """检查代码风格"""
    cmd = "python -m flake8 system/scripts/forgeai_modules/ --max-line-length=100 --exclude=__pycache__"
    success, _ = run_command(cmd, "代码风格检查 (flake8)", project_root)
    return success


def check_code_format(project_root: Path) -> bool:
    """检查代码格式"""
    cmd = "python -m black --check system/scripts/forgeai_modules/"
    success, _ = run_command(cmd, "代码格式检查 (black)", project_root)
    return success


def check_types(project_root: Path) -> bool:
    """检查类型"""
    cmd = "python -m mypy system/scripts/forgeai_modules/ --ignore-missing-imports --no-error-summary"
    success, _ = run_command(cmd, "类型检查 (mypy)", project_root)
    return success


def check_security(project_root: Path) -> bool:
    """检查依赖安全性"""
    # 检查 pip-audit 是否安装
    try:
        subprocess.run(["pip-audit", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("pip-audit 未安装，跳过安全检查")
        print_warning("安装方法: pip install pip-audit")
        return True  # 不阻塞发布
    
    cmd = "pip-audit --desc"
    success, _ = run_command(cmd, "依赖安全检查 (pip-audit)", project_root)
    return success


def check_imports(project_root: Path) -> bool:
    """检查导入是否正常"""
    print_header("检查: 模块导入测试")
    
    try:
        # 测试主要模块导入
        sys.path.insert(0, str(project_root / "system" / "scripts"))
        
        import forgeai_modules
        print_success(f"forgeai_modules 导入成功 (version: {forgeai_modules.__version__})")
        
        # 测试关键模块
        from forgeai_modules import config
        print_success("config 模块导入成功")
        
        from forgeai_modules import cli_formatter
        print_success("cli_formatter 模块导入成功")
        
        from forgeai_modules import help_system
        print_success("help_system 模块导入成功")
        
        from forgeai_modules import progress_display
        print_success("progress_display 模块导入成功")
        
        from forgeai_modules import error_handler
        print_success("error_handler 模块导入成功")
        
        return True
    
    except Exception as e:
        print_error(f"模块导入失败: {str(e)}")
        return False


def print_summary(results: List[Tuple[str, bool]]) -> None:
    """打印结果汇总"""
    print_header("检查结果汇总")
    
    if HAS_RICH:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("检查项目", style="white")
        table.add_column("状态", style="white")
        
        for desc, passed in results:
            status = "✅ 通过" if passed else "❌ 失败"
            status_style = "green" if passed else "red"
            table.add_row(desc, f"[{status_style}]{status}[/{status_style}]")
        
        console.print(table)
    else:
        for desc, passed in results:
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"{status}: {desc}")
    
    # 统计
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print()
    if passed_count == total_count:
        print_success(f"所有检查通过！({passed_count}/{total_count})")
        print_success("可以发布 v1.1.0 版本")
    else:
        print_error(f"部分检查失败 ({passed_count}/{total_count})")
        print_error("请修复失败项后再发布")


def main():
    """运行所有检查"""
    project_root = Path(__file__).resolve().parent.parent
    
    print_header("ForgeAI v1.1.0 发布前检查")
    print(f"项目根目录: {project_root}\n")
    
    # 定义所有检查
    checks = [
        ("测试套件", lambda: check_tests(project_root)),
        ("代码风格", lambda: check_code_style(project_root)),
        ("代码格式", lambda: check_code_format(project_root)),
        ("类型检查", lambda: check_types(project_root)),
        ("依赖安全", lambda: check_security(project_root)),
        ("模块导入", lambda: check_imports(project_root)),
    ]
    
    # 运行所有检查
    results = []
    for desc, check_func in checks:
        try:
            passed = check_func()
            results.append((desc, passed))
        except Exception as e:
            print_error(f"{desc} 检查异常: {str(e)}")
            results.append((desc, False))
    
    # 打印汇总
    print_summary(results)
    
    # 返回退出码
    all_passed = all(passed for _, passed in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
