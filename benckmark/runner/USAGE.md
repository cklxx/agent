# AI Agent Benchmark 使用指南

## 快速开始

### 1. 环境设置

首先进入benchmark目录：

```bash
cd benckmark/runner
```

运行快速设置脚本：

```bash
chmod +x setup.sh
./setup.sh
```

或者手动安装依赖：

```bash
pip install -r requirements.txt
```

### 2. 运行演示

运行演示脚本了解系统功能：

```bash
python3 run_demo.py
```

这个演示会展示：
- 代码功能测试
- 代码质量分析
- 安全性检查
- 多维度评估
- 任务配置管理

### 3. 运行测试

#### 运行特定难度级别的测试：

```bash
# 入门级测试
python3 test_runner.py --level beginner

# 初级测试
python3 test_runner.py --level elementary

# 中级测试
python3 test_runner.py --level intermediate

# 高级测试
python3 test_runner.py --level advanced

# 专家级测试
python3 test_runner.py --level expert

# 大师级测试
python3 test_runner.py --level master
```

#### 运行特定技术领域的测试：

```bash
# 算法与数据结构
python3 test_runner.py --domain algorithms

# Web开发
python3 test_runner.py --domain web_development

# 移动应用开发
python3 test_runner.py --domain mobile_app

# DevOps与自动化
python3 test_runner.py --domain devops

# 数据科学与机器学习
python3 test_runner.py --domain data_science
```

#### 运行所有测试：

```bash
python3 test_runner.py --level all --domain all
```

#### 指定输出格式：

```bash
# 生成HTML报告
python3 test_runner.py --level beginner --output html

# 生成JSON报告
python3 test_runner.py --level beginner --output json
```

### 4. 查看结果

测试完成后，报告会保存在以下位置：

- JSON报告：`reports/benchmark_report_YYYYMMDD_HHMMSS.json`
- HTML报告：`reports/benchmark_report_YYYYMMDD_HHMMSS.html`
- 日志文件：`logs/benchmark.log`

### 5. 目录结构

```
benckmark/benchmark/
├── README.md                    # 项目总览
├── USAGE.md                     # 使用指南（本文件）
├── test_runner.py              # 主测试运行器
├── run_demo.py                 # 演示脚本
├── setup.sh                    # 快速设置脚本
├── requirements.txt            # Python依赖
├── config/                     # 配置文件
│   └── test_config.yaml        # 测试配置
├── levels/                     # 按难度级别的任务
│   ├── beginner/               # 入门级
│   ├── elementary/             # 初级
│   ├── intermediate/           # 中级
│   ├── advanced/               # 高级
│   ├── expert/                 # 专家级
│   └── master/                 # 大师级
├── domains/                    # 按技术领域的任务
│   ├── algorithms/             # 算法与数据结构
│   ├── web_development/        # Web开发
│   ├── mobile_app/             # 移动应用
│   ├── devops/                 # DevOps
│   └── data_science/           # 数据科学
├── utils/                      # 工具模块
│   ├── sandbox_manager.py      # 沙箱管理器
│   └── evaluator.py           # 代码评估器
├── test_data/                  # 测试数据
├── reports/                    # 测试报告
├── logs/                       # 日志文件
└── sandbox/                    # 代码执行沙箱
```

### 6. 任务示例

当前包含的测试任务：

#### 入门级 (Beginner)
- **温度转换器**: 实现摄氏度和华氏度相互转换
- **个人简历页面**: 创建HTML个人简历页面

#### 初级 (Elementary)  
- **搜索排序算法**: 实现线性搜索、二分搜索、冒泡排序、选择排序

#### 中级 (Intermediate)
- **全栈待办应用**: 完整的CRUD待办事项Web应用

#### 高级 (Advanced)
- **实时协作平台**: 多用户实时协作文档编辑系统

### 7. 自定义任务

如需添加自定义任务，请参考现有的YAML配置文件格式：

```yaml
id: "task_id"
level: "beginner|elementary|intermediate|advanced|expert|master"
domain: "algorithms|web_development|mobile_app|devops|data_science"
title: "任务标题"
description: "任务描述"
input_spec: 
  # 输入规范
output_spec:
  # 输出规范
evaluation_criteria:
  # 评估标准
test_cases:
  # 测试用例
time_limit: 300  # 超时时间（秒）
```

### 8. 故障排除

#### 常见问题：

1. **Python版本不兼容**
   - 确保使用Python 3.12或更高版本
   
2. **依赖安装失败**
   - 使用虚拟环境：`python3 -m venv venv && source venv/bin/activate`
   - 升级pip：`pip install --upgrade pip`
   
3. **权限错误**
   - 确保脚本有执行权限：`chmod +x setup.sh test_runner.py`
   
4. **沙箱执行失败**
   - 检查系统资源（内存、磁盘空间）
   - 查看日志文件：`tail -f logs/benchmark.log`

### 9. 扩展和开发

要扩展测试框架：

1. **添加新的评估维度**: 修改`utils/evaluator.py`
2. **增加安全检查规则**: 修改`utils/sandbox_manager.py`
3. **支持新的编程语言**: 扩展沙箱管理器
4. **集成AI Agent**: 修改`test_runner.py`中的代码生成部分

### 10. 贡献指南

如需贡献新的测试任务或功能：

1. Fork项目
2. 创建功能分支
3. 添加测试任务（按照YAML格式）
4. 更新文档
5. 提交Pull Request

更多详细信息请参考`README.md`文件。 