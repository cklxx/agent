# Scripts 目录

这个目录包含了项目的各种脚本文件，按照功能进行了分类整理。

## 目录结构

```
scripts/
├── README.md                    # 本说明文件
├── code_agent_cli.py           # 完整版CLI工具（带任务规划）
├── code_agent_simple_cli.py    # 简化版CLI工具（推荐使用）
├── demo_code_agent_cli.py      # 功能演示脚本
└── utils/                      # 工具脚本目录（预留）
```

## 主要脚本说明

### 1. code_agent_simple_cli.py（推荐）
**简化版Code Agent CLI工具**

- 🎯 **用途**: 日常使用的智能编程助手
- 🚀 **特性**: 
  - 交互式任务选择界面
  - 支持代码生成、分析、修改、自动化
  - 直接集成LLM配置
  - 完整的工具调用支持

- 📖 **使用方法**:
  ```bash
  # 从项目根目录运行
  ./code_agent                                    # 交互式模式
  ./code_agent --task "创建一个Python计算器"      # 直接执行任务
  ./code_agent --debug                           # 调试模式
  
  # 或者直接运行脚本
  cd scripts
  uv run python code_agent_simple_cli.py
  ```

### 2. code_agent_cli.py
**完整版CLI工具**

- 🎯 **用途**: 复杂任务的规划和执行
- 🚀 **特性**:
  - 任务规划和分解功能
  - 多轮执行和状态管理
  - 更详细的执行报告

- 📖 **使用方法**:
  ```bash
  cd scripts
  uv run python code_agent_cli.py
  ```

### 3. demo_code_agent_cli.py
**功能演示脚本**

- 🎯 **用途**: 展示Code Agent的各项能力
- 🚀 **演示内容**:
  - 代码生成功能
  - 文件分析功能
  - 任务自动化
  - 多轮交互

- 📖 **使用方法**:
  ```bash
  cd scripts
  uv run python demo_code_agent_cli.py
  ```

## 快速开始

1. **确保环境配置正确**:
   - 已安装uv包管理器
   - 已配置LLM API密钥（conf.yaml）
   - 已运行 `uv sync` 安装依赖

2. **启动CLI工具**:
   ```bash
   # 最简单的方式（从项目根目录）
   ./code_agent
   
   # 或者
   cd scripts
   uv run python code_agent_simple_cli.py
   ```

3. **选择任务类型**:
   - 📝 代码生成 - 创建新的代码文件
   - 🔍 代码分析 - 分析现有代码结构  
   - ✏️ 代码修改 - 修改现有代码
   - ⚡ 任务自动化 - 执行复杂的自动化任务
   - 💬 自定义任务 - 描述具体需求

## 开发说明

### 添加新脚本
1. 将脚本文件放入相应的目录
2. 如果需要导入src模块，添加路径配置：
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```

### 脚本分类
- **CLI工具**: 直接放在scripts/目录下
- **测试脚本**: 放在项目根目录的tests/目录下
- **工具脚本**: 放在scripts/utils/目录下

## 故障排除

### 常见问题

1. **导入错误**:
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   - 确保从正确的目录运行脚本
   - 使用项目根目录的 `./code_agent` 启动脚本

2. **权限错误**:
   ```
   Permission denied: ./code_agent
   ```
   - 运行 `chmod +x code_agent` 添加可执行权限

3. **依赖错误**:
   ```
   ModuleNotFoundError: No module named 'InquirerPy'
   ```
   - 运行 `uv sync` 安装所有依赖

### 获取帮助

```bash
# 查看启动脚本帮助
./code_agent --help

# 查看CLI详细帮助
cd scripts
uv run python code_agent_simple_cli.py --help
```

---

🎉 享受使用 Code Agent 进行智能编程！ 