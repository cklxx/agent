from pocketflow import Node
from tools.parser import analyze_site
from typing import Dict

class ParserNode(Node):
    """Node to analyze crawled site content and output structured analysis"""
    def prep(self, shared: Dict) -> object:
        # 期望 shared["crawl_results"] 里有抓取结果
        return shared.get("crawl_results", [])

    def exec(self, crawl_results: object) -> object:
        if not crawl_results:
            return []
        return analyze_site(crawl_results)

    def post(self, shared: Dict, prep_res: object, exec_res: object) -> str:
        shared["analyze_results"] = exec_res
        return "default" 