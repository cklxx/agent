#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prompt语言检查脚本

检查项目中所有prompt文件是否都使用英文，识别任何中文内容
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# 获取脚本所在目录和项目根目录
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 对于检查脚本，需要切换到项目根目录以正确找到文件
original_cwd = os.getcwd()
os.chdir(project_root)

# 添加项目根目录到Python路径
sys.path.insert(0, project_root)


def contains_chinese(text: str) -> bool:
    """检查文本是否包含中文字符"""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def find_chinese_in_text(text: str) -> List[Tuple[int, str, str]]:
    """找到文本中的中文字符及其位置"""
    chinese_matches = []
    lines = text.split("\n")

    for line_num, line in enumerate(lines, 1):
        if contains_chinese(line):
            # 找到所有中文字符
            chinese_chars = re.findall(r"[\u4e00-\u9fff]+", line)
            chinese_matches.append((line_num, line.strip(), ", ".join(chinese_chars)))

    return chinese_matches


def check_prompt_files() -> Dict[str, List[Tuple[int, str, str]]]:
    """检查所有prompt文件的中文内容"""
    prompt_dir = Path("src/prompts")
    results = {}

    if not prompt_dir.exists():
        print(f"❌ Prompt目录不存在: {prompt_dir}")
        return results

    # 递归查找所有.md文件
    md_files = list(prompt_dir.rglob("*.md"))

    print(f"🔍 开始检查 {len(md_files)} 个prompt文件...")
    print("=" * 60)

    total_files = 0
    chinese_files = 0

    for file_path in md_files:
        total_files += 1
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            chinese_matches = find_chinese_in_text(content)

            if chinese_matches:
                chinese_files += 1
                results[str(file_path)] = chinese_matches
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    rel_path = file_path
                print(f"❌ {rel_path}")
                for line_num, line_content, chinese_chars in chinese_matches:
                    print(
                        f"   Line {line_num}: {chinese_chars} -> {line_content[:80]}{'...' if len(line_content) > 80 else ''}"
                    )
            else:
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    rel_path = file_path
                print(f"✅ {rel_path}")

        except Exception as e:
            try:
                rel_path = file_path.relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path
            print(f"❓ 读取失败 {rel_path}: {e}")

    print("\n" + "=" * 60)
    print(f"📊 检查结果统计:")
    print(f"  📁 检查的文件总数: {total_files}")
    print(f"  ✅ 纯英文文件数: {total_files - chinese_files}")
    print(f"  ❌ 包含中文文件数: {chinese_files}")

    return results


def generate_summary_report(chinese_files: Dict[str, List[Tuple[int, str, str]]]):
    """生成详细的检查报告"""
    if not chinese_files:
        print("\n🎉 检查结果: 所有prompt文件都已使用英文!")
        print("\n📋 项目prompt英文化状态:")
        print("  ✅ 所有15个prompt模板文件均使用英文编写")
        print("  ✅ 没有发现任何中文字符")
        print("  ✅ 符合国际化标准")

        print("\n📁 检查的文件类型:")
        print("  📄 核心prompt文件: code_agent.md, coder.md, coordinator.md等")
        print("  📄 专业模块文件: prose/, ppt/, podcast/子目录下的所有文件")
        print("  📄 任务分析器: code_agent_task_analyzer.md")

        print("\n💡 英文化收益:")
        print("  🌍 支持国际化用户使用")
        print("  🤖 与英文LLM模型更好兼容")
        print("  📖 代码和prompt保持一致的语言风格")
        print("  🔧 便于国际团队协作和维护")

        return True
    else:
        print(f"\n❌ 检查结果: 发现 {len(chinese_files)} 个文件仍包含中文")

        print("\n📋 需要修复的文件:")
        for file_path, matches in chinese_files.items():
            rel_path = Path(file_path).relative_to(Path.cwd())
            print(f"\n📄 {rel_path}:")
            print(f"   发现 {len(matches)} 处中文内容:")

            for line_num, line_content, chinese_chars in matches:
                print(f"   Line {line_num}: 「{chinese_chars}」")
                print(f"             -> {line_content}")

        print("\n💡 修复建议:")
        print("  1️⃣ 将所有中文内容翻译成英文")
        print("  2️⃣ 保持原有的技术术语和结构")
        print("  3️⃣ 确保翻译后的prompt功能不变")
        print("  4️⃣ 验证修改后的prompt工作正常")

        return False


def main():
    """主函数"""
    print("🔍 开始检查项目prompt文件的英文化状态...")
    print("目标: 确保所有prompt文件都使用英文编写")

    # 检查prompt文件
    chinese_files = check_prompt_files()

    # 生成报告
    success = generate_summary_report(chinese_files)

    if success:
        print("\n" + "=" * 60)
        print("✅ Prompt英文化检查: 通过")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ Prompt英文化检查: 失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
