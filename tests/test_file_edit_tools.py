#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File Edit Tools 模块详细测试
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.file_edit_tools import edit_file, replace_file


class TestEditFile:
    """测试edit_file工具"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_new_file(self):
        """测试创建新文件"""
        new_file = os.path.join(self.temp_dir, "new_file.txt")
        content = "This is a new file"

        result = edit_file.func(new_file, "", content)

        assert "Successfully created" in result
        assert os.path.exists(new_file)

        with open(new_file, "r") as f:
            assert f.read() == content

    def test_edit_existing_file(self):
        """测试编辑现有文件"""
        # 创建测试文件
        original_content = "Hello World\nThis is line 2\nThis is line 3"
        with open(self.test_file, "w") as f:
            f.write(original_content)

        # 编辑文件
        old_string = "This is line 2"
        new_string = "This is the modified line 2"

        result = edit_file.func(self.test_file, old_string, new_string)

        assert "Successfully edited" in result

        with open(self.test_file, "r") as f:
            content = f.read()
            assert new_string in content
            assert old_string not in content

    def test_edit_file_with_context(self):
        """测试带上下文的文件编辑"""
        content = """def hello():
    print("Hello")
    return "world"

def goodbye():
    print("Goodbye")
    return "farewell"
"""
        with open(self.test_file, "w") as f:
            f.write(content)

        # 使用足够的上下文来唯一标识要修改的位置
        old_string = """def hello():
    print("Hello")
    return "world\""""

        new_string = """def hello():
    print("Hello, World!")
    return "greeting\""""

        result = edit_file.func(self.test_file, old_string, new_string)

        assert "Successfully edited" in result

        with open(self.test_file, "r") as f:
            content = f.read()
            assert "Hello, World!" in content
            assert "greeting" in content

    def test_edit_file_multiple_occurrences_error(self):
        """测试多次出现相同字符串时的错误处理"""
        content = "test\ntest\ntest"
        with open(self.test_file, "w") as f:
            f.write(content)

        result = edit_file.func(self.test_file, "test", "modified")

        assert "Error" in result
        assert "times" in result

    def test_edit_file_string_not_found(self):
        """测试找不到字符串时的错误处理"""
        content = "Hello World"
        with open(self.test_file, "w") as f:
            f.write(content)

        result = edit_file.func(self.test_file, "nonexistent", "new")

        assert "Error" in result
        assert "not found" in result

    def test_edit_file_relative_path_error(self):
        """测试相对路径错误"""
        result = edit_file.func("relative/path.txt", "old", "new")

        assert "Error" in result
        assert "absolute path" in result

    def test_edit_file_nonexistent_file(self):
        """测试编辑不存在的文件"""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.txt")

        result = edit_file.func(nonexistent_file, "old", "new")

        assert "Error" in result
        assert "does not exist" in result

    def test_edit_file_create_existing_file_error(self):
        """测试创建已存在文件时的错误"""
        with open(self.test_file, "w") as f:
            f.write("existing content")

        result = edit_file.func(self.test_file, "", "new content")

        assert "Error" in result
        assert "already exists" in result

    def test_edit_file_nonexistent_parent_directory(self):
        """测试父目录不存在时的错误"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent", "file.txt")

        result = edit_file.func(nonexistent_path, "", "content")

        assert "Error" in result
        assert "Parent directory does not exist" in result

    def test_edit_file_encoding_handling(self):
        """测试编码处理"""
        # 创建包含特殊字符的文件
        content = "Hello 世界\nПривет мир\n"
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write(content)

        result = edit_file.func(self.test_file, "世界", "World")

        assert "Successfully edited" in result

        with open(self.test_file, "r", encoding="utf-8") as f:
            new_content = f.read()
            assert "World" in new_content
            assert "世界" not in new_content


class TestReplaceFile:
    """测试replace_file工具"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_replace_file_create_new(self):
        """测试创建新文件"""
        content = "This is new content\nWith multiple lines\n"

        result = replace_file.func(self.test_file, content)

        assert "Successfully created" in result
        assert os.path.exists(self.test_file)

        with open(self.test_file, "r") as f:
            assert f.read() == content

    def test_replace_file_overwrite_existing(self):
        """测试覆盖现有文件"""
        # 创建原始文件
        original_content = "Original content"
        with open(self.test_file, "w") as f:
            f.write(original_content)

        # 替换内容
        new_content = "Completely new content\nWith new lines"
        result = replace_file.func(self.test_file, new_content)

        assert "Successfully updated" in result

        with open(self.test_file, "r") as f:
            assert f.read() == new_content

    def test_replace_file_relative_path_error(self):
        """测试相对路径错误"""
        result = replace_file.func("relative/path.txt", "content")

        assert "Error" in result
        assert "absolute path" in result

    def test_replace_file_nonexistent_parent_directory(self):
        """测试父目录不存在时的错误"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent", "file.txt")

        result = replace_file.func(nonexistent_path, "content")

        assert "Error" in result
        assert "Parent directory does not exist" in result

    def test_replace_file_size_tracking(self):
        """测试文件大小跟踪"""
        small_content = "Small content"
        large_content = "A" * 1000  # 1KB content

        # 测试小文件
        result = replace_file.func(self.test_file, small_content)
        assert "Successfully created" in result

        # 测试大文件替换
        result = replace_file.func(self.test_file, large_content)
        assert "Successfully updated" in result

    def test_replace_file_empty_content(self):
        """测试空内容"""
        result = replace_file.func(self.test_file, "")

        assert "Successfully created" in result
        assert os.path.exists(self.test_file)

        with open(self.test_file, "r") as f:
            assert f.read() == ""

    def test_replace_file_encoding_handling(self):
        """测试编码处理"""
        content = "Hello 世界\nПривет мир\n"

        result = replace_file.func(self.test_file, content)

        assert "Successfully created" in result

        with open(self.test_file, "r", encoding="utf-8") as f:
            read_content = f.read()
            assert "世界" in read_content
            assert "мир" in read_content


class TestFileEditToolsIntegration:
    """测试文件编辑工具的集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_edit_and_replace_workflow(self):
        """测试编辑和替换的工作流"""
        test_file = os.path.join(self.temp_dir, "workflow_test.txt")

        # 1. 创建文件
        initial_content = "Line 1\nLine 2\nLine 3"
        result = edit_file.func(test_file, "", initial_content)
        assert "Successfully created" in result

        # 2. 编辑特定行
        result = edit_file.func(test_file, "Line 2", "Modified Line 2")
        assert "Successfully edited" in result

        # 3. 完全替换文件
        new_content = "Completely different content"
        result = replace_file.func(test_file, new_content)
        assert "Successfully updated" in result

        # 验证最终内容
        with open(test_file, "r") as f:
            assert f.read() == new_content

    def test_complex_file_editing_scenario(self):
        """测试复杂的文件编辑场景"""
        test_file = os.path.join(self.temp_dir, "complex_test.py")

        # 创建Python文件
        python_code = '''def function1():
    """First function"""
    return "result1"

def function2():
    """Second function"""
    return "result2"

if __name__ == "__main__":
    print(function1())
    print(function2())
'''

        result = edit_file.func(test_file, "", python_code)
        assert "Successfully created" in result

        # 修改第一个函数
        old_func = '''def function1():
    """First function"""
    return "result1"'''

        new_func = '''def function1():
    """Modified first function"""
    return "modified_result1"'''

        result = edit_file.func(test_file, old_func, new_func)
        assert "Successfully edited" in result

        # 验证修改结果
        with open(test_file, "r") as f:
            content = f.read()
            assert "Modified first function" in content
            assert "modified_result1" in content
            assert "Second function" in content  # 确保其他部分未受影响


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
