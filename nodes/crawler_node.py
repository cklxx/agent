from pocketflow import Node
from tools.crawler import WebCrawler
from typing import Dict

class CrawlerNode(Node):
    """Node to crawl a website and output crawl results"""
    def prep(self, shared: Dict) -> str:
        # 期望 shared["url"] 里有要抓取的网址
        return shared.get("url", "")

    def exec(self, url: str) -> object:
        if not url:
            return []
        crawler = WebCrawler(url, max_pages=5)
        return crawler.crawl()

    def post(self, shared: Dict, prep_res: str, exec_res: object) -> str:
        shared["crawl_results"] = exec_res
        return "default" 