#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计章节字数
"""

import re
from pathlib import Path


def count_chinese_words(text: str) -> int:
    """统计中文字数（不包括标点符号和空格）"""
    # 移除标题行
    text = re.sub(r'^#.*$', '', text, flags=re.MULTILINE)
    # 移除标点符号和空格
    text = re.sub(r'[，。！？、；：""''（）《》【】 ]', '', text)
    # 统计中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    return len(chinese_chars)


def main():
    """统计测试章节字数"""
    base_dir = Path("e:/xiangmu/小说/novel-forge-kit/projects/示例小说/4-正文")
    
    chapters = [
        "第001章-末世降临.md",
        "第002章-初战妖兽.md"
    ]
    
    print("=" * 60)
    print("章节字数统计")
    print("=" * 60)
    
    for chapter in chapters:
        file_path = base_dir / chapter
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8")
            word_count = count_chinese_words(text)
            
            print(f"\n{chapter}")
            print(f"字数: {word_count}")
            status = "[OK]" if word_count >= 2300 else "[FAIL]"
            print(f"达标: {status} (要求: 2300-3000字)")
        else:
            print(f"\n{chapter} - 文件不存在")
    
    print("\n" + "=" * 60)
    print("系统要求: 2300-3000字/章")
    print("=" * 60)


if __name__ == "__main__":
    main()
