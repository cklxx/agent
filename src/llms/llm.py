# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict
import os
import logging

from langchain_openai import ChatOpenAI

from src.config import load_yaml_config
from src.config.agents import LLMType

# 设置日志
logger = logging.getLogger(__name__)

# Cache for LLM instances
_llm_cache: dict[LLMType, ChatOpenAI] = {}


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
        logger.debug(f"从环境变量加载配置: {llm_type}, 配置项: {list(conf.keys())}")

    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> ChatOpenAI:
    logger.info(f"创建LLM实例: {llm_type}")

    llm_type_map = {
        "reasoning": conf.get("REASONING_MODEL", {}),
        "basic": conf.get("BASIC_MODEL", {}),
        "vision": conf.get("VISION_MODEL", {}),
    }
    llm_conf = llm_type_map.get(llm_type)
    if not isinstance(llm_conf, dict):
        logger.error(f"无效的LLM配置: {llm_type}")
        raise ValueError(f"Invalid LLM Conf: {llm_type}")

    # Get configuration from environment variables
    env_conf = _get_env_llm_conf(llm_type)

    # Merge configurations, with environment variables taking precedence
    merged_conf = {**llm_conf, **env_conf}

    if not merged_conf:
        logger.error(f"未找到LLM配置: {llm_type}")
        raise ValueError(f"Unknown LLM Conf: {llm_type}")

    # 记录关键配置信息（隐藏敏感信息）
    safe_conf = {}
    for key, value in merged_conf.items():
        if key == "api_key":
            safe_conf[key] = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        else:
            safe_conf[key] = value

    logger.info(f"LLM配置: {safe_conf}")

    try:
        llm = ChatOpenAI(**merged_conf)
        logger.info(f"LLM实例创建成功: {llm_type}")
        return llm
    except Exception as e:
        logger.error(f"创建LLM实例失败: {str(e)}")
        raise


def get_llm_by_type(
    llm_type: LLMType,
) -> ChatOpenAI:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    if llm_type in _llm_cache:
        logger.debug(f"使用缓存的LLM实例: {llm_type}")
        return _llm_cache[llm_type]

    logger.info(f"首次创建LLM实例: {llm_type}")

    try:
        conf = load_yaml_config(
            str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())
        )
        logger.debug("配置文件加载成功")

        llm = _create_llm_use_conf(llm_type, conf)
        _llm_cache[llm_type] = llm

        logger.info(f"LLM实例已缓存: {llm_type}")
        return llm

    except Exception as e:
        logger.error(f"获取LLM实例失败: {str(e)}")
        raise


# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")


if __name__ == "__main__":
    # Initialize LLMs for different purposes - now these will be cached
    basic_llm = get_llm_by_type("basic")
    print(basic_llm.invoke("Hello"))
