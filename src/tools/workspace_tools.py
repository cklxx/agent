#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Workspace-aware tools that resolve file paths relative to a workspace directory.
These tools provide a workspace-specific interface to file system operations.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

# Import raw tools
from src.tools.file_system_tools import (
    view_file as view_file_raw,
    list_files as list_files_raw,
    glob_search as glob_search_raw,
    grep_search as grep_search_raw,
)
from src.tools.file_edit_tools import (
    edit_file as edit_file_raw,
    replace_file as replace_file_raw,
)
from src.tools.notebook_tools import (
    notebook_read as notebook_read_raw,
    notebook_edit_cell as notebook_edit_cell_raw,
)
from src.tools.bash_tool import bash_command as bash_command_raw

# 导入RAG增强搜索工具
from src.tools.rag_enhanced_search_tools import (
    rag_enhanced_glob_search,
    rag_enhanced_grep_search,
    semantic_code_search,
)


def resolve_workspace_path(file_path: str, workspace: Optional[str] = None) -> str:
    """
    Resolve file path relative to workspace.

    Args:
        file_path: The file path (relative or absolute)
        workspace: The workspace directory

    Returns:
        Absolute path resolved from workspace
    """
    if not workspace:
        return file_path

    # If already absolute, return as-is
    if os.path.isabs(file_path):
        return file_path

    # Join relative path with workspace
    return str(Path(workspace) / file_path)


