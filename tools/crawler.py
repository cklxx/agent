import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set
import logging

class WebCrawler:
    """Simple web crawler that extracts content and follows links"""
    def __init__(self, base_url: str, max_pages: int = 10):
        self.base_url = base_url
        self.max_pages = max_pages
        self.visited: Set[str] = set()
        # 添加默认请求头，模拟浏览器
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh,en;q=0.9',
            'Cookie': 'rewardsn=; wxtokenkey=777; _qimei_q36=; _qimei_h38=3c62efce6b41c2bd88ba068903000003418316; RK=3sN9mNIDci; ptcz=b9cd1c9dca9bfc739c267b3553ecae9558b3cef705eb26e8c0d7d78d5d085503; ua_id=lAxhWun3jEjC9b6TAAAAAGEZdqmaCxppf0fecgFAxuY=; wxuin=26667516031044; mm_lang=zh_CN; cert=L5rr8Mj5fkpUuTfM3pLNiauIAC11pPb8; eas_sid=G1i7f2d790Q1d6H3k7W0C9P1M4; pgv_info=ssid=s3470382100; pgv_pvid=2921969913; IED_LOG_INFO2=userUin%3D2433696111%26nickName%3Doo%26nickname%3Doo%26userLoginTime%3D1727069464%26logtype%3Dqq%26loginType%3Dqq%26uin%3D2433696111; wetest_lang=zh; utm_platform=webv2_plat_PC; _ga_0KGGHBND6H=GS1.1.1739433009.1.0.1739433009.0.0.0; _ga=GA1.1.24241448.1739433010; qq_domain_video_guid_verify=f3b34723f6429ca0; o_cookie=2433696111; video_omgid=b56b84b2911afcac6fe9d789efe9a520; vversion_name=8.5.50; _qimei_fingerprint=7e396153e9286065ffadd61ae1a4330c; uuid=f7b02c46b9e6e88996c88733e96d0082; xid=bd42b2a3fa21bf573d81b68a13b52e00; _clck=3597799382|1|ftz|0' # 如果需要，可以在这里添加 cookie，但不推荐硬编码
        }
    def is_valid_url(self, url: str) -> bool:
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        return base_domain == url_domain
    def extract_page_content(self, url: str) -> Dict | None:
        try:
            # 在这里传入 headers
            response = requests.get(url, headers=self.headers)
            response.raise_for_status() # 检查HTTP请求是否成功
            soup = BeautifulSoup(response.text, "html.parser")
            content = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "text": soup.get_text(separator="\n", strip=True), # 保持提取完整文本，但日志不打印
                "links": []
            }
            for link in soup.find_all("a"):
                href = link.get("href")
                if href:
                    absolute_url = urljoin(url, href)
                    if self.is_valid_url(absolute_url):
                        content["links"].append(absolute_url)
            # 打印摘要日志，而不是完整内容
            logging.info(f"✅ Extracted: {url} | Title: {content['title']} | Links found: {len(content['links'])}")
            return content
        except Exception as e:
            logging.error(f"Error crawling {url}: {str(e)}")
            return None
    def crawl(self) -> List[Dict]:
        to_visit = [self.base_url]
        results = []
        logging.info(f"Crawler started with base URL: {self.base_url}, max_pages: {self.max_pages}")
        while to_visit and len(self.visited) < self.max_pages:
            url = to_visit.pop(0)
            if url in self.visited:
                logging.info(f"⏭️ Skipping already visited: {url}")
                continue

            logging.info(f"🌐 Crawling: {url}")
            content = self.extract_page_content(url)

            if content:
                self.visited.add(url)
                logging.info(f"✔️ Added to visited: {url} (Total visited: {len(self.visited)})")
                results.append(content)
                # 过滤掉已经访问过或已在队列中的链接
                new_urls = []
                for link in content.get("links", []):
                    if link not in self.visited and link not in to_visit:
                        new_urls.append(link)
                        # logging.debug(f"➕ Adding to visit queue: {link}") # 如果需要更详细的队列添加日志，可以取消注释
                to_visit.extend(new_urls)
                # logging.info(f"🔄 to_visit queue size: {len(to_visit)}") # 打印队列大小 (可选)

        logging.info(f"Crawler finished. Visited {len(self.visited)} pages.")
        return results 