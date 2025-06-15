# 工具测试指南

本文档介绍如何运行和维护项目中工具模块的单元测试。

## 📁 测试文件结构

```
tests/
├── test_workspace_tools.py      # Workspace工具测试
├── test_file_edit_tools.py      # 文件编辑工具测试
├── test_file_system_tools.py    # 文件系统工具测试
├── test_architect_tools.py      # 架构工具测试
├── test_bash_tool.py            # Bash工具测试
├── test_maps_tools.py           # 地图工具测试
├── test_tools.py                # 基础工具测试
├── conftest.py                  # pytest配置
└── ...                          # 其他测试文件
```

## 🚀 快速开始

### 运行所有工具测试

```bash
# 使用Python脚本
python scripts/run_all_tool_tests.py

# 使用Bash脚本
./scripts/test_tools.sh --all

# 使用pytest直接运行
pytest tests/test_*_tools.py -v
```

### 运行特定工具测试

```bash
# Workspace工具测试
./scripts/test_tools.sh --workspace

# 文件编辑工具测试
./scripts/test_tools.sh --file-edit

# 文件系统工具测试
./scripts/test_tools.sh --file-system

# 架构工具测试
./scripts/test_tools.sh --architect

# Bash工具测试
./scripts/test_tools.sh --bash

# 地图工具测试
./scripts/test_tools.sh --maps
```

### 快速测试模式

```bash
# 只运行基础测试
./scripts/test_tools.sh --quick

# 或使用Python脚本
python scripts/run_all_tool_tests.py --quick
```

## 🔧 测试脚本选项

### Bash脚本 (`scripts/test_tools.sh`)

| 选项 | 简写 | 描述 |
|------|------|------|
| `--all` | `-a` | 运行所有工具测试 |
| `--workspace` | `-w` | 运行workspace工具测试 |
| `--file-edit` | `-f` | 运行文件编辑工具测试 |
| `--file-system` | `-s` | 运行文件系统工具测试 |
| `--architect` | `-r` | 运行架构工具测试 |
| `--bash` | `-b` | 运行bash工具测试 |
| `--maps` | `-m` | 运行地图工具测试 |
| `--verbose` | `-v` | 详细输出 |
| `--quick` | `-q` | 快速测试（只运行基础测试） |
| `--help` | `-h` | 显示帮助信息 |

### Python脚本 (`scripts/run_all_tool_tests.py`)

| 选项 | 简写 | 描述 |
|------|------|------|
| `--pattern` | `-p` | 测试文件名模式过滤 |
| `--verbose` | `-v` | 详细输出 |
| `--quick` | `-q` | 快速模式（只运行基本测试） |

## 📊 测试覆盖范围

### Workspace工具测试 (`test_workspace_tools.py`)

- ✅ 路径解析功能
- ✅ 工具创建和配置
- ✅ 工作区感知功能
- ✅ 集成测试
- ✅ 错误处理
- ✅ 文档验证

**测试类:**
- `TestResolveWorkspacePath` - 路径解析测试
- `TestWorkspaceToolsCreation` - 工具创建测试
- `TestWorkspaceAwareToolsIntegration` - 集成测试
- `TestWorkspaceToolsErrorHandling` - 错误处理测试
- `TestWorkspaceToolsDocumentation` - 文档测试

### 文件编辑工具测试 (`test_file_edit_tools.py`)

- ✅ 文件创建和编辑
- ✅ 文本替换功能
- ✅ 编码处理
- ✅ 错误场景处理
- ✅ 复杂编辑场景
- ✅ 工作流测试

**测试类:**
- `TestEditFile` - edit_file工具测试
- `TestReplaceFile` - replace_file工具测试
- `TestFileEditToolsIntegration` - 集成测试

### 文件系统工具测试 (`test_file_system_tools.py`)

- ✅ 文件读取功能
- ✅ 目录列表功能
- ✅ Glob搜索功能
- ✅ Grep搜索功能
- ✅ 图像文件处理
- ✅ 大文件处理
- ✅ 编码支持

**测试类:**
- `TestViewFile` - view_file工具测试
- `TestListFiles` - list_files工具测试
- `TestGlobSearch` - glob_search工具测试
- `TestGrepSearch` - grep_search工具测试
- `TestFileSystemToolsIntegration` - 集成测试

### 架构工具测试 (`test_architect_tools.py`)

- ✅ 架构规划功能
- ✅ 代理分发功能
- ✅ 参数验证
- ✅ 特殊字符处理
- ✅ 并发使用
- ✅ 文档完整性

**测试类:**
- `TestArchitectPlan` - architect_plan工具测试
- `TestDispatchAgent` - dispatch_agent工具测试
- `TestArchitectToolsIntegration` - 集成测试
- `TestArchitectToolsDocumentation` - 文档测试

### Bash工具测试 (`test_bash_tool.py`)

