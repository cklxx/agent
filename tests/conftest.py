import os
import sys
import pytest

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 保存原始工作目录
    original_cwd = os.getcwd()

    # 切换到测试目录
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(test_dir)

    yield

    # 恢复原始工作目录
    os.chdir(original_cwd)
