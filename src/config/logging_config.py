# SPDX-License-Identifier: MIT

"""
Logging configuration for the agent system.
专注于LLM和Agent规划的精简日志配置
"""

import logging
import sys


def setup_simplified_logging():
    """设置精简的日志配置，专注于核心功能"""

    # 设置根日志级别
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清除已有的handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 设置精简的格式
    formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(formatter)

    # 添加处理器到根日志
    root_logger.addHandler(console_handler)

    # 设置重要模块的日志级别
    _configure_module_logging()

    print("✅ 精简日志模式已启用 - 专注于LLM和Agent规划输出")


def setup_debug_logging():
    """设置详细的调试日志配置"""

    # 设置根日志级别
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除已有的handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # 设置详细的格式
    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # 添加处理器到根日志
    root_logger.addHandler(console_handler)

    # 设置调试模式的模块日志级别
    _configure_debug_module_logging()

    print("🔧 调试日志模式已启用 - 显示详细信息")


def _configure_module_logging():
    """配置各模块的日志级别 - 精简模式"""

    # 核心模块保持INFO级别
    core_modules = [
        "src.agents.code_agent",
        "src.graph.nodes",
        "src.llms.llm",
        "src.workflow",
    ]
    for module in core_modules:
        logging.getLogger(module).setLevel(logging.INFO)

    # 重要的LLM和规划日志
    important_loggers = [
        "code_agent_llm_planner",
        "code_agent_llm_execution",
        "llm_planner",
        "llm_api",
    ]
    for logger_name in important_loggers:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    # Terminal执行日志 - 精简模式显示主要操作
    logging.getLogger("terminal_execution").setLevel(logging.INFO)

    # Terminal工具模块设置为WARNING级别，减少冗余输出
    logging.getLogger("src.tools.terminal_executor").setLevel(logging.WARNING)

    # 抑制第三方库的冗余日志
    noisy_modules = [
        "httpx",
        "requests",
        "urllib3",
        "langchain",
        "langgraph",
        "openai._base_client",
        "httpcore",
        "httpcore.connection",
        "httpcore.http11",
    ]
    for module in noisy_modules:
        logging.getLogger(module).setLevel(logging.ERROR)

    # OpenAI核心日志保持WARNING级别
    logging.getLogger("openai").setLevel(logging.WARNING)


def _configure_debug_module_logging():
    """配置各模块的日志级别 - 调试模式"""

    # 核心模块开启DEBUG
    core_modules = ["src.agents", "src.graph.nodes", "src.llms", "src.workflow"]
    for module in core_modules:
        logging.getLogger(module).setLevel(logging.DEBUG)

    # 重要的LLM和规划日志
    important_loggers = [
        "code_agent_llm_planner",
        "code_agent_llm_execution",
        "llm_planner",
        "llm_api",
    ]
    for logger_name in important_loggers:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

    # Terminal执行日志 - 调试模式显示详细信息
    logging.getLogger("terminal_execution").setLevel(logging.DEBUG)

    # Terminal工具模块在调试模式下显示INFO级别
    logging.getLogger("src.tools.terminal_executor").setLevel(logging.INFO)

    # 适当控制第三方库日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)


def get_agent_logger(name: str) -> logging.Logger:
    """获取专用的agent日志器"""
    logger = logging.getLogger(f"agent.{name}")
    logger.setLevel(logging.INFO)
    return logger


def get_llm_logger(name: str) -> logging.Logger:
    """获取专用的LLM日志器"""
    logger = logging.getLogger(f"llm.{name}")
    logger.setLevel(logging.INFO)
    return logger


def get_terminal_logger() -> logging.Logger:
    """获取专用的Terminal日志器，格式化Terminal执行信息"""
    logger = logging.getLogger("terminal_execution")
    logger.setLevel(logging.INFO)
    return logger
