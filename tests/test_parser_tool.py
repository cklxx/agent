import unittest
from unittest.mock import patch, MagicMock
from tools.parser import analyze_content, analyze_site
import yaml # For creating valid/invalid YAML scenarios
import logging

class TestParserTool(unittest.TestCase):

    @patch('tools.parser.call_llm')
    def test_analyze_content(self, mock_call_llm):
        # Scenario 1: Successful LLM call, valid YAML
        valid_yaml_str = """
```yaml
summary: "This is a test summary."
topics:
  - "topic1"
  - "topic2"
content_type: "article"
```
"""
        mock_call_llm.return_value = valid_yaml_str
        expected_output_s1 = {
            "summary": "This is a test summary.",
            "topics": ["topic1", "topic2"],
            "content_type": "article"
        }
        result_s1 = analyze_content("Sample text content")
        self.assertEqual(result_s1, expected_output_s1)
        mock_call_llm.assert_called_once()

        mock_call_llm.reset_mock()

        # Scenario 2: Successful LLM call, invalid YAML/missing keys
        invalid_yaml_str_missing_key = """
```yaml
topics:
  - "topic1"
content_type: "blog"
```
"""
        mock_call_llm.return_value = invalid_yaml_str_missing_key
        error_output = {"summary": "Error analyzing content", "topics": [], "content_type": "unknown"}
        with self.assertLogs(logger='tools.parser', level='ERROR') as cm_s2_missing:
            result_s2_missing = analyze_content("Sample text content")
            self.assertEqual(result_s2_missing, error_output)
        self.assertIn("Error parsing LLM response YAML", cm_s2_missing.output[0]) # or "Missing key 'summary' in parsed YAML"
        mock_call_llm.assert_called_once()
        mock_call_llm.reset_mock()

        malformed_yaml_str = """
```yaml
summary: "Test"
topics: - topic1
  - topic2 # Incorrect indentation
content_type: "news"
```
"""
        mock_call_llm.return_value = malformed_yaml_str
        with self.assertLogs(logger='tools.parser', level='ERROR') as cm_s2_malformed:
            result_s2_malformed = analyze_content("Sample text content")
            self.assertEqual(result_s2_malformed, error_output)
        self.assertIn("Error parsing LLM response YAML", cm_s2_malformed.output[0])
        mock_call_llm.assert_called_once()
        mock_call_llm.reset_mock()

        # Scenario 3: LLM call raises an exception
        mock_call_llm.side_effect = Exception("LLM processing error")
        with self.assertLogs(logger='tools.parser', level='ERROR') as cm_s3:
            result_s3 = analyze_content("Sample text content")
            self.assertEqual(result_s3, error_output)
        self.assertIn("LLM call failed: LLM processing error", cm_s3.output[0])
        mock_call_llm.assert_called_once()
        mock_call_llm.reset_mock()
        mock_call_llm.side_effect = None # Reset side_effect

        # Scenario 4: LLM response without YAML block
        no_yaml_block_str = "This is a response without any YAML."
        mock_call_llm.return_value = no_yaml_block_str
        with self.assertLogs(logger='tools.parser', level='ERROR') as cm_s4:
            result_s4 = analyze_content("Sample text content")
            self.assertEqual(result_s4, error_output)
        self.assertIn("Could not find YAML block in LLM response", cm_s4.output[0])
        mock_call_llm.assert_called_once()

    @patch('tools.parser.analyze_content')
    def test_analyze_site(self, mock_analyze_content):
        # Scenario 1: List of valid crawl results
        crawl_data_s1 = [
            {'title': 'Page 1', 'url': 'url1', 'text': 'text1 about topicA'},
            {'title': 'Page 2', 'url': 'url2', 'text': 'text2 about topicB'}
        ]
        analysis_result_1 = {"summary": "Summary 1", "topics": ["topicA"], "content_type": "article"}
        analysis_result_2 = {"summary": "Summary 2", "topics": ["topicB"], "content_type": "blog"}
        
        mock_analyze_content.side_effect = [analysis_result_1, analysis_result_2]
        
        expected_output_s1 = [
            {'title': 'Page 1', 'url': 'url1', 'text': 'text1 about topicA', 'analysis': analysis_result_1},
            {'title': 'Page 2', 'url': 'url2', 'text': 'text2 about topicB', 'analysis': analysis_result_2}
        ]
        
        result_s1 = analyze_site(crawl_data_s1)
        self.assertEqual(result_s1, expected_output_s1)
        self.assertEqual(mock_analyze_content.call_count, 2)
        mock_analyze_content.assert_any_call('text1 about topicA')
        mock_analyze_content.assert_any_call('text2 about topicB')

        mock_analyze_content.reset_mock()
        mock_analyze_content.side_effect = None

        # Scenario 2: Empty crawl results list
        result_s2 = analyze_site([])
        self.assertEqual(result_s2, [])
        mock_analyze_content.assert_not_called()

        # Scenario 3: Crawl results with missing 'text' or None items
        crawl_data_s3 = [
            {'title': 'Page 1', 'url': 'url1', 'text': 'text1 valid'},
            None, # Should be skipped
            {'title': 'Page 3', 'url': 'url3'}, # Missing 'text'
            {'title': 'Page 4', 'url': 'url4', 'text': 'text4 valid'}
        ]
        analysis_result_3_1 = {"summary": "Summary 3_1", "topics": ["valid1"], "content_type": "news"}
        analysis_result_3_4 = {"summary": "Summary 3_4", "topics": ["valid4"], "content_type": "other"}
        
        # analyze_content will only be called for items with 'text'
        mock_analyze_content.side_effect = [analysis_result_3_1, analysis_result_3_4]
        
        expected_output_s3 = [
            {'title': 'Page 1', 'url': 'url1', 'text': 'text1 valid', 'analysis': analysis_result_3_1},
            # None is skipped
            {'title': 'Page 3', 'url': 'url3'}, # Item without 'text' is passed through without 'analysis'
            {'title': 'Page 4', 'url': 'url4', 'text': 'text4 valid', 'analysis': analysis_result_3_4}
        ]
        
        result_s3 = analyze_site(crawl_data_s3)
        self.assertEqual(result_s3, expected_output_s3)
        self.assertEqual(mock_analyze_content.call_count, 2)
        mock_analyze_content.assert_any_call('text1 valid')
        mock_analyze_content.assert_any_call('text4 valid')

if __name__ == '__main__':
    unittest.main()
