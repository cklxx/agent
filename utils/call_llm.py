import yaml
from openai import OpenAI
import logging
from utils.config import config

# 全局变量，用于存储不同的模型客户端
_clients = {}
_models = {}

# 初始化模型配置
def _init_model_configs():
    """初始化所有模型配置"""
    global _clients, _models
    
    # 基础模型配置
    basic_config = config.get_basic_model_config()
    _models["basic"] = {
        "model": basic_config.get("model", "gpt-3.5-turbo"),
        "api_key": basic_config.get("api_key", ""),
        "base_url": basic_config.get("base_url", None),
        "max_tokens": basic_config.get("max_tokens", 1024)
    }
    
    # 大型模型配置
    large_config = config.get("LARGE_MODEL", {})
    if large_config:
        _models["large"] = {
            "model": large_config.get("model", "gpt-4o"),
            "api_key": large_config.get("api_key", ""),
            "base_url": large_config.get("base_url", None),
            "max_tokens": large_config.get("max_tokens", 4096)
        }
    
    # 中型模型配置
    medium_config = config.get("MEDIUM_MODEL", {})
    if medium_config:
        _models["medium"] = {
            "model": medium_config.get("model", "gpt-3.5-turbo-16k"),
            "api_key": medium_config.get("api_key", ""),
            "base_url": medium_config.get("base_url", None),
            "max_tokens": medium_config.get("max_tokens", 2048)
        }
    
    # 小型模型配置
    small_config = config.get("SMALL_MODEL", {})
    if small_config:
        _models["small"] = {
            "model": small_config.get("model", "mistral-small"),
            "api_key": small_config.get("api_key", ""),
            "base_url": small_config.get("base_url", None),
            "max_tokens": small_config.get("max_tokens", 1024)
        }
    
    # 初始化客户端
    for model_type, model_config in _models.items():
        api_key = model_config["api_key"]
        base_url = model_config["base_url"]
        _clients[model_type] = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

# 初始化模型配置
_init_model_configs()

# 根据任务类型选择合适的模型
def get_model_for_task(task_type=None):
    """
    根据任务类型选择合适的模型
    
    Args:
        task_type (str): 任务类型，可以是 "complex_reasoning", "general_conversation", "quick_response" 等
                         如果为None，则使用基础模型
    
    Returns:
        tuple: (client, model_name, max_tokens) 客户端实例、模型名称和最大token数
    """
    # 默认使用基础模型
    model_size = "basic"
    
    # 根据任务类型选择模型大小
    if task_type:
        if task_type in ["complex_reasoning", "complex_tool_chains", "high_quality_content"]:
            if "large" in _models:
                model_size = "large"
        elif task_type in ["general_conversation", "standard_tool_calls", "content_generation"]:
            if "medium" in _models:
                model_size = "medium"
        elif task_type in ["quick_response", "simple_tasks", "classification"]:
            if "small" in _models:
                model_size = "small"
    
    # 获取选择的模型配置
    model_config = _models[model_size]
    client = _clients[model_size]
    
    return client, model_config["model"], model_config["max_tokens"]

def get_time():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

functions = [
    {
        "name": "get_time",
        "description": "获取当前时间",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def call_llm(messages, with_function_call=False, task_type=None, **kwargs):
    """
    调用LLM模型
    
    Args:
        messages (list): 消息列表
        with_function_call (bool): 是否启用函数调用
        task_type (str): 任务类型，用于选择合适的模型
        **kwargs: 其他参数
    
    Returns:
        str: 模型回复内容
    """
    try:
        # 根据任务类型选择模型
        client, model_name, max_tokens = get_model_for_task(task_type)
        
        logging.info(f"[call_llm] 使用模型: {model_name} 进行任务类型: {task_type or '默认'}")
        
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", max_tokens),
        }
        
        if with_function_call:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": f
                } for f in functions
            ]
            kwargs["tool_choice"] = "auto"
            
        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.type == 'function' and tool_call.function.name == "get_time":
                    result = get_time()
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": "get_time",
                                    "arguments": "{}"
                                }
                            }
                        ]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
                    return call_llm(messages, with_function_call=False, task_type=task_type)
                    
        if hasattr(msg, 'reasoning') and msg.reasoning:
            logging.info("[call_llm] LLM返回reasoning：%s", msg.reasoning)
            
        return msg.content
        
    except Exception as e:
        logging.error("[call_llm] LLM请求失败！messages=%s, kwargs=%s, error=%s", messages, kwargs, e)
        raise 

def stream_llm(messages, with_function_call=False, task_type=None, **kwargs):
    """
    使用流式聊天完成请求调用 LLM。
    
    Args:
        messages (list): 消息列表
        with_function_call (bool): 是否启用函数调用
        task_type (str): 任务类型，用于选择合适的模型
        **kwargs: 其他参数
        
    Yields:
        str: 模型回复的内容片段
    """
    try:
        # 根据任务类型选择模型
        client, model_name, max_tokens = get_model_for_task(task_type)
        
        logging.info(f"[stream_llm] 使用模型: {model_name} 进行任务类型: {task_type or '默认'}")
        
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", max_tokens),
            "stream": True,  # Enable streaming
        }
        
        if with_function_call:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": f
                } for f in functions
            ]
            kwargs["tool_choice"] = "auto"

        logging.info("[stream_llm] Calling LLM with streaming...")
        response = client.chat.completions.create(**kwargs)

        # Iterate over the streamed response
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            # You might also want to handle tool_calls delta here if needed for streaming function calls
            # elif chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
            #     yield chunk.choices[0].delta.tool_calls

    except Exception as e:
        logging.error("[stream_llm] LLM流式请求失败！messages=%s, kwargs=%s, error=%s", messages, kwargs, e)
        # Depending on desired error handling, you might raise the exception or yield an error message
        raise 