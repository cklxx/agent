import unittest
from unittest.mock import patch, MagicMock
from nodes.parser_node import ParserNode

class TestParserNode(unittest.TestCase):

    def test_prep_method(self):
        node = ParserNode()

        # Scenario 1: crawl_results in shared
        shared_s1 = {"crawl_results": [{"text": "some text"}]}
        self.assertEqual(node.prep(shared_s1), [{"text": "some text"}])

        # Scenario 2: crawl_results not in shared
        shared_s2 = {}
        self.assertEqual(node.prep(shared_s2), []) # As per shared.get("crawl_results", [])

        # Scenario 3: crawl_results is None in shared
        shared_s3 = {"crawl_results": None}
        self.assertIsNone(node.prep(shared_s3))

    @patch('nodes.parser_node.analyze_site') # Patch analyze_site in the parser_node module
    def test_exec_method(self, mock_analyze_site):
        node = ParserNode()

        # Scenario 1: Valid crawl_results provided
        mock_crawl_data_s1 = [{"text": "text1"}, {"text": "text2"}]
        mock_analysis_results_s1 = [{"analysis": "analysis1"}, {"analysis": "analysis2"}]
        mock_analyze_site.return_value = mock_analysis_results_s1
        
        result_s1 = node.exec(mock_crawl_data_s1)
        
        mock_analyze_site.assert_called_once_with(mock_crawl_data_s1)
        self.assertEqual(result_s1, mock_analysis_results_s1)

        mock_analyze_site.reset_mock()

        # Scenario 2: Empty or None crawl_results provided
        result_s2_empty = node.exec([])
        self.assertEqual(result_s2_empty, [])
        mock_analyze_site.assert_not_called()

        result_s2_none = node.exec(None)
        self.assertEqual(result_s2_none, [])
        mock_analyze_site.assert_not_called()
        
        mock_analyze_site.reset_mock()

        # Scenario 3: analyze_site raises an exception
        mock_crawl_data_s3 = [{"text": "text_for_exception"}]
        mock_analyze_site.side_effect = Exception("Analysis failed")
        
        with self.assertRaises(Exception) as context:
            node.exec(mock_crawl_data_s3)
        self.assertTrue("Analysis failed" in str(context.exception))
        mock_analyze_site.assert_called_once_with(mock_crawl_data_s3)

    def test_post_method(self):
        node = ParserNode()
        shared = {}
        prep_res_crawl_data = [{"text": "some text"}] # Not directly used by post, but part of the flow
        exec_res_analysis_data = [{"analysis": "analysis1"}]

        result = node.post(shared, prep_res_crawl_data, exec_res_analysis_data)

        self.assertEqual(shared.get("analyze_results"), exec_res_analysis_data)
        self.assertEqual(result, "default")

        # Test with pre-existing shared data (should be overwritten for "analyze_results")
        shared_preexisting = {"other_key": "other_value", "analyze_results": "old_analysis"}
        exec_res_new_analysis_data = [{"analysis": "new_analysis"}]
        result_new = node.post(shared_preexisting, prep_res_crawl_data, exec_res_new_analysis_data)
        
        self.assertEqual(shared_preexisting.get("analyze_results"), exec_res_new_analysis_data)
        self.assertEqual(shared_preexisting.get("other_key"), "other_value") # Ensure other keys are not lost
        self.assertEqual(result_new, "default")

if __name__ == '__main__':
    unittest.main()
