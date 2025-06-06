#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Code Agent Simple CLI - 简化版编程助手命令行工具

直接使用项目现有的LLM配置和Agent架构，提供简单高效的编程任务执行界面。
"""

import argparse
import asyncio
import os
import sys
from typing import Dict, Any

# 获取脚本所在目录和项目根目录，但保持当前工作目录不变
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 添加项目根目录到Python路径，以便导入src模块
sys.path.insert(0, project_root)

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from src.agents.code_agent import create_code_agent
from src.tools import (
    execute_terminal_command, get_current_directory, list_directory_contents,
    read_file, read_file_lines, get_file_info,
    write_file, append_to_file, create_new_file, generate_file_diff
)


class SimpleCodeAgentCLI:
    """简化版Code Agent CLI"""
    
    def __init__(self, debug: bool = False):
        """初始化CLI"""
        self.debug = debug
        
        # 设置工具
        self.tools = [
            # 命令行工具
            execute_terminal_command,
            get_current_directory,
            list_directory_contents,
            
            # 文件读取工具
            read_file,
            read_file_lines,
            get_file_info,
            
            # 文件写入工具
            write_file,
            append_to_file,
            create_new_file,
            generate_file_diff,
        ]
        
        # 创建agent
        self.agent = create_code_agent(self.tools)
    
    def print_banner(self):
        """显示欢迎信息"""
        print("🤖 Code Agent CLI - 智能编程助手")
        print("=" * 50)
        print("✨ 使用真实大模型驱动的编程任务自动化工具")
        print(f"📍 当前目录: {os.getcwd()}")
        print(f"🔧 可用工具: {len(self.tools)} 个")
        print("=" * 50)
    
    def select_task_type(self) -> str:
        """选择任务类型"""
        choices = [
            Choice("generate", "📝 代码生成 - 创建新的代码文件"),
            Choice("analyze", "🔍 代码分析 - 分析现有代码结构"),
            Choice("modify", "✏️ 代码修改 - 修改现有代码"),
            Choice("automate", "⚡ 任务自动化 - 执行复杂的自动化任务"),
            Choice("custom", "💬 自定义任务 - 描述具体需求"),
        ]
        
        return inquirer.select(
            message="请选择任务类型:",
            choices=choices
        ).execute()
    
    def get_task_description(self, task_type: str) -> str:
        """根据任务类型获取详细描述"""
        if task_type == "generate":
            return inquirer.text(
                message="请描述要生成的代码 (例如: 创建一个Python脚本读取CSV文件):",
                multiline=True
            ).execute()
            
        elif task_type == "analyze":
            # 列出可分析的文件
            files = [f for f in os.listdir(".") if os.path.isfile(f) and f.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs'))]
            
            if files:
                file_choices = [Choice(f, f) for f in files[:10]]
                selected_file = inquirer.select(
                    message="选择要分析的文件:",
                    choices=file_choices
                ).execute()
                return f"请分析文件 {selected_file} 的代码结构、功能和可能的改进建议"
            else:
                return "请分析当前项目的整体代码结构和组织方式"
                
        elif task_type == "modify":
            return inquirer.text(
                message="请描述要修改的内容 (例如: 修复main.py中的bug, 添加错误处理等):",
                multiline=True
            ).execute()
            
        elif task_type == "automate":
            automation_tasks = [
                Choice("backup", "创建文件备份系统"),
                Choice("test", "生成单元测试"),
                Choice("docs", "生成项目文档"),
                Choice("deploy", "创建部署脚本"),
                Choice("ci", "设置CI/CD配置"),
                Choice("custom", "自定义自动化任务")
            ]
            
            selected = inquirer.select(
                message="选择自动化任务:",
                choices=automation_tasks
            ).execute()
            
            if selected == "custom":
                return inquirer.text(
                    message="请描述自动化任务:",
                    multiline=True
                ).execute()
            else:
                task_descriptions = {
                    "backup": "创建一个自动备份系统，能够备份重要文件并支持恢复功能",
                    "test": "为现有代码生成完整的单元测试，包括边界情况测试",
                    "docs": "分析项目代码并生成详细的API文档和使用说明",
                    "deploy": "创建部署脚本，支持不同环境的自动化部署",
                    "ci": "设置持续集成配置文件，包括测试、构建和部署流程"
                }
                return task_descriptions.get(selected, "")
                
        else:  # custom
            return inquirer.text(
                message="请详细描述您的编程任务:",
                multiline=True
            ).execute()
    
    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """执行编程任务"""
        print(f"\n🚀 开始执行任务...")
        print(f"📋 任务描述: {task_description}")
        print("=" * 60)
        
        try:
            # 构建agent输入状态
            state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""
请帮我完成以下编程任务：

{task_description}

你可以使用以下工具来完成任务：
- 文件读取工具：read_file, read_file_lines, get_file_info
- 文件写入工具：write_file, append_to_file, create_new_file, generate_file_diff  
- 命令行工具：execute_terminal_command, get_current_directory, list_directory_contents

请分步骤完成任务，并在每个步骤后说明你做了什么。如果需要创建或修改文件，请使用相应的工具。
                        """
                    }
                ],
                "locale": "zh-CN"
            }
            
            print("🔄 正在执行任务...")
            
            # 调用agent
            result = await self.agent.ainvoke(state)
            
            if self.debug:
                print(f"\n🔍 Agent执行结果:")
                print(f"结果类型: {type(result)}")
                print(f"结果键: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
                if "messages" in result:
                    print(f"消息数量: {len(result['messages'])}")
                    for i, msg in enumerate(result["messages"]):
                        print(f"  消息 {i}: {type(msg)} - {getattr(msg, 'type', 'no type')}")
            
            # 解析结果
            final_output = "Agent执行完成"
            
            if "messages" in result and len(result["messages"]) > 0:
                # 查找所有AI消息
                ai_messages = []
                for msg in result["messages"]:
                    if hasattr(msg, 'type') and msg.type in ["ai", "assistant"]:
                        ai_messages.append(msg)
                
                if ai_messages:
                    # 获取最后一个AI消息
                    last_ai_msg = ai_messages[-1]
                    if hasattr(last_ai_msg, 'content'):
                        final_output = last_ai_msg.content
                        
                        print("\n" + "=" * 60)
                        print("✅ 任务执行完成!")
                        print("=" * 60)
                        print(final_output)
                        
                        return {
                            "success": True,
                            "output": final_output,
                            "full_result": result
                        }
                
                # 如果没有AI消息，显示所有消息用于调试
                if self.debug:
                    print("\n🔍 所有消息内容:")
                    for i, msg in enumerate(result["messages"]):
                        print(f"  消息 {i}: {msg}")
            
            print(f"\n❌ 任务执行失败: 没有获得有效的AI回复")
            return {
                "success": False,
                "error": "没有获得有效的AI回复",
                "full_result": result
            }
            
        except Exception as e:
            error_msg = f"任务执行出现异常: {str(e)}"
            print(f"\n❌ {error_msg}")
            
            if self.debug:
                import traceback
                traceback.print_exc()
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def show_tool_info(self):
        """显示可用工具信息"""
        print("\n🔧 可用工具:")
        print("-" * 40)
        
        tool_categories = {
            "文件读取": ["read_file", "read_file_lines", "get_file_info"],
            "文件写入": ["write_file", "append_to_file", "create_new_file", "generate_file_diff"],
            "命令行": ["execute_terminal_command", "get_current_directory", "list_directory_contents"]
        }
        
        for category, tool_names in tool_categories.items():
            print(f"\n📂 {category}:")
            for tool_name in tool_names:
                # 找到对应的工具
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if tool:
                    description = getattr(tool, 'description', '无描述')
                    print(f"  • {tool_name}: {description}")
    
    async def run_interactive_mode(self):
        """运行交互式模式"""
        self.print_banner()
        
        while True:
            try:
                print("\n" + "=" * 50)
                
                # 选择操作
                action = inquirer.select(
                    message="请选择操作:",
                    choices=[
                        Choice("task", "🚀 执行编程任务"),
                        Choice("tools", "🔧 查看可用工具"),
                        Choice("status", "📊 查看当前状态"),
                        Choice("quit", "👋 退出程序")
                    ]
                ).execute()
                
                if action == "quit":
                    print("\n👋 感谢使用 Code Agent CLI!")
                    break
                    
                elif action == "tools":
                    self.show_tool_info()
                    
                elif action == "status":
                    print(f"\n📍 当前目录: {os.getcwd()}")
                    files = [f for f in os.listdir(".") if os.path.isfile(f)]
                    dirs = [d for d in os.listdir(".") if os.path.isdir(d)]
                    print(f"📂 文件统计: {len(files)} 个文件, {len(dirs)} 个目录")
                    
                elif action == "task":
                    # 选择任务类型
                    task_type = self.select_task_type()
                    
                    # 获取任务描述
                    task_description = self.get_task_description(task_type)
                    
                    if task_description:
                        # 执行任务
                        result = await self.execute_task(task_description)
                        
                        # 显示结果摘要
                        if result["success"]:
                            print(f"\n✅ 任务成功完成!")
                        else:
                            print(f"\n❌ 任务执行失败: {result.get('error', '未知错误')}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户取消操作，再见!")
                break
            except Exception as e:
                print(f"\n❌ 程序错误: {str(e)}")
                if self.debug:
                    import traceback
                    traceback.print_exc()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Code Agent Simple CLI - 智能编程助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  uv run python code_agent_simple_cli.py                    # 启动交互式界面
  uv run python code_agent_simple_cli.py --task "创建API"   # 直接执行任务
  uv run python code_agent_simple_cli.py --debug            # 启用调试模式
        """
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="直接指定要执行的编程任务"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="启用调试模式，显示详细错误信息"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Code Agent Simple CLI v1.0.0"
    )
    
    args = parser.parse_args()
    
    # 创建CLI实例
    cli = SimpleCodeAgentCLI(debug=args.debug)
    
    if args.task:
        # 直接执行指定任务
        cli.print_banner()
        result = await cli.execute_task(args.task)
        
        print(f"\n📋 最终结果:")
        if result["success"]:
            print("✅ 任务执行成功")
        else:
            print(f"❌ 任务执行失败: {result.get('error', '未知错误')}")
    else:
        # 运行交互式界面
        await cli.run_interactive_mode()

if __name__ == "__main__":
    asyncio.run(main())