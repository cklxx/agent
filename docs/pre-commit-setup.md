# Git 提交时自动格式化设置

## 概述

项目已配置Git pre-commit hook，在每次提交时自动使用Black格式化Python代码，确保代码风格的一致性。

## 配置详情

### 格式化工具配置
- **工具**: Black (Python代码格式化工具)
- **行长度**: 88个字符
- **目标Python版本**: 3.12+
- **配置文件**: `pyproject.toml`

### Pre-commit Hook流程
1. **自动格式化**: 运行 `make format` 使用Black格式化所有Python文件
2. **重新暂存**: 将格式化后的文件重新添加到Git暂存区
3. **检查验证**: 运行 `make lint` 确保代码格式正确
4. **提交验证**: 如果所有检查通过，允许提交；否则阻止提交

### 相关命令
```bash
# 手动格式化代码
make format

# 检查代码格式
make lint

# 安装开发依赖（包含Black）
make install-dev
```

## 文件结构

```
.
├── pre-commit              # Pre-commit脚本源文件
├── .git/hooks/pre-commit   # Git hook（自动生成）
├── pyproject.toml          # Black配置
└── Makefile               # 格式化和检查命令
```

## 使用方式

### 正常提交流程
```bash
git add .
git commit -m "提交信息"
```

提交时会自动：
1. 格式化代码
2. 重新暂存格式化后的文件  
3. 验证格式正确性
4. 如果通过验证，完成提交

### 如果提交失败
如果pre-commit hook检测到无法自动修复的问题：
1. 查看错误信息
2. 手动修复问题
3. 重新提交

## 注意事项

1. **自动格式化**: 代码会在提交时自动格式化，无需手动运行Black
2. **暂存区更新**: 格式化后的文件会自动重新添加到暂存区
3. **提交阻止**: 如果格式化失败或检查不通过，提交会被阻止
4. **团队协作**: 确保团队所有成员都使用相同的格式化配置

## 故障排除

### 如果pre-commit hook未生效
```bash
# 重新安装hook
cp pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### 如果Black未安装
```bash
# 安装开发依赖
uv pip install -e ".[dev]"
```

### 跳过pre-commit检查（不推荐）
```bash
git commit -m "提交信息" --no-verify
``` 