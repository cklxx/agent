#!/usr/bin/env python3
"""
构建环境测试脚本
用于验证构建依赖和环境是否正确配置
"""

import sys
import subprocess
import importlib
from pathlib import Path


def test_uv_installation():
    """测试UV是否安装"""
    print("\n🔍 检查UV:")

    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ UV - {result.stdout.strip()}")
            return True
        else:
            print("❌ UV - 命令执行失败")
            return False
    except FileNotFoundError:
        print("❌ UV - 未安装")
        print("请安装UV: https://docs.astral.sh/uv/getting-started/installation/")
        return False


def test_python_version():
    """测试Python版本"""
    print(f"🐍 Python版本: {sys.version}")

    version_info = sys.version_info
    if version_info.major == 3 and version_info.minor >= 8:
        print("✅ Python版本符合要求 (>=3.8)")
        return True
    else:
        print("❌ Python版本过低，需要 Python 3.8+")
        return False


def test_required_modules():
    """测试必需的模块"""
    required_modules = ["PyInstaller", "pathlib", "subprocess", "shutil", "platform"]

    print("\n🔍 检查必需模块:")
    all_ok = True

    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
            print(f"✅ {module_name}")
        except ImportError:
            print(f"❌ {module_name} - 未安装")
            all_ok = False

    return all_ok


def test_project_structure():
    """测试项目结构"""
    project_root = Path(__file__).parent.parent

    required_files = ["main.py", "pyproject.toml", "src", "conf.yaml.example"]

    print("\n📁 检查项目结构:")
    all_ok = True

    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")
            all_ok = False

    return all_ok


def test_build_files():
    """测试构建文件"""
    packaging_dir = Path(__file__).parent

    required_files = ["pyinstaller.spec", "build.py", "README.md"]

    print("\n🔧 检查构建文件:")
    all_ok = True

    for file_path in required_files:
        full_path = packaging_dir / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")
            all_ok = False

    return all_ok


def main():
    """主测试函数"""
    print("🧪 Code Agent 构建环境测试 (UV版本)")
    print("=" * 40)

    tests = [
        ("UV安装", test_uv_installation),
        ("Python版本", test_python_version),
        ("必需模块", test_required_modules),
        ("项目结构", test_project_structure),
        ("构建文件", test_build_files),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} 测试失败: {e}")
            results[test_name] = False

    # 显示测试结果
    print("\n📊 测试结果:")
    print("-" * 20)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 40)

    if all_passed:
        print("🎉 所有测试通过！可以开始构建。")
        print("\n💡 运行构建命令:")
        print("   uv run python packaging/build.py")
        print("   或")
        print("   ./packaging/build.sh  (Linux/macOS)")
        print("   packaging\\build.bat  (Windows)")
        print("   make all  (如果有make)")
        return 0
    else:
        print("❌ 部分测试失败，请检查环境配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
