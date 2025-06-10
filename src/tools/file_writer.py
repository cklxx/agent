# SPDX-License-Identifier: MIT

"""
File writer tool for safe file content writing operations.
"""

import os
import shutil
import difflib
from datetime import datetime
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool


class FileWriter:
    """安全的文件写入器"""

    def __init__(self, backup_dir: str = ".backups", max_backup_files: int = 10):
        """
        初始化文件写入器

        Args:
            backup_dir: 备份目录
            max_backup_files: 最大备份文件数量
        """
        self.backup_dir = backup_dir
        self.max_backup_files = max_backup_files
        self.forbidden_paths = {
            "/etc",
            "/bin",
            "/sbin",
            "/usr/bin",
            "/usr/sbin",
            "/system",
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
        }

    def is_path_safe(self, file_path: str) -> tuple[bool, str]:
        """检查路径是否安全可写"""
        # 获取绝对路径
        abs_path = os.path.abspath(file_path)

        # 检查是否在禁止路径中
        for forbidden in self.forbidden_paths:
            if abs_path.startswith(forbidden):
                return False, f"禁止写入系统路径: {abs_path}"

        # 检查父目录是否存在或可创建
        parent_dir = os.path.dirname(abs_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                return False, f"无法创建父目录: {str(e)}"

        # 检查是否有写入权限
        if os.path.exists(abs_path):
            if not os.access(abs_path, os.W_OK):
                return False, f"没有写入权限: {abs_path}"
        else:
            # 检查父目录的写入权限
            if parent_dir and not os.access(parent_dir, os.W_OK):
                return False, f"没有在父目录创建文件的权限: {parent_dir}"

        return True, "路径安全可写"

    def create_backup(self, file_path: str) -> Optional[str]:
        """创建文件备份"""
        if not os.path.exists(file_path):
            return None

        try:
            # 确保备份目录存在
            os.makedirs(self.backup_dir, exist_ok=True)

            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_name = f"{filename}.{timestamp}.backup"
            backup_path = os.path.join(self.backup_dir, backup_name)

            # 创建备份
            shutil.copy2(file_path, backup_path)

            # 清理旧备份
            self._cleanup_old_backups(filename)

            return backup_path
        except Exception as e:
            print(f"创建备份失败: {str(e)}")
            return None

    def _cleanup_old_backups(self, filename: str):
        """清理旧的备份文件"""
        try:
            if not os.path.exists(self.backup_dir):
                return

            # 获取同一文件的所有备份
            backups = []
            for item in os.listdir(self.backup_dir):
                if item.startswith(f"{filename}.") and item.endswith(".backup"):
                    backup_path = os.path.join(self.backup_dir, item)
                    backups.append((backup_path, os.path.getmtime(backup_path)))

            # 按修改时间排序
            backups.sort(key=lambda x: x[1], reverse=True)

            # 删除超出限制的备份
            for backup_path, _ in backups[self.max_backup_files :]:
                os.remove(backup_path)
        except Exception as e:
            print(f"清理备份失败: {str(e)}")

    def write_file(
        self,
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        create_backup: bool = True,
    ) -> Dict[str, Any]:
        """
        写入文件内容

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码
            create_backup: 是否创建备份

        Returns:
            写入结果字典
        """
        safe, message = self.is_path_safe(file_path)
        if not safe:
            return {
                "success": False,
                "error": message,
                "file_path": file_path,
                "backup_path": None,
            }

        backup_path = None
        try:
            # 创建备份
            if create_backup and os.path.exists(file_path):
                backup_path = self.create_backup(file_path)

            # 写入文件
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)

            file_size = os.path.getsize(file_path)
            line_count = len(content.splitlines())

            return {
                "success": True,
                "file_path": file_path,
                "backup_path": backup_path,
                "size": file_size,
                "lines": line_count,
                "encoding": encoding,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"写入文件时发生错误: {str(e)}",
                "file_path": file_path,
                "backup_path": backup_path,
            }

    def append_to_file(
        self, file_path: str, content: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        向文件末尾追加内容

        Args:
            file_path: 文件路径
            content: 要追加的内容
            encoding: 文件编码

        Returns:
            追加结果字典
        """
        safe, message = self.is_path_safe(file_path)
        if not safe:
            return {"success": False, "error": message, "file_path": file_path}

        try:
            with open(file_path, "a", encoding=encoding) as f:
                f.write(content)

            file_size = os.path.getsize(file_path)

            return {
                "success": True,
                "file_path": file_path,
                "size": file_size,
                "encoding": encoding,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"追加文件时发生错误: {str(e)}",
                "file_path": file_path,
            }

    def generate_diff(
        self, original_content: str, new_content: str, file_path: str = "file"
    ) -> str:
        """生成文件差异对比"""
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        return "".join(diff)


# 创建全局文件写入器实例
file_writer = FileWriter()


@tool
def write_file(
    file_path: str, content: str, encoding: str = "utf-8", create_backup: bool = True
) -> str:
    """
    写入文件内容

    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 文件编码，默认为utf-8
        create_backup: 是否创建备份，默认为True

    Returns:
        写入结果信息
    """
    result = file_writer.write_file(file_path, content, encoding, create_backup)

    if result["success"]:
        backup_info = (
            f"\n备份路径: {result['backup_path']}" if result["backup_path"] else ""
        )
        return f"文件写入成功: {file_path}\n大小: {result['size']} bytes\n行数: {result['lines']}\n编码: {result['encoding']}{backup_info}"
    else:
        return f"文件写入失败: {result['error']}"


@tool
def append_to_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    向文件末尾追加内容

    Args:
        file_path: 文件路径
        content: 要追加的内容
        encoding: 文件编码，默认为utf-8

    Returns:
        追加结果信息
    """
    result = file_writer.append_to_file(file_path, content, encoding)

    if result["success"]:
        return f"内容追加成功: {file_path}\n当前文件大小: {result['size']} bytes\n编码: {result['encoding']}"
    else:
        return f"内容追加失败: {result['error']}"


@tool
def create_new_file(file_path: str, content: str = "", encoding: str = "utf-8") -> str:
    """
    创建新文件

    Args:
        file_path: 文件路径
        content: 初始内容，默认为空
        encoding: 文件编码，默认为utf-8

    Returns:
        创建结果信息
    """
    if os.path.exists(file_path):
        return f"文件已存在: {file_path}"

    result = file_writer.write_file(file_path, content, encoding, create_backup=False)

    if result["success"]:
        return f"新文件创建成功: {file_path}\n大小: {result['size']} bytes\n行数: {result['lines']}\n编码: {result['encoding']}"
    else:
        return f"新文件创建失败: {result['error']}"


@tool
def generate_file_diff(
    file_path: str, new_content: str, encoding: str = "utf-8"
) -> str:
    """
    生成文件内容差异对比

    Args:
        file_path: 文件路径
        new_content: 新内容
        encoding: 文件编码，默认为utf-8

    Returns:
        差异对比结果
    """
    try:
        if not os.path.exists(file_path):
            return f"原文件不存在: {file_path}"

        with open(file_path, "r", encoding=encoding) as f:
            original_content = f.read()

        diff = file_writer.generate_diff(original_content, new_content, file_path)

        if not diff:
            return "文件内容没有变化"

        return f"文件差异对比:\n{diff}"

    except Exception as e:
        return f"生成差异对比时发生错误: {str(e)}"
