#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强Code Agent测试脚本

演示新的三阶段执行模式：
1. 前置信息收集阶段
2. 任务实施阶段  
3. 验证确认阶段
"""

import asyncio
import os
import sys
from typing import Dict, Any

# 获取脚本所在目录和项目根目录
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 对于测试脚本，需要切换到项目根目录以正确导入模块
original_cwd = os.getcwd()
os.chdir(project_root)

# 添加项目根目录到Python路径
sys.path.insert(0, project_root)

from src.code_agent_workflow import CodeAgentWorkflow
from src.config.logging_config import setup_simplified_logging


def print_separator(title: str, char: str = "=", width: int = 60):
    """打印分隔符"""
    print(f"\n{char * width}")
    print(f"{title.center(width)}")
    print(f"{char * width}")


def print_phase_header(phase_name: str, description: str):
    """打印阶段标题"""
    phase_icons = {
        "pre_analysis": "🔍",
        "implementation": "⚙️", 
        "verification": "🔬"
    }
    icon = phase_icons.get(phase_name, "📋")
    print(f"\n{icon} {description}")
    print("-" * 40)


async def demonstrate_task_planning():
    """演示任务规划功能"""
    print_separator("📋 任务规划演示")
    
    workflow = CodeAgentWorkflow()
    planner = workflow.task_planner
    
    # 测试不同类型的任务
    test_tasks = [
        "创建一个Python脚本，实现文件备份功能，包含错误处理",
        "分析当前项目的代码结构，生成技术文档",
        "实现一个简单的Web API，提供JSON响应功能"
    ]
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n🧪 测试任务 {i}: {task}")
        print("-" * 50)
        
        plan = planner.plan_task(task)
        
        # 按阶段组织步骤
        phases = {}
        for step in plan:
            phase = step.get('phase', 'unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(step)
        
        print(f"📊 生成计划: {len(phases)} 个阶段，共 {len(plan)} 个步骤")
        
        for phase_name, phase_steps in phases.items():
            print_phase_header(phase_name, f"{phase_name.upper()} - {len(phase_steps)} 步骤")
            
            for j, step in enumerate(phase_steps, 1):
                step_type = step.get('type', 'unknown')
                title = step.get('title', '未命名步骤')
                description = step.get('description', '')
                tools = step.get('tools', [])
                verification = step.get('verification_criteria', [])
                
                print(f"  {j}. [{step_type.upper()}] {title}")
                print(f"     📖 {description}")
                print(f"     🔧 工具: {', '.join(tools)}")
                if verification:
                    print(f"     ✅ 验证: {', '.join(verification[:2])}{'...' if len(verification) > 2 else ''}")
                print()


async def demonstrate_enhanced_features():
    """演示增强功能"""
    print_separator("🚀 增强功能演示")
    
    # 演示各阶段的优势
    enhancements = {
        "前置信息收集": {
            "icon": "🔍",
            "features": [
                "自动环境评估 - 获取工作目录和项目结构",
                "智能上下文分析 - 理解现有代码模式和依赖",
                "需求验证 - 确保所有前置条件满足",
                "风险评估 - 识别潜在冲突和问题"
            ]
        },
        "任务实施": {
            "icon": "⚙️",
            "features": [
                "基于前置信息的精确实施",
                "持续验证每个步骤的执行结果", 
                "智能错误处理和恢复机制",
                "代码质量检查和最佳实践"
            ]
        },
        "验证确认": {
            "icon": "🔬",
            "features": [
                "文件完整性验证 - 确保文件正确创建/修改",
                "功能测试 - 验证实现的功能正常工作",
                "集成验证 - 确保与现有系统兼容",
                "回滚准备 - 支持安全回退机制"
            ]
        }
    }
    
    for phase_name, phase_info in enhancements.items():
        print(f"\n{phase_info['icon']} {phase_name}阶段增强:")
        for feature in phase_info['features']:
            print(f"  ✨ {feature}")


async def demonstrate_verification_system():
    """演示验证系统"""
    print_separator("🔬 验证系统演示")
    
    verification_types = {
        "文件验证": {
            "description": "检查文件操作的完整性和正确性",
            "criteria": [
                "文件是否存在且可访问",
                "文件内容是否符合预期",
                "文件权限是否正确设置",
                "备份文件是否已创建"
            ]
        },
        "功能验证": {
            "description": "测试实现功能的正确性和稳定性",
            "criteria": [
                "基本功能是否正常工作",
                "边界条件是否正确处理",
                "错误处理是否完善",
                "性能是否在可接受范围"
            ]
        },
        "集成验证": {
            "description": "确保新代码与现有系统的兼容性",
            "criteria": [
                "依赖关系是否正确解决",
                "API接口是否兼容",
                "现有功能是否受到影响",
                "配置文件是否正确更新"
            ]
        }
    }
    
    for verify_type, verify_info in verification_types.items():
        print(f"\n🔍 {verify_type}:")
        print(f"   📋 {verify_info['description']}")
        print("   验证标准:")
        for criterion in verify_info['criteria']:
            print(f"     ✅ {criterion}")


async def main():
    """主函数"""
    # 设置简化日志模式
    setup_simplified_logging()
    
    print_separator("🤖 增强Code Agent演示", "=", 70)
    print("本演示展示了Code Agent的三阶段执行模式和增强功能")
    
    # 演示任务规划
    await demonstrate_task_planning()
    
    # 演示增强功能
    await demonstrate_enhanced_features()
    
    # 演示验证系统
    await demonstrate_verification_system()
    
    print_separator("📝 使用建议", "=", 70)
    suggestions = [
        "🎯 让Agent自主完成三阶段执行流程，充分利用前置信息收集",
        "🔍 关注验证阶段的输出，确保实现质量和系统稳定性",
        "🐛 在调试模式下查看详细的步骤分析和错误信息",
        "📊 利用阶段化执行提升复杂任务的成功率",
        "🔄 善用验证失败后的回滚机制，保证系统安全性"
    ]
    
    for suggestion in suggestions:
        print(f"  {suggestion}")
    
    print_separator("🎉 演示完成", "=", 70)
    print("增强的Code Agent已准备就绪，可以处理更复杂的编程任务！")


if __name__ == "__main__":
    asyncio.run(main()) 