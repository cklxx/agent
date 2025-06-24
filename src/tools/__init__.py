# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from .agent_tools import clear_conversation, compact_conversation
from .architect_tool import architect_plan, dispatch_agent
from .bash_tool import bash_command
from .file_edit_tools import edit_file, replace_file
from .file_system_tools import view_file, list_files, glob_search, grep_search
from .notebook_tools import notebook_read, notebook_edit_cell
from .tts import VolcengineTTS
from .thinking_tool import think

# Import workspace-aware tool factory
from .workspace_tools import (
    create_workspace_aware_tools,
    create_workspace_tool_factory,
    get_workspace_tools,
    resolve_workspace_path,
)

# Import existing tools (maintained for compatibility)
from .crawl import crawl_tool
from .maps import search_location, get_route, get_nearby_places
from .python_repl import python_repl_tool
from .retriever import get_retriever_tool
from .search import get_web_search_tool

# Import optimized tools (NEW)
from .unified_tools import (
    get_unified_tool_manager,
    UnifiedToolManager,
    ToolExecutionError,
    unified_view_file,
    unified_bash_command,
    unified_list_files,
    unified_glob_search,
    unified_grep_search,
    get_tool_stats,
    cleanup_unified_tools,
)

from .middleware import (
    get_tool_middleware,
    ToolMiddleware,
    CacheConfig,
    CachePolicy,
    tool_middleware,
)

from .async_tools import (
    get_async_tool_manager,
    AsyncToolManager,
    run_tool_async,
    run_tool_sync,
    async_tool_wrapper,
    sync_tool_wrapper,
)

from .optimized_tools import (
    optimized_view_file,
    optimized_list_files,
    optimized_glob_search,
    optimized_grep_search,
    optimized_edit_file,
    optimized_bash_command,
    create_optimized_workspace_tools,
    get_optimization_stats,
    cleanup_all_optimized_resources,
)

from .optimized_bash_tool import (
    list_background_processes,
    stop_background_process,
    get_process_logs,
    cleanup_all_processes,
)

__all__ = [
    # Agent tools
    "dispatch_agent",
    "clear_conversation",
    "compact_conversation",
    # Architecture tool
    "architect_plan",
    # System tools
    "bash_command",
    # File tools
    "edit_file",
    "replace_file",
    "view_file",
    "list_files",
    "glob_search",
    "grep_search",
    # Notebook tools
    "notebook_read",
    "notebook_edit_cell",
    "VolcengineTTS",
    # Thinking tool
    "think",
    # Workspace-aware tool factory
    "create_workspace_aware_tools",
    "create_workspace_tool_factory",
    "get_workspace_tools",
    "resolve_workspace_path",
    # External tools
    "crawl_tool",
    "search_location",
    "get_route",
    "get_nearby_places",
    "python_repl_tool",
    "get_retriever_tool",
    "get_web_search_tool",
    # ========== 优化工具 (NEW) ==========
    # 统一工具管理器
    "get_unified_tool_manager",
    "UnifiedToolManager",
    "ToolExecutionError",
    # 统一工具接口
    "unified_view_file",
    "unified_bash_command",
    "unified_list_files",
    "unified_glob_search",
    "unified_grep_search",
    "get_tool_stats",
    "cleanup_unified_tools",
    # 中间件
    "get_tool_middleware",
    "ToolMiddleware",
    "CacheConfig",
    "CachePolicy",
    "tool_middleware",
    # 异步工具管理
    "get_async_tool_manager",
    "AsyncToolManager",
    "run_tool_async",
    "run_tool_sync",
    "async_tool_wrapper",
    "sync_tool_wrapper",
    # 优化工具实现
    "optimized_view_file",
    "optimized_list_files",
    "optimized_glob_search",
    "optimized_grep_search",
    "optimized_edit_file",
    "optimized_bash_command",
    "create_optimized_workspace_tools",
    "get_optimization_stats",
    "cleanup_all_optimized_resources",
    # 进程管理
    "list_background_processes",
    "stop_background_process",
    "get_process_logs",
    "cleanup_all_processes",
]
