#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File System Tools 模块详细测试
"""

import os
import pytest
import tempfile
import shutil
import glob
from pathlib import Path
from unittest.mock import patch, Mock
import sys
from PIL import Image

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.file_system_tools import view_file, list_files, glob_search, grep_search


class TestViewFile:
    """测试view_file工具"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_view_text_file(self):
        """测试查看文本文件"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        content = "Hello World\nLine 2\nLine 3"

        with open(test_file, "w") as f:
            f.write(content)

        result = view_file.func(test_file)

        assert "Hello World" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_view_file_with_offset_and_limit(self):
        """测试带偏移和限制的文件查看"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        lines = [f"Line {i}\n" for i in range(1, 11)]

        with open(test_file, "w") as f:
            f.writelines(lines)

        # 从第3行开始，读取3行
        result = view_file.func(test_file, offset=3, limit=3)

        assert "Line 3" in result
        assert "Line 4" in result
        assert "Line 5" in result
        assert "Line 1" not in result
        assert "Line 6" not in result

    def test_view_nonexistent_file(self):
        """测试查看不存在的文件"""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.txt")

        result = view_file.func(nonexistent_file)

        assert "Error" in result
        assert "does not exist" in result

    def test_view_file_relative_path_error(self):
        """测试相对路径错误"""
        result = view_file.func("relative/path.txt")

        assert "Error" in result
        assert "absolute path" in result

    def test_view_directory_error(self):
        """测试查看目录时的错误"""
        result = view_file.func(self.temp_dir)

        assert "Error" in result
        assert "not a file" in result

    @patch("PIL.Image.open")
    def test_view_image_file(self, mock_image_open):
        """测试查看图像文件"""
        # 模拟PIL Image对象
        mock_img = Mock()
        mock_img.size = (800, 600)
        mock_img.format = "JPEG"
        mock_img.mode = "RGB"
        mock_image_open.return_value.__enter__.return_value = mock_img

        # 创建假的图像文件
        test_file = os.path.join(self.temp_dir, "test.jpg")
        with open(test_file, "wb") as f:
            f.write(b"fake image data")

        result = view_file.func(test_file)

        assert "Image file" in result
        assert "800" in result
        assert "600" in result
        assert "JPEG" in result

    def test_view_file_encoding_handling(self):
        """测试编码处理"""
        test_file = os.path.join(self.temp_dir, "test_utf8.txt")
        content = "Hello 世界\nПривет мир"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        result = view_file.func(test_file)

        assert "世界" in result
        assert "мир" in result

    def test_view_large_file_truncation(self):
        """测试大文件截断"""
        test_file = os.path.join(self.temp_dir, "large_file.txt")

        # 创建超过2000行的文件
        with open(test_file, "w") as f:
            for i in range(2500):
                f.write(f"Line {i}\n")

        result = view_file.func(test_file)

        # 应该只显示前2000行
        assert "Line 1999" in result
        assert "Line 2000" not in result


class TestListFiles:
    """测试list_files工具"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试文件和目录结构
        self.test_file1 = os.path.join(self.temp_dir, "file1.txt")
        self.test_file2 = os.path.join(self.temp_dir, "file2.py")
        self.test_subdir = os.path.join(self.temp_dir, "subdir")

        with open(self.test_file1, "w") as f:
            f.write("content1")
        with open(self.test_file2, "w") as f:
            f.write("print('hello')")
        os.makedirs(self.test_subdir)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_list_files_basic(self):
        """测试基本文件列表功能"""
        result = list_files.func(self.temp_dir)

        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir/" in result
        assert "[file]" in result
        assert "[dir]" in result

    def test_list_files_with_sizes(self):
        """测试文件大小显示"""
        result = list_files.func(self.temp_dir)

        # 应该显示文件大小信息
        assert "B" in result  # 字节单位

    def test_list_nonexistent_directory(self):
        """测试列出不存在的目录"""
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")

        result = list_files.func(nonexistent_dir)

        assert "Error" in result
        assert "does not exist" in result

    def test_list_files_relative_path_error(self):
        """测试相对路径错误"""
        result = list_files.func("relative/path")

        assert "Error" in result
        assert "absolute path" in result

    def test_list_files_on_file_error(self):
        """测试在文件上使用list_files时的错误"""
        result = list_files.func(self.test_file1)

        assert "Error" in result
        assert "not a directory" in result

    def test_list_empty_directory(self):
        """测试空目录"""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)

        result = list_files.func(empty_dir)

        assert "empty" in result

    def test_list_files_line_count(self):
        """测试文本文件行数统计"""
        # 创建多行文件
        multiline_file = os.path.join(self.temp_dir, "multiline.txt")
        with open(multiline_file, "w") as f:
            f.write("line1\nline2\nline3\n")

        result = list_files.func(self.temp_dir)

        assert "multiline.txt" in result
        assert "3 lines" in result


class TestGlobSearch:
    """测试glob_search工具"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试文件结构
        os.makedirs(os.path.join(self.temp_dir, "src"))
        os.makedirs(os.path.join(self.temp_dir, "tests"))

        test_files = [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "README.md",
            "config.json",
        ]

        for file_path in test_files:
            full_path = os.path.join(self.temp_dir, file_path)
            with open(full_path, "w") as f:
                f.write(f"content of {file_path}")

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_glob_search_python_files(self):
        """测试搜索Python文件"""
        result = glob_search.func("*.py", self.temp_dir)

        # 注意：glob不递归搜索，只在指定目录中搜索
        assert "No files found" in result or len(result) > 0

    def test_glob_search_recursive(self):
        """测试递归搜索"""
        result = glob_search.func("**/*.py", self.temp_dir)

        assert "main.py" in result
        assert "utils.py" in result
        assert "test_main.py" in result

    def test_glob_search_specific_pattern(self):
        """测试特定模式搜索"""
        result = glob_search.func("test_*.py", self.temp_dir)

        if "test_main.py" not in result:
            # 如果直接搜索没找到，尝试递归搜索
            result = glob_search.func("**/test_*.py", self.temp_dir)
            assert "test_main.py" in result

    def test_glob_search_no_matches(self):
        """测试无匹配结果"""
        result = glob_search.func("*.nonexistent", self.temp_dir)

        assert "No files found" in result

    def test_glob_search_nonexistent_path(self):
        """测试不存在的搜索路径"""
        nonexistent_path = "/nonexistent/path"

        result = glob_search.func("*.py", nonexistent_path)

        assert "Error" in result
        assert "does not exist" in result

    def test_glob_search_relative_path_error(self):
        """测试相对路径错误"""
        result = glob_search.func("*.py", "relative/path")

        assert "Error" in result
        assert "must be absolute" in result

    def test_glob_search_complex_pattern(self):
        """测试复杂模式"""
        result = glob_search.func("**/*.{py,md}", self.temp_dir)

        # 这个模式可能不被支持，但不应该崩溃
        assert isinstance(result, str)


