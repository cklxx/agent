# 日志配置指南

本项目已优化日志输出，提供精简和详细两种模式，重点突出LLM和Agent规划相关的核心信息。

## 日志模式

### 精简模式（默认）
- 专注于关键的执行流程信息
- 显示LLM规划和Agent执行的核心步骤
- 隐藏第三方库的冗余日志
- 提供清晰的进度指示

### 调试模式
- 显示详细的执行信息
- 包含完整的LLM响应和分析过程
- 显示工具调用的详细参数
- 适用于问题排查和开发调试

## 使用方法

### 命令行参数
```bash
# 精简模式（默认）
python main.py "您的查询"

# 调试模式
python main.py --debug "您的查询"
```

### 代码中使用
```python
from src.workflow import run_agent_workflow_async

# 精简模式
await run_agent_workflow_async(
    user_input="您的查询",
    debug=False  # 默认值
)

# 调试模式
await run_agent_workflow_async(
    user_input="您的查询", 
    debug=True
)
```

## 日志级别说明

### 精简模式日志级别
- `src.agents`: INFO
- `src.graph.nodes`: INFO
- `src.llms`: INFO
- `code_agent_llm_planner`: INFO
- `code_agent_llm_execution`: INFO
- `llm_planner`: INFO
- `terminal_execution`: INFO（Terminal执行状态）
- `src.tools.terminal_executor`: WARNING（减少冗余）
- 第三方库: ERROR级别（隐藏大部分输出）

### 调试模式日志级别
- 核心模块: DEBUG
- LLM相关: DEBUG
- `terminal_execution`: DEBUG（详细Terminal执行信息）
- `src.tools.terminal_executor`: INFO（Terminal内部日志）
- 第三方库: WARNING级别（显示重要信息）

## 重点输出内容

### LLM规划相关
- ✅ 任务分析和规划结果
- 📝 生成的执行步骤数量
- 🧠 LLM模型调用状态
- 🔄 规划迭代和异常处理

### Agent执行相关
- 🚀 任务开始和进度
- 📋 当前执行的步骤
- 🔧 使用的工具列表
- ✅ 步骤完成状态
- ⚠️ 执行异常和错误

### Terminal执行相关
- ⚡ 命令执行状态（精简格式）
- ✅ 执行成功/失败状态
- 🔄 后台任务管理
- ⏰ 执行时间统计

### 调试信息（仅调试模式）
- 详细的执行步骤描述
- 完整的LLM响应内容
- 工具调用的参数详情
- 内部状态和变量信息

## 日志格式

### 精简模式
- 纯消息格式，无时间戳和模块名
- 使用emoji和简洁的描述
- 重点突出关键信息

### 调试模式
- 包含时间戳和模块名
- 详细的上下文信息
- 便于问题定位和分析

## 自定义配置

如需自定义日志配置，可以修改 `src/config/logging_config.py` 文件：

```python
from src.config.logging_config import setup_simplified_logging, setup_debug_logging

# 启用精简日志
setup_simplified_logging()

# 启用调试日志  
setup_debug_logging()
```

## 注意事项

1. 精简模式下，详细的调试信息会被隐藏，如需排查问题请使用调试模式
2. 调试模式会产生大量日志输出，建议仅在开发和调试时使用
3. 日志配置会影响所有模块，切换模式后会立即生效
4. 第三方库日志已被大幅精简，以避免信息过载

## 模块优化说明

### LLM规划日志优化
- **简化前**: 详细的多行输出，包含分隔符和冗长的技术细节
- **简化后**: 简洁的状态信息，如 "🧠 Planner generating plan" 和 "✅ 生成 3 个执行步骤"

### Agent执行日志优化
- **简化前**: 详细的步骤分析和执行过程
- **简化后**: 专注于执行进度，如 "📋 执行: 任务描述" 和 "✅ 步骤完成"

### Terminal执行日志优化
- **简化前**: 极其详细的技术输出（10+行每个命令）
- **简化后**: 简洁格式 "⚡ 执行: command" → "✅ 完成 (0.3s): result"

### Code Agent 增强优化
本次优化重点改进了Code Agent的执行流程，增加了三阶段执行模式：

#### 阶段1: 前置信息收集
- **环境评估**: 自动获取工作目录和项目结构
- **上下文分析**: 分析相关文件和代码模式
- **需求验证**: 验证前置条件和资源可用性

