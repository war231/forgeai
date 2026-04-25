"""
ForgeAI - AI-powered novel writing system with multi-agent collaboration
"""

__version__ = "1.0.0"
__author__ = "ForgeAI Team"

__all__ = ["main", "__version__"]

# 导入CLI入口（延迟导入以避免循环依赖）
def main():
    """CLI entry point"""
    from .forgeai import main as _main
    _main()
