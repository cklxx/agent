#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified Code Agent CLI - 智能编程助手命令行工具

简化版本，专注于核心功能，避免复杂的事件循环和兼容性问题。
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

# 添加父目录到Python路径，以便导入src模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.agents.code_agent import create_code_agent
    from src.tools import (
        execute_terminal_command, get_current_directory, list_directory_contents,
        read_file, read_file_lines, get_file_info,
        write_file, append_to_file, create_new_file, generate_file_diff
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you are running this script from the correct project directory")
    sys.exit(1)


class SimpleCodeAgentCLI:
    """Simplified Code Agent CLI"""
    
    def __init__(self, debug: bool = False):
        """初始化CLI"""
        self.debug = debug
        
        print("🔧 DEBUG: Initializing CLI...")
        
        # 设置工具
        self.tools = [
            execute_terminal_command,
            get_current_directory,
            list_directory_contents,
            read_file,
            read_file_lines,
            get_file_info,
            write_file,
            append_to_file,
            create_new_file,
            generate_file_diff,
        ]
        
        print(f"🔧 DEBUG: Configured {len(self.tools)} tools")
        
        # 创建agent
        try:
            self.agent = create_code_agent(self.tools)
            print("✅ DEBUG: Agent created successfully")
        except Exception as e:
            print(f"❌ DEBUG: Failed to create agent: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            raise
    
    def print_banner(self):
        """显示欢迎信息"""
        print("\n🤖 Simplified Code Agent CLI")
        print("=" * 50)
        print("✨ AI-powered programming automation tool")
        print(f"📍 Current directory: {os.getcwd()}")
        print(f"🔧 Available tools: {len(self.tools)}")
        print("=" * 50)
    
    async def execute_task(self, task_description: str) -> dict:
        """执行编程任务"""
        print(f"\n🚀 Executing task: {task_description}")
        print("=" * 60)
        
        try:
            # 构建agent输入状态
            state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""
Please help me complete the following programming task:

{task_description}

You can use the following tools:
- File reading tools: read_file, read_file_lines, get_file_info
- File writing tools: write_file, append_to_file, create_new_file, generate_file_diff  
- Command line tools: execute_terminal_command, get_current_directory, list_directory_contents

Please complete the task step by step and explain what you did after each step.
If you need to create or modify files, please use the appropriate tools.
                        """
                    }
                ],
                "locale": "en-US"
            }
            
            print("🔄 Calling agent...")
            
            # 调用agent
            result = await self.agent.ainvoke(state)
            
            print("✅ DEBUG: Agent execution completed")
            
            if self.debug:
                print(f"🔍 DEBUG: Agent result type: {type(result)}")
                print(f"🔍 DEBUG: Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                if "messages" in result:
                    print(f"🔍 DEBUG: Messages count: {len(result['messages'])}")
            
            # 解析结果
            final_output = "Agent execution completed"
            tool_calls_found = False
            
            if "messages" in result and len(result["messages"]) > 0:
                print("🔍 DEBUG: Analyzing messages for tool calls and responses...")
                
                # 检查所有消息，包括工具调用
                for i, msg in enumerate(result["messages"]):
                    if self.debug:
                        print(f"🔍 DEBUG: Message {i}: type={getattr(msg, 'type', 'unknown')}")
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            print(f"🔍 DEBUG: Found tool calls in message {i}: {len(msg.tool_calls)} calls")
                            tool_calls_found = True
                            for j, tool_call in enumerate(msg.tool_calls):
                                print(f"  Tool call {j}: {tool_call.get('name', 'unknown')} with args: {tool_call.get('args', {})}")
                        
                        if hasattr(msg, 'content') and msg.content:
                            content_preview = str(msg.content)[:200] + "..." if len(str(msg.content)) > 200 else str(msg.content)
                            print(f"🔍 DEBUG: Message {i} content preview: {content_preview}")
                
                # 查找AI消息
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
                        print("✅ Task execution completed!")
                        print("=" * 60)
                        print(f"🔧 Tool calls detected: {tool_calls_found}")
                        print(final_output)
                        
                        return {
                            "success": True,
                            "output": final_output,
                            "tool_calls_made": tool_calls_found,
                            "full_result": result
                        }
                
                # 如果没有AI消息，显示所有消息用于调试
                if self.debug:
                    print("🔍 DEBUG: All messages (no AI messages found):")
                    for i, msg in enumerate(result["messages"]):
                        print(f"  Message {i}: {msg}")
            
            print(f"\n❌ Task execution failed: No valid AI response")
            return {
                "success": False,
                "error": "No valid AI response",
                "full_result": result
            }
            
        except Exception as e:
            error_msg = f"Task execution exception: {str(e)}"
            print(f"\n❌ {error_msg}")
            
            if self.debug:
                import traceback
                print("🔍 DEBUG: Full traceback:")
                traceback.print_exc()
            
            return {
                "success": False,
                "error": error_msg
            }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Simplified Code Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python code_agent_cli.py --task "Create a Python calculator"
  python code_agent_cli.py --task "List current directory contents" --debug
        """
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        required=True,
        help="Specify the programming task to execute"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode for detailed error information"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Simplified Code Agent CLI v1.0.0"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting Simplified Code Agent CLI...")
    
    try:
        # 创建CLI实例
        cli = SimpleCodeAgentCLI(debug=args.debug)
        cli.print_banner()
        
        # 执行任务
        result = await cli.execute_task(args.task)
        
        print(f"\n📋 Final result:")
        if result["success"]:
            print("✅ Task execution successful")
        else:
            print(f"❌ Task execution failed: {result.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        print("\n\n👋 User cancelled operation, goodbye!")
    except Exception as e:
        print(f"\n❌ CLI error: {str(e)}")
        if args.debug:
            import traceback
            print("🔍 DEBUG: Full traceback:")
            traceback.print_exc()


def run_main():
    """运行主函数"""
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Failed to start CLI: {e}")
        print("Please try running in a new terminal")


if __name__ == "__main__":
    run_main() 