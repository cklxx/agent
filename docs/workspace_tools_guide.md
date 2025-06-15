# Workspace工具使用指南

## 概述

Workspace工具工厂提供了一套支持workspace路径自动拼接的文件系统工具，使得agent可以使用相对路径来操作文件和执行命令，而无需手动处理绝对路径转换。

## 主要功能

### 🔧 核心工具工厂函数

1. **`get_workspace_tools(workspace)`** - 直接获取workspace工具
2. **`create_workspace_aware_tools(workspace)`** - 创建workspace感知工具
3. **`create_workspace_tool_factory(state)`** - 从state创建工具工厂
4. **`resolve_workspace_path(file_path, workspace)`** - 路径解析工具

### 📁 支持的Workspace工具

| 原始工具 | Workspace版本 | 功能描述 |
|---------|--------------|----------|
| `view_file` | `workspace_view_file` | 查看文件内容，支持相对路径 |
| `list_files` | `workspace_list_files` | 列出目录内容，支持相对路径 |
| `glob_search` | `workspace_glob_search` | 文件模式搜索，支持相对路径 |
| `grep_search` | `workspace_grep_search` | 文件内容搜索，支持相对路径 |
| `edit_file` | `workspace_edit_file` | 编辑文件，支持相对路径 |
| `replace_file` | `workspace_replace_file` | 替换文件，支持相对路径 |
| `notebook_read` | `workspace_notebook_read` | 读取笔记本，支持相对路径 |
| `notebook_edit_cell` | `workspace_notebook_edit_cell` | 编辑笔记本单元格，支持相对路径 |
| `bash_command` | `workspace_bash_command` | 执行命令，自动设置工作目录 |

## 使用方法

### 方法1：直接使用

```python
from src.tools import get_workspace_tools

# 获取workspace工具
workspace = "/Users/ckl/code/agent"
tools = get_workspace_tools(workspace)

# 使用相对路径读取文件
result = tools["workspace_view_file"]("src/main.py")

# 使用相对路径列出目录
listing = tools["workspace_list_files"]("src/tools")

# 执行命令（自动在workspace中执行）
output = tools["workspace_bash_command"]("ls -la")
```

### 方法2：在LangGraph节点中使用

```python
from src.tools import get_workspace_tools
from src.llms.llm import get_llm_by_type

def my_node(state: State):
    # 从state获取workspace
    workspace = state.get("workspace", "")
    
    # 创建workspace工具
    workspace_tools = get_workspace_tools(workspace)
    
    # 创建LLM并绑定工具
    llm = get_llm_by_type("basic")
    tool_list = list(workspace_tools.values())
    llm_with_tools = llm.bind_tools(tool_list)
    
    # 使用工具...
```

### 方法3：使用工具工厂

```python
from src.tools import create_workspace_tool_factory

def dynamic_node(state: State):
    # 创建动态工具工厂
    tool_factory = create_workspace_tool_factory(state)
    
    # 随时获取最新的workspace工具
    current_tools = tool_factory()
    
    # 使用工具...
```

## 路径解析规则

### 自动路径处理

- **相对路径**：自动拼接到workspace目录
  - 输入：`"src/main.py"`
  - 输出：`"/Users/ckl/code/agent/src/main.py"`

- **绝对路径**：保持不变
  - 输入：`"/absolute/path/file.py"`
  - 输出：`"/absolute/path/file.py"`

- **当前目录**：解析为workspace根目录
  - 输入：`"."`
  - 输出：`"/Users/ckl/code/agent"`

### 示例对比

```python
# 传统方式 - 需要手动处理路径
workspace = "/Users/ckl/code/agent"
abs_path = os.path.join(workspace, "src/main.py")
result = view_file(abs_path)

# Workspace工具 - 自动处理路径
tools = get_workspace_tools(workspace)
result = tools["workspace_view_file"]("src/main.py")
```

## 完整集成示例

### 在agent节点中的完整使用

```python
def enhanced_architect_node(state: State):
    """使用workspace工具的增强架构师节点"""
    
    # 1. 获取workspace工具
    workspace = state.get("workspace", "")
    workspace_tools = get_workspace_tools(workspace)
    
    # 2. 准备所有工具（workspace + 其他工具）
    from src.tools import think, crawl_tool, python_repl_tool
    
    all_tools = list(workspace_tools.values()) + [
        think, crawl_tool, python_repl_tool
    ]
    
    # 3. 创建LLM并绑定工具
    llm = get_llm_by_type(AGENT_LLM_MAP["architect"])
    llm_with_tools = llm.bind_tools(all_tools)
    
    # 4. 构建消息并执行
    messages = state.get("messages", [])
    result = llm_with_tools.invoke(messages)
    
    return Command(update={"messages": messages + [result]})
```

### 便捷集成函数

```python
from src.code.graph.workspace_node_example import get_workspace_aware_agent_tools

def my_agent_node(state: State):
    """使用便捷函数的agent节点"""
    
    # 一行代码获取所有workspace感知工具
    all_tools = get_workspace_aware_agent_tools(state)
    
    # 创建LLM
    llm = get_llm_by_type("architect")
    llm_with_tools = llm.bind_tools(all_tools)
    
    # 使用...
```

## 最佳实践

### ✅ 推荐做法

1. **优先使用workspace工具**：在需要文件操作时优先使用workspace版本
2. **保持向后兼容**：可以同时提供原版工具和workspace工具
3. **统一路径规范**：在prompt中指导模型使用相对路径
4. **错误处理**：workspace为空时有适当的fallback机制

### ❌ 避免做法

1. **不要混用路径风格**：避免在同一个工作流中混用相对和绝对路径
2. **不要硬编码workspace**：总是从state中获取workspace信息
3. **不要忽略错误**：要正确处理路径解析失败的情况

## 故障排除

### 常见问题

1. **Q: workspace工具无法找到文件**
   - A: 检查workspace路径是否正确设置在state中
   - A: 验证相对路径是否正确（不要以"/"开头）

2. **Q: 命令执行在错误的目录**
   - A: 使用`workspace_bash_command`确保在正确的工作目录执行

3. **Q: 路径解析错误**
   - A: 使用`resolve_workspace_path`函数单独测试路径解析

### 调试技巧

```python
# 调试路径解析
from src.tools import resolve_workspace_path

workspace = "/Users/ckl/code/agent"
test_path = "src/main.py"
resolved = resolve_workspace_path(test_path, workspace)
print(f"原路径: {test_path}")
print(f"解析后: {resolved}")

# 检查workspace设置
def debug_workspace(state: State):
    workspace = state.get("workspace", "")
    print(f"当前workspace: {workspace}")
    print(f"Workspace存在: {os.path.exists(workspace) if workspace else False}")
```

## 总结

Workspace工具工厂提供了一个强大而灵活的方式来处理文件路径相关的操作，通过自动路径解析大大简化了agent的文件操作逻辑。配合适当的集成模式，可以显著提升开发效率和代码可维护性。 