#### 阶段2: 任务实施
- 基于前置信息进行精确实施
- 持续验证每个步骤的执行结果
- 智能错误处理和恢复

#### 阶段3: 验证确认
- **文件完整性验证**: 检查文件创建/修改是否正确
- **功能测试**: 验证实现的功能正常工作
- **集成验证**: 确保与现有系统兼容

#### 日志输出示例

```
🚀 开始执行代码任务
📋 任务描述: 创建一个Python脚本实现文件备份功能

📋 阶段1: 任务规划...
📊 规划完成: 3 个阶段，共 8 个步骤
  🔹 pre_analysis: 2 个步骤
  🔹 implementation: 3 个步骤  
  🔹 verification: 3 个步骤

🔍 阶段2: 前置信息收集...
📋 步骤 1: 环境评估
  ✅ 步骤 1 完成
📋 步骤 2: 上下文分析
  ✅ 步骤 2 完成
✅ 前置信息收集完成: 2/2 步骤成功

⚙️ 阶段3: 任务实施...
📋 步骤 3: 代码实现
  ✅ 步骤 3 完成
✅ 任务实施完成: 3/3 步骤成功

🔬 阶段4: 验证确认...
📋 步骤 6: 文件完整性验证
  ✅ 步骤 6 完成
📋 步骤 7: 功能测试
  ✅ 步骤 7 完成
📋 步骤 8: 集成验证
  ✅ 步骤 8 完成
✅ 验证确认完成: 3/3 步骤成功

🎉 任务执行成功完成!
📈 执行统计: 8/8 步骤成功
🔹 执行阶段: pre_analysis, implementation, verification
```

## 自定义日志记录器

### 获取专用记录器

```python
from src.config.logging_config import get_llm_logger, get_terminal_logger

# LLM专用记录器
llm_logger = get_llm_logger("my_llm_component")
llm_logger.info("🧠 LLM processing...")

# Terminal专用记录器  
terminal_logger = get_terminal_logger()
terminal_logger.info("⚡ 执行命令...")
```

## 最佳实践

### 1. 日志级别选择
- **INFO**: 用户需要了解的关键信息
- **DEBUG**: 开发调试信息
- **WARNING**: 非致命问题
- **ERROR**: 错误信息

### 2. 表情符号使用
- 🚀 开始/启动
- ✅ 成功/完成
- ❌ 失败/错误
- ⚠️ 警告
- 🧠 LLM相关
- ⚡ 命令执行
- 📋 任务/步骤
- 🔍 分析/检查
- 🔬 验证/测试

### 3. 消息格式
- 保持简洁明了
- 包含关键上下文信息
- 避免技术术语过多
- 提供可操作的信息

### 4. Code Agent 使用建议
- 让Agent自主完成三阶段执行流程
- 关注验证阶段的输出，确保质量
- 在调试模式下查看详细的步骤分析
- 利用阶段化执行提升任务成功率

## 故障排查

### 日志不显示
1. 检查日志级别设置
2. 确认模块名称正确
3. 验证import路径

## Prompt管理优化

### Prompt统一化优化
本项目已完成全面的prompt统一化工作：

- **统一前**: 项目中存在多种prompt使用方式（get_prompt_template、硬编码等）
- **统一后**: 所有prompt都通过apply_prompt_template统一管理，共涉及12个文件的修改
- **技术收益**: 
  - 统一性：消除了不一致的prompt使用方式
  - 维护性：prompt内容集中在.md模板文件中
  - 可扩展性：支持分层目录结构和Jinja2模板语法
  - 调试性：统一的模板引擎处理和错误信息

### Prompt使用最佳实践
- 新增prompt时使用apply_prompt_template模式
- 运行scripts/check_prompt_consistency.py检查一致性
- 参考docs/PROMPT_UNIFICATION_SUMMARY.md了解详细信息

通过这些优化，项目的日志系统现在更加清晰、高效，同时建立了统一的prompt管理体系，为后续开发维护奠定了坚实基础。

### 格式异常
1. 检查logging_config导入
2. 确认setup函数调用
3. 验证环境变量设置

### 性能问题
1. 使用简化模式减少输出
2. 调整第三方库日志级别
3. 考虑异步日志记录

## 配置文件

日志配置主要在 `src/config/logging_config.py` 中管理，支持：
- 动态日志级别调整
- 自定义格式器
- 模块化记录器管理
- 环境变量控制 