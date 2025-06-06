#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prompt一致性检查脚本

检查项目中所有prompt是否都使用apply_prompt_template统一管理
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set

# 获取脚本所在目录和项目根目录
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 对于检查脚本，需要切换到项目根目录以正确找到文件
original_cwd = os.getcwd()
os.chdir(project_root)

# 添加项目根目录到Python路径
sys.path.insert(0, project_root)


def find_python_files(directory: str) -> List[Path]:
    """找到所有Python文件"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # 跳过一些不需要检查的目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files


def check_file_for_prompt_patterns(file_path: Path) -> Dict[str, List[str]]:
    """检查文件中的prompt使用模式"""
    issues = {
        "direct_get_prompt_template": [],
        "hardcoded_system_message": [],
        "hardcoded_prompt_strings": [],
        "correct_apply_prompt_template": []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 检查每一行
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # 检查直接使用get_prompt_template的情况
            if 'get_prompt_template(' in line and 'SystemMessage' in line:
                issues["direct_get_prompt_template"].append(f"Line {line_num}: {line_stripped}")
            
            # 检查硬编码的SystemMessage
            if 'SystemMessage(content=' in line and 'get_prompt_template' not in line and 'apply_prompt_template' not in line:
                issues["hardcoded_system_message"].append(f"Line {line_num}: {line_stripped}")
            
            # 检查可能的硬编码prompt字符串（多行字符串开始）
            if re.search(r'(prompt|system_prompt|analysis_prompt)\s*=\s*[f]?["\']', line):
                issues["hardcoded_prompt_strings"].append(f"Line {line_num}: {line_stripped}")
            
            # 检查正确使用apply_prompt_template的情况
            if 'apply_prompt_template(' in line:
                issues["correct_apply_prompt_template"].append(f"Line {line_num}: {line_stripped}")
    
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
    
    return issues


def check_prompt_templates_exist() -> Set[str]:
    """检查prompt模板文件是否存在"""
    prompt_dir = Path("src/prompts")
    template_files = set()
    
    if prompt_dir.exists():
        for file_path in prompt_dir.rglob("*.md"):
            # 获取相对于prompts目录的路径，去掉.md扩展名
            relative_path = file_path.relative_to(prompt_dir)
            template_name = str(relative_path).replace('.md', '').replace(os.sep, '/')
            template_files.add(template_name)
    
    return template_files


def main():
    """主函数"""
    print("🔍 开始检查项目中prompt使用的一致性...")
    print("=" * 60)
    
    # 1. 检查prompt模板文件
    print("\n📁 检查可用的prompt模板文件:")
    prompt_templates = check_prompt_templates_exist()
    for template in sorted(prompt_templates):
        print(f"  ✅ {template}")
    
    print(f"\n📊 共找到 {len(prompt_templates)} 个prompt模板文件")
    
    # 2. 检查Python文件中的prompt使用
    print("\n🔍 检查Python文件中的prompt使用模式...")
    
    src_dir = "src"
    python_files = find_python_files(src_dir)
    
    total_issues = 0
    total_correct_usage = 0
    files_with_issues = []
    files_with_correct_usage = []
    
    for file_path in python_files:
        issues = check_file_for_prompt_patterns(file_path)
        
        # 统计问题
        file_has_issues = False
        file_has_correct = False
        
        for issue_type, issue_list in issues.items():
            if issue_type == "correct_apply_prompt_template":
                if issue_list:
                    file_has_correct = True
                    total_correct_usage += len(issue_list)
            else:
                if issue_list:
                    file_has_issues = True
                    total_issues += len(issue_list)
        
        if file_has_issues:
            files_with_issues.append((file_path, issues))
        
        if file_has_correct:
            files_with_correct_usage.append((file_path, len(issues["correct_apply_prompt_template"])))
    
    # 3. 报告结果
    print(f"\n📈 检查结果统计:")
    print(f"  📄 检查的Python文件数: {len(python_files)}")
    print(f"  ✅ 正确使用apply_prompt_template的次数: {total_correct_usage}")
    print(f"  ❌ 发现的问题数量: {total_issues}")
    print(f"  📁 有问题的文件数: {len(files_with_issues)}")
    print(f"  📁 正确使用的文件数: {len(files_with_correct_usage)}")
    
    # 4. 详细报告
    if files_with_correct_usage:
        print("\n✅ 正确使用apply_prompt_template的文件:")
        for file_path, count in files_with_correct_usage:
            try:
                rel_path = file_path.relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path
            print(f"  ✅ {rel_path} ({count} 次使用)")
    
    if files_with_issues:
        print("\n❌ 发现问题的文件:")
        for file_path, issues in files_with_issues:
            try:
                rel_path = file_path.relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path
            print(f"\n📄 {rel_path}:")
            
            if issues["direct_get_prompt_template"]:
                print("  ⚠️ 直接使用get_prompt_template + SystemMessage:")
                for issue in issues["direct_get_prompt_template"][:3]:  # 最多显示3个
                    print(f"    {issue}")
                if len(issues["direct_get_prompt_template"]) > 3:
                    print(f"    ... 还有 {len(issues['direct_get_prompt_template']) - 3} 个类似问题")
            
            if issues["hardcoded_system_message"]:
                print("  ⚠️ 硬编码的SystemMessage:")
                for issue in issues["hardcoded_system_message"][:3]:
                    print(f"    {issue}")
                if len(issues["hardcoded_system_message"]) > 3:
                    print(f"    ... 还有 {len(issues['hardcoded_system_message']) - 3} 个类似问题")
            
            if issues["hardcoded_prompt_strings"]:
                print("  ⚠️ 硬编码的prompt字符串:")
                for issue in issues["hardcoded_prompt_strings"][:3]:
                    print(f"    {issue}")
                if len(issues["hardcoded_prompt_strings"]) > 3:
                    print(f"    ... 还有 {len(issues['hardcoded_prompt_strings']) - 3} 个类似问题")
    
    # 5. 建议
    print("\n💡 修复建议:")
    if total_issues == 0:
        print("  🎉 所有prompt都已统一使用apply_prompt_template管理！")
    else:
        print("  📝 将所有直接使用get_prompt_template的地方改为apply_prompt_template")
        print("  📝 将硬编码的SystemMessage改为使用prompt模板文件")
        print("  📝 将硬编码的prompt字符串移到独立的.md模板文件中")
        print("  📝 确保所有模块都通过src.prompts.apply_prompt_template统一管理")
    
    print("\n📚 最佳实践:")
    print("  1️⃣ 所有prompt都应该放在src/prompts/目录下的.md文件中")
    print("  2️⃣ 使用apply_prompt_template(template_name, state)来获取格式化的消息")
    print("  3️⃣ 在模板中使用Jinja2语法进行变量替换")
    print("  4️⃣ 模板文件应该包含CURRENT_TIME等标准变量")
    
    print("\n" + "=" * 60)
    if total_issues == 0:
        print("✅ Prompt一致性检查通过！")
        return 0
    else:
        print(f"❌ 发现 {total_issues} 个需要修复的问题")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 