# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict
import os
import logging
import json
import time

from langchain_openai import ChatOpenAI

from src.config import load_yaml_config
from src.config.agents import LLMType

# Set up logging
logger = logging.getLogger(__name__)

# Cache for LLM instances
_llm_cache: dict[LLMType, ChatOpenAI] = {}

# LLM调试相关导入
try:
    from src.config.llm_debug import get_llm_debugger

    LLM_DEBUG_AVAILABLE = True
except ImportError:
    LLM_DEBUG_AVAILABLE = False
    logger.debug("LLM调试模块未找到，跳过调试功能")


class DebugChatOpenAI(ChatOpenAI):
    """带调试功能的ChatOpenAI包装类"""

    def __init__(self, llm_type: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self.llm_type = llm_type
        self.debugger = get_llm_debugger() if LLM_DEBUG_AVAILABLE else None

    def invoke(self, input, config=None, **kwargs):
        """重写invoke方法，添加调试日志"""
        if self.debugger and self.debugger.enabled:
            # 记录调用开始
            start_time = time.time()

            # 提取消息内容用于调试
            messages = self._extract_messages_for_debug(input)
            if messages:
                self.debugger.log_llm_call(
                    agent_name=f"LLM({self.llm_type})",
                    messages=messages,
                    model_type=self.llm_type,
                    extra_context={
                        "model_name": getattr(self, "model_name", "unknown"),
                        "temperature": getattr(self, "temperature", "unknown"),
                    },
                )

            try:
                # 执行原始调用
                result = super().invoke(input, config, **kwargs)

                # 记录响应
                duration_ms = (time.time() - start_time) * 1000
                self.debugger.log_llm_response(
                    agent_name=f"LLM({self.llm_type})",
                    response=result,
                    duration_ms=duration_ms,
                )

                return result
            except Exception as e:
                if self.debugger:
                    self.debugger.logger.error(f"❌ LLM调用失败: {str(e)}")
                raise
        else:
            # 正常调用，无调试
            return super().invoke(input, config, **kwargs)

    def _extract_messages_for_debug(self, input):
        """从输入中提取消息用于调试显示"""
        messages = []

        if isinstance(input, list):
            for item in input:
                if hasattr(item, "type") and hasattr(item, "content"):
                    # LangChain消息对象
                    messages.append(
                        {
                            "role": item.type,
                            "content": str(item.content),
                            "name": getattr(item, "name", ""),
                        }
                    )
                elif isinstance(item, dict):
                    # 字典格式的消息
                    messages.append(item)
        elif hasattr(input, "messages"):
            # 如果input有messages属性
            return self._extract_messages_for_debug(input.messages)
        elif isinstance(input, str):
            # 纯文本输入
            messages.append({"role": "user", "content": input})

        return messages


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value

    if conf:
        logger.debug(
            f"Load configuration from environment variables: {llm_type}, config items: {list(conf.keys())}"
        )

    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> ChatOpenAI:
    logger.info(f"Creating LLM instance: {llm_type}")

    llm_type_map = {
        "reasoning": conf.get("REASONING_MODEL", {}),
        "basic": conf.get("BASIC_MODEL", {}),
        "vision": conf.get("VISION_MODEL", {}),
    }
    llm_conf = llm_type_map.get(llm_type)
    if not isinstance(llm_conf, dict):
        logger.error(f"Invalid LLM configuration: {llm_type}")
        raise ValueError(f"Invalid LLM Conf: {llm_type}")

    # Get configuration from environment variables
    env_conf = _get_env_llm_conf(llm_type)

    # Merge configurations, with environment variables taking precedence
    merged_conf = {**llm_conf, **env_conf}

    if not merged_conf:
        logger.error(f"LLM configuration not found: {llm_type}")
        raise ValueError(f"Unknown LLM Conf: {llm_type}")

    # Log key configuration information (hide sensitive info)
    safe_conf = {}
    for key, value in merged_conf.items():
        if key == "api_key":
            safe_conf[key] = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        else:
            safe_conf[key] = value

    logger.info(f"LLM configuration: {safe_conf}")

    try:
        # 创建带调试功能的LLM实例
        if LLM_DEBUG_AVAILABLE and os.getenv("LLM_DEBUG", "false").lower() in [
            "true",
            "1",
            "yes",
        ]:
            llm = DebugChatOpenAI(llm_type=llm_type, **merged_conf)
            logger.info(f"Debug-enabled LLM instance created successfully: {llm_type}")
        else:
            llm = ChatOpenAI(**merged_conf)
            logger.info(f"LLM instance created successfully: {llm_type}")
        return llm
    except Exception as e:
        logger.error(f"Failed to create LLM instance: {str(e)}")
        raise


def create_llm_from_env(llm_type: str = "main"):
    """
    从环境变量创建LLM实例
    优先级: 环境变量 > 配置文件
    """
    # Load config from environment variable
    conf = {}
    env_var = f"LLM_CONFIG_{llm_type.upper()}"
    if env_var in os.environ:
        try:
            conf = json.loads(os.environ[env_var])
            logger.debug(
                f"Load config from environment variable: {llm_type}, config items: {list(conf.keys())}"
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in environment variable {env_var}: {e}")

    if conf:
        logger.info(f"Creating LLM instance: {llm_type}")
        return _create_llm_use_conf(llm_type, conf)

    # If no environment variable, load from file
    config = load_yaml_config(
        str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())
    )
    llm_configs = config.get("llms", {})

    if llm_type not in llm_configs:
        logger.error(f"Invalid LLM configuration: {llm_type}")
        available_types = list(llm_configs.keys())
        raise ValueError(
            f"LLM type '{llm_type}' not found in configuration. "
            f"Available types: {available_types}"
        )

    conf = llm_configs[llm_type]
    if not conf:
        logger.error(f"LLM configuration not found: {llm_type}")
        raise ValueError(f"Empty configuration for LLM type: {llm_type}")

    # Log key configuration information (hide sensitive info)
    safe_conf = {k: v for k, v in conf.items() if k not in ["api_key", "password"]}
    logger.info(f"LLM configuration: {safe_conf}")

    try:
        llm = _create_llm_use_conf(llm_type, conf)
        logger.info(f"LLM instance created successfully: {llm_type}")
        return llm
    except Exception as e:
        logger.error(f"Failed to create LLM instance: {str(e)}")
        raise


def get_llm_by_type(
    llm_type: LLMType,
) -> ChatOpenAI:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    if llm_type in _llm_cache:
        logger.debug(f"Using cached LLM instance: {llm_type}")
        return _llm_cache[llm_type]

    logger.info(f"Creating new LLM instance: {llm_type}")

    try:
        conf = load_yaml_config(
            str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())
        )
        logger.debug("Configuration file loaded successfully")

        llm = _create_llm_use_conf(llm_type, conf)
        _llm_cache[llm_type] = llm

        logger.info(f"LLM instance cached: {llm_type}")
        return llm

    except Exception as e:
        logger.error(f"Failed to get LLM instance: {str(e)}")
        raise


def get_llm():
    """Get default LLM instance"""
    try:
        return get_llm_by_type("main")
    except Exception as e:
        logger.error(f"Failed to get LLM instance: {str(e)}")
        raise


# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")


if __name__ == "__main__":
    # Initialize LLMs for different purposes - now these will be cached
    basic_llm = get_llm_by_type("basic")
    print(basic_llm.invoke("Hello"))
