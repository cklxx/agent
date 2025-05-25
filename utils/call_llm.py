import yaml
from openai import OpenAI
import logging

# 读取conf.yaml配置
with open("conf.yaml", "r") as f:
    conf = yaml.safe_load(f)

api_key = conf.get("BASIC_MODEL", {}).get("api_key", "")
base_url = conf.get("BASIC_MODEL", {}).get("base_url", None)
model = conf.get("BASIC_MODEL", {}).get("model", "gpt-3.5-turbo-1106")

client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

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

def call_llm(messages, with_function_call=False, **kwargs):
    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
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
                    return call_llm(messages, with_function_call=False)
        logging.info("[call_llm] LLM返回reasoning：%s", msg.reasoning)
        return msg.content
    except Exception as e:
        logging.error("[call_llm] LLM请求失败！messages=%s, kwargs=%s, error=%s", messages, kwargs, e)
        raise 

def stream_llm(messages, with_function_call=False, **kwargs):
    """
    使用流式聊天完成请求调用 LLM。
    """
    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
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