import os
import httpx
from typing import Dict, List, Optional
import logging
from utils.config import config

class TavilySearchTool:
    """Tavily 搜索工具，结构化返回结果"""
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Tavily 搜索工具
        Args:
            api_key (str, optional): Tavily API key，默认读取 TAVILY_API_KEY 环境变量
        """
        self.api_key = api_key or config.get_env("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("Tavily API key 未配置，请设置 TAVILY_API_KEY 环境变量或传入 api_key 参数。")

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        使用 Tavily API 进行搜索
        Args:
            query (str): 搜索关键词
            num_results (int, optional): 返回结果数量，默认5
        Returns:
            List[Dict]: 每个结果包含 title、snippet、link
        """
        url = "https://api.tavily.com/search"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        json_data = {
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": num_results
        }
        try:
            resp = httpx.post(url, headers=headers, json=json_data, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                processed_results = []
                for result in results[:num_results]:
                    processed_results.append({
                        "title": result.get("title", "无标题"),
                        "snippet": result.get("content", ""),
                        "link": result.get("url", "无链接")
                    })
                return processed_results
            else:
                logging.error(f"Tavily搜索失败，状态码：{resp.status_code}")
                return []
        except Exception as e:
            logging.error(f"Tavily搜索异常：{e}")
            return []

def tavily_search(query: str, api_key: str = None, num_results: int = 5):
    """
    兼容外部调用的 Tavily 搜索函数，返回格式为字符串。
    Args:
        query (str): 搜索关键词
        api_key (str, optional): Tavily API key
        num_results (int, optional): 返回结果数量，默认5
    Returns:
        str: 搜索结果的字符串拼接
    """
    try:
        tool = TavilySearchTool(api_key)
        results = tool.search(query, num_results)
        if not results:
            return "未找到相关搜索结果。"
        result_str = "\n".join([
            f"[{i+1}] {item['title']}\n{item['snippet']}\n链接: {item['link']}" for i, item in enumerate(results)
        ])
        return result_str
    except Exception as e:
        return f"Tavily 搜索异常: {e}" 