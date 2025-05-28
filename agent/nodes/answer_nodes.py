from pocketflow import Node
from agent.tools.tavily import tavily_search
from agent.utils.call_llm import call_llm, stream_llm
from typing import List, Dict, TypedDict, Annotated, Sequence
import os
import logging
import json
import re
from langgraph.graph import StateGraph, END
import time

class AnswerNode:
    """Responsible for final answer generation, calls LLM"""
    def __call__(self, state: dict) -> dict:
        # Prepare input
        question = state.get('question', '')
        
        # Get all tool execution results
        tool_results = state.get('tool_results', [])
        tool_results_text = "\n".join([
            f"Step {i+1}:\n{result}" 
            for i, result in enumerate(tool_results)
        ]) if tool_results else "No tool results available."
        
        # Get tool execution history
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
        
        # Build prompt
        prompt = f"""User Question: {question}

Tool Execution Results:
{tool_results_text}

Tool Execution History:
{tool_history_text}

Please generate a complete answer based on all the tool execution results and history above. Note:
1. Integrate all information returned by the tools
2. Consider both successful and failed tool executions
3. If some tools failed to execute, mention this in your answer
4. Ensure the answer is complete and coherent
"""
        
        # Call LLM
        messages = [{"role": "user", "content": prompt}]
        try:
            # Use streaming output
            final_answer = ""
            for chunk in stream_llm(messages, with_function_call=True, task_type="high_quality_content"):
                print(chunk, end='')
                final_answer += chunk
            print()  # New line
            
            # Update state
            state["answer"] = final_answer.strip()
        except Exception as e:
            logging.error(f"[AnswerNode] Error processing stream: {e}")
            state["answer"] = f"Error processing stream: {e}"
        
        return state 