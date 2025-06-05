# Code Agent CLI - 智能编程助手

## 概述

Code Agent CLI 是一个基于大模型驱动的智能编程助手命令行工具。它能够理解自然语言的编程需求，自动生成代码、分析现有代码、执行复杂的编程任务，并提供安全的文件操作和命令行集成。

## 功能特性

### 🤖 智能代码生成
- 根据自然语言描述生成完整的代码文件
- 支持多种编程语言和框架
- 自动添加错误处理和最佳实践

### 🔍 代码分析与重构
- 分析现有代码的结构和质量
- 提供代码优化建议
- 支持代码重构和改进

### ⚡ 任务自动化
- 创建自动化脚本和工具
- 生成测试代码和文档
- 支持复杂的项目管理任务

### 🛡️ 安全可靠
- 自动文件备份机制
- 安全的命令行执行
- 路径和权限验证

## 安装和配置

### 前提条件
- Python 3.8+
- UV 包管理器
- 配置有效的LLM API密钥

### 快速开始

1. **克隆项目并安装依赖**
   ```bash
   git clone <repository>
   cd agent
   uv sync
   ```

2. **配置LLM**
   - 复制 `conf.yaml.example` 到 `conf.yaml`
   - 配置你的LLM API密钥和模型设置

3. **启动CLI**
   ```bash
   # 交互式模式
   uv run python code_agent_simple_cli.py
   
   # 直接执行任务
   uv run python code_agent_simple_cli.py --task "创建一个Python脚本"
   ```

## 使用方法

### 命令行参数

```bash
uv run python code_agent_simple_cli.py [选项]

选项:
  --task TASK, -t TASK     直接指定要执行的编程任务
  --debug, -d             启用调试模式，显示详细错误信息
  --version, -v           显示版本信息
  --help, -h              显示帮助信息
```

### 交互式模式

启动后选择任务类型：

1. **📝 代码生成** - 创建新的代码文件
2. **🔍 代码分析** - 分析现有代码结构
3. **✏️ 代码修改** - 修改现有代码
4. **⚡ 任务自动化** - 执行复杂的自动化任务
5. **💬 自定义任务** - 描述具体需求

### 示例用法

#### 1. 代码生成示例
```bash
uv run python code_agent_simple_cli.py --task "创建一个Python脚本，实现JSON文件的读取和写入功能，包含错误处理"
```

#### 2. 代码分析示例
```bash
uv run python code_agent_simple_cli.py --task "分析main.py文件的代码结构，提供优化建议"
```

#### 3. 自动化任务示例
```bash
uv run python code_agent_simple_cli.py --task "创建一个备份脚本，自动备份重要文件到指定目录"
```

## 可用工具

Code Agent CLI 内置了以下工具：

### 文件操作工具
- `read_file` - 读取文件内容
- `write_file` - 写入文件（自动备份）
- `get_file_info` - 获取文件信息
- `generate_file_diff` - 生成文件差异

### 目录操作工具
- `list_directory_contents` - 列出目录内容
- `get_current_directory` - 获取当前目录

### 命令行工具
- `execute_terminal_command` - 安全执行命令行命令

## 高级功能

### 多轮对话
CLI支持多轮对话，可以基于前面的结果继续优化和改进：

```bash
# 第一轮：创建基础功能
"创建一个计算器程序"

# 第二轮：添加功能
"为计算器添加历史记录功能"

# 第三轮：优化
"添加单元测试和错误处理"
```

### 项目分析
自动分析项目结构，生成文档和报告：

```bash
uv run python code_agent_simple_cli.py --task "分析当前项目结构，生成技术文档"
```

### 自动化测试
生成测试代码和测试脚本：

```bash
uv run python code_agent_simple_cli.py --task "为现有代码生成完整的单元测试"
```

## 功能演示

运行完整功能演示：

```bash
uv run python demo_code_agent_cli.py
```

这将展示：
- 代码生成能力
- 文件分析功能
- 任务自动化
- 多轮交互

## 安全性说明

### 文件安全
- 所有文件修改前都会自动创建备份
- 限制文件操作范围，防止系统文件被误修改
- 支持文件编码检测和安全验证

### 命令执行安全
- 只允许执行白名单中的安全命令
- 禁止执行危险的系统命令
- 支持命令超时和错误处理

## 故障排除

### 常见问题

1. **LLM API错误**
   - 检查 `conf.yaml` 中的API密钥配置
   - 验证网络连接和API服务状态

2. **权限错误**
   - 确保有足够的文件读写权限
   - 检查目录访问权限

3. **依赖问题**
   - 运行 `uv sync` 重新安装依赖
   - 检查Python版本兼容性

### 调试模式

启用调试模式获取详细信息：

```bash
uv run python code_agent_simple_cli.py --debug --task "你的任务"
```

## 开发和扩展

### 添加新工具
在 `src/tools/` 目录下添加新的工具模块，并在CLI中注册。

### 自定义提示
修改 `src/prompts/code_agent.md` 来自定义AI助手的行为。

### 扩展LLM支持
在 `src/llms/` 中添加新的LLM提供商支持。

## 版本信息

- **当前版本**: 1.0.0
- **最后更新**: 2025-06-05
- **支持的Python版本**: 3.8+

## 许可证

本项目使用 MIT 许可证。详见 LICENSE 文件。

---

🎉 享受使用 Code Agent CLI 进行智能编程！如有问题请提交 Issue 或贡献 Pull Request。 