def create_workspace_aware_tools(workspace: Optional[str] = None) -> Dict[str, Any]:
    """
    Create workspace-aware versions of file system tools.

    Args:
        workspace: The workspace directory to use as base path

    Returns:
        Dictionary of workspace-aware tools
    """

    @tool
    def view_file(
        file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """
        Read and display file contents.

        Args:
            file_path: Path to file
            offset: Start line number
            limit: Number of lines to read
        """
        logger.info(f"🔍 view_file: {file_path}")
        resolved_path = resolve_workspace_path(file_path, workspace)
        return view_file_raw.func(resolved_path, offset, limit)

    @tool
    def list_files(path: str) -> str:
        """
        List files and directories in given path.

        Args:
            path: Directory path to list
        """
        logger.info(f"🔍 list_files: {path}")
        resolved_path = resolve_workspace_path(path, workspace)
        return list_files_raw.func(resolved_path)

    @tool
    def glob_search(pattern: str, path: Optional[str] = None) -> str:
        """
        Find files matching glob pattern with RAG enhancement.

        Args:
            pattern: Glob pattern to match (e.g. *.py, **/*.js)
            path: Directory to search in
        """
        logger.info(f"🔍 glob_search: {pattern}, {path}")
        try:
            # 使用事件循环运行异步RAG增强搜索
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建任务
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        rag_enhanced_glob_search.func(pattern, path, workspace),
                    )
                    return future.result()
            else:
                # 如果没有事件循环，直接运行
                return asyncio.run(
                    rag_enhanced_glob_search.func(pattern, path, workspace)
                )
        except Exception as e:
            # RAG增强失败时，回退到传统搜索
            if path:
                resolved_path = resolve_workspace_path(path, workspace)
            else:
                resolved_path = workspace
            basic_result = glob_search_raw.func(pattern, resolved_path)
            return f"{basic_result}\n\n[注意: RAG增强搜索不可用 ({str(e)}), 显示基础搜索结果]"

    @tool
    def grep_search(
        pattern: str, path: Optional[str] = None, include: Optional[str] = None
    ) -> str:
        """
        Search text content inside files.
        Args:
            pattern: Text pattern to search for (regex supported)
            path: Directory to search in
            include: File pattern filter (e.g. *.py)
        """
        logger.info(f"🔍 grep_search: {pattern}, {path}, {include}")
        try:
            # 使用事件循环运行异步RAG增强搜索
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建任务
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        rag_enhanced_grep_search.func(
                            pattern, path, include, workspace
                        ),
                    )
                    return future.result()
            else:
                # 如果没有事件循环，直接运行
                return asyncio.run(
                    rag_enhanced_grep_search.func(pattern, path, include, workspace)
                )
        except Exception as e:
            # RAG增强失败时，回退到传统搜索
            if path:
                resolved_path = resolve_workspace_path(path, workspace)
            else:
                resolved_path = workspace
            basic_result = grep_search_raw.func(pattern, resolved_path, include)
            return f"{basic_result}\n\n[注意: RAG增强搜索不可用 ({str(e)}), 显示基础搜索结果]"

    @tool
    def semantic_search(query: str, max_results: int = 5) -> str:
        """
        Semantic code search using RAG.

        Args:
            query: Semantic query (e.g. "database connection", "user authentication")
            max_results: Maximum number of results
        """
        try:
            logger.info(f"🔍 semantic_search: {query}, {max_results}")
            # 使用事件循环运行异步语义搜索
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建任务
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        semantic_code_search.func(query, max_results, workspace),
                    )
                    return future.result()
            else:
                # 如果没有事件循环，直接运行
                return asyncio.run(
                    semantic_code_search.func(query, max_results, workspace)
                )
        except Exception as e:
            return f"语义搜索不可用: {str(e)}"

    @tool
    def edit_file(file_path: str, old_string: str, new_string: str) -> str:
        """
        Replace specific text in a file.

        Args:
            file_path: Path to file
            old_string: Exact text to replace
            new_string: New text content
        """
        logger.info(f"🔍 edit_file: {file_path}, {old_string}, {new_string}")
        resolved_path = resolve_workspace_path(file_path, workspace)
        return edit_file_raw.func(resolved_path, old_string, new_string)

    @tool
    def replace_file(file_path: str, content: str) -> str:
        """
        Overwrite entire file with new content.

        Args:
            file_path: Path to file
            content: Complete new file content
        """
        logger.debug(f"🔍 replace_file: {file_path}, {content}")
        resolved_path = resolve_workspace_path(file_path, workspace)
        return replace_file_raw.func(resolved_path, content)

    @tool
    def notebook_read(notebook_path: str) -> str:
        """
        Read Jupyter notebook content and structure.

        Args:
            notebook_path: Path to .ipynb file
        """
        logger.info(f"🔍 notebook_read: {notebook_path}")
        resolved_path = resolve_workspace_path(notebook_path, workspace)
        return notebook_read_raw.func(resolved_path)

    @tool
    def notebook_edit_cell(
        notebook_path: str, cell_index: int, new_content: str, cell_type: str = "code"
    ) -> str:
        """
        Modify content of specific notebook cell.

        Args:
            notebook_path: Path to .ipynb file
            cell_index: Cell number to edit (0-based)
            new_content: New cell content
            cell_type: Cell type (code/markdown)
        """
        logger.info(
            f"🔍 notebook_edit_cell: {notebook_path}, {cell_index}, {new_content}, {cell_type}"
        )
        resolved_path = resolve_workspace_path(notebook_path, workspace)
        return notebook_edit_cell_raw.func(
            resolved_path, cell_index, new_content, cell_type
        )

    @tool
    def bash_command(
        command: str, timeout: Optional[int] = None, run_in_background: bool = False
    ) -> str:
        """
        Run shell commands in the workspace directory.

        Args:
            command: Shell command to execute
            timeout: Timeout in milliseconds
            run_in_background: Run as background process
        """
        logger.info(f"🔍 bash_command: {command}, {timeout}, {run_in_background}")
        working_directory = workspace if workspace else None
        return bash_command_raw.func(
            command, timeout, working_directory, run_in_background
        )

    return [
        view_file,
        list_files,
        glob_search,
        grep_search,
        semantic_search,
        edit_file,
        replace_file,
        notebook_read,
        notebook_edit_cell,
        bash_command,
    ]


def create_workspace_tool_factory(
    state: Dict[str, Any],
) -> Callable[[], Dict[str, Any]]:
    """
    Create a tool factory function that uses workspace from state.

    Args:
        state: The current state containing workspace information

    Returns:
        Factory function that creates workspace-aware tools
    """

    def tool_factory() -> Dict[str, Any]:
        workspace = state.get("workspace")
        return create_workspace_aware_tools(workspace)

    return tool_factory


# Convenience function for direct usage
def get_workspace_tools(workspace: Optional[str] = None) -> Dict[str, Any]:
    """
    Get workspace-aware tools directly.

    Args:
        workspace: The workspace directory

    Returns:
        Dictionary of workspace-aware tools
    """
    return create_workspace_aware_tools(workspace)
