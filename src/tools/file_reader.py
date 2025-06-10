# SPDX-License-Identifier: MIT

"""
File reader tool for safe file content reading operations.
"""

import os
import mimetypes
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool


class FileReader:
    """安全的文件读取器"""

    def __init__(self, max_file_size: int = 10 * 1024 * 1024):  # 10MB
        """
        初始化文件读取器

        Args:
            max_file_size: 最大文件大小限制（字节）
        """
        self.max_file_size = max_file_size
        self.allowed_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".cs",
            ".php",
            ".rb",
            ".go",
            ".rs",
            ".swift",
            ".kt",
            ".scala",
            ".txt",
            ".md",
            ".rst",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".log",
            ".sql",
            ".sh",
            ".bat",
            ".ps1",
            ".html",
            ".htm",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".vue",
            ".dockerfile",
            ".gitignore",
            ".gitattributes",
            ".editorconfig",
        }

    def is_file_readable(self, file_path: str) -> tuple[bool, str]:
        """检查文件是否可读"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"

        # 检查是否为文件
        if not os.path.isfile(file_path):
            return False, f"不是一个文件: {file_path}"

        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            return (
                False,
                f"文件太大: {file_size} bytes (最大: {self.max_file_size} bytes)",
            )

        # 检查文件扩展名
        _, ext = os.path.splitext(file_path.lower())
        if ext not in self.allowed_extensions:
            # 尝试通过MIME类型判断
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and not mime_type.startswith("text/"):
                return False, f"不支持的文件类型: {ext} (MIME: {mime_type})"

        return True, "文件可读"

    def read_file_content(
        self, file_path: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        读取文件内容

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            包含文件内容和元信息的字典
        """
        readable, message = self.is_file_readable(file_path)
        if not readable:
            return {
                "success": False,
                "error": message,
                "content": "",
                "file_path": file_path,
            }

        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()

            file_info = os.stat(file_path)
            return {
                "success": True,
                "content": content,
                "file_path": file_path,
                "size": file_info.st_size,
                "lines": len(content.splitlines()),
                "encoding": encoding,
                "error": None,
            }

        except UnicodeDecodeError:
            # 尝试其他编码
            for alt_encoding in ["gbk", "gb2312", "latin1"]:
                try:
                    with open(file_path, "r", encoding=alt_encoding) as f:
                        content = f.read()

                    file_info = os.stat(file_path)
                    return {
                        "success": True,
                        "content": content,
                        "file_path": file_path,
                        "size": file_info.st_size,
                        "lines": len(content.splitlines()),
                        "encoding": alt_encoding,
                        "error": None,
                    }
                except UnicodeDecodeError:
                    continue

            return {
                "success": False,
                "error": f"无法解码文件: {file_path}",
                "content": "",
                "file_path": file_path,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"读取文件时发生错误: {str(e)}",
                "content": "",
                "file_path": file_path,
            }

    def read_file_lines(
        self,
        file_path: str,
        start_line: int = 1,
        end_line: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """
        读取文件的指定行范围

        Args:
            file_path: 文件路径
            start_line: 起始行号（从1开始）
            end_line: 结束行号（包含），None表示到文件末尾
            encoding: 文件编码

        Returns:
            包含指定行内容的字典
        """
        result = self.read_file_content(file_path, encoding)
        if not result["success"]:
            return result

        lines = result["content"].splitlines()
        total_lines = len(lines)

        # 调整行号范围
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line) if end_line else total_lines

        selected_lines = lines[start_idx:end_idx]

        return {
            "success": True,
            "content": "\n".join(selected_lines),
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_idx,
            "total_lines": total_lines,
            "selected_lines": len(selected_lines),
            "encoding": result["encoding"],
            "error": None,
        }


# 创建全局文件读取器实例
file_reader = FileReader()


@tool
def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    读取文件内容

    Args:
        file_path: 文件路径
        encoding: 文件编码，默认为utf-8

    Returns:
        文件内容或错误信息
    """
    result = file_reader.read_file_content(file_path, encoding)

    if result["success"]:
        return f"文件: {file_path}\n大小: {result['size']} bytes\n行数: {result['lines']}\n编码: {result['encoding']}\n\n内容:\n{result['content']}"
    else:
        return f"读取文件失败: {result['error']}"


@tool
def read_file_lines(
    file_path: str, start_line: int = 1, end_line: int = None, encoding: str = "utf-8"
) -> str:
    """
    读取文件的指定行范围

    Args:
        file_path: 文件路径
        start_line: 起始行号（从1开始）
        end_line: 结束行号（包含），None表示到文件末尾
        encoding: 文件编码，默认为utf-8

    Returns:
        指定行的内容或错误信息
    """
    result = file_reader.read_file_lines(file_path, start_line, end_line, encoding)

    if result["success"]:
        return f"文件: {file_path}\n行范围: {result['start_line']}-{result['end_line']} (总共 {result['total_lines']} 行)\n选中行数: {result['selected_lines']}\n编码: {result['encoding']}\n\n内容:\n{result['content']}"
    else:
        return f"读取文件行失败: {result['error']}"


@tool
def get_file_info(file_path: str) -> str:
    """
    获取文件基本信息

    Args:
        file_path: 文件路径

    Returns:
        文件信息字符串
    """
    try:
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"

        if not os.path.isfile(file_path):
            return f"不是一个文件: {file_path}"

        file_info = os.stat(file_path)
        file_size = file_info.st_size

        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(file_path)

        # 获取文件扩展名
        _, ext = os.path.splitext(file_path)

        # 尝试快速获取行数（对于文本文件）
        line_count = "N/A"
        if ext.lower() in file_reader.allowed_extensions:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
            except:
                line_count = "无法获取"

        return f"""文件信息:
路径: {file_path}
大小: {file_size} bytes
扩展名: {ext}
MIME类型: {mime_type or '未知'}
行数: {line_count}
可读性: {'是' if file_reader.is_file_readable(file_path)[0] else '否'}"""

    except Exception as e:
        return f"获取文件信息时发生错误: {str(e)}"
