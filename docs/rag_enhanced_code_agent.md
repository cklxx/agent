# RAG增强Code Agent

## 概述

RAG增强Code Agent是一个集成了检索增强生成(RAG)和上下文管理功能的智能代码助手。它能够理解项目结构、学习现有代码模式，并生成与项目风格一致的高质量代码。

## 核心特性

### 🧠 RAG增强功能
- **语义代码搜索**: 基于语义理解检索相关代码片段
- **模式识别**: 自动识别项目中的代码模式和最佳实践
- **依赖分析**: 理解代码间的依赖关系和架构结构
- **架构感知**: 深度理解项目架构和设计模式

### 🎯 上下文感知
- **历史上下文**: 访问之前的任务执行历史和结果
- **相关代码上下文**: 自动检索相关的代码实现和模式
- **项目知识**: 深度理解项目约定和编码规范
- **自适应规划**: 基于检索到的上下文信息调整任务规划

### ⚡ 智能代码生成
- **模式一致代码**: 生成遵循现有项目模式的代码
- **上下文驱动实现**: 基于相似现有实现作为参考
- **智能导入管理**: 理解并复用现有的导入模式
- **架构兼容**: 确保新代码符合现有架构

## 架构设计

```
RAG增强Code Agent
├── RAGEnhancedCodeTaskPlanner     # RAG增强任务规划器
│   ├── 代码检索器 (CodeRetriever)
│   ├── 代码索引器 (CodeIndexer)
│   └── 上下文管理器 (ContextManager)
├── RAGEnhancedCodeAgent          # RAG增强代理
│   ├── 任务执行引擎
│   ├── 提示模板管理
│   └── 结果处理器
└── RAGEnhancedCodeAgentWorkflow  # 完整工作流
    ├── 代码分析
    ├── 重构支持
    ├── 文档生成
    └── 改进建议
```

## 使用方法

### 1. 基本使用

```python
from src.agents.rag_enhanced_code_agent import create_rag_enhanced_code_agent
from src.tools import *

# 创建RAG增强的Code Agent
agent = create_rag_enhanced_code_agent(
    repo_path=".",  # 项目路径
    tools=[read_file, write_file, execute_terminal_command, ...]
)

# 执行任务
result = await agent.execute_task_with_rag(
    "创建一个新的HTTP客户端类，参考现有的API模式"
)
```

### 2. 使用工作流

```python
from src.rag_enhanced_code_agent_workflow import RAGEnhancedCodeAgentWorkflow

# 创建工作流
workflow = RAGEnhancedCodeAgentWorkflow(repo_path=".")

# 执行任务
result = await workflow.execute_task(
    "重构用户认证模块，提高安全性和可维护性"
)

# 分析代码库
analysis = await workflow.analyze_codebase()

# 生成改进建议
suggestions = await workflow.suggest_improvements("性能优化")

# 执行重构
refactor_result = await workflow.execute_refactoring(
    target_files=["src/auth/user.py"],
    refactoring_goals="提高安全性和性能"
)
```

### 3. 命令行使用

```bash
# 交互模式
python scripts/rag_enhanced_code_agent_cli.py --interactive

# 执行特定任务
python scripts/rag_enhanced_code_agent_cli.py --task "创建新的数据库连接池"

# 调试模式
python scripts/rag_enhanced_code_agent_cli.py --task "修复登录bug" --debug
```

## 工作流程

### 阶段1: RAG增强分析
1. **上下文代码检索**: 使用RAG检索相关代码示例和模式
2. **相似实现分析**: 识别解决类似问题的现有实现
3. **模式发现**: 提取通用模式、约定和最佳实践
4. **依赖映射**: 理解组件间的交互和依赖关系

### 阶段2: 上下文感知规划
1. **基于模式的规划**: 创建利用现有成功模式的计划
2. **风险评估**: 识别潜在冲突或破坏性变更
3. **兼容性分析**: 确保计划的变更与现有代码兼容
4. **资源优化**: 规划高效使用现有组件和工具

### 阶段3: 上下文指导实现
1. **模式一致开发**: 匹配现有代码风格、格式和约定
2. **智能代码复用**: 识别并复用现有组件
3. **集成感知开发**: 确保新代码符合现有接口
4. **错误处理模式**: 遵循已建立的错误处理模式

### 阶段4: 上下文验证
1. **模式合规验证**: 验证代码遵循项目风格指南
2. **影响分析**: 分析对依赖组件的影响
3. **集成测试**: 验证与现有组件的集成
4. **回归测试**: 确保现有功能保持完整

## 质量指标

RAG增强Code Agent通过以下指标衡量成功：

