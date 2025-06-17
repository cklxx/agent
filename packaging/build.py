#!/usr/bin/env python3
"""
优化的PyInstaller构建脚本
解决构建卡住问题，采用更简洁的配置
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"

def clean_build():
    """清理构建目录"""
    print("🧹 清理构建目录...")
    clean_dirs = [PROJECT_ROOT / "build", PROJECT_ROOT / "dist"]
    for dir_path in clean_dirs:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✅ 已清理 {dir_path}")

def build_executable():
    """优化的构建流程"""
    print("🔨 开始优化构建...")
    
    # 切换到项目根目录
    original_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)
    
    try:
        # 简化的PyInstaller命令，只包含核心依赖
        cmd = [
            "uv", "run", "pyinstaller",
            "--onefile",
            "--name", "code_agent",
            "--clean",
            "--noconfirm",
            "--log-level", "WARN",  # 减少日志输出
            "--add-data", "conf.yaml.example:.",
            # 只添加核心隐藏导入
            "--hidden-import", "langchain_community",
            "--hidden-import", "langchain_openai", 
            "--hidden-import", "fastapi",
            "--hidden-import", "uvicorn",
            "--hidden-import", "litellm",
            "--hidden-import", "sklearn",
            "--hidden-import", "scipy",
            "--hidden-import", "numpy",
            "--exclude-module", "tkinter",  # 排除不需要的模块
            "--exclude-module", "matplotlib",
            "main.py"
        ]
        
        print("执行优化构建命令...")
        # 设置超时防止卡死
        result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 构建成功!")
            exe_name = "code_agent.exe" if platform.system() == "Windows" else "code_agent"
            exe_path = DIST_DIR / exe_name
            
            if exe_path.exists():
                size = exe_path.stat().st_size / (1024 * 1024)
                print(f"📦 可执行文件: {exe_path}")
                print(f"📊 文件大小: {size:.1f} MB")
                return True
            else:
                print(f"❌ 未找到可执行文件")
                return False
        else:
            print("❌ 构建失败!")
            print("错误输出:")
            print(result.stderr[-1000:])  # 只显示最后1000字符
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 构建超时，正在终止...")
        return False
    finally:
        os.chdir(original_cwd)

def main():
    """主函数"""
    print("🚀 开始优化构建 Code Agent")
    print(f"项目根目录: {PROJECT_ROOT}")
    print("--" * 30)
    
    # 清理构建目录
    clean_build()
    
    # 构建可执行文件
    if build_executable():
        print("🎉 构建完成!")
        return True
    else:
        print("💥 构建失败!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 