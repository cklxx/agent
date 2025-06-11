# Code Agent 测试指南

本指南介绍如何测试和演示Code Agent的功能，特别是新增的反思功能。

## 概述

Code Agent现在具备强大的反思能力，能够：
- 评估任务完成质量
- 检测测试失败和代码问题
- 识别实现的不完整性
- 自动重新规划和改进

## 快速开始

### 使用测试脚本（推荐）

```bash
# 给脚本添加执行权限（如果需要）
chmod +x scripts/test_code_agent.sh

# 快速演示
./scripts/test_code_agent.sh quick

# 反思功能演示
./scripts/test_code_agent.sh reflection test_failure

# 交互式测试
./scripts/test_code_agent.sh interactive

# 完整测试套件
./scripts/test_code_agent.sh full
```

### 直接运行Python脚本

```bash
# 快速演示
python examples/code_agent_reflection_demo.py quick

# 完整工作流测试
python tests/test_code_agent_workflow.py
```

## 测试场景

### 1. 基本功能测试

测试Code Agent的基本代码生成能力：

```bash
./scripts/test_code_agent.sh quick "创建一个简单的Python函数计算最大公约数"
```

### 2. 反思功能演示

#### 成功完成场景（不触发反思）
```bash
./scripts/test_code_agent.sh reflection success
```

#### 测试失败场景（触发反思）
```bash
./scripts/test_code_agent.sh reflection test_failure
```

#### 不完整实现场景
```bash
./scripts/test_code_agent.sh reflection incomplete
```

#### 代码质量问题场景
```bash
./scripts/test_code_agent.sh reflection quality
```

#### 依赖配置问题场景
```bash
./scripts/test_code_agent.sh reflection dependency
```

### 3. 完整测试套件

运行所有测试用例：

```bash
./scripts/test_code_agent.sh full
```

这将执行以下测试：
- 基本代码生成功能
- 文件操作功能
- 调试场景测试
- 复杂项目测试
- 测试失败场景
- 不完整实现场景

## 测试结果分析

### 反思功能检查点

在测试过程中，注意观察以下关键点：

1. **反思触发检测**
   - 查找日志中的"🔄 检测到反思重新规划!"
   - 检查是否有"质量评估反馈"消息

2. **最终报告质量**
   - 报告是否包含"反思与评估"章节
   - 规划迭代次数是否合理
   - 报告内容是否完整

3. **状态清理验证**
   - 重新规划时是否正确清理了之前的状态
   - 观察结果数是否被重置

### 测试报告

完整测试套件会生成详细的测试报告：
- 控制台输出：测试执行过程和总结
- JSON报告：`test_code_agent_workflow_report.json`

## 自定义测试

### 创建自定义测试场景

```python
# 在 tests/test_code_agent_workflow.py 中添加
async def test_custom_scenario(self):
    """自定义测试场景"""
    test_input = {
        "messages": [{
            "role": "user",
            "content": "您的自定义测试提示"
        }],
        "locale": "zh-CN"
    }
    
    return await self.run_workflow_test("custom_scenario", test_input)
```

### 触发反思的测试提示示例

以下类型的提示更容易触发反思功能：

1. **包含错误的代码**
   ```
   "创建一个Python脚本，但故意在其中留下一些错误，然后编写测试来发现并修复这些错误。"
   ```

2. **高要求的复杂项目**
   ```
   "创建一个生产级的Web应用，包含完整的测试、文档、部署配置和监控。"
   ```

3. **需要迭代改进的任务**
   ```
   "创建一个机器学习模型，如果性能不达标，需要优化算法和参数。"
   ```

## 调试和故障排除

### 常见问题

1. **测试超时**
   - 检查网络连接
   - 确认LLM服务配置正确
   - 增加最大步数限制

2. **反思功能未触发**
   - 使用更明确的问题场景
   - 检查prompt模板配置
   - 验证JSON解析逻辑

3. **状态清理问题**
   - 检查`_clear_report_state`函数
   - 验证状态更新逻辑

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能基准

### 预期性能指标

- **基本代码生成**: 5-15步完成
- **反思重新规划**: 10-25步完成
- **复杂项目**: 15-30步完成

### 成功率预期

- **简单任务**: >90%成功率
- **中等复杂度**: >80%成功率
- **复杂项目**: >70%成功率

## 持续改进

### 添加新测试用例

1. 识别新的反思触发场景
2. 在测试套件中添加对应用例
3. 验证反思逻辑的准确性
4. 更新文档和示例

### 优化反思逻辑

1. 分析失败的测试用例
2. 改进反思检查条件
3. 优化状态清理逻辑
4. 测试边界情况

## 结论

通过这些测试工具，您可以：
- 验证Code Agent的基本功能
- 演示反思功能的强大能力
- 识别和修复潜在问题
- 持续改进系统性能

定期运行这些测试有助于确保Code Agent的稳定性和可靠性。 