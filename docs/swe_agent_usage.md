# SWE Agent使用指南

SWE Agent是一个专门用于软件工程分析和代码质量评估的智能代理系统。

## 功能特性

### 🔍 核心功能
- **代码质量分析**: 深度分析代码结构、复杂度和可维护性
- **技术债务识别**: 发现需要重构的代码区域
- **安全漏洞检测**: 扫描常见的安全问题
- **性能瓶颈分析**: 识别性能优化机会
- **架构评估**: 评估软件架构设计和模式使用

### 🛠️ 专业工具
- 静态代码分析工具集成
- 依赖关系分析
- 测试覆盖率评估
- 文档质量检查
- 编码规范合规性检查

## 快速开始

### 1. 基本使用

```bash
# 使用Python模块方式
python src/swe_agent_workflow.py --preset code_analysis --workspace .

# 使用便捷脚本
python scripts/test_swe_agent.py quick
```

### 2. 预设任务

SWE Agent提供了多种预设任务：

| 任务类型 | 说明 | 使用场景 |
|---------|------|----------|
| `code_analysis` | 整体代码质量分析 | 项目健康度检查 |
| `todo_finder` | 查找TODO/FIXME注释 | 技术债务清理 |
| `dependency_check` | 依赖项验证 | 安全性审查 |
| `structure_summary` | 项目结构摘要 | 新团队成员了解项目 |
| `security_scan` | 安全漏洞扫描 | 安全审计 |
| `performance_analysis` | 性能瓶颈分析 | 性能优化 |
| `test_coverage` | 测试覆盖率分析 | 质量保证 |
| `refactor_suggestions` | 重构建议 | 代码改进 |

### 3. 命令行参数

```bash
python src/swe_agent_workflow.py [OPTIONS]

选项:
  --task TEXT           自定义任务描述
  --preset CHOICE       使用预设任务模板
  --workspace PATH      代码库工作目录
  --debug              启用调试模式
  --max-iterations INT  最大迭代次数 (默认: 10)
  --locale TEXT        语言环境 (默认: zh-CN)
  --recursion-limit INT 递归限制 (默认: 100)
```

## 使用示例

### 示例1: 代码质量分析

```bash
# 分析当前项目的代码质量
python src/swe_agent_workflow.py \
  --preset code_analysis \
  --workspace . \
  --debug
```

### 示例2: 查找技术债务

```bash
# 查找所有TODO和FIXME注释
python src/swe_agent_workflow.py \
  --preset todo_finder \
  --workspace /path/to/project
```

### 示例3: 自定义分析任务

```bash
# 执行自定义分析任务
python src/swe_agent_workflow.py \
  --task "分析src/目录下的Python代码，重点关注性能问题和内存使用" \
  --workspace . \
  --max-iterations 15
```

### 示例4: 安全审计

```bash
# 进行安全漏洞扫描
python src/swe_agent_workflow.py \
  --preset security_scan \
  --workspace /path/to/web/app
```

## 测试工具

### 使用Python测试脚本

```bash
# 快速测试
python scripts/test_swe_agent.py quick

# 综合测试
python scripts/test_swe_agent.py comprehensive

# 预设任务测试
python scripts/test_swe_agent.py preset

# 交互式测试
python scripts/test_swe_agent.py interactive

# 运行所有测试
python scripts/test_swe_agent.py all
```

### 使用Bash脚本 (Unix/Linux/macOS)

```bash
# 快速演示
./scripts/test_swe_agent.sh demo

# 基本测试
./scripts/test_swe_agent.sh quick

# 调试模式测试
./scripts/test_swe_agent.sh comprehensive --debug

# 指定工作目录测试
./scripts/test_swe_agent.sh all --workspace /path/to/project
```

## 编程接口

### Python API

