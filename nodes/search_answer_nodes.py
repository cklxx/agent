from pocketflow import Node
from tools.tavily import tavily_search
from utils.call_llm import call_llm, stream_llm
from typing import List, Dict
import os
import logging
import json
import re

""" 搜索节点  暂时不用了 """
class SearchNode(Node):
    """Node to perform web search using Tavily API"""
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.max_retries = 1
        self.cur_retry = 0
        self.successors = {}

    def prep(self, shared: Dict) -> str:
        return shared.get("question", "")

    def exec(self, question: str) -> str:
        if not question:
            return ""
        return tavily_search(question, self.api_key)

    def post(self, shared: Dict, prep_res: str, exec_res: str) -> str:
        shared["search_result"] = exec_res
        return "default"

def mock_llm(messages, with_function_call=False):
    content = messages[0]["content"] if messages else ""
    # 尝试从内容中提取当前参数
    return "模拟思考：，内容：" + content

class AnswerNode(Node):
    """只负责最终答案生成，调用LLM"""
    def prep(self, shared: Dict) -> str:
        # 汇总所有sequential_thoughts
        thought = shared.get("thought", [])
        if not thought:
            # 没有多步思考，直接返回用户问题和工具结果
            question = shared.get('question', '')
            tool_result = shared.get('tool_execution_result', '')
            return f"用户问题：{question}\n工具返回结果：{tool_result}\n请基于工具结果直接回答用户问题。 /think"
        summary = ""
        for i, t in enumerate(thought, 1):
            if isinstance(t, dict):
                summary += f"【第{i}步】{t.get('thought', json.dumps(t, ensure_ascii=False))}\n"
            else:
                summary += f"【第{i}步】{t}\n"
        return f"多步推理过程如下：\n{summary}\n请基于以上推理链，回答用户问题：{shared.get('question', '')}"
    def exec(self, question: str) -> str:
        messages = [{"role": "user", "content": question}]
        # 调用 stream_llm 并返回生成器
        return stream_llm(messages, with_function_call=True)
    def post(self, shared: Dict, prep_res: str, exec_res: str) -> str:
        # 迭代流式输出并拼接结果
        final_answer = ""
        try:
            for chunk in exec_res:
                print(chunk, end='') # Print without newline
                final_answer += chunk
                # 可选：在这里可以处理每个chunk，例如实时显示给用户
                # logging.info(f"Stream chunk: {chunk}")
        except Exception as e:
            logging.error(f"[AnswerNode.post] Error processing stream: {e}")
            final_answer += f"Error processing stream: {e}"

        print() # Print a newline after the stream finishes

        shared["answer"] = final_answer.strip() # Strip to remove leading/trailing whitespace
        return "default" 