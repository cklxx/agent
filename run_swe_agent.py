import asyncio
import uuid
import argparse
import os
import logging
import sys
import traceback
from langchain_core.messages import HumanMessage
from src.config.logging_config import setup_debug_logging, setup_simplified_logging
from src.swe.graph.builder import graph

logger = logging.getLogger(__name__)


def _setup_logging(debug: bool):
    """设置日志配置"""
    if debug:
        setup_debug_logging()
        # 即使在调试模式下，也明确禁用asyncio的详细日志
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        # 禁用其他可能过于冗长的模块日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logger.debug(
            "Architect Agent: Debug logging enabled (verbose logs from common libraries suppressed)"
        )
    else:
        setup_simplified_logging()


async def run_agent(task: str, workspace: str, debug: bool = False):
    """
    Asynchronously runs the SWE agent workflow with a given task.

    Args:
        task (str): The task description for the agent to execute.
        workspace (str): The absolute path to the workspace directory.
        debug (bool): Whether to enable debug mode for verbose output.
    """

    # Unique conversation ID for each run
    conv_id = str(uuid.uuid4())

    # Define the initial input for the graph, including workspace context
    inputs = {
        "messages": [HumanMessage(content=task)],
        "workspace": workspace,
        "debug": debug,
    }

    # Configuration for the graph invocation
    config = {"configurable": {"thread_id": conv_id}, "recursion_limit": 100}

    print(f"🚀 Starting agent for task: '{task}'")
    print(f"📂 Workspace: {workspace}")
    print(f"✨ Conversation ID: {conv_id}")
    if debug:
        print(f"🐞 Debug mode: ON (focused on application logs only)")
    print("-" * 40)

    try:
        # Stream the results from the graph
        event_count = 0
        async for event in graph.astream_events(inputs, config=config, version="v2"):
            kind = event["event"]
            event_count += 1

            # 在调试模式下输出事件信息，但保持简洁
            if debug:
                # 只打印关键事件类型，减少噪音
                if kind in ["on_chain_start", "on_chain_end", "on_chain_error"]:
                    print(f"\n🔄 Event: {kind}")
                    if "name" in event:
                        print(f"📌 Node: {event}")

            if kind == "on_chain_end":
                if event["name"] == "architect":
                    # Print the final report from the architect node
                    report_data = event["data"]["output"]
                    print("\n" + "-" * 40)
                    print("✅ Agent run complete. Final Report:")
                    print(report_data)
            elif debug and kind == "on_chain_error":
                # 只在错误事件中详细展示数据
                if "data" in event:
                    if "input" in event["data"]:
                        print(f"📥 Input: {event['data']['input']}")
                    if "output" in event["data"]:
                        print(f"📤 Output: {event['data']['output']}")
                    if "error" in event["data"]:
                        print(f"❌ Error: {event['data']['error']}")
                        if debug:
                            tb = event["data"].get(
                                "traceback", "No traceback available"
                            )
                            print(f"🔍 Error Traceback:\n{tb}")

    except Exception as e:
        print(f"\n❌ An error occurred during the agent run: {e}")
        if debug:
            print("\n🔍 Error Traceback:")
            traceback.print_exc()


def interactive_mode():
    """
    Displays an interactive menu for the user to select a task.
    """
    print("\n🏗️  SWE Agent - Interactive Mode")
    print("------------------------------------")
    print("Please select a preset task or define a custom one:\n")

    tasks = {
        "1": (
            "Analyze the entire codebase, identify potential areas for improvement, and create a brief report."
        ),
        "2": (
            "Find all occurrences of 'TODO' or 'FIXME' comments in the source code and list their locations."
        ),
        "3": (
            "Based on the pyproject.toml, verify that all dependencies are correctly imported and used."
        ),
        "4": (
            "Generate a summary of the project structure, highlighting key modules and their purposes."
        ),
    }

    for key, value in tasks.items():
        print(f"{key}. {value}")
    print("5. Enter a custom task")
    print("\n")

    choice = input("Your choice (1-5): ")

    if choice in tasks:
        return tasks[choice]
    elif choice == "5":
        return input("Please enter your custom task: ")
    else:
        print("❌ Invalid choice. Exiting.")
        return None


async def main():
    """
    Main function to parse CLI arguments and run the SWE agent.
    """
    # 首先禁用所有的asyncio调试日志，即使在DEBUG模式
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        description="""
🏗️  SWE Agent CLI - A smart agent for software engineering tasks.

This agent can analyze code, perform modifications, and execute tasks within your workspace.
""",
        epilog="""
Examples:
  python run_swe_agent.py "Refactor the 'utils' module to improve modularity."
  python run_swe_agent.py -i
  python run_swe_agent.py "Fix bugs in authentication" --debug
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "task",
        nargs="?",  # Makes the task optional
        default=None,
        help="The software engineering task for the agent to perform.",
    )

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode to select from a list of predefined tasks.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for important application logs (excludes verbose library logs).",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all debug logs, including detailed library logs (very verbose).",
    )

    args = parser.parse_args()

    # 如果开启了调试模式，先配置全局日志
    if args.debug:
        _setup_logging(debug=True)

        # 如果不是明确要求详细日志，则始终抑制特定模块
        if not args.verbose:
            # 确保这些库不会产生过多日志
            logging.getLogger("asyncio").setLevel(logging.WARNING)
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            logging.getLogger("openai").setLevel(logging.WARNING)
            logging.getLogger("langchain").setLevel(logging.INFO)
    else:
        _setup_logging(debug=False)

    task_to_run = ""

    if args.interactive:
        task_to_run = interactive_mode()
    elif args.task:
        task_to_run = args.task
    else:
        # If no task and not interactive, show help and exit
        parser.print_help()
        return

    if task_to_run:
        workspace_path = os.getcwd()
        await run_agent(task_to_run, workspace_path, debug=args.debug)


if __name__ == "__main__":
    # 设置默认异常处理程序，确保未捕获的异常也能显示堆栈
    def exception_handler(exc_type, exc_value, exc_traceback):
        print(f"\n❌ Uncaught {exc_type.__name__}: {exc_value}")
        print("🔍 Error Traceback:")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    # 在debug模式下，设置全局异常处理器
    if "--debug" in sys.argv:
        sys.excepthook = exception_handler

    asyncio.run(main())
