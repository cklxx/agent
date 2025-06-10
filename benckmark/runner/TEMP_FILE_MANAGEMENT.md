# 临时文件管理系统

## 概述

为了更好地管理测试过程中生成的临时文件，我们实现了统一的临时文件管理系统。所有测试生成的文件现在都会集中存放在 `temp_generated/` 目录中，便于统一管理和清理。

## 目录结构

```
benckmark/runner/
├── temp_generated/          # 🆕 统一的临时文件目录
│   ├── sandbox/            # 沙箱执行环境
│   │   └── task_*_*/       # 每个任务的独立沙箱
│   └── generated_code/     # 生成的代码文件
│       ├── *.py           # Python 代码文件
│       ├── *.js           # JavaScript 代码文件
│       ├── *.html         # HTML 文件
│       └── *.css          # CSS 文件
├── reports/                # 测试报告（保留）
├── config/                 # 配置文件（保留）
├── levels/                 # 测试级别定义（保留）
├── domains/                # 测试领域定义（保留）
└── utils/                  # 工具模块（保留）
```

## 新特性

### 🎯 统一临时文件管理
- **集中存储**: 所有临时文件都放在 `temp_generated/` 目录
- **分类管理**: 代码文件和沙箱环境分别存储
- **命名规范**: 生成的代码文件使用 `{task_id}_{level}_{domain}.{ext}` 格式

### 🧹 简化清理操作
- **一键清理**: 直接删除整个 `temp_generated/` 目录
- **保留核心**: 不影响测试框架和配置文件
- **智能保留**: 自动保留最新的测试报告和日志

### 📁 文件命名示例
```
temp_generated/
├── generated_code/
│   ├── beginner_mobile_weather_app_beginner_mobile_development.py
│   ├── intermediate_web_todo_app_intermediate_web_development.html
│   └── advanced_ml_recommendation_advanced_data_science.py
└── sandbox/
    ├── task_beginner_mobile_weather_app_1734567890/
    └── task_intermediate_web_todo_app_1734567891/
```

## 使用方法

### 运行测试
测试照常运行，临时文件会自动保存到新的目录结构中：
```bash
python test_runner.py --level beginner --enable-rag --output json
```

### 清理临时文件
使用升级后的清理脚本：
```bash
python cleanup.py
```

清理脚本会：
- ✅ 删除整个 `temp_generated/` 目录
- ✅ 清理 Python 缓存文件
- ✅ 保留最新的 5 个测试报告
- ✅ 保留最新的 10 个日志文件

### 手动清理
如果只想清理临时文件：
```bash
rm -rf temp_generated/
```

## 配置选项

在 `test_runner.py` 中，可以自定义临时文件目录：

```python
# 在 BenchmarkTestRunner.__init__ 中
self.temp_dir = self.base_dir / "temp_generated"  # 可以修改为其他名称
self.sandbox_dir = self.temp_dir / "sandbox"
self.generated_code_dir = self.temp_dir / "generated_code"
```

## 优势

### ✅ 更好的组织性
- 临时文件不再散布在项目各处
- 清晰的目录结构，易于理解和维护
- 测试框架文件与临时文件完全分离

### ✅ 更简单的清理
- 一个命令即可清理所有临时文件
- 不用担心误删重要文件
- 清理过程有详细的日志和统计

### ✅ 更好的可维护性
- 便于 CI/CD 流水线中的清理操作
- 支持版本控制忽略临时文件
- 减少项目体积和噪音

## 迁移说明

### 从旧版本迁移
如果您之前使用过旧版本的测试框架：

1. **自动迁移**: 新版本会自动创建 `temp_generated/` 目录
2. **清理旧文件**: 运行 `python cleanup.py` 清理旧的散布文件
3. **更新 .gitignore**: 添加 `temp_generated/` 到忽略列表

### 推荐的 .gitignore 配置
```gitignore
# Benchmark临时文件
benckmark/runner/temp_generated/

# 旧的临时文件模式（可以删除）
benckmark/runner/sandbox/
benckmark/runner/*.py  # 生成的代码文件
benckmark/runner/*.js
benckmark/runner/*.html
benckmark/runner/*.css
```

## 故障排除

### 问题：权限错误
```bash
# 确保有写入权限
chmod 755 benckmark/runner/
```

### 问题：目录创建失败
```bash
# 手动创建目录
mkdir -p benckmark/runner/temp_generated/{sandbox,generated_code}
```

### 问题：清理失败
```bash
# 强制清理
sudo rm -rf benckmark/runner/temp_generated/
```

## 技术细节

### 实现原理
- 在 `BenchmarkTestRunner.__init__()` 中创建统一的临时目录
- 在 `_simulate_code_generation()` 中保存生成的代码文件
- 在 `run_single_task()` 中创建任务专用的沙箱目录

### 代码改动
主要改动在 `test_runner.py` 文件中：
- 增加了 `temp_dir` 和 `generated_code_dir` 属性
- 修改了代码文件保存逻辑
- 更新了目录创建逻辑

---

💡 **提示**: 这个新的文件管理系统让测试环境更加整洁，维护更加简单。建议在每次重要测试后运行清理脚本来保持环境干净。 