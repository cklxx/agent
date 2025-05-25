import unittest
from unittest.mock import patch, MagicMock
from nodes.crawler_node import CrawlerNode
from tools.crawler import WebCrawler # Needed for isinstance check if not mocking __init__

class TestCrawlerNode(unittest.TestCase):

    def test_prep_method(self):
        node = CrawlerNode()

        # Scenario 1: URL in shared
        shared_s1 = {"url": "http://example.com"}
        self.assertEqual(node.prep(shared_s1), "http://example.com")

        # Scenario 2: URL not in shared
        shared_s2 = {}
        self.assertEqual(node.prep(shared_s2), "") # As per current implementation

        # Scenario 3: shared is None
        self.assertIsNone(node.prep(None)) # .get on None raises AttributeError, but current code is `shared.get("url", "")`

        # Scenario 3b: key "url" exists but is None
        shared_s3b = {"url": None}
        self.assertIsNone(node.prep(shared_s3b))


    @patch('nodes.crawler_node.WebCrawler') # Patch WebCrawler in the crawler_node module
    def test_exec_method(self, MockWebCrawler):
        node = CrawlerNode(max_pages=10)

        # Scenario 1: Valid URL provided
        mock_crawler_instance = MockWebCrawler.return_value
        mock_crawl_results = [{"url": "http://example.com", "title": "Test"}]
        mock_crawler_instance.crawl.return_value = mock_crawl_results
        
        url_s1 = "http://example.com"
        result_s1 = node.exec(url_s1)
        
        MockWebCrawler.assert_called_once_with(base_url=url_s1, max_pages=10)
        mock_crawler_instance.crawl.assert_called_once_with()
        self.assertEqual(result_s1, mock_crawl_results)

        MockWebCrawler.reset_mock() # Reset mock for the next scenario

        # Scenario 2: Empty URL provided
        result_s2_empty = node.exec("")
        self.assertEqual(result_s2_empty, [])
        MockWebCrawler.assert_not_called() # Should not be called for empty URL

        # Scenario 2b: None URL provided
        result_s2_none = node.exec(None)
        self.assertEqual(result_s2_none, [])
        MockWebCrawler.assert_not_called() # Should not be called for None URL

        MockWebCrawler.reset_mock()

        # Scenario 3: WebCrawler.crawl raises an exception
        mock_crawler_instance_s3 = MockWebCrawler.return_value
        mock_crawler_instance_s3.crawl.side_effect = Exception("Crawl failed")
        
        url_s3 = "http://anotherexample.com"
        with self.assertRaises(Exception) as context:
            node.exec(url_s3)
        self.assertTrue("Crawl failed" in str(context.exception))
        MockWebCrawler.assert_called_once_with(base_url=url_s3, max_pages=10)
        mock_crawler_instance_s3.crawl.assert_called_once_with()


    def test_post_method(self):
        node = CrawlerNode()
        shared = {}
        prep_res_url = "http://example.com" # Not directly used by post, but part of the flow
        exec_res_crawl_data = [{"url": "http://example.com", "title": "Test Page"}]

        result = node.post(shared, prep_res_url, exec_res_crawl_data)

        self.assertEqual(shared.get("crawl_results"), exec_res_crawl_data)
        self.assertEqual(result, "default")

        # Test with pre-existing shared data (should be overwritten)
        shared_preexisting = {"other_key": "other_value", "crawl_results": "old_data"}
        exec_res_new_data = [{"url": "http://new.com", "title": "New Page"}]
        result_new = node.post(shared_preexisting, "http://new.com", exec_res_new_data)
        self.assertEqual(shared_preexisting.get("crawl_results"), exec_res_new_data)
        self.assertEqual(shared_preexisting.get("other_key"), "other_value") # Ensure other keys are not lost
        self.assertEqual(result_new, "default")


if __name__ == '__main__':
    unittest.main()
