#!/usr/bin/env python3
"""
PyInstaller 构建脚本
用于将 code agent 打包成可执行文件
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
PACKAGING_DIR = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = PACKAGING_DIR / "pyinstaller.spec"


def check_dependencies():
    """检查构建依赖"""
    print("🔍 检查构建依赖...")

    # 检查 uv 是否安装
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ UV {result.stdout.strip()}")
        else:
            print("❌ UV 未安装")
            print("请安装UV: https://docs.astral.sh/uv/getting-started/installation/")
            return False
    except FileNotFoundError:
        print("❌ UV 未安装")
        print("请安装UV: https://docs.astral.sh/uv/getting-started/installation/")
        return False

    try:
        import PyInstaller

        print(f"✅ PyInstaller {PyInstaller.__version__} 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("请运行: uv add --dev pyinstaller")
        return False

    # 检查主要项目依赖
    required_packages = [
        "langchain_community",
        "langchain_openai",
        "fastapi",
        "uvicorn",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")

    if missing_packages:
        print(f"请安装缺失的包: uv sync")
        return False

    return True


def clean_build():
    """清理之前的构建文件"""
    print("🧹 清理构建目录...")

    # 清理PyInstaller生成的目录
    clean_dirs = [
        PROJECT_ROOT / "build",
        PROJECT_ROOT / "dist",
        PACKAGING_DIR / "dist",
        PACKAGING_DIR / "build",
    ]

    for dir_path in clean_dirs:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✅ 已清理 {dir_path}")


def build_executable():
    """使用PyInstaller构建可执行文件"""
    print("🔨 开始构建可执行文件...")

    # 切换到项目根目录
    original_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)

    try:
        # 使用简单的命令行参数构建，避免spec文件的复杂性
        cmd = [
            "uv",
            "run",
            "pyinstaller",
            "--onefile",  # 生成单个可执行文件
            "--name",
            "code_agent",  # 指定输出文件名
            "--clean",  # 清理缓存
            "--noconfirm",  # 不询问覆盖
            # 添加数据文件
            "--add-data",
            "conf.yaml.example:.",
            "--add-data",
            "src:src",
            # 隐藏导入
            "--hidden-import",
            "langchain_community",
            "--hidden-import",
            "langchain_openai",
            "--hidden-import",
            "fastapi",
            "--hidden-import",
            "uvicorn",
            "--hidden-import",
            "sse_starlette",
            "--hidden-import",
            "httpx",
            "--hidden-import",
            "readabilipy",
            "--hidden-import",
            "python_dotenv",
            "--hidden-import",
            "socksio",
            "--hidden-import",
            "markdownify",
            "--hidden-import",
            "pandas",
            "--hidden-import",
            "numpy",
            "--hidden-import",
            "yfinance",
            "--hidden-import",
            "litellm",
            "--hidden-import",
            "json_repair",
            "--hidden-import",
            "jinja2",
            "--hidden-import",
            "duckduckgo_search",
            "--hidden-import",
            "inquirerpy",
            "--hidden-import",
            "arxiv",
            "--hidden-import",
            "mcp",
            "--hidden-import",
            "tenacity",
            "--hidden-import",
            "nest_asyncio",
            "main.py",  # 主入口文件
        ]

        print(f"执行命令: {' '.join(cmd[:10])}... (省略部分参数)")

        # 执行构建
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ 构建成功!")

            # 检查生成的文件
            exe_name = (
                "code_agent.exe" if platform.system() == "Windows" else "code_agent"
            )
            exe_path = DIST_DIR / exe_name

            if exe_path.exists():
                size = exe_path.stat().st_size / (1024 * 1024)  # MB
                print(f"📦 可执行文件: {exe_path}")
                print(f"📊 文件大小: {size:.1f} MB")
                return True
            else:
                print(f"❌ 未找到可执行文件: {exe_path}")
                return False
        else:
            print("❌ 构建失败!")
            print("错误输出:")
            print(result.stderr)
            return False

    finally:
        os.chdir(original_cwd)


def test_executable():
    """测试生成的可执行文件"""
    print("🧪 测试可执行文件...")

    exe_name = "code_agent.exe" if platform.system() == "Windows" else "code_agent"
    exe_path = DIST_DIR / exe_name

    if not exe_path.exists():
        print(f"❌ 可执行文件不存在: {exe_path}")
        return False

    try:
        # 测试版本信息
        result = subprocess.run(
            [str(exe_path), "--help"], capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print("✅ 可执行文件运行正常")
            print("📄 帮助信息:")
            # 显示前几行帮助信息
            lines = result.stdout.split("\n")[:5]
            for line in lines:
                if line.strip():
                    print(f"    {line}")
            return True
        else:
            print("❌ 可执行文件运行失败")
            print(f"错误输出: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  可执行文件运行超时")
        return False
    except Exception as e:
        print(f"❌ 测试可执行文件时出错: {e}")
        return False


def create_package():
    """创建发布包"""
    print("📦 创建发布包...")

    # 获取系统信息
    system = platform.system().lower()
    arch = platform.machine().lower()

    # 创建包目录
    package_name = f"code_agent-{system}-{arch}"
    package_dir = DIST_DIR / package_name

    if package_dir.exists():
        shutil.rmtree(package_dir)

    package_dir.mkdir(parents=True)

    # 复制可执行文件
    exe_name = "code_agent.exe" if system == "windows" else "code_agent"
    exe_path = DIST_DIR / exe_name

    if exe_path.exists():
        shutil.copy2(exe_path, package_dir / exe_name)

        # 添加配置文件示例
        config_example = PROJECT_ROOT / "conf.yaml.example"
        if config_example.exists():
            shutil.copy2(config_example, package_dir / "conf.yaml.example")

        # 添加README
        readme_content = f"""# Code Agent - {system.title()} {arch.upper()}

## 使用方法

1. 复制 conf.yaml.example 为 conf.yaml 并配置API密钥
2. 运行可执行文件:
   - 交互模式: ./{exe_name} --interactive
   - 直接查询: ./{exe_name} "你的问题"

## 配置

请确保在 conf.yaml 中配置正确的API密钥和端点。

## 版本信息

构建时间: {__import__('datetime').datetime.now()}
系统: {system.title()}
架构: {arch.upper()}
"""

        (package_dir / "README.md").write_text(readme_content, encoding="utf-8")

        # 创建压缩包
        archive_path = DIST_DIR / f"{package_name}.zip"
        shutil.make_archive(str(archive_path).replace(".zip", ""), "zip", package_dir)

        print(f"✅ 发布包已创建: {archive_path}")
        return True
    else:
        print(f"❌ 找不到可执行文件: {exe_path}")
        return False


def main():
    """主函数"""
    print("🚀 开始构建 Code Agent 可执行文件")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"打包目录: {PACKAGING_DIR}")
    print(f"目标平台: {platform.system()} {platform.machine()}")
    print("-" * 50)

    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，退出构建")
        return 1

    # 清理构建目录
    clean_build()

    # 构建可执行文件
    if not build_executable():
        print("❌ 构建失败")
        return 1

    # 测试可执行文件
    if not test_executable():
        print("⚠️  可执行文件测试失败，但构建已完成")

    # 创建发布包
    if not create_package():
        print("⚠️  创建发布包失败")

    print("🎉 构建完成!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
