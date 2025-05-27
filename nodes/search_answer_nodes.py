from pocketflow import Node
from tools.tavily import tavily_search
from utils.call_llm import call_llm, stream_llm
from typing import List, Dict, TypedDict, Annotated, Sequence
import os
import logging
import json
import re
from langgraph.graph import StateGraph, END
import time

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

class AnswerNode:
    """负责最终答案生成，调用LLM"""
    def __call__(self, state: dict) -> dict:
        # 准备输入
        question = state.get('question', '')
        
        # 获取所有工具执行结果
        tool_results = state.get('tool_results', [])
        tool_results_text = "\n".join([
            f"Step {i+1}:\n{result}" 
            for i, result in enumerate(tool_results)
        ]) if tool_results else "No tool results available."
        
        # 获取工具执行历史
        tool_history = state.get('tool_history', [])
        tool_history_text = "\n".join([
            f"Execution {i+1}:\n" +
            f"Tool: {hist.get('tool', 'Unknown')}\n" +
            f"Parameters: {hist.get('parameters', {})}\n" +
            f"Result: {hist.get('result', 'No result')}\n" +
            f"Status: {hist.get('status', 'Unknown')}\n" +
            f"Execution Time: {hist.get('execution_time', 0):.2f}s\n" +
            f"Reason: {hist.get('reason', 'No reason provided')}"
            for i, hist in enumerate(tool_history)
        ]) if tool_history else "No tool execution history available."
        
        # 构建提示词
        prompt = f"""用户问题：{question}

工具执行结果：
{tool_results_text}

工具执行历史：
{tool_history_text}

请基于以上所有工具执行结果和历史记录，生成一个完整的答案。注意：
1. 综合所有工具返回的信息
2. 考虑工具执行的成功和失败情况
3. 如果某些工具执行失败，在答案中说明这一点
4. 确保答案完整且连贯
"""
        
        # 调用 LLM
        messages = [{"role": "user", "content": prompt}]
        try:
            # 使用流式输出
            final_answer = ""
            for chunk in stream_llm(messages, with_function_call=True, task_type="high_quality_content"):
                print(chunk, end='')
                final_answer += chunk
            print()  # 换行
            
            # 更新状态
            state["answer"] = final_answer.strip()
        except Exception as e:
            logging.error(f"[AnswerNode] Error processing stream: {e}")
            state["answer"] = f"Error processing stream: {e}"
        
        return state 