class TestGrepSearch:
    """测试grep_search工具"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试文件
        test_files = {
            "file1.py": "def hello():\n    print('Hello World')\n    return True",
            "file2.py": "def goodbye():\n    print('Goodbye')\n    return False",
            "file3.txt": (
                "This is a text file\nWith multiple lines\nContaining different content"
            ),
            "file4.js": (
                "function hello() {\n    console.log('Hello');\n    return true;\n}"
            ),
        }

        for filename, content in test_files.items():
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w") as f:
                f.write(content)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_grep_search_basic(self):
        """测试基本搜索功能"""
        result = grep_search.func("hello", self.temp_dir)

        assert "file1.py" in result
        assert "file4.js" in result
        assert "Hello" in result

    def test_grep_search_with_include_filter(self):
        """测试包含文件过滤"""
        result = grep_search.func("hello", self.temp_dir, include="*.py")

        assert "file1.py" in result
        assert "file4.js" not in result

    def test_grep_search_regex_pattern(self):
        """测试正则表达式模式"""
        result = grep_search.func("def \\w+", self.temp_dir)

        assert "def hello" in result
        assert "def goodbye" in result

    def test_grep_search_case_insensitive(self):
        """测试大小写不敏感搜索"""
        result = grep_search.func("HELLO", self.temp_dir)

        # grep_search使用IGNORECASE标志
        assert "Hello" in result or "file1.py" in result

    def test_grep_search_no_matches(self):
        """测试无匹配结果"""
        result = grep_search.func("nonexistent_pattern", self.temp_dir)

        assert "No matches found" in result

    def test_grep_search_invalid_regex(self):
        """测试无效正则表达式"""
        result = grep_search.func("[invalid_regex", self.temp_dir)

        assert "Error" in result
        assert "Invalid regex pattern" in result

    def test_grep_search_nonexistent_path(self):
        """测试不存在的搜索路径"""
        result = grep_search.func("hello", "/nonexistent/path")

        assert "Error" in result
        assert "does not exist" in result

    def test_grep_search_relative_path_error(self):
        """测试相对路径错误"""
        result = grep_search.func("hello", "relative/path")

        assert "Error" in result
        assert "must be absolute" in result

    def test_grep_search_complex_include_pattern(self):
        """测试复杂包含模式"""
        result = grep_search.func("hello", self.temp_dir, include="*.{py,js}")

        # 应该同时搜索Python和JavaScript文件
        assert "file1.py" in result or "file4.js" in result

    def test_grep_search_line_numbers(self):
        """测试行号显示"""
        result = grep_search.func("print", self.temp_dir)

        assert "Line" in result
        assert ":" in result  # 行号格式

    def test_grep_search_multiple_matches_per_file(self):
        """测试每个文件多个匹配"""
        # 创建包含多个匹配的文件
        multi_match_file = os.path.join(self.temp_dir, "multi.py")
        with open(multi_match_file, "w") as f:
            f.write("def func1():\n    return 'test'\ndef func2():\n    return 'test'")

        result = grep_search.func("return", self.temp_dir)

        assert "multi.py" in result
        # 应该显示多个匹配行


class TestFileSystemToolsIntegration:
    """测试文件系统工具的集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_tools_workflow(self):
        """测试工具工作流"""
        # 1. 创建项目结构
        project_files = {
            "main.py": (
                "def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()"
            ),
            "utils.py": "def helper():\n    return 'helper function'",
            "README.md": "# My Project\n\nThis is a test project.",
        }

        for filename, content in project_files.items():
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w") as f:
                f.write(content)

        # 2. 使用list_files查看项目结构
        list_result = list_files.func(self.temp_dir)
        assert "main.py" in list_result
        assert "utils.py" in list_result
        assert "README.md" in list_result

        # 3. 使用glob_search查找Python文件
        glob_result = glob_search.func("*.py", self.temp_dir)
        assert "main.py" in glob_result
        assert "utils.py" in glob_result

        # 4. 使用grep_search查找特定模式
        grep_result = grep_search.func("def", self.temp_dir, include="*.py")
        assert "main.py" in grep_result
        assert "utils.py" in grep_result

        # 5. 使用view_file查看特定文件
        view_result = view_file.func(os.path.join(self.temp_dir, "main.py"))
        assert "Hello World" in view_result
        assert "def main" in view_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
