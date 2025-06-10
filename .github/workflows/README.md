# GitHub Actions工作流程文档

本目录包含了Code Agent项目的所有CI/CD工作流程配置。

## 📋 工作流程概览

### 1. 代码质量检查

#### `lint.yaml` - 代码规范检查
- **触发**: Push和Pull Request
- **功能**: 代码格式化和静态分析检查
- **工具**: black, flake8, mypy等

#### `unittest.yaml` - 单元测试
- **触发**: Push到main分支，所有Pull Request
- **功能**: 运行完整测试套件并生成覆盖率报告
- **要求**: 测试覆盖率 ≥ 25%
- **产物**: HTML覆盖率报告

### 2. 构建和发布

#### `build-and-release.yaml` - 主要构建流程
- **触发**: 
  - Push到main分支 (开发构建)
  - 版本标签推送 (正式发布)
  - Pull Request (测试构建)
  - 手动触发 (可选发布)
- **平台**: Linux x86_64, Windows x86_64, macOS x86_64/ARM64
- **流程**: 测试 → 构建 → 验证 → 打包 → 发布

#### `quick-build.yaml` - 快速开发构建
- **触发**: 手动触发
- **用途**: 开发时快速测试单个平台构建
- **选项**: 可选择平台和跳过测试

## 🚀 使用指南

### 自动触发

1. **日常开发**: 
   ```bash
   git push origin feature-branch  # 触发测试
   ```

2. **合并到main**:
   ```bash
   git checkout main
   git merge feature-branch
   git push origin main  # 触发完整构建
   ```

3. **发布版本**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0  # 触发发布流程
   ```

### 手动触发

1. **访问GitHub Actions页面**
2. **选择工作流程**:
   - `Build and Release`: 完整构建和可选发布
   - `Quick Build (Dev)`: 快速单平台构建
3. **点击"Run workflow"并配置参数**

### 下载构建产物

#### 开发构建
```bash
# 使用GitHub CLI
gh run list --workflow="build-and-release.yaml"
gh run download [RUN_ID]

# 或通过网页界面下载Artifacts
```

#### 正式发布
- 直接从GitHub Releases页面下载
- 包含完整发布包和校验和文件

## 🛠️ 工作流程详解

### 构建阶段

1. **环境准备**
   - 安装UV和Python 3.12
   - 安装项目依赖和PyInstaller

2. **质量检查**
   - 运行完整测试套件
   - 确保代码质量达标

3. **构建执行**
   - 使用PyInstaller打包成单文件可执行程序
   - 包含所有必要的依赖和数据文件

4. **构建验证**
   - 测试可执行文件基本功能
   - 验证帮助命令和基本选项

5. **产物打包**
   - 创建包含文档的完整发布包
   - 生成压缩文件 (.tar.gz/.zip)

### 发布阶段

1. **版本检测**
   - 检查是否为版本标签
   - 生成版本号和发布名称

2. **资产准备**
   - 收集所有平台的构建产物
   - 生成SHA256校验和文件

3. **创建发布**
   - 自动生成发布说明
   - 上传所有平台的安装包
   - 标记正式版本或预发布

## 📊 构建矩阵

| 平台 | 系统版本 | 架构 | 输出文件 |
|------|----------|------|----------|
| Linux | ubuntu-latest | x86_64 | code_agent-linux-x86_64.tar.gz |
| Windows | windows-latest | x86_64 | code_agent-windows-x86_64.zip |
| macOS Intel | macos-latest | x86_64 | code_agent-macos-x86_64.tar.gz |
| macOS Apple Silicon | macos-14 | arm64 | code_agent-macos-arm64.tar.gz |

## 🔧 配置说明

### 环境变量
```yaml
env:
  PYTHON_VERSION: "3.12"     # Python版本
  TAVILY_API_KEY: "mock-key" # 测试用API密钥
```

### 关键步骤

#### 依赖安装
```yaml
- name: Install dependencies
  run: |
    uv venv --python ${{ env.PYTHON_VERSION }}
    uv pip install -e ".[dev]"
    uv add --dev pyinstaller
```

#### 构建命令
```yaml
- name: Build executable
  run: |
    uv run python packaging/build.py
```

#### 产物上传
```yaml
- name: Upload build artifacts
  uses: actions/upload-artifact@v4
  with:
    name: ${{ steps.package_name.outputs.package_name }}
    path: dist/${{ steps.package_name.outputs.package_name }}.*
    retention-days: 30
```

## 🐛 故障排除

### 常见问题

1. **测试失败**
   - 检查代码更改是否破坏现有功能
   - 查看测试日志确定失败原因
   - 本地运行 `make test` 复现问题

2. **构建失败**
   - 检查依赖是否正确安装
   - 查看PyInstaller的隐藏导入警告
   - 确保 `packaging/build.py` 配置正确

3. **发布失败**
   - 检查版本标签格式 (必须是 v*.*)
   - 确保所有平台构建成功
   - 检查GitHub token权限

### 调试技巧

1. **本地复现**
   ```bash
   # 复现构建环境
   uv sync
   uv add --dev pyinstaller
   uv run python packaging/test_build.py
   uv run python packaging/build.py
   ```

2. **查看详细日志**
   - 在GitHub Actions页面展开失败的步骤
   - 查看完整的错误输出和堆栈跟踪

3. **使用act本地测试**
   ```bash
   # 安装act并测试工作流程
   brew install act
   act -j build --platform ubuntu-latest=node:16-buster-slim
   ```

## 📈 性能优化

### 缓存策略
- UV依赖缓存: 加速依赖安装
- PyInstaller缓存: 加速重复构建
- 构建产物缓存: 减少重复工作

### 并行构建
- 多平台并行构建
- 测试和构建分离
- 失败快速退出 (fail-fast: false)

### 资源管理
- 合理的artifact保留期
- 按需下载构建产物
- 清理临时文件

## 🔄 维护建议

1. **定期更新**
   - 更新GitHub Actions版本
   - 更新Python和依赖版本
   - 检查安全漏洞和修复

2. **监控构建时间**
   - 跟踪构建性能
   - 优化慢步骤
   - 调整缓存策略

3. **测试覆盖率**
   - 维持测试覆盖率要求
   - 添加关键功能的测试
   - 定期审查测试质量

---

需要更多帮助请查看:
- [GitHub Actions文档](https://docs.github.com/en/actions)
- [PyInstaller文档](https://pyinstaller.readthedocs.io/)
- [UV文档](https://docs.astral.sh/uv/) 