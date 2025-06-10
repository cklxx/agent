# Code Agent PyInstaller 打包方案 (UV版本)

这个目录包含了将 Code Agent Python 应用打包成二进制可执行文件的完整方案，使用 UV 作为包管理器。

## 📁 文件结构

```
packaging/
├── README.md                 # 本说明文档
├── pyinstaller.spec         # PyInstaller 配置文件（备用）
├── build.py                 # Python 构建脚本（主要）
└── test_build.py            # 构建环境测试脚本
```

## 🚀 快速开始

### 前提条件

1. **安装 UV**：https://docs.astral.sh/uv/getting-started/installation/
2. **Python 3.12+** 已安装

### 一键构建

```bash
# 1. 同步环境和安装依赖
uv sync
uv add --dev pyinstaller

# 2. 执行构建
uv run python packaging/build.py
```

### 构建产物

构建成功后，在 `dist/` 目录下会生成：

- `code_agent` - 可执行文件 (~65MB)
- `code_agent-{系统}-{架构}/` - 发布包目录
- `code_agent-{系统}-{架构}.zip` - 压缩的发布包

## 🔧 构建特性

### 自动化功能

- ✅ **环境检查** - 自动检查 UV、PyInstaller 和项目依赖
- ✅ **清理构建** - 自动清理之前的构建文件
- ✅ **单文件打包** - 生成单个可执行文件，无需额外依赖
- ✅ **数据文件包含** - 自动包含配置文件和源码目录
- ✅ **隐藏导入** - 自动处理 LangChain、FastAPI 等复杂依赖
- ✅ **可执行文件测试** - 构建后自动测试可执行文件
- ✅ **发布包创建** - 自动创建包含 README 和配置的发布包

### 支持的平台

- ✅ **macOS** (Intel/Apple Silicon)
- ✅ **Linux** (x86_64/ARM64)
- ✅ **Windows** (x86_64)

## 📦 使用生成的可执行文件

```bash
# 查看帮助
./dist/code_agent --help

# 交互模式
./dist/code_agent --interactive

# 直接查询
./dist/code_agent "你的问题"

# 调试模式
./dist/code_agent --debug "你的问题"
```

## 🛠️ 高级配置

### 自定义构建参数

编辑 `packaging/build.py` 中的 `build_executable()` 函数来自定义：

- 添加更多隐藏导入
- 包含额外的数据文件
- 修改可执行文件名称
- 启用/禁用 UPX 压缩

### 环境变量

- `PYINSTALLER_COMPILE_BOOTLOADER` - 编译自定义 bootloader
- `PYINSTALLER_CONFIG_DIR` - 指定配置目录

## 🐛 故障排除

### 常见问题

1. **模块找不到错误**
   - 在 `build.py` 中添加 `--hidden-import` 参数

2. **文件大小过大**
   - 在 `excludes` 列表中添加不需要的模块
   - 启用 UPX 压缩（需要单独安装 UPX）

3. **运行时错误**
   - 检查数据文件路径是否正确
   - 使用 `--debug` 模式查看详细错误

### 调试技巧

```bash
# 查看构建警告
cat build/code_agent/warn-code_agent.txt

# 查看依赖关系图
open build/code_agent/xref-code_agent.html

# 测试构建环境
uv run python packaging/test_build.py
```

## 📈 性能优化

### 减小文件大小

1. **排除不需要的模块**：
   ```python
   excludes = ['tkinter', 'matplotlib', 'jupyter', 'pytest']
   ```

2. **启用 UPX 压缩**：
   ```bash
   # 安装 UPX
   brew install upx  # macOS
   # 然后在构建参数中添加 --upx-dir
   ```

3. **使用 --strip** 参数移除调试信息

### 提升启动速度

1. 使用 `--onedir` 模式而不是 `--onefile`
2. 预编译 Python 字节码
3. 优化导入路径

## 🔄 CI/CD 集成

本项目已经集成了完整的GitHub Actions工作流程，支持自动化构建和发布。

### 工作流程概览

#### 1. 主要构建工作流程 (build-and-release.yaml)

**触发条件:**
- 推送到 `main` 分支
- 创建版本标签 (v*)
- Pull Request 到 `main` 分支
- 手动触发 (可选择创建发布)