- ✅ 基本命令执行
- ✅ 工作目录设置
- ✅ 命令超时处理
- ✅ 安全性检查
- ✅ 错误处理
- ✅ 复杂命令链

### 地图工具测试 (`test_maps_tools.py`)

- ✅ 位置搜索功能
- ✅ 路线规划功能
- ✅ 周边搜索功能
- ✅ API错误处理
- ✅ 数据模型验证
- ✅ 工作流测试

## 🛠️ 开发指南

### 添加新的工具测试

1. **创建测试文件**
   ```python
   # tests/test_new_tool.py
   #!/usr/bin/env python3
   # -*- coding: utf-8 -*-
   
   """
   New Tool 模块详细测试
   """
   
   import pytest
   from unittest.mock import patch, Mock
   import sys
   import os
   
   # 添加项目根目录到 Python 路径
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   
   from src.tools.new_tool import new_tool_function
   
   class TestNewTool:
       """测试new_tool_function工具"""
       
       def test_basic_functionality(self):
           """测试基本功能"""
           # 测试代码
           pass
   ```

2. **更新测试脚本**
   - 在 `scripts/test_tools.sh` 中添加新选项
   - 在 `scripts/run_all_tool_tests.py` 中添加新测试文件
   - 更新 `pytest.ini` 中的标记定义

3. **测试设计原则**
   - **全面性**: 覆盖正常情况、边界情况和异常情况
   - **独立性**: 每个测试应该独立运行
   - **可重复性**: 测试结果应该一致
   - **清晰性**: 测试意图应该明确

### 测试最佳实践

1. **使用Mock对象**
   ```python
   @patch('src.tools.my_tool.external_api_call')
   def test_with_mock(self, mock_api):
       mock_api.return_value = "expected_result"
       result = my_tool.func("test_input")
       assert result == "expected_result"
   ```

2. **测试数据管理**
   ```python
   def setUp(self):
       """设置测试环境"""
       self.temp_dir = tempfile.mkdtemp()
       
   def tearDown(self):
       """清理测试环境"""
       if os.path.exists(self.temp_dir):
           shutil.rmtree(self.temp_dir)
   ```

3. **参数化测试**
   ```python
   @pytest.mark.parametrize("input_value,expected", [
       ("input1", "output1"),
       ("input2", "output2"),
   ])
   def test_multiple_cases(self, input_value, expected):
       result = my_function(input_value)
       assert result == expected
   ```

## 🔍 调试测试

### 详细输出模式

```bash
# 获取详细的测试输出
./scripts/test_tools.sh --workspace --verbose

# 或使用pytest直接运行
pytest tests/test_workspace_tools.py -v -s
```

### 运行特定测试

```bash
# 运行特定测试类
pytest tests/test_workspace_tools.py::TestResolveWorkspacePath -v

# 运行特定测试方法
pytest tests/test_workspace_tools.py::TestResolveWorkspacePath::test_resolve_relative_path_with_workspace -v
```

### 调试失败的测试

```bash
# 显示完整的错误堆栈
pytest tests/test_file_edit_tools.py --tb=long

# 进入pdb调试模式
pytest tests/test_file_edit_tools.py --pdb
```

## 📈 持续集成

### 在CI/CD中运行测试

```yaml
# .github/workflows/test-tools.yml
name: Tool Tests

on: [push, pull_request]

jobs:
  test-tools:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install pytest
        pip install -r requirements.txt
    - name: Run tool tests
      run: python scripts/run_all_tool_tests.py --verbose
```

## 📝 测试报告

### 生成覆盖率报告

```bash
# 安装coverage工具
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest tests/test_*_tools.py --cov=src/tools --cov-report=html

# 查看HTML报告
open htmlcov/index.html
```

### 测试结果分析

测试脚本会自动生成测试结果统计：

```
📊 测试结果总结:
===============================
✅ tests/test_workspace_tools.py: PASSED
✅ tests/test_file_edit_tools.py: PASSED
✅ tests/test_file_system_tools.py: PASSED
✅ tests/test_architect_tools.py: PASSED
✅ tests/test_bash_tool.py: PASSED
⚠️ tests/test_maps_tools.py: SKIPPED

📈 测试统计:
   通过: 5
   失败: 0
   跳过: 1
   错误: 0
   总计: 6

🎉 所有测试通过!
```

## 🤝 贡献指南

1. **提交新测试时**:
   - 确保测试覆盖新功能的所有场景
   - 添加适当的文档字符串
   - 遵循现有的测试风格

2. **修复测试时**:
   - 理解测试失败的根本原因
   - 修复代码而不是降低测试标准
   - 添加回归测试防止问题重现

3. **性能考虑**:
   - 避免在测试中进行真实的网络请求
   - 使用临时文件和目录
   - 及时清理测试资源

---

**注意**: 本测试系统设计为简洁高效，重点关注工具功能的核心测试。如需更复杂的测试场景，请参考相应的集成测试文档。 