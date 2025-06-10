# 代码RAG功能说明

## 概述

代码RAG (Retrieval-Augmented Generation) 功能为agent系统提供了强大的代码检索和上下文增强能力。该功能可以索引当前代码仓库，并为agent提供相关的代码上下文。
For an overview of how the RAG subsystem integrates into the overall DeepTool architecture, please refer to the [System Architecture Document](SYSTEM_ARCHITECTURE.md#rag-subsystem-srcrag-srccontextcode_rag_adapterpy).

## 核心组件

### 1. CodeIndexer (代码索引器)
位置: `src/rag/code_indexer.py`

功能:
- 扫描代码仓库并提取代码信息
- 支持多种编程语言 (.py, .js, .ts, .java, .cpp等)
- 使用Python AST解析提取函数和类定义
- 将代码信息存储到SQLite数据库

### 2. CodeRetriever (代码检索器)
位置: `src/rag/code_retriever.py`

功能:
- 基于查询关键词检索相关代码
- 支持函数名和类名搜索
- 计算相似度评分
- 返回格式化的文档结果

### 3. CodeRAGAdapter (RAG适配器)
位置: `src/context/code_rag_adapter.py`

功能:
- 连接RAG功能与现有的Context管理系统
- 将检索结果转换为Context对象
- 提供高级搜索和增强方法
- 支持自动上下文增强

## 主要功能

### 基础搜索
```python
# 搜索相关代码
context_ids = await code_rag.enhance_context_with_code("ContextManager", max_results=3)
```

### 函数搜索
```python
# 搜索特定函数
context_ids = await code_rag.search_and_add_function_context("__init__")
```

### 类搜索
```python
# 搜索特定类
context_ids = await code_rag.search_and_add_class_context("CodeIndexer")
```

### 自动增强
```python
# 自动增强查询
result = await code_rag.auto_enhance_code_context("如何使用ContextManager?")
```

## 使用方式

### 1. 程序化使用
```python
from src.context.manager import ContextManager
from src.context.code_rag_adapter import CodeRAGAdapter

# 初始化
context_manager = ContextManager()
code_rag = CodeRAGAdapter(
    context_manager=context_manager,
    repo_path=".",
    db_path="code_index.db"
)

# 使用
context_ids = await code_rag.enhance_context_with_code("search query")
```

### 2. 命令行工具
```bash
# 交互式使用
python scripts/code_rag_cli.py

# 在CLI中的命令：
search ContextManager     # 搜索代码
function __init__         # 搜索函数
class CodeIndexer         # 搜索类
auto 如何使用管理器?       # 自动增强
list                     # 列出当前context
summary                  # 显示摘要
stats                    # 显示统计
```

### 3. 演示脚本
```bash
# 运行完整演示
python examples/code_rag_example.py

# 运行集成测试
python integration_test.py
```

## 技术特性

### 索引能力
- **多语言支持**: Python, JavaScript, TypeScript, Java, C++等
- **智能解析**: 使用AST解析Python代码，准确提取函数和类
- **增量索引**: 支持增量更新代码索引
- **过滤机制**: 自动排除.git, .venv, __pycache__等目录

### 搜索能力
- **语义搜索**: 基于代码内容的相似度匹配
- **精确搜索**: 支持函数名和类名的精确匹配
- **相关性评分**: 为搜索结果计算相关性分数
- **批量搜索**: 支持一次搜索多个结果

### 集成能力
- **Context管理**: 无缝集成现有的Context管理系统
- **元数据丰富**: 为每个Context提供丰富的元数据
- **优先级支持**: 支持设置Context优先级
- **标签系统**: 自动生成相关标签便于管理

## 性能统计

根据集成测试结果：
- **索引文件数**: 626个文件 (Python: 109个)
- **总代码块数**: 64,346个代码块
- **搜索性能**: 毫秒级响应时间
- **内存效率**: 使用SQLite持久化存储

## 文件结构

```
src/
├── rag/
│   ├── code_indexer.py      # 代码索引器
│   └── code_retriever.py    # 代码检索器
├── context/
│   ├── code_rag_adapter.py  # RAG适配器
│   └── __init__.py          # 导出CodeRAGAdapter
scripts/
├── code_rag_cli.py          # 命令行工具
examples/
├── code_rag_example.py      # 演示脚本
tests/
├── test_code_rag.py         # 单元测试
```

## 开发和扩展

### 添加新语言支持
在`CodeParser`类中扩展`LANGUAGE_EXTENSIONS`字典：
```python
LANGUAGE_EXTENSIONS = {
    # ... 现有语言 ...
    'go': ['.go'],
    'rust': ['.rs'],
}
```

### 自定义搜索逻辑
继承`CodeRetriever`类并重写相关方法：
```python
class CustomCodeRetriever(CodeRetriever):
    def calculate_similarity(self, query: str, content: str) -> float:
        # 自定义相似度计算逻辑
        pass
```

### 扩展Context格式
修改`CodeRAGAdapter`中的格式化方法：
```python
def _format_code_document(self, doc) -> str:
    # 自定义格式化逻辑
    pass
```

## 配置选项

### 索引配置
- `excluded_patterns`: 排除的文件模式
- `max_file_size`: 最大文件大小限制
- `chunk_size`: 代码块大小

### 搜索配置
- `min_similarity`: 最小相似度阈值
- `max_results`: 最大结果数量
- `enable_fuzzy_search`: 启用模糊搜索

## 故障排除

### 常见问题

1. **索引失败**
   - 检查文件权限
   - 确保数据库路径可写
   - 查看日志输出

2. **搜索无结果**
   - 确认索引已完成
   - 调整相似度阈值
   - 尝试不同的查询关键词

3. **性能问题**
   - 减少max_results数量
   - 清理旧的索引数据
   - 优化查询关键词

### 日志调试
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 版本信息

- **版本**: 1.0.0
- **兼容性**: Python 3.8+
- **依赖**: SQLite3, pathlib, ast

## 更新日志

### v1.0.0 (2024-12-19)
- ✅ 初始发布
- ✅ 完整的代码索引和检索功能
- ✅ Context管理系统集成
- ✅ 命令行工具和演示脚本
- ✅ 完整的测试覆盖 