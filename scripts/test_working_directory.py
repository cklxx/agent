#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试工作目录自动切换功能

验证所有脚本都能正确自动切换到项目根目录作为工作目录
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# 获取脚本所在目录和项目根目录
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 对于测试脚本，需要切换到项目根目录以正确找到其他脚本
original_cwd = os.getcwd()
os.chdir(project_root)

# 添加项目根目录到Python路径
sys.path.insert(0, project_root)


def test_script_working_directory(script_path: str, temp_dir: str) -> Tuple[bool, str, str]:
    """测试单个脚本的工作目录切换功能"""
    try:
        # 创建一个简单的测试脚本来运行目标脚本
        test_script_content = f'''
import os
import sys
print("BEFORE_IMPORT_CWD:" + os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
exec(open("{script_path}").read())
print("AFTER_IMPORT_CWD:" + os.getcwd())
'''
        
        # 在临时目录下运行测试
        result = subprocess.run(
            [sys.executable, "-c", test_script_content],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout
        error = result.stderr
        
        # 解析输出查找工作目录信息
        before_cwd = None
        after_cwd = None
        
        for line in output.split('\n'):
            if line.startswith("BEFORE_IMPORT_CWD:"):
                before_cwd = line.replace("BEFORE_IMPORT_CWD:", "")
            elif line.startswith("AFTER_IMPORT_CWD:"):
                after_cwd = line.replace("AFTER_IMPORT_CWD:", "")
        
        # 检查是否成功切换到项目根目录
        project_root_abs = os.path.abspath(project_root)
        success = after_cwd and os.path.abspath(after_cwd) == project_root_abs
        
        return success, output, error
        
    except subprocess.TimeoutExpired:
        return False, "", "执行超时"
    except Exception as e:
        return False, "", str(e)


def create_temp_directory() -> str:
    """创建临时测试目录"""
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="test_cwd_")
    return temp_dir


def get_test_scripts() -> List[str]:
    """获取需要测试的脚本列表"""
    scripts_dir = Path("scripts")
    test_scripts = []
    
    for script_file in scripts_dir.glob("*.py"):
        # 跳过当前测试脚本
        if script_file.name == "test_working_directory.py":
            continue
        test_scripts.append(str(script_file))
    
    return test_scripts


def test_import_syntax():
    """测试脚本的导入语法是否正确"""
    print("🔍 测试脚本导入语法...")
    scripts = get_test_scripts()
    
    # CLI脚本：保持当前工作目录
    cli_scripts = ['code_agent_cli.py', 'code_agent_simple_cli.py', 'demo_code_agent_cli.py']
    # 实用工具脚本：需要切换到项目根目录
    utility_scripts = ['check_prompt_language.py', 'check_prompt_consistency.py', 'test_enhanced_code_agent.py', 'test_working_directory.py']
    
    results = {}
    for script_path in scripts:
        script_name = os.path.basename(script_path)
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查基本的路径设置
            basic_patterns = [
                "script_dir = os.path.dirname(os.path.abspath(__file__))",
                "project_root = os.path.dirname(script_dir)",
            ]
            
            has_basic = all(pattern in content for pattern in basic_patterns)
            
            if script_name in cli_scripts:
                # CLI脚本不应该自动切换工作目录
                if has_basic and "os.chdir(project_root)" not in content:
                    results[script_name] = "✅ CLI脚本正确配置（保持当前目录）"
                else:
                    results[script_name] = "❌ CLI脚本不应自动切换工作目录"
            elif script_name in utility_scripts:
                # 实用工具脚本需要切换到项目根目录
                if has_basic and "os.chdir(project_root)" in content:
                    results[script_name] = "✅ 实用工具脚本正确配置（切换到项目根目录）"
                else:
                    results[script_name] = "❌ 实用工具脚本需要切换到项目根目录"
            else:
                # 其他脚本
                if has_basic:
                    results[script_name] = "✅ 基本路径配置正确"
                else:
                    missing = [p for p in basic_patterns if p not in content]
                    results[script_name] = f"❌ 缺少: {', '.join(missing)}"
                
        except Exception as e:
            results[script_name] = f"❌ 读取失败: {e}"
    
    return results


