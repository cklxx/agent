# Execute Prompt Claude 风格优化实现

## 概述

借鉴 Claude Code prompt 的优秀设计理念，对 `src/prompts/execute.md` 进行了极致简化和优化，实现了更高效、更直接的任务执行体验。

## Claude Prompt 设计理念学习

### 核心特点分析
1. **极致简洁**：输出限制在4行以内，避免冗余解释
2. **直接行动**：立即执行任务，不要前言后语
3. **并发优化**：鼓励并行工具调用以提高效率
4. **约定遵循**：理解并遵循现有代码风格和模式
5. **立即验证**：代码修改后必须立即测试

### 具体学习要点
```markdown
# Claude 的输出规则
- MUST answer concisely with fewer than 4 lines
- NO preamble or postamble
- Direct answers: "4" not "The answer is 4"
- Avoid "Based on...", "Here is...", "I will..."
- One word answers are best when possible
```

## 重构对比

### 原版问题（246行）
- 冗长详细（246行 → 82行）
- 重复解释过多
- 输出格式复杂
- 过度说明工具使用

### 优化后特点（82行）
- **压缩 66%**：从246行压缩到82行
- **强制简洁**：最多3行输出，无例外
- **立即行动**：去除所有解释性内容
- **核心聚焦**：只保留最关键的执行指导

## 主要改进

### 1. 极简标题和说明
```markdown
# 原版
# Execute Node - Task Execution Specialist
You are a skilled execution agent responsible for...

# 优化后  
# Execute Agent - Direct Task Execution
Execute tasks efficiently with minimal output. Focus on action, not explanation.
```

### 2. 强制输出限制
```markdown
# 原版
**CRITICAL: Provide concise, essential-information-only responses...**

# 优化后
**CRITICAL OUTPUT RULE: Maximum 3 lines of text. No explanations unless requested.**
```

### 3. 工具列表精简
```markdown
# 原版（分类详述）
### File System Operations
- **view_file(file_path)**: Read file contents (supports relative paths)
- **list_files(path)**: List directory contents...

# 优化后（单行列举）
- **view_file(path)**, **list_files(path)**, **glob_search(pattern, path)**, **grep_search(pattern, path)**
- **edit_file(path, old, new)** (PREFERRED), **replace_file(path, content)**
```

### 4. 核心工作流简化
```markdown
# 原版（多段详述）
#### Step 1: Understanding & Analysis
- Analyze the step description carefully
- Use `think()` to log your approach...

# 优化后（单行要点）
## Core Workflow
1. **Understand** → **Modify** → **Test Immediately** → **Report**
2. **Use parallel tool calls** when possible
```

### 5. 标准模式压缩
```markdown
# 原版（5个详细模式，50+行）
### Code Modification Pattern (STANDARD WORKFLOW)
### New Feature Implementation Pattern
### Bug Fix Pattern
### Research and Implementation Pattern

# 优化后（1个核心模式，5行）
## Code Modification Pattern (STANDARD)
```
1. view_file(target) + grep_search(pattern) // understand current state
2. edit_file(target, old_code, new_code) // make changes  
3. bash_command("python -m py_compile target") // test syntax
4. bash_command("python target") // test functionality
5. bash_command("python -m pytest tests/") // run tests
```
```

### 6. 输出格式极简化
```markdown
# 原版
[COMPLETED/FAILED/PARTIAL] Task: [title]
Results: [key finding 1], [test result], [key finding 2]
Issues: [if any]
Files: [modified files with test status]

# 优化后
[STATUS] Task: [brief title]
Result: [key outcome], [test status]  
Files: [changed files]
```

### 7. 实例演示优化
```markdown
# 原版（详细步骤说明）
**Step**: "Add error handling to the file processor function"
**Execution**: [5行详细步骤]
**Output**: [4行详细输出]

# 优化后（直接对比）
**Task**: Add error handling to process_file()
**Execution**: view_file → edit_file → bash_command test → output
**Output**: [3行简洁输出]
```

## 技术实现细节

### 核心原则贯彻
1. **行动导向**：删除所有理论说明，只保留执行指导
2. **模板化**：提供标准化的执行模式
3. **强制简洁**：硬性限制输出长度
4. **测试强制**：明确要求立即测试

### 关键规则强化
```markdown
## Critical Rules
- **Never explain your approach** unless asked
- **Always test immediately** after code changes  
- **Use edit_file over replace_file** for safety
- **Make parallel tool calls** when independent
- **Follow existing code style and patterns**
- **Maximum 3 lines output** - be direct and concise
- **No preamble or postamble** - just results
```

### 结尾强化
```markdown
# 原版结尾（说教式）
Remember: **Always modify code with edit_file/replace_file and immediately test...**

# 优化后（命令式）
Execute tasks directly. Test immediately. Report concisely.
```

## 效果预期

### 1. **大幅提升效率**
- Token 消耗减少 60-70%
- 执行速度显著提升
- 专注于核心任务

### 2. **减少冗余输出**
- 消除不必要的解释
- 直接报告关键结果
- 遵循3行输出限制

### 3. **标准化执行流程**
- 统一的代码修改模式
- 强制的测试要求
- 一致的输出格式

### 4. **保持质量标准**
- 保留所有关键安全检查
- 维持测试覆盖要求
- 确保代码质量验证

## 向 Claude 学习的收获

1. **简洁胜过详尽**：过多解释反而降低效率
2. **行动胜过说明**：直接执行比描述执行更有价值  
3. **标准化模式**：重复的工作流应该模板化
4. **强制约束**：硬性规则比软性建议更有效
5. **用户体验优先**：优化 AI 输出就是优化用户体验

这次优化完全体现了 Claude Code 的设计哲学：**最少的话，最直接的行动，最好的结果**。 