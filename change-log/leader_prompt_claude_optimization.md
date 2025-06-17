# Leader Prompt Claude 风格优化实现

## 概述

继续借鉴 Claude Code prompt 的极简设计理念，对 `src/prompts/leader.md` 进行大幅精简和优化，实现更高效的战略规划和决策制定。

## 优化对比

### 压缩效果
- **原版**：202行，冗长详细
- **优化后**：75行，压缩 62%
- **核心保留**：JSON 接口定义和关键决策逻辑

### 主要改进

#### 1. 极简角色定义
```markdown
# 原版
# Leader Node - Task Planning and Coordination
You are a strategic leader agent responsible for analyzing user requests and creating comprehensive execution plans...

# 优化后  
# Leader Agent - Strategic Planning
Analyze user requests and create execution plans. Generate final reports when sufficient context is available.
```

#### 2. 上下文信息压缩
```markdown
# 原版（多行分类）
**Environment Details:**
- {{ environment_info }}
- Workspace: {{workspace}}
- Locale: {{locale}}

**Available Context:**
{{context}}

# 优化后（单行集成）
{{environment_info}}
Workspace: {{workspace}} | Locale: {{locale}}
Context: {{context}}
```

#### 3. 输出格式简化
```markdown
# 原版
Directly output the raw JSON format of `Plan` without "```json". The `Plan` interface is defined as follows:

# 优化后
**Direct JSON output only. No markdown blocks.**
```

#### 4. 接口定义精简
```typescript
// 原版（详细注释）
interface Step {
  need_search: boolean; // Must be explicitly set for each step
  title: string;
  description: string; // Specify exactly what data to collect...
  step_type: "research" | "processing"; // Indicates the nature of the step
}

// 优化后（核心要素）
interface Step {
  need_search: boolean;
  title: string; 
  description: string;
  step_type: "execute";
}
```

#### 5. 决策逻辑压缩
```markdown
# 原版（详细解释，30+行）
### Context Assessment:
- Set `has_enough_context: true` when:
  - The task is clearly defined and actionable
  - Sufficient information has been gathered from previous observations
  - All necessary analysis has been completed
  - Ready to provide final conclusions and recommendations

# 优化后（要点列举，6行）
## Decision Logic

**Set has_enough_context=true when:**
- Task is clearly defined and actionable
- Sufficient observations gathered
- Ready for final conclusions
```

#### 6. 报告结构模板化
```markdown
# 原版（散文描述）
Your final report should include:
1. **Executive Summary**: Clear overview of findings and conclusions
2. **Key Insights**: Important discoveries and analysis results
...

# 优化后（直接模板）
## Report Structure (when has_enough_context=true)

```markdown
# [Title]

## 执行摘要
[Key findings and conclusions]

## 主要发现  
- [Discovery 1]
- [Discovery 2]
```
```

#### 7. 示例大幅精简
```json
// 原版（详细完整示例）
{
  "locale": "zh-CN",
  "has_enough_context": true,
  "thought": "基于前面的观察和分析，我已经收集了足够的信息来生成最终报告",
  "report": "# 项目架构分析报告\n\n## 执行摘要\n经过详细分析，该项目采用了模块化架构设计，包含以下主要组件：...\n\n## 主要发现\n- 项目结构清晰，遵循最佳实践\n- 代码质量良好，测试覆盖率达到85%\n- 存在性能优化空间...\n\n## 建议\n1. 建议优化数据库查询性能\n2. 增加API文档\n3. 完善错误处理机制\n\n## 结论\n项目整体架构合理，建议按照上述建议进行优化。",
  "title": "项目架构分析",
  "steps": []
}

// 优化后（核心要素）
{
  "locale": "zh-CN",
  "has_enough_context": true,
  "thought": "已收集足够信息，可生成最终报告",
  "report": "# 分析报告\n\n## 执行摘要\n项目架构清晰...\n\n## 建议\n1. 优化性能\n2. 增加文档",
  "title": "项目分析",
  "steps": []
}
```

#### 8. 删除冗余章节
**完全移除的章节**：
- Field Specifications（字段详细说明）
- Planning Guidelines（详细规划指导）
- Report Generation（报告生成详述）
- Step Creation Principles（步骤创建原则）
- Quality Standards（质量标准详述）
- Error Handling（错误处理说明）
- Final Checklist（最终检查清单）

#### 9. 结尾极简化
```markdown
# 原版（说教式）
Remember: Your output will be parsed as JSON, so ensure perfect formatting and structure.

# 优化后（命令式）
Output JSON directly. No explanations.
```

## 核心设计理念

### 1. **信息密度最大化**
- 删除所有冗余解释和重复说明
- 保留最核心的接口定义和决策逻辑
- 用模板替代长篇描述

### 2. **操作指导极简化**
- 明确的二元决策逻辑（true/false）
- 简洁的步骤分类（search vs execute）
- 直接的输出要求（JSON only）

### 3. **模板化标准输出**
- 提供标准的报告结构模板
- 简化的示例格式
- 清晰的字段映射关系

### 4. **认知负担最小化**
- 从202行压缩到75行
- 去除学习成本高的详细说明
- 突出核心决策点

## 技术实现优化

### JSON 接口简化
- 统一 step_type 为 "execute"
- 简化字段注释
- 保留核心布尔判断逻辑

### 决策流程优化
```
原版流程：阅读详细指导 → 理解复杂规则 → 生成复杂输出
优化流程：快速评估 → 二元决策 → 直接输出
```

### 输出约束强化
- 强制 JSON 直接输出
- 禁止 markdown 代码块包装
- 要求零解释输出

## 效果预期

### 1. **决策效率提升**
- Token 消耗减少 60%+
- 决策时间显著缩短
- 认知负担大幅降低

### 2. **输出质量保证**
- 标准化的报告格式
- 一致的 JSON 结构
- 清晰的步骤定义

### 3. **系统集成优化**
- 更快的 JSON 解析
- 减少错误输出概率
- 提高系统响应速度

## Claude 风格体现

**核心理念**：**最少的指导，最清晰的结构，最直接的输出**

优化后的 leader agent 将：
- 快速评估上下文充分性
- 生成标准化的 JSON 输出
- 提供简洁的战略决策
- 遵循模板化的报告结构

这个优化完美体现了 Claude Code 的设计哲学：通过极致简化来实现最高效率的 AI 协作体验。 