def test_directory_switching():
    """测试目录配置策略"""
    print("🚀 测试目录配置策略...")
    
    scripts = get_test_scripts()
    
    # CLI脚本：保持当前工作目录
    cli_scripts = ['code_agent_cli.py', 'code_agent_simple_cli.py', 'demo_code_agent_cli.py']
    # 实用工具脚本：需要切换到项目根目录
    utility_scripts = ['check_prompt_language.py', 'check_prompt_consistency.py', 'test_enhanced_code_agent.py', 'test_working_directory.py']
    
    results = {}
    
    for script_path in scripts:
        script_name = os.path.basename(script_path)
        print(f"   检查 {script_name}...")
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找关键的工作目录设置代码
            has_chdir = "os.chdir(project_root)" in content
            has_script_dir = "script_dir = os.path.dirname(os.path.abspath(__file__))" in content
            has_project_root = "project_root = os.path.dirname(script_dir)" in content
            
            if script_name in cli_scripts:
                # CLI脚本：应该有基本配置，但不自动切换目录
                if has_script_dir and has_project_root and not has_chdir:
                    results[script_name] = "✅ CLI脚本配置正确（保持当前目录）"
                elif has_chdir:
                    results[script_name] = "❌ CLI脚本不应自动切换工作目录"
                else:
                    results[script_name] = "❌ CLI脚本缺少基本路径配置"
                    
            elif script_name in utility_scripts:
                # 实用工具脚本：需要切换到项目根目录
                if has_script_dir and has_project_root and has_chdir:
                    results[script_name] = "✅ 实用工具脚本配置正确（切换到项目根目录）"
                elif not has_chdir:
                    results[script_name] = "❌ 实用工具脚本需要切换到项目根目录"
                else:
                    results[script_name] = "❌ 实用工具脚本配置不完整"
            else:
                # 其他脚本
                if has_script_dir and has_project_root:
                    results[script_name] = "✅ 基本路径配置正确"
                else:
                    results[script_name] = "❌ 缺少基本路径配置"
                
        except Exception as e:
            results[script_name] = f"❌ 检查失败: {e}"
    
    return results


def main():
    """主函数"""
    print("🔍 工作目录自动切换功能测试")
    print("=" * 60)
    
    # 显示当前状态
    print(f"📍 当前工作目录: {os.getcwd()}")
    print(f"📍 项目根目录: {project_root}")
    print(f"📍 脚本目录: {script_dir}")
    
    # 测试导入语法
    print("\n" + "=" * 60)
    syntax_results = test_import_syntax()
    
    print("📋 导入语法检查结果:")
    for script, result in syntax_results.items():
        print(f"  {script}: {result}")
    
    # 测试目录切换
    print("\n" + "=" * 60)
    switching_results = test_directory_switching()
    
    print("📋 目录切换配置检查结果:")
    for script, result in switching_results.items():
        print(f"  {script}: {result}")
    
    # 统计结果
    print("\n" + "=" * 60)
    total_scripts = len(switching_results)
    successful_scripts = sum(1 for result in switching_results.values() if "✅" in result)
    
    print(f"📊 测试结果统计:")
    print(f"  📄 测试脚本总数: {total_scripts}")
    print(f"  ✅ 配置正确的脚本: {successful_scripts}")
    print(f"  ❌ 需要修复的脚本: {total_scripts - successful_scripts}")
    print(f"  📈 成功率: {(successful_scripts/total_scripts*100):.1f}%")
    
    # 显示好处
    print("\n💡 新的工作目录策略好处:")
    benefits = [
        "🎯 CLI脚本保持当前工作目录，支持用户在任意目录下工作",
        "📁 实用工具脚本自动切换到项目根目录，确保能找到项目文件",
        "🔧 避免 'FileNotFoundError' 和 'ModuleNotFoundError'",
        "👥 满足不同使用场景的需求",
        "🚀 提升脚本的灵活性和用户体验"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    # 使用场景说明
    print("\n📚 使用场景说明:")
    scenarios = [
        "🤖 CLI脚本（code_agent_cli.py等）：保持在用户当前目录，允许用户操作任意目录的文件",
        "🔧 实用工具脚本（check_prompt_*.py等）：自动切换到项目根目录，确保能找到项目文件",
        "📝 所有脚本都添加了项目根目录到Python路径，确保能正确导入模块",
        "🎯 CLI脚本支持 --dir 参数指定特定工作目录覆盖默认行为"
    ]
    
    for scenario in scenarios:
        print(f"  {scenario}")
    
    print("\n" + "=" * 60)
    if successful_scripts == total_scripts:
        print("✅ 所有脚本都已正确配置工作目录策略！")
        print("🎯 CLI脚本保持当前目录，实用工具脚本切换到项目根目录")
        return 0
    else:
        print(f"❌ 发现 {total_scripts - successful_scripts} 个脚本需要修复")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 