**功能特性:**
- ✅ **多平台构建**: Linux x86_64, Windows x86_64, macOS x86_64/ARM64
- ✅ **自动测试**: 构建前运行完整测试套件
- ✅ **构建验证**: 自动测试生成的可执行文件
- ✅ **智能打包**: 自动创建包含文档的发布包
- ✅ **自动发布**: 标签推送时自动创建GitHub Release
- ✅ **构建摘要**: 详细的构建状态报告

**输出产物:**
- 单个可执行文件 (约65MB)
- 完整发布包 (.tar.gz/.zip)
- 校验和文件 (checksums.txt)

#### 2. 快速构建工作流程 (quick-build.yaml)

**用途**: 开发时快速测试单个平台构建

**特性:**
- 🚀 **选择平台**: 手动选择要构建的平台
- ⚡ **跳过测试**: 可选择跳过测试以加快构建
- 📦 **快速下载**: 短期保留构建产物 (3天)

### 使用方法

#### 自动构建

1. **开发构建**: 推送到main分支触发完整构建流程
2. **PR测试**: 创建PR时自动构建和测试
3. **版本发布**: 推送版本标签 (如 `v1.0.0`) 自动创建Release

```bash
# 创建版本标签并推送
git tag v1.0.0
git push origin v1.0.0
```

#### 手动构建

1. **完整构建**: 在Actions页面手动触发 "Build and Release"
2. **快速构建**: 选择平台进行快速测试构建

### 工作流程详细配置

#### 环境配置
```yaml
env:
  PYTHON_VERSION: "3.12"
```

#### 构建矩阵
```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - os: ubuntu-latest
        platform: linux
        arch: x86_64
      - os: windows-latest
        platform: windows
        arch: x86_64
      - os: macos-latest
        platform: macos
        arch: x86_64
      - os: macos-14
        platform: macos
        arch: arm64
```

#### 自动发布配置
- **标签匹配**: `v*` 格式的标签触发正式发布
- **预发布**: 非标签构建标记为预发布
- **发布内容**: 自动生成发布说明和下载链接
- **校验和**: 自动生成SHA256校验文件

### 本地测试GitHub Actions

使用 [act](https://github.com/nektos/act) 在本地测试工作流程:

```bash
# 安装 act
brew install act  # macOS

# 测试构建工作流程
act -j build --platform ubuntu-latest=node:16-buster-slim

# 测试快速构建
act workflow_dispatch -j quick-build
```

### 故障排除

#### 常见构建错误

1. **依赖安装失败**
   - 检查 `pyproject.toml` 中的依赖配置
   - 确保所有可选依赖已正确定义

2. **PyInstaller构建失败**
   - 查看构建日志中的隐藏导入警告
   - 在 `packaging/build.py` 中添加缺失的模块

3. **可执行文件测试失败**
   - 检查 `--help` 命令是否正确实现
   - 确保所有必需的配置文件已包含

#### 调试技巧

```bash
# 查看工作流程状态
gh run list

# 下载构建产物
gh run download [run-id]

# 查看构建日志
gh run view [run-id] --log
```

### 发布管理

#### 版本命名规范
- **正式版本**: `v1.0.0`, `v1.1.0`, `v2.0.0`
- **预发布**: `v1.0.0-rc1`, `v1.0.0-beta1`
- **开发版本**: 自动生成 `dev-YYYYMMDD-HHMMSS`

#### 发布检查清单
- [ ] 更新版本号和变更日志
- [ ] 确保所有测试通过
- [ ] 检查构建配置和依赖
- [ ] 验证所有平台构建成功
- [ ] 测试下载的可执行文件

## 📝 版本信息

- **PyInstaller**: 6.14.0+
- **UV**: 0.7.8+
- **Python**: 3.12+
- **支持的架构**: x86_64, ARM64

## 🗂️ 数据库文件管理

**重要**: 所有临时数据库文件现在存储在 `temp/` 目录下：

- **Context数据库**: `temp/contexts.db`
- **RAG数据库**: `temp/rag_data/code_index.db`

这确保了：
- 项目根目录保持整洁
- 临时文件不会被误提交到版本控制
- 与项目的 `.gitignore` 配置保持一致

## 🤝 贡献

如果你发现问题或有改进建议，请：

1. 检查现有的 Issues
2. 创建新的 Issue 描述问题
3. 提交 Pull Request

---

**注意**: 生成的可执行文件包含了完整的 Python 运行时和所有依赖，因此文件较大（~65MB）是正常的。这确保了可执行文件可以在没有 Python 环境的机器上运行。 