- **模式一致性**: 代码遵循现有模式的程度 (目标: 95%+)
- **上下文利用**: 有效使用RAG检索上下文的程度 (目标: 80%+)
- **集成质量**: 与现有代码库的无缝集成 (目标: 零破坏性变更)
- **代码复用**: 适当复用现有组件的程度 (目标: 60%+)
- **约定遵循**: 遵循项目约定的程度 (目标: 100%)
- **性能影响**: 最小负面性能影响 (目标: <5%性能下降)

## 高级功能

### 代码库分析
```python
# 分析整个代码库的结构和模式
analysis = await workflow.analyze_codebase()
print(f"发现 {analysis['project_structure']['total_files']} 个文件")
print(f"主要语言: {analysis['project_structure']['main_languages']}")
```

### 智能重构
```python
# 基于上下文感知的代码重构
result = await workflow.execute_refactoring(
    target_files=["src/models/user.py", "src/auth/login.py"],
    refactoring_goals="提高性能和安全性"
)
```

### 文档生成
```python
# 基于代码分析生成文档
api_docs = await workflow.generate_documentation("api")
arch_docs = await workflow.generate_documentation("architecture")
```

### 改进建议
```python
# 基于RAG分析生成改进建议
suggestions = await workflow.suggest_improvements("安全性和性能")
```

## 配置选项

### RAG配置
- `repo_path`: 代码仓库路径
- `db_path`: RAG数据库路径 (默认: `temp/rag_data/code_index.db`)
- `max_iterations`: 最大执行迭代次数

### Context配置
- `working_memory_limit`: 工作记忆容量限制
- `auto_compress`: 是否自动压缩上下文
- `compression_threshold`: 压缩阈值

## 示例场景

### 1. 新功能开发
```python
task = """
创建一个新的缓存管理器，要求：
1. 支持多种缓存后端 (Redis, Memcached, 内存)
2. 包含过期时间和LRU策略
3. 遵循项目现有的缓存模式
4. 包含完整的错误处理和日志
"""
result = await workflow.execute_task(task)
```

### 2. Bug修复
```python
task = """
修复用户登录模块的并发问题：
1. 分析现有的并发处理模式
2. 识别竞态条件和死锁风险
3. 应用项目中成功的并发解决方案
4. 确保修复不破坏现有功能
"""
result = await workflow.execute_task(task)
```

### 3. 性能优化
```python
task = """
优化数据库查询性能：
1. 分析现有的查询优化模式
2. 识别N+1查询和慢查询
3. 应用项目中的缓存和索引策略
4. 保持API兼容性
"""
result = await workflow.execute_task(task)
```

## 最佳实践

### 1. 任务描述
- 提供清晰、具体的任务描述
- 提及相关的现有代码或模块
- 指定特定的实现要求或约束

### 2. 上下文利用
- 让agent分析相关的现有实现
- 参考项目中的成功模式
- 保持与现有架构的一致性

### 3. 质量保证
- 验证生成的代码符合项目标准
- 运行测试确保功能正确性
- 检查性能和安全性影响

## 故障排除

### 常见问题

1. **RAG检索失败**
   - 检查代码库是否已正确索引
   - 验证数据库路径和权限
   - 重新运行索引构建

2. **上下文管理错误**
   - 检查内存使用情况
   - 调整工作记忆限制
   - 清理过期的上下文数据

3. **代码生成质量问题**
   - 改进任务描述的具体性
   - 检查相关代码的质量
   - 调整RAG检索参数

### 调试技巧

```bash
# 启用调试模式
python scripts/rag_enhanced_code_agent_cli.py --task "..." --debug

# 检查RAG数据库状态
python -c "
from src.rag.code_indexer import CodeIndexer
indexer = CodeIndexer('.')
print(indexer.get_statistics())
"
```

## 扩展开发

### 添加新工具
```python
def my_custom_tool(param: str) -> str:
    """自定义工具函数"""
    return f"处理: {param}"

# 添加到工具列表
tools = [my_custom_tool, ...existing_tools]
agent = create_rag_enhanced_code_agent(tools=tools)
```

### 自定义提示模板
```markdown
<!-- src/prompts/my_custom_agent.md -->
---
CURRENT_TIME: {{ CURRENT_TIME }}
---

你是一个自定义的RAG增强代理...
{% if rag_context_available %}
相关文件数: {{ relevant_files_count }}
{% endif %}
```

### 扩展工作流
```python
class CustomRAGWorkflow(RAGEnhancedCodeAgentWorkflow):
    async def custom_analysis(self):
        """自定义分析功能"""
        # 实现自定义逻辑
        pass
```

## 贡献指南

欢迎贡献代码和改进建议！请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支
3. 实现功能并添加测试
4. 提交Pull Request

## 许可证

本项目采用MIT许可证。详见LICENSE文件。 