import unittest
from unittest.mock import patch, MagicMock
import os
import httpx # Import httpx for mocking
from tools.tavily import TavilySearchTool, tavily_search
import logging

class TestTavilyTool(unittest.TestCase):

    # Test TavilySearchTool.__init__
    def test_init_with_api_key_direct(self):
        tool = TavilySearchTool(api_key="direct_key")
        self.assertEqual(tool.api_key, "direct_key")

    @patch.dict(os.environ, {"TAVILY_API_KEY": "env_key"})
    def test_init_with_api_key_env(self):
        tool = TavilySearchTool()
        self.assertEqual(tool.api_key, "env_key")

    @patch.dict(os.environ, {}, clear=True) # Ensure TAVILY_API_KEY is not set
    def test_init_no_api_key(self):
        with self.assertRaises(ValueError) as context:
            TavilySearchTool()
        self.assertEqual(str(context.exception), "Tavily API key not provided. Set TAVILY_API_KEY environment variable or pass api_key.")

    # Test TavilySearchTool.search
    @patch('tools.tavily.httpx.post')
    def test_search_successful_valid_response(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "content": "Snippet 1", "url": "url1"},
                {"title": "Result 2", "content": "Snippet 2", "url": "url2"},
                {"title": "Result 3", "content": "Snippet 3", "url": "url3"}
            ]
        }
        mock_httpx_post.return_value = mock_response
        
        tool = TavilySearchTool(api_key="test_key")
        results = tool.search("test query")
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], {"title": "Result 1", "snippet": "Snippet 1", "link": "url1"})
        mock_httpx_post.assert_called_once()
        # print(mock_httpx_post.call_args[1]['json']) # For debugging the payload
        self.assertEqual(mock_httpx_post.call_args[1]['json']['query'], "test query")

        # Test num_results
        results_limited = tool.search("test query", num_results=1)
        self.assertEqual(len(results_limited), 1)
        self.assertEqual(results_limited[0], {"title": "Result 1", "snippet": "Snippet 1", "link": "url1"})
        # httpx.post is called again, check num_results in payload
        self.assertEqual(mock_httpx_post.call_args[1]['json']['max_results'], 1)


    @patch('tools.tavily.httpx.post')
    def test_search_successful_empty_results(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_httpx_post.return_value = mock_response
        
        tool = TavilySearchTool(api_key="test_key")
        results = tool.search("test query")
        
        self.assertEqual(results, [])
        mock_httpx_post.assert_called_once_with(
            "https://api.tavily.com/search",
            json={
                "api_key": "test_key",
                "query": "test query",
                "search_depth": "basic",
                "include_answer": False,
                "include_images": False,
                "include_raw_content": False,
                "max_results": 5, # Default
                "include_domains": [],
                "exclude_domains": []
            }
        )

    @patch('tools.tavily.httpx.post')
    @patch('tools.tavily.logging.error')
    def test_search_api_error_status_code(self, mock_logging_error, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_httpx_post.return_value = mock_response
        
        tool = TavilySearchTool(api_key="test_key")
        results = tool.search("test query")
        
        self.assertEqual(results, [])
        mock_logging_error.assert_called_once_with("Tavily API error (500): Internal Server Error")

    @patch('tools.tavily.httpx.post')
    @patch('tools.tavily.logging.error')
    def test_search_api_request_exception(self, mock_logging_error, mock_httpx_post):
        mock_httpx_post.side_effect = httpx.RequestError("Network error")
        
        tool = TavilySearchTool(api_key="test_key")
        results = tool.search("test query")
        
        self.assertEqual(results, [])
        mock_logging_error.assert_called_once_with("Error calling Tavily API: Network error")

    @patch('tools.tavily.httpx.post')
    @patch('tools.tavily.logging.warning')
    def test_search_api_response_missing_results(self, mock_logging_warning, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "no results here"} # Missing 'results' key
        mock_httpx_post.return_value = mock_response
        
        tool = TavilySearchTool(api_key="test_key")
        results = tool.search("test query")
        
        self.assertEqual(results, [])
        mock_logging_warning.assert_called_once_with("Tavily API response missing 'results' key or 'results' is not a list.")

    @patch('tools.tavily.httpx.post')
    @patch('tools.tavily.logging.warning')
    def test_search_api_response_malformed_item(self, mock_logging_warning, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # 'content' key is missing in the first item
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "url": "url1"}, 
                {"title": "Result 2", "content": "Snippet 2", "url": "url2"}
            ]
        }
        mock_httpx_post.return_value = mock_response
        
        tool = TavilySearchTool(api_key="test_key")
        results = tool.search("test query")
        
        self.assertEqual(len(results), 1) # Only the valid item should be returned
        self.assertEqual(results[0], {"title": "Result 2", "snippet": "Snippet 2", "link": "url2"})
        mock_logging_warning.assert_called_once_with("Skipping a result due to missing 'title', 'content', or 'url'.")


    # Test tavily_search (wrapper function)
    @patch('tools.tavily.TavilySearchTool')
    def test_tavily_search_wrapper_successful(self, MockTavilySearchTool):
        mock_search_instance = MockTavilySearchTool.return_value
        mock_search_instance.search.return_value = [
            {"title": "R1", "snippet": "S1", "link": "L1"},
            {"title": "R2", "snippet": "S2", "link": "L2"}
        ]
        
        expected_output = "搜索结果:\n[1] R1 (S1) - L1\n[2] R2 (S2) - L2"
        result = tavily_search("test query", num_results=2)
        
        self.assertEqual(result, expected_output)
        MockTavilySearchTool.assert_called_once() # API key handling implicitly tested by TavilySearchTool init
        mock_search_instance.search.assert_called_once_with("test query", num_results=2)

    @patch('tools.tavily.TavilySearchTool')
    def test_tavily_search_wrapper_empty_results(self, MockTavilySearchTool):
        mock_search_instance = MockTavilySearchTool.return_value
        mock_search_instance.search.return_value = []
        
        expected_output = "未找到相关搜索结果。"
        result = tavily_search("test query")
        
        self.assertEqual(result, expected_output)
        mock_search_instance.search.assert_called_once_with("test query", num_results=3) # Default num_results

    @patch('tools.tavily.TavilySearchTool')
    def test_tavily_search_wrapper_search_exception(self, MockTavilySearchTool):
        mock_search_instance = MockTavilySearchTool.return_value
        mock_search_instance.search.side_effect = Exception("Search failed unexpectedly")
        
        expected_output = "Tavily 搜索异常: Search failed unexpectedly"
        result = tavily_search("test query")
        
        self.assertEqual(result, expected_output)

    @patch.dict(os.environ, {}, clear=True) # Ensure TAVILY_API_KEY is not set for this specific test
    @patch('tools.tavily.TavilySearchTool') # Still mock the class to prevent actual API calls if init somehow passes
    def test_tavily_search_wrapper_init_exception(self, MockTavilySearchTool):
        # This tests if the ValueError from TavilySearchTool.__init__ (due to no API key)
        # is caught by the wrapper.
        MockTavilySearchTool.side_effect = ValueError("API key missing")

        expected_output = "Tavily 搜索异常: API key missing"
        result = tavily_search("test query")
        self.assertEqual(result, expected_output)
        MockTavilySearchTool.assert_called_once_with(api_key=None) # api_key is None by default in wrapper

if __name__ == '__main__':
    unittest.main()