```python
from src.swe_agent_workflow import run_swe_agent, SWEAgentWorkflow

# 方式1: 使用便捷函数
result = run_swe_agent(
    task="分析代码质量并提供改进建议",
    workspace="/path/to/project",
    debug=True,
    max_iterations=10
)

print(f"分析成功: {result['success']}")
print(f"分析报告: {result['report']}")

# 方式2: 使用工作流类
workflow = SWEAgentWorkflow(debug=True)
result = workflow.run_sync(
    task="检测性能瓶颈",
    workspace="/path/to/project"
)

# 方式3: 异步执行
import asyncio

async def analyze_code():
    workflow = SWEAgentWorkflow(debug=False)
    result = await workflow.run_async(
        task="进行安全漏洞扫描",
        workspace="/path/to/project"
    )
    return result

result = asyncio.run(analyze_code())
```

### 结果处理

```python
# 分析返回结果
if result['success']:
    print("✅ 分析成功完成")
    print(f"📄 报告内容: {result['report']}")
    print(f"🔄 迭代次数: {result['iteration_count']}")
    print(f"📊 执行步骤: {result['step_count']}")
    
    if 'environment_info' in result:
        print(f"🌍 环境信息: {result['environment_info']}")
        
else:
    print("❌ 分析失败")
    print(f"错误信息: {result.get('error', '未知错误')}")
```

## 配置和自定义

### 环境变量

```bash
# 设置默认工作目录
export SWE_DEFAULT_WORKSPACE=/path/to/default/project

# 设置调试模式
export SWE_DEBUG=true

# 设置最大迭代次数
export SWE_MAX_ITERATIONS=15
```

### 自定义Prompt模板

SWE Agent使用专门的prompt模板：

- `src/prompts/swe_architect.md` - SWE架构师Agent
- `src/prompts/swe_analyzer.md` - 代码分析师Agent (可选)

可以修改这些模板来自定义分析行为。

## 最佳实践

### 1. 选择合适的任务类型
- **新项目评估**: 使用 `structure_summary` + `code_analysis`
- **维护阶段**: 使用 `todo_finder` + `refactor_suggestions`
- **发布前检查**: 使用 `security_scan` + `performance_analysis`
- **持续集成**: 使用 `test_coverage` + `dependency_check`

### 2. 优化执行参数
- **大型项目**: 增加 `max_iterations` 到 15-20
- **快速检查**: 设置 `max_iterations` 为 3-5
- **详细分析**: 启用 `debug` 模式
- **生产环境**: 关闭 `debug` 模式

### 3. 结果解读
- 关注**执行摘要**部分的关键发现
- 优先处理**高优先级**的技术债务
- 参考**行动计划**中的时间估算
- 定期跟踪改进进度

## 故障排除

### 常见问题

1. **工作目录不存在**
   ```bash
   # 确保工作目录路径正确
   ls -la /path/to/project
   ```

2. **分析超时**
   ```bash
   # 减少迭代次数或增加递归限制
   --max-iterations 5 --recursion-limit 150
   ```

3. **内存不足**
   ```bash
   # 分析较小的目录或启用增量分析
   --workspace ./src --max-iterations 3
   ```

### 调试技巧

```bash
# 启用详细日志
python src/swe_agent_workflow.py --preset code_analysis --debug

# 查看环境信息
python -c "from src.swe_agent_workflow import *; print('SWE Agent 环境正常')"

# 测试基本功能
python scripts/test_swe_agent.py quick
```

## 性能优化

### 提高分析速度
1. 使用合适的工作目录范围
2. 选择针对性的预设任务
3. 调整迭代次数参数
4. 使用并行工具执行

### 提高分析质量
1. 提供清晰的任务描述
2. 确保工作目录包含完整项目
3. 使用足够的迭代次数
4. 结合多种分析类型

## 扩展开发

### 添加自定义分析节点

1. 在 `src/swe/graph/nodes.py` 中添加新节点
2. 在 `src/swe/graph/builder.py` 中注册节点
3. 在 `src/config/agents.py` 中添加agent配置
4. 创建对应的prompt模板

### 集成新的分析工具

1. 在节点中添加工具调用逻辑
2. 更新工具列表配置
3. 添加相应的错误处理
4. 编写单元测试验证

这样，您就可以充分利用SWE Agent来提升代码质量和开发效率了！ 