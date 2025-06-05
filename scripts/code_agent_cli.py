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
            
            print("🔄 Starting agent execution with streaming output...")
            print("📝 Agent thinking process:")
            print("-" * 40)
            
            # 使用流式调用来获取实时输出
            step_counter = 1
            tool_calls_found = False
            
            try:
                # 调用agent并监控流式输出
                async for chunk in self.agent.astream(state, {"configurable": {"thread_id": "demo"}}):
                    if self.debug:
                        print(f"🔍 DEBUG: Received chunk: {type(chunk)}")
                    
                    # 检查chunk中的消息
                    if isinstance(chunk, dict) and "messages" in chunk:
                        messages = chunk["messages"]
                        if messages:
                            last_msg = messages[-1]
                            
                            # 检查是否是AI消息
                            if hasattr(last_msg, 'type') and last_msg.type == "ai":
                                # 检查工具调用
                                if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                    tool_calls_found = True
                                    print(f"\n🔧 Step {step_counter}: Agent is calling tools...")
                                    for i, tool_call in enumerate(last_msg.tool_calls):
                                        tool_name = tool_call.get('name', 'unknown')
                                        tool_args = tool_call.get('args', {})
                                        print(f"  🛠️  Tool {i+1}: {tool_name}")
                                        print(f"      Arguments: {tool_args}")
                                    step_counter += 1
                                
                                # 显示AI的思考内容
                                if hasattr(last_msg, 'content') and last_msg.content:
                                    content = last_msg.content.strip()
                                    if content and not content.startswith('['):  # 过滤掉系统消息
                                        print(f"\n💭 Agent thinking:")
                                        print(f"   {content[:200]}{'...' if len(content) > 200 else ''}")
                            
                            # 检查工具执行结果
                            elif hasattr(last_msg, 'type') and last_msg.type == "tool":
                                tool_result = getattr(last_msg, 'content', 'No result')
                                print(f"\n✅ Tool execution result:")
                                print(f"   {tool_result}")
                
                # 获取最终结果
                final_result = await self.agent.ainvoke(state)
                
            except Exception as streaming_error:
                print(f"⚠️  Streaming failed, using standard invoke: {streaming_error}")
                # 如果流式调用失败，使用标准调用
                final_result = await self.agent.ainvoke(state)
            
            print("\n" + "-" * 40)
            print("✅ DEBUG: Agent execution completed")
            
            if self.debug:
                print(f"🔍 DEBUG: Agent result type: {type(final_result)}")
                print(f"🔍 DEBUG: Result keys: {list(final_result.keys()) if isinstance(final_result, dict) else 'Not a dict'}")
                if "messages" in final_result:
                    print(f"🔍 DEBUG: Total messages: {len(final_result['messages'])}")
            
            # 详细分析最终结果
            print("\n🔍 DEBUG: Detailed result analysis...")
            
            if "messages" in final_result and len(final_result["messages"]) > 0:
                print("🔍 DEBUG: Analyzing all messages for comprehensive view...")
                
                # 统计不同类型的消息
                human_msgs = []
                ai_msgs = []
                tool_msgs = []
                total_tool_calls = 0
                
                for i, msg in enumerate(final_result["messages"]):
                    msg_type = getattr(msg, 'type', 'unknown')
                    
                    if msg_type == "human":
                        human_msgs.append(msg)
                    elif msg_type == "ai":
                        ai_msgs.append(msg)
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            total_tool_calls += len(msg.tool_calls)
                            if self.debug:
                                print(f"🔍 DEBUG: AI message {i} has {len(msg.tool_calls)} tool calls")
                    elif msg_type == "tool":
                        tool_msgs.append(msg)
                        if self.debug:
                            tool_content = getattr(msg, 'content', 'No content')
                            print(f"🔍 DEBUG: Tool message {i}: {tool_content[:100]}...")
                
                print(f"\n📊 Execution Summary:")
                print(f"   👤 Human messages: {len(human_msgs)}")
                print(f"   🤖 AI messages: {len(ai_msgs)}")
                print(f"   🛠️  Tool messages: {len(tool_msgs)}")
                print(f"   🔧 Total tool calls: {total_tool_calls}")
                
                # 获取最终AI回复
                if ai_msgs:
                    last_ai_msg = ai_msgs[-1]
                    if hasattr(last_ai_msg, 'content'):
                        final_output = last_ai_msg.content
                        
                        print("\n" + "=" * 60)
                        print("✅ Task execution completed!")
                        print("=" * 60)
                        print(f"🔧 Tool calls made: {total_tool_calls > 0}")
                        print(f"🛠️  Total tool calls: {total_tool_calls}")
                        print("\n📄 Final agent response:")
                        print(final_output)
                        
                        return {
                            "success": True,
                            "output": final_output,
                            "tool_calls_made": total_tool_calls > 0,
                            "total_tool_calls": total_tool_calls,
                            "message_stats": {
                                "human": len(human_msgs),
                                "ai": len(ai_msgs),
                                "tool": len(tool_msgs)
                            },
                            "full_result": final_result
                        }
                
                # 如果没有AI消息，显示调试信息
                print("⚠️  No AI messages found in final result")
                if self.debug:
                    print("🔍 DEBUG: All messages:")
                    for i, msg in enumerate(final_result["messages"]):
                        print(f"  Message {i}: type={getattr(msg, 'type', 'unknown')}, content={str(msg)[:100]}...")
            
            print(f"\n❌ Task execution failed: No valid AI response")
            return {
                "success": False,
                "error": "No valid AI response",
                "full_result": final_result
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