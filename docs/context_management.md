# Context管理系统

## 概述

Context管理系统负责管理AI Agent的上下文信息，包括对话历史、任务状态、知识片段等。

## 数据存储

### 存储位置

**重要更新**: 从当前版本开始，所有临时数据库文件都存储在 `temp/` 目录下：

- **Context数据库**: `temp/contexts.db` - 存储对话和任务上下文
- **RAG数据库**: `temp/rag_data/code_index.db` - 存储代码索引和检索数据

### 目录结构

```
temp/
├── contexts.db              # Context管理数据库
└── rag_data/
    └── code_index.db        # RAG代码索引数据库
```

### 优势

1. **项目整洁**: 避免在项目根目录创建临时文件
2. **版本控制**: `temp/` 目录已包含在 `.gitignore` 中
3. **一致性**: 与RAG数据存储位置保持一致
4. **易于清理**: 可以安全删除整个 `temp/` 目录

## 内存架构

### 两层存储模型

1. **工作记忆 (Working Memory)**
   - 基于内存的快速访问
   - LRU缓存策略
   - 默认容量: 50个context

2. **长期记忆 (Long-term Memory)**
   - 基于SQLite的持久化存储
   - 支持复杂查询和检索
   - 自动备份和恢复

### Context类型

- `CONVERSATION`: 对话上下文
- `TASK`: 任务上下文
- `KNOWLEDGE`: 知识上下文
- `SYSTEM`: 系统上下文
- `CODE`: 代码上下文
- `FILE`: 文件上下文
- `EXECUTION`: 执行上下文
- `PLANNING`: 规划上下文

## 使用示例

### 基本使用

```python
from src.context.manager import ContextManager

# 初始化管理器（使用默认temp/contexts.db）
manager = ContextManager()

# 添加context
context_id = await manager.add_context(
    content="用户询问关于Python的问题",
    context_type=ContextType.CONVERSATION,
    priority=Priority.HIGH,
    tags=["python", "question"]
)

# 检索context
context = await manager.get_context(context_id)
```

### 自定义数据库路径

```python
from src.context.memory import SQLiteStorage, LongTermMemory

# 使用自定义路径
storage = SQLiteStorage("custom/path/contexts.db")
memory = LongTermMemory(storage)
manager = ContextManager(long_term_memory=memory)
```

## 配置和优化

### 性能调优

- **工作记忆大小**: 根据可用内存调整
- **自动压缩**: 启用以减少存储空间
- **清理策略**: 定期清理过期context

### 备份和恢复

```bash
# 备份context数据
cp temp/contexts.db backup/contexts_$(date +%Y%m%d).db

# 恢复数据
cp backup/contexts_20241208.db temp/contexts.db
```

## 故障排除

### 常见问题

1. **数据库锁定**: 确保没有多个进程同时访问
2. **权限问题**: 检查temp目录的读写权限
3. **空间不足**: 定期清理temp目录

### 清理命令

```bash
# 清理所有临时数据
rm -rf temp/

# 只清理context数据
rm -f temp/contexts.db

# 只清理RAG数据
rm -rf temp/rag_data/
``` 