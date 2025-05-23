from pocketflow import Node
from tools.tavily import tavily_search
from utils.call_llm import call_llm, stream_llm
from typing import List, Dict
import os
import logging
import json
import re

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

class ThinkingNode(Node):
    """负责多步推理链调度与参数管理，并实际调用LLM生成下一步推理内容"""
    def prep(self, shared: Dict) -> Dict:
        # 获取推理链相关参数
        thought_number = shared.get("thoughtNumber", 1)
        total_thoughts = shared.get("totalThoughts", 3)
        branches = shared.get("branches", [])
        question = shared.get("question", "")
        next_thought_needed = shared.get("nextThoughtNeeded", True)
        thought_history_length = shared.get("thoughtHistoryLength", len(branches))
        # 组装当前推理链上下文
        return {
            "thought_number": thought_number,
            "total_thoughts": total_thoughts,
            "branches": branches,
            "question": question,
            "next_thought_needed": next_thought_needed,
            "thought_history_length": thought_history_length
        }

    def exec(self, context: Dict) -> Dict:
        thought_number = context["thought_number"]
        total_thoughts = context["total_thoughts"]
        branches = context["branches"]
        question = context["question"]
        next_thought_needed = context.get("next_thought_needed", True)
        thought_history_length = context.get("thought_history_length", len(branches))
        # 判断是否继续思考
        if (thought_number > total_thoughts) or (not next_thought_needed):
            logging.info(f"[ThinkingNode.exec] 推理终止，thought_number={thought_number}, total_thoughts={total_thoughts}, next_thought_needed={next_thought_needed}")
            return {
                "continue": False,
                "branches": branches,
                "nextThoughtNeeded": False,
                "thoughtHistoryLength": thought_history_length
            }
        # 拼接前面所有思考内容
        history = ""
        for i, b in enumerate(branches, 1):
            if isinstance(b, dict):
                history += f"【第{i}步】{b.get('thought', str(b))}\n"
            else:
                history += f"【第{i}步】{b}\n"
        prompt = f"已知推理历史：\n{history}\n第{thought_number}步推理，用户问题：{question}\n请给出本步推理内容。"
        logging.info(f"[ThinkingNode.exec] prompt=\n{prompt}")
        messages = [{"role": "user", "content": prompt}]
        thought = call_llm(messages)
        logging.info(f"[ThinkingNode.exec] 第{thought_number}步思考内容: {thought}")
        # 记录到 branches
        branches = branches + [{
            "thought_number": thought_number,
            "thought": thought
        }]
        logging.info(f"[ThinkingNode.exec] 当前 branches: {branches}")
        return {
            "continue": True,
            "branches": branches,
            "nextThoughtNeeded": True,
            "thoughtHistoryLength": len(branches)
        }

    def post(self, shared: Dict, prep_res: Dict, exec_res: Dict) -> str:
        import logging
        # 更新 shared 中的 branches 及相关参数
        shared["branches"] = exec_res["branches"]
        shared["nextThoughtNeeded"] = exec_res.get("nextThoughtNeeded", True)
        shared["thoughtHistoryLength"] = exec_res.get("thoughtHistoryLength", len(exec_res["branches"]))
        logging.info(f"[ThinkingNode.post] branches: {shared['branches']}")
        logging.info(f"[ThinkingNode.post] nextThoughtNeeded: {shared['nextThoughtNeeded']}, thoughtHistoryLength: {shared['thoughtHistoryLength']}")
        # 判断是否继续思考
        if exec_res.get("continue"):
            # 增加 thoughtNumber
            shared["thoughtNumber"] = shared.get("thoughtNumber", 1) + 1
            logging.info(f"[ThinkingNode.post] 继续下一步推理，thoughtNumber={shared['thoughtNumber']}")
            return "continue"
        else:
            # 推理终止
            shared["thought"] = exec_res["branches"]
            logging.info(f"[ThinkingNode.post] 推理终止，thought: {shared.get('thought')}")
            return "default"

class AnswerNode(Node):
    """只负责最终答案生成，调用LLM"""
    def prep(self, shared: Dict) -> str:
        # 汇总所有sequential_thoughts
        thought = shared.get("thought", [])
        if not thought:
            # 没有多步思考，直接返回用户问题和工具结果
            question = shared.get('question', '')
            tool_result = shared.get('tool_execution_result', '')
            return f"用户问题：{question}\n工具返回结果：{tool_result}\n请基于工具结果直接回答用户问题。"
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
                logging.info(chunk)
                final_answer += chunk
                # 可选：在这里可以处理每个chunk，例如实时显示给用户
                # logging.info(f"Stream chunk: {chunk}")
        except Exception as e:
            logging.error(f"[AnswerNode.post] Error processing stream: {e}")
            final_answer += f"Error processing stream: {e}"

        shared["answer"] = final_answer.strip() # Strip to remove leading/trailing whitespace
        return "default" 