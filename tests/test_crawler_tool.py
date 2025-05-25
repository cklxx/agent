import unittest
from unittest.mock import patch, MagicMock
from tools.crawler import WebCrawler
import requests

class TestWebCrawler(unittest.TestCase):
    def setUp(self):
        self.crawler = WebCrawler(base_url="http://example.com")

    def test_is_valid_url(self):
        # Test cases for is_valid_url
        self.assertTrue(self.crawler.is_valid_url("http://example.com/path"))
        self.assertFalse(self.crawler.is_valid_url("http://sub.example.com/path"))
        self.assertTrue(self.crawler.is_valid_url("https://example.com/path")) # Scheme difference
        self.assertFalse(self.crawler.is_valid_url("http://another.com/path"))
        self.assertFalse(self.crawler.is_valid_url("ftp://example.com/path")) # Different scheme
        self.assertTrue(self.crawler.is_valid_url("http://example.com")) # Exactly base url
        self.assertTrue(self.crawler.is_valid_url("http://example.com/")) # Base url with slash
        self.assertFalse(self.crawler.is_valid_url("http://example.com:8080/path")) # Different port

    @patch('tools.crawler.requests.get')
    @patch('tools.crawler.BeautifulSoup')
    def test_extract_page_content(self, mock_beautiful_soup, mock_requests_get):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head><title>Test Title</title></head>
            <body>
                <p>Some text here.</p>
                <a href="/path1">Link 1</a>
                <a href="http://example.com/path2">Link 2</a>
                <a href="http://sub.example.com/path3">External Link</a>
                <a href="https://example.com/path4">Secure Link</a>
            </body>
        </html>
        """
        mock_requests_get.return_value = mock_response

        mock_soup = MagicMock()
        mock_soup.title.string = "Test Title"
        mock_soup.get_text.return_value = "Test Title Some text here. Link 1 Link 2 External Link Secure Link"
        
        # Mock find_all for links
        mock_a_tag_1 = MagicMock()
        mock_a_tag_1.get.return_value = "/path1"
        mock_a_tag_2 = MagicMock()
        mock_a_tag_2.get.return_value = "http://example.com/path2"
        mock_a_tag_3 = MagicMock()
        mock_a_tag_3.get.return_value = "http://sub.example.com/path3" # Invalid
        mock_a_tag_4 = MagicMock()
        mock_a_tag_4.get.return_value = "https://example.com/path4" # Valid (scheme difference)

        mock_soup.find_all.return_value = [mock_a_tag_1, mock_a_tag_2, mock_a_tag_3, mock_a_tag_4]
        mock_beautiful_soup.return_value = mock_soup

        result = self.crawler.extract_page_content("http://example.com/testpage")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], "Test Title")
        self.assertEqual(result['text'], "Test Title Some text here. Link 1 Link 2 External Link Secure Link")
        self.assertIn("http://example.com/path1", result['links'])
        self.assertIn("http://example.com/path2", result['links'])
        self.assertNotIn("http://sub.example.com/path3", result['links']) # External link
        self.assertIn("https://example.com/path4", result['links']) # Scheme difference but valid domain
        mock_requests_get.assert_called_once_with("http://example.com/testpage", timeout=5)
        mock_beautiful_soup.assert_called_once_with(mock_response.text, 'html.parser')

        # Test no title
        mock_soup.title = None
        result_no_title = self.crawler.extract_page_content("http://example.com/notitle")
        self.assertIsNotNone(result_no_title)
        self.assertIsNone(result_no_title['title'])

        # Test no links
        mock_soup.find_all.return_value = []
        result_no_links = self.crawler.extract_page_content("http://example.com/nolinks")
        self.assertIsNotNone(result_no_links)
        self.assertEqual(result_no_links['links'], [])
        
        # Test requests.get raising an exception
        mock_requests_get.side_effect = requests.exceptions.RequestException("Test error")
        with patch('tools.crawler.logging.error') as mock_logging_error:
            result_exception = self.crawler.extract_page_content("http://example.com/errorpage")
            self.assertIsNone(result_exception)
            mock_logging_error.assert_called_once()

    @patch('tools.crawler.WebCrawler.extract_page_content')
    def test_crawl(self, mock_extract_page_content):
        # Scenario 1: extract_page_content returns content with links
        mock_extract_page_content.side_effect = [
            {'title': 'Page 1', 'text': 'Text 1', 'links': ['http://example.com/page2']},
            {'title': 'Page 2', 'text': 'Text 2', 'links': []}
        ]
        results = self.crawler.crawl(max_pages=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'Page 1')
        self.assertEqual(results[1]['title'], 'Page 2')
        self.assertIn('http://example.com', self.crawler.visited)
        self.assertIn('http://example.com/page2', self.crawler.visited)
        self.assertEqual(mock_extract_page_content.call_count, 2)
        mock_extract_page_content.assert_any_call('http://example.com')
        mock_extract_page_content.assert_any_call('http://example.com/page2')

        # Reset visited for next scenario
        self.crawler.visited = set()
        mock_extract_page_content.reset_mock()

        # Scenario 2: extract_page_content returns content with no new links
        mock_extract_page_content.side_effect = [
            {'title': 'Page 1', 'text': 'Text 1', 'links': ['http://example.com']} # Link to itself
        ]
        results = self.crawler.crawl(max_pages=5) # max_pages is high, but should stop after 1
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Page 1')
        self.assertIn('http://example.com', self.crawler.visited)
        mock_extract_page_content.assert_called_once_with('http://example.com')
        
        self.crawler.visited = set()
        mock_extract_page_content.reset_mock()

        # Scenario 3: extract_page_content returns None for some URLs
        mock_extract_page_content.side_effect = [
            {'title': 'Page 1', 'text': 'Text 1', 'links': ['http://example.com/errorpage', 'http://example.com/page2']},
            None, # Simulating error on /errorpage
            {'title': 'Page 2', 'text': 'Text 2', 'links': []}
        ]
        results = self.crawler.crawl(max_pages=3)
        self.assertEqual(len(results), 2) # Page 1 and Page 2, errorpage is skipped
        self.assertEqual(results[0]['title'], 'Page 1')
        self.assertEqual(results[1]['title'], 'Page 2')
        self.assertIn('http://example.com', self.crawler.visited)
        self.assertIn('http://example.com/errorpage', self.crawler.visited) # Visited, but no content
        self.assertIn('http://example.com/page2', self.crawler.visited)
        self.assertEqual(mock_extract_page_content.call_count, 3)
        mock_extract_page_content.assert_any_call('http://example.com')
        mock_extract_page_content.assert_any_call('http://example.com/errorpage')
        mock_extract_page_content.assert_any_call('http://example.com/page2')

        self.crawler.visited = set()
        mock_extract_page_content.reset_mock()

        # Scenario 4: Test max_pages limit
        mock_extract_page_content.side_effect = [
            {'title': 'Page 1', 'text': 'Text 1', 'links': ['http://example.com/page2']},
            {'title': 'Page 2', 'text': 'Text 2', 'links': ['http://example.com/page3']},
            # Should not reach page 3
        ]
        results = self.crawler.crawl(max_pages=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Page 1')
        self.assertIn('http://example.com', self.crawler.visited)
        self.assertNotIn('http://example.com/page2', self.crawler.visited) # Not visited due to max_pages
        mock_extract_page_content.assert_called_once_with('http://example.com')

if __name__ == '__main__':
    unittest.main()
