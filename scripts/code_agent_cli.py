#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified Code Agent CLI - 智能编程助手命令行工具

简化版本，专注于核心功能，避免复杂的事件循环和兼容性问题。
支持指定工作目录运行。
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

# 获取脚本所在目录和项目根目录，但保持当前工作目录不变
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 添加项目根目录到Python路径，以便导入src模块
sys.path.insert(0, project_root)

try:
    from src.agents.code_agent import create_code_agent
    from src.tools import (
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
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(
        "Please ensure you are running this script from the correct project directory"
    )
    sys.exit(1)


class SimpleCodeAgentCLI:
    """Simplified Code Agent CLI"""

    def __init__(self, debug: bool = False, working_directory: Optional[str] = None):
        """初始化CLI"""
        self.debug = debug
        self.working_directory = working_directory

        print("🔧 DEBUG: Initializing Code Agent CLI...")
        print(f"🔧 DEBUG: Debug mode: {'ON' if debug else 'OFF'}")

        # 如果指定了工作目录，检查并切换到该目录
        if self.working_directory:
            print(f"🔧 DEBUG: Working directory specified: {self.working_directory}")

            if not os.path.exists(self.working_directory):
                print(f"❌ 错误: 工作目录不存在: {self.working_directory}")
                sys.exit(1)
            if not os.path.isdir(self.working_directory):
                print(f"❌ 错误: 不是一个有效的目录: {self.working_directory}")
                sys.exit(1)

            # 转换为绝对路径
            original_path = self.working_directory
            self.working_directory = os.path.abspath(self.working_directory)
            print(
                f"🔧 DEBUG: 转换工作目录路径: {original_path} -> {self.working_directory}"
            )

            # 显示当前目录和目标目录
            current_dir = os.getcwd()
            print(f"🔧 DEBUG: 当前目录: {current_dir}")
            print(f"🔧 DEBUG: 目标目录: {self.working_directory}")

            # 切换当前工作目录
            os.chdir(self.working_directory)
            new_current_dir = os.getcwd()
            print(f"🔧 DEBUG: 成功切换到工作目录: {new_current_dir}")

            # 验证目录权限
            try:
                test_file = os.path.join(self.working_directory, ".agent_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                print(f"🔧 DEBUG: 工作目录权限检查: ✅ 可读写")
            except Exception as e:
                print(f"🔧 DEBUG: 工作目录权限检查: ⚠️ 权限限制 - {e}")
        else:
            print(f"🔧 DEBUG: 使用当前目录: {os.getcwd()}")

        # 设置工具
        print("🔧 DEBUG: 初始化工具集...")
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

        print(f"🔧 DEBUG: 已配置 {len(self.tools)} 个工具:")
        for i, tool in enumerate(self.tools, 1):
            tool_name = getattr(tool, "name", "Unknown")
            print(f"🔧 DEBUG:   {i}. {tool_name}")

        # 创建agent
        print("🔧 DEBUG: 正在创建 AI Agent...")
        try:
            self.agent = create_code_agent(self.tools)
            print("✅ DEBUG: AI Agent 创建成功")

            # 显示agent配置信息
            if self.debug:
                print(f"🔧 DEBUG: Agent 类型: {type(self.agent)}")
                if hasattr(self.agent, "nodes"):
                    print(f"🔧 DEBUG: Agent 节点数: {len(self.agent.nodes)}")
                if hasattr(self.agent, "edges"):
                    print(f"🔧 DEBUG: Agent 边数: {len(self.agent.edges)}")

        except Exception as e:
            print(f"❌ DEBUG: AI Agent 创建失败: {e}")
            if debug:
                import traceback

                print("🔧 DEBUG: 完整错误信息:")
                traceback.print_exc()
            raise

        print("🔧 DEBUG: CLI 初始化完成")
        print("-" * 50)

    def print_banner(self):
        """显示欢迎信息"""
        print("\n🤖 Simplified Code Agent CLI")
        print("=" * 60)
        print("✨ AI-powered programming automation tool")

        # 环境信息
        current_dir = os.getcwd()
        print(f"📍 Current working directory: {current_dir}")
        if self.working_directory and current_dir != self.working_directory:
            print(f"🎯 Target working directory: {self.working_directory}")

        # 系统信息
        import sys
        import platform

        print(f"🐍 Python version: {sys.version.split()[0]}")
        print(f"💻 System: {platform.system()} {platform.release()}")

        # 工具信息
        print(f"🔧 Available tools: {len(self.tools)}")
        if self.debug:
            print("🛠️  Tool list:")
            for i, tool in enumerate(self.tools, 1):
                tool_name = getattr(tool, "name", "Unknown")
                tool_desc = getattr(tool, "description", "No description")
                print(f"   {i}. {tool_name}")
                if tool_desc and len(tool_desc) < 80:
                    print(f"      └─ {tool_desc}")

        # 配置信息
        print(f"🔍 Debug mode: {'ON' if self.debug else 'OFF'}")

        # 目录权限状态
        try:
            import tempfile

            with tempfile.NamedTemporaryFile(dir=current_dir, delete=True):
                pass
            permission_status = "✅ 可读写"
        except:
            permission_status = "⚠️ 权限受限"
        print(f"📝 Directory permissions: {permission_status}")

        print("=" * 60)

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
                        "content": (
                            f"""
Please help me complete the following programming task:

{task_description}

You can use the following tools:
- File reading tools: read_file, read_file_lines, get_file_info
- File writing tools: write_file, append_to_file, create_new_file, generate_file_diff  
- Command line tools: execute_terminal_command, get_current_directory, list_directory_contents

Please complete the task step by step and explain what you did after each step.
If you need to create or modify files, please use the appropriate tools.
                        """
                        ),
                    }
                ],
                "locale": "en-US",
            }

            print("🔄 Starting agent execution with enhanced logging...")
            print("📝 Agent execution flow:")
            print("-" * 60)

            # 使用简化的监控方式
            step_counter = 1
            all_messages = []

            try:
                # 调用agent并监控流式输出
                processed_messages = set()  # 跟踪已处理的消息

                async for chunk in self.agent.astream(
                    state, {"configurable": {"thread_id": "demo"}}
                ):
                    if self.debug:
                        print(f"🔍 DEBUG: Received chunk: {type(chunk)}")
                        if hasattr(chunk, "keys"):
                            print(f"🔍 DEBUG: Chunk keys: {list(chunk.keys())}")

                    # 检查chunk中的消息
                    if isinstance(chunk, dict) and "messages" in chunk:
                        messages = chunk["messages"]

                        # 处理所有新消息
                        for msg_idx, msg in enumerate(messages):
                            msg_id = (
                                f"{msg_idx}_{getattr(msg, 'type', 'unknown')}_{id(msg)}"
                            )

                            if msg_id not in processed_messages:
                                processed_messages.add(msg_id)
                                msg_type = getattr(msg, "type", "unknown")

                                # 检查是否是AI消息
                                if msg_type == "ai":
                                    # 检查工具调用
                                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                                        tool_calls_found = True
                                        print(
                                            f"\n🔧 Step {step_counter}: Agent is calling tools..."
                                        )
                                        for i, tool_call in enumerate(msg.tool_calls):
                                            tool_name = tool_call.get("name", "unknown")
                                            tool_args = tool_call.get("args", {})
                                            print(f"  🛠️  Tool {i+1}: {tool_name}")
                                            # 显示参数，但限制长度
                                            if tool_args:
                                                for key, value in tool_args.items():
                                                    if (
                                                        isinstance(value, str)
                                                        and len(value) > 100
                                                    ):
                                                        display_value = (
                                                            value[:100] + "..."
                                                        )
                                                    else:
                                                        display_value = value
                                                    print(
                                                        f"      {key}: {display_value}"
                                                    )
                                        step_counter += 1

                                    # 显示AI的思考内容
                                    elif hasattr(msg, "content") and msg.content:
                                        content = msg.content.strip()
                                        if content and not content.startswith(
                                            "["
                                        ):  # 过滤掉系统消息
                                            print(f"\n💭 Agent thinking:")
                                            # 分段显示长内容
                                            lines = content.split("\n")
                                            for line in lines[:5]:  # 只显示前5行
                                                if line.strip():
                                                    print(
                                                        f"   {line[:150]}{'...' if len(line) > 150 else ''}"
                                                    )
                                            if len(lines) > 5:
                                                print(
                                                    f"   ... ({len(lines) - 5} more lines)"
                                                )

                                # 检查工具执行结果
                                elif msg_type == "tool":
                                    tool_result = getattr(msg, "content", "No result")
                                    print(f"\n✅ Tool execution result:")
                                    # 显示工具执行结果，限制长度
                                    result_lines = str(tool_result).split("\n")
                                    for line in result_lines[:3]:  # 只显示前3行
                                        print(f"   {line}")
                                    if len(result_lines) > 3:
                                        print(
                                            f"   ... ({len(result_lines) - 3} more lines)"
                                        )

                                # 显示人类消息（用户输入）
                                elif msg_type == "human" and self.debug:
                                    print(f"🔍 DEBUG: Human message processed")

                    # 检查其他类型的chunk
                    elif self.debug:
                        print(f"🔍 DEBUG: Non-message chunk: {chunk}")

                # 获取最终结果
                final_result = await self.agent.ainvoke(state)

            except Exception as execution_error:
                print(f"⚠️ Execution issue: {execution_error}")
                if self.debug:
                    import traceback

                    print("🔍 DEBUG: Execution error details:")
                    traceback.print_exc()

                # 尝试获取结果
                final_result = await self.agent.ainvoke(state)

            print("\n" + "=" * 60)
            print("🏁 Agent execution completed - Analyzing results...")
            print("=" * 60)

            if self.debug:
                print(f"🔍 DEBUG: Final result type: {type(final_result)}")
                print(
                    f"🔍 DEBUG: Result keys: {list(final_result.keys()) if isinstance(final_result, dict) else 'Not a dict'}"
                )
                if "messages" in final_result:
                    print(
                        f"🔍 DEBUG: Total messages in final result: {len(final_result['messages'])}"
                    )

            # 详细分析最终结果
            print("\n📊 Task Execution Summary:")
            print("-" * 40)

            if "messages" in final_result and len(final_result["messages"]) > 0:
                # 统计不同类型的消息
                human_msgs = []
                ai_msgs = []
                tool_msgs = []
                total_tool_calls = 0
                actions_taken = []

                print("🔍 Analyzing execution flow...")

                for i, msg in enumerate(final_result["messages"]):
                    msg_type = getattr(msg, "type", "unknown")

                    if msg_type == "human":
                        human_msgs.append(msg)
                    elif msg_type == "ai":
                        ai_msgs.append(msg)
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            total_tool_calls += len(msg.tool_calls)
                            # 收集执行的动作
                            for tc in msg.tool_calls:
                                tool_name = tc.get("name", "unknown")
                                if tool_name == "list_directory_contents":
                                    actions_taken.append("📂 探索目录结构")
                                elif tool_name == "read_file":
                                    file_path = tc.get("args", {}).get(
                                        "file_path", "unknown"
                                    )
                                    actions_taken.append(f"📖 读取文件: {file_path}")
                                elif tool_name in ["write_file", "create_new_file"]:
                                    file_path = tc.get("args", {}).get(
                                        "file_path", "unknown"
                                    )
                                    actions_taken.append(
                                        f"✍️ 创建/编辑文件: {file_path}"
                                    )
                                elif tool_name == "execute_terminal_command":
                                    command = tc.get("args", {}).get(
                                        "command", "unknown"
                                    )
                                    actions_taken.append(f"💻 执行命令: {command}")
                                elif tool_name == "get_current_directory":
                                    actions_taken.append("📍 获取工作目录")
                                else:
                                    actions_taken.append(f"🔧 执行工具: {tool_name}")
                    elif msg_type == "tool":
                        tool_msgs.append(msg)

                print(f"\n📈 Execution Statistics:")
                print(f"   💬 Total interactions: {len(final_result['messages'])}")
                print(f"   🤖 AI reasoning steps: {len(ai_msgs)}")
                print(f"   🛠️ Actions executed: {total_tool_calls}")
                print(f"   📊 Tool responses: {len(tool_msgs)}")

                # 显示主要执行的动作
                if actions_taken:
                    print(f"\n🎯 Main Actions Performed:")
                    for i, action in enumerate(actions_taken, 1):
                        print(f"   {i}. {action}")

                # 获取最终AI回复
                if ai_msgs:
                    last_ai_msg = ai_msgs[-1]
                    if hasattr(last_ai_msg, "content"):
                        final_output = last_ai_msg.content

                        print("\n" + "=" * 60)
                        print("🎉 TASK COMPLETED SUCCESSFULLY!")
                        print("=" * 60)

                        # 分析最终输出的关键信息
                        output_lower = final_output.lower()
                        if any(
                            word in output_lower
                            for word in ["created", "generated", "built"]
                        ):
                            print("✅ Status: Files/Content Created")
                        elif any(
                            word in output_lower
                            for word in ["found", "discovered", "located"]
                        ):
                            print("✅ Status: Information Retrieved")
                        elif any(
                            word in output_lower
                            for word in ["completed", "finished", "done"]
                        ):
                            print("✅ Status: Task Completed")
                        elif any(
                            word in output_lower for word in ["exists", "already"]
                        ):
                            print("ℹ️ Status: Resources Already Available")
                        else:
                            print("✅ Status: Task Processed")

                        print(f"🔧 Tools Used: {total_tool_calls > 0}")
                        print(f"🛠️ Total Actions: {total_tool_calls}")
                        print(f"💭 Reasoning Steps: {len(ai_msgs)}")

                        print("\n📋 Final Result:")
                        print("-" * 40)

                        # 智能格式化最终输出
                        lines = final_output.split("\n")
                        in_code_block = False

                        for line in lines:
                            if line.strip().startswith("```"):
                                in_code_block = not in_code_block
                                print(f"💻 {line}")
                            elif in_code_block:
                                print(f"   {line}")
                            elif line.strip().startswith("#"):
                                print(f"📌 {line}")
                            elif line.strip().startswith(
                                "-"
                            ) or line.strip().startswith("*"):
                                print(f"   • {line.strip()[1:].strip()}")
                            elif (
                                line.strip().startswith("1.")
                                or line.strip().startswith("2.")
                                or line.strip().startswith("3.")
                            ):
                                print(f"   🔢 {line.strip()}")
                            elif line.strip() and not line.startswith(" "):
                                print(f"{line}")
                            elif line.strip():
                                print(f"   {line}")
                            else:
                                print()

                        print("-" * 40)

                        return {
                            "success": True,
                            "output": final_output,
                            "tool_calls_made": total_tool_calls > 0,
                            "total_tool_calls": total_tool_calls,
                            "actions_taken": actions_taken,
                            "message_stats": {
                                "human": len(human_msgs),
                                "ai": len(ai_msgs),
                                "tool": len(tool_msgs),
                            },
                            "full_result": final_result,
                        }

                # 如果没有AI消息，显示调试信息
                print("⚠️ WARNING: No AI messages found in final result")
                if self.debug:
                    print("🔍 DEBUG: Dumping all messages for analysis:")
                    for i, msg in enumerate(final_result["messages"]):
                        msg_type = getattr(msg, "type", "unknown")
                        msg_content = str(getattr(msg, "content", ""))[:150]
                        print(f"  Message {i}: type={msg_type}")
                        print(f"    Content: {msg_content}...")
                        print(f"    Full object: {type(msg)}")

            print(f"\n❌ TASK EXECUTION FAILED: No valid AI response found")
            return {
                "success": False,
                "error": "No valid AI response",
                "full_result": final_result,
            }

        except Exception as e:
            error_msg = f"Task execution exception: {str(e)}"
            print(f"\n💥 EXECUTION ERROR: {error_msg}")

            if self.debug:
                import traceback

                print("\n🔍 DEBUG: Complete error traceback:")
                print("=" * 50)
                traceback.print_exc()
                print("=" * 50)

            return {"success": False, "error": error_msg}


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Simplified Code Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python code_agent_cli.py --task "Create a Python calculator"
  python code_agent_cli.py --task "List current directory contents" --debug
        """,
    )

    parser.add_argument(
        "--task",
        "-t",
        type=str,
        required=True,
        help="Specify the programming task to execute",
    )

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode for detailed error information",
    )

    parser.add_argument(
        "--version", "-v", action="version", version="Simplified Code Agent CLI v1.0.0"
    )

    parser.add_argument(
        "--working-directory",
        "-w",
        type=str,
        help="Specify the working directory for the task",
    )

    args = parser.parse_args()

    print("🚀 Starting Simplified Code Agent CLI...")

    try:
        # 创建CLI实例
        cli = SimpleCodeAgentCLI(
            debug=args.debug, working_directory=args.working_directory
        )
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
