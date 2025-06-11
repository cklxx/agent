# SPDX-License-Identifier: MIT

"""
Unit tests for writing-related components like tools and planners.
"""

import unittest
import os
import shutil
import datetime
import json
from unittest.mock import patch, MagicMock

# Modules to test
from src.tools.writing_tools import (
    get_current_datetime,
    save_content_to_file,
    list_saved_content,
    BASE_SAVE_DIR # Import for constructing test paths
)
from src.agents.writing_task_planner import WritingTaskPlanner
# For mocking LLM calls if needed for other tools, not directly used in WritingTaskPlanner test below
# from src.llms.llm import get_llm_by_type


class TestWritingTools(unittest.TestCase):
    """Tests for functions in writing_tools.py"""

    def test_get_current_datetime(self):
        """Test if get_current_datetime returns a string in the expected format."""
        dt_str = get_current_datetime()
        self.assertIsInstance(dt_str, str)
        try:
            datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.fail("get_current_datetime did not return a string in 'YYYY-MM-DD HH:MM:SS' format.")

    def test_save_and_list_content(self):
        """Test saving content to a file and then listing it."""
        test_category = "_test_category_temp"
        test_category_path = os.path.join(BASE_SAVE_DIR, test_category)
        filename_prefix = "my_test_inspiration"
        test_content = "This is a unit test for saving and listing inspirations.\nIt has multiple lines."

        # Ensure clean state before test
        if os.path.exists(test_category_path):
            shutil.rmtree(test_category_path)

        try:
            # Test saving
            save_message = save_content_to_file(test_content, filename_prefix, category=test_category)
            self.assertTrue("Successfully saved to" in save_message)

            # Extract filepath from message (this depends on the exact message format)
            # Assuming message is "Content successfully saved to: <filepath>"
            filepath_in_message = save_message.split("Successfully saved to: ")[-1]
            self.assertTrue(os.path.exists(filepath_in_message))

            # Verify file content
            with open(filepath_in_message, "r", encoding="utf-8") as f:
                content_in_file = f.read()
            self.assertEqual(content_in_file, test_content)

            # Test listing
            saved_files_preview = list_saved_content(category=test_category, count=1)
            self.assertEqual(len(saved_files_preview), 1)

            # Check if the filename and preview are in the listed content
            # Filename might have a timestamp, so check for prefix
            self.assertTrue(filename_prefix in saved_files_preview[0])
            # Preview replaces newline with space and adds "..."
            expected_preview_part = test_content.replace('\n', ' ')[:200]
            self.assertTrue(expected_preview_part in saved_files_preview[0])

        finally:
            # Teardown: Remove the test category directory and its contents
            if os.path.exists(test_category_path):
                shutil.rmtree(test_category_path)
                # print(f"Cleaned up test directory: {test_category_path}")


class TestWritingTaskPlanner(unittest.TestCase):
    """Tests for the WritingTaskPlanner class."""

    @patch('src.agents.writing_task_planner.get_llm_by_type')
    def test_planner_fallback_logic(self, mock_get_llm_by_type):
        """
        Test that the WritingTaskPlanner uses its fallback logic when LLM analysis fails.
        """
        # Configure the mock LLM's invoke method to raise an exception
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = Exception("Simulated LLM API error")
        mock_get_llm_by_type.return_value = mock_llm_instance

        planner = WritingTaskPlanner()
        test_description = "A test writing request that will trigger fallback."

        # The plan_task method should catch the exception from _analyze_task (due to LLM failure)
        # and proceed to generate the fallback plan.
        plan = planner.plan_task(test_description)

        self.assertIsNotNone(plan, "Plan should not be None even on LLM failure (fallback expected).")
        self.assertTrue(len(plan) > 0, "Fallback plan should contain steps.")

        # Check for expected fallback phases and step characteristics
        phases_in_plan = {step['phase'] for step in plan}
        self.assertIn("inspiration_gathering", phases_in_plan, "Fallback plan should have 'inspiration_gathering' phase.")
        self.assertIn("content_development", phases_in_plan, "Fallback plan should have 'content_development' phase.")
        self.assertIn("refinement_suggestions", phases_in_plan, "Fallback plan should have 'refinement_suggestions' phase.")

        # Check a specific step from the fallback plan
        # For example, the first step in the fallback plan
        first_fallback_step = plan[0]
        self.assertEqual(first_fallback_step['type'], 'analyze_request')
        self.assertEqual(first_fallback_step['phase'], 'inspiration_gathering')
        self.assertTrue(test_description[:20] in first_fallback_step['description'],
                        "First fallback step description should contain part of the original task description.")

        # Check another step to be more certain
        found_develop_idea_step = any(step['type'] == 'develop_chosen_idea' for step in plan)
        self.assertTrue(found_develop_idea_step, "Fallback plan should include a 'develop_chosen_idea' step.")


if __name__ == "__main__":
    unittest.main()
```
