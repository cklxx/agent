import unittest
from unittest.mock import patch, MagicMock
import os
from nodes.search_answer_nodes import SearchNode # Assuming AnswerNode is in the same file

class TestSearchNode(unittest.TestCase):

    # Test __init__ method (API Key Handling)
    @patch.dict(os.environ, {"TAVILY_API_KEY": "env_key_for_searchnode"})
    def test_init_with_api_key_env(self):
        node = SearchNode()
        self.assertEqual(node.api_key, "env_key_for_searchnode")

    @patch.dict(os.environ, {}, clear=True) # Ensure TAVILY_API_KEY is not set
    def test_init_without_api_key_env(self):
        # It seems the __init__ method of SearchNode doesn't explicitly check for the API key
        # or raise an error if it's missing, it just sets self.api_key = os.getenv("TAVILY_API_KEY")
        # which would be None if not set. The actual check happens in the tavily_search tool or TavilySearchTool class.
        node = SearchNode()
        self.assertIsNone(node.api_key) # os.getenv returns None if key doesn't exist

    # Test prep method
    def test_prep_method(self):
        # Assuming TAVILY_API_KEY is not needed for prep
        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key"}): # Ensure api_key is not None for init
            node = SearchNode()

        # Scenario 1: question in shared
        shared_s1 = {"question": "What is AI?"}
        self.assertEqual(node.prep(shared_s1), "What is AI?")

        # Scenario 2: question not in shared
        shared_s2 = {}
        self.assertEqual(node.prep(shared_s2), "")

        # Scenario 3: shared is None
        self.assertEqual(node.prep(None), "") # shared.get("question", "") if shared is None would error, current code is `shared.get("question", "")`

        # Scenario 4: question key exists but is None
        shared_s4 = {"question": None}
        self.assertIsNone(node.prep(shared_s4))


    @patch('nodes.search_answer_nodes.tavily_search')
    def test_exec_method(self, mock_tavily_search):
        # Scenario 1: Valid question provided
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test_api_key_exec"}):
            node_s1 = SearchNode() # api_key will be set via mocked env
        
        question_s1 = "What is the capital of France?"
        mock_search_result_s1 = "Search results: Paris is the capital of France."
        mock_tavily_search.return_value = mock_search_result_s1
        
        result_s1 = node_s1.exec(question_s1)
        
        mock_tavily_search.assert_called_once_with(question_s1, api_key="test_api_key_exec", num_results=3)
        self.assertEqual(result_s1, mock_search_result_s1)

        mock_tavily_search.reset_mock()

        # Ensure node for S2 and S3 has an api_key for consistency, though not strictly needed if tavily_search isn't called
        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key_s2_s3"}):
            node_s2_s3 = SearchNode()

        # Scenario 2: Empty or None question provided
        result_s2_empty = node_s2_s3.exec("")
        self.assertEqual(result_s2_empty, "")
        mock_tavily_search.assert_not_called()

        result_s2_none = node_s2_s3.exec(None)
        self.assertEqual(result_s2_none, "")
        mock_tavily_search.assert_not_called()
        
        mock_tavily_search.reset_mock()

        # Scenario 3: tavily_search raises an exception
        question_s3 = "This will cause an error"
        mock_tavily_search.side_effect = Exception("Tavily API Error")
        
        # We need a node instance for this test that has an API key
        with patch.dict(os.environ, {"TAVILY_API_KEY": "key_for_exception_test"}):
            node_s3_exception = SearchNode()

        with self.assertRaises(Exception) as context:
            node_s3_exception.exec(question_s3)
        self.assertTrue("Tavily API Error" in str(context.exception))
        mock_tavily_search.assert_called_once_with(question_s3, api_key="key_for_exception_test", num_results=3)


    def test_post_method(self):
        # Assuming TAVILY_API_KEY is not needed for post
        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key"}): # Ensure api_key is not None for init
            node = SearchNode()

        shared = {}
        prep_res_question = "What is the weather like?" # Not directly used by post
        exec_res_search_output = "Sunny with a chance of clouds."

        result = node.post(shared, prep_res_question, exec_res_search_output)

        self.assertEqual(shared.get("search_result"), exec_res_search_output)
        self.assertEqual(result, "default")

        # Test with pre-existing shared data
        shared_preexisting = {"other_key": "other_value", "search_result": "old_search_data"}
        exec_res_new_search_output = "Rainy day."
        result_new = node.post(shared_preexisting, prep_res_question, exec_res_new_search_output)
        
        self.assertEqual(shared_preexisting.get("search_result"), exec_res_new_search_output)
        self.assertEqual(shared_preexisting.get("other_key"), "other_value") # Ensure other keys are preserved
        self.assertEqual(result_new, "default")

if __name__ == '__main__':
    # This part is for local execution, will be removed by the testing framework
    # Placeholder for AnswerNode tests if they were in the same file and needed to be run
    # class TestAnswerNode(unittest.TestCase):
    #     def test_placeholder(self):
    #         self.assertTrue(True)

# --- Tests for AnswerNode ---
from nodes.search_answer_nodes import AnswerNode # Assuming AnswerNode is in the same file
import logging # For checking logs in post method

class TestAnswerNode(unittest.TestCase):

    def test_prep_method(self):
        node = AnswerNode()

        # Scenario 1: With "thought" data
        shared_s1 = {
            "question": "User question?",
            "thought": [
                {"thought_number": 1, "thought": "Step 1 thought"},
                {"thought": "Step 2 raw thought"} # Older format thought
            ]
        }
        prompt_s1 = node.prep(shared_s1)
        self.assertIn("User question?", prompt_s1)
        self.assertIn("Thought Process Summary:", prompt_s1)
        self.assertIn("Step 1: Step 1 thought", prompt_s1)
        self.assertIn("Step 2: Step 2 raw thought", prompt_s1)
        self.assertNotIn("Tool Execution Result:", prompt_s1)

        # Scenario 2: Without "thought" data, with "question" and "tool_execution_result"
        shared_s2 = {"question": "User question?", "tool_execution_result": "Tool output"}
        prompt_s2 = node.prep(shared_s2)
        self.assertIn("User question?", prompt_s2)
        self.assertIn("Tool Execution Result:", prompt_s2)
        self.assertIn("Tool output", prompt_s2)
        self.assertNotIn("Thought Process Summary:", prompt_s2)

        # Scenario 3: Without "thought", only "question"
        shared_s3 = {"question": "User question?"}
        prompt_s3 = node.prep(shared_s3)
        self.assertIn("User question?", prompt_s3)
        self.assertNotIn("Tool Execution Result:", prompt_s3) # or it might say "None" or "N/A"
        self.assertNotIn("Thought Process Summary:", prompt_s3)
        # Check for specific phrasing if only question is present
        self.assertTrue(prompt_s3.startswith("Please provide a direct and concise answer to the following question based on the information provided.\nUser Question: User question?\nAnswer:"))


        # Scenario 4: Without "thought", only "tool_execution_result"
        shared_s4 = {"tool_execution_result": "Tool output"}
        prompt_s4 = node.prep(shared_s4)
        self.assertIn("Tool Execution Result:", prompt_s4)
        self.assertIn("Tool output", prompt_s4)
        self.assertNotIn("User Question:", prompt_s4) # or it might say "None" or "N/A"
        self.assertNotIn("Thought Process Summary:", prompt_s4)
        # Check for specific phrasing if only tool result is present
        self.assertTrue(prompt_s4.startswith("Please provide a direct and concise answer based on the following tool execution result.\nTool Execution Result: Tool output\nAnswer:"))


        # Scenario 5: Empty shared or missing relevant keys
        shared_s5 = {}
        prompt_s5 = node.prep(shared_s5)
        # Based on the implementation, if both are empty, it will be:
        # "Please provide a direct and concise answer to the following question based on the information provided.\nUser Question: \nTool Execution Result: \nAnswer:"
        self.assertIn("User Question: \n", prompt_s5) # Empty question
        self.assertIn("Tool Execution Result: \n", prompt_s5) # Empty tool result
        self.assertNotIn("Thought Process Summary:", prompt_s5)


    @patch('nodes.search_answer_nodes.stream_llm')
    def test_exec_method(self, mock_stream_llm):
        node = AnswerNode()

        # Scenario 1: Successful stream_llm call
        prompt_s1 = "Test prompt for exec"
        mock_generator_s1 = iter(["Hello", " ", "World"])
        mock_stream_llm.return_value = mock_generator_s1
        
        result_s1 = node.exec(prompt_s1)
        
        self.assertEqual(result_s1, mock_generator_s1) # exec should return the generator
        mock_stream_llm.assert_called_once()
        called_args, called_kwargs = mock_stream_llm.call_args
        self.assertEqual(len(called_args[0]), 2) # messages list
        self.assertEqual(called_args[0][0]["role"], "system")
        self.assertEqual(called_args[0][1]["role"], "user")
        self.assertEqual(called_args[0][1]["content"], prompt_s1)
        self.assertIsNone(called_kwargs.get("model")) # model is optional in call_llm/stream_llm

        mock_stream_llm.reset_mock()

        # Scenario 2: stream_llm raises an exception
        prompt_s2 = "Prompt that causes error"
        mock_stream_llm.side_effect = Exception("LLM Stream Error")
        
        with self.assertRaises(Exception) as context:
            node.exec(prompt_s2)
        self.assertTrue("LLM Stream Error" in str(context.exception))
        mock_stream_llm.assert_called_once() # Check it was called


    def test_post_method(self):
        node = AnswerNode()

        # Scenario 1: Successful streaming aggregation
        shared_s1 = {}
        prep_res_s1 = "some prompt for scenario 1"
        exec_res_s1 = iter(["Final", " ", "Answer", "."])
        
        result_s1 = node.post(shared_s1, prep_res_s1, exec_res_s1)
        
        self.assertEqual(shared_s1.get("answer"), "Final Answer.")
        self.assertEqual(result_s1, "default")

        # Scenario 2: Generator from exec_res raises an exception during iteration
        shared_s2 = {}
        prep_res_s2 = "some prompt for scenario 2"
        
        def error_generator():
            yield "Part 1"
            yield "Part 2"
            raise Exception("Stream consumption error")

        exec_res_s2 = error_generator()
        
        with patch.object(logging, 'error') as mock_log_error: # Check logging
            result_s2 = node.post(shared_s2, prep_res_s2, exec_res_s2)
        
        self.assertIn("Part 1Part 2", shared_s2.get("answer"))
        self.assertIn("Error during answer generation: Stream consumption error", shared_s2.get("answer"))
        self.assertEqual(result_s2, "default")
        mock_log_error.assert_called_once()
        self.assertIn("Error consuming stream for AnswerNode: Stream consumption error", mock_log_error.call_args[0][0])

# --- Tests for ThinkingNode ---
from nodes.search_answer_nodes import ThinkingNode

class TestThinkingNode(unittest.TestCase):

    def test_prep_method(self):
        node = ThinkingNode()

        # Scenario 1: All relevant keys in shared
        shared_s1 = {
            "thoughtNumber": 2,
            "totalThoughts": 5,
            "branches": [{"thought_number": 1, "thought": "Initial thought"}],
            "question": "What is the process?",
            "nextThoughtNeeded": True,
            "thoughtHistoryLength": 1
        }
        expected_prep_s1 = {
            "thought_number": 2,
            "total_thoughts": 5,
            "branches": [{"thought_number": 1, "thought": "Initial thought"}],
            "question": "What is the process?",
            "next_thought_needed": True,
            "thought_history_length": 1
        }
        self.assertEqual(node.prep(shared_s1), expected_prep_s1)

        # Scenario 2: Some keys missing, relying on defaults
        shared_s2 = {"question": "What if only question?"}
        expected_prep_s2 = {
            "thought_number": 1,
            "total_thoughts": 3,
            "branches": [],
            "question": "What if only question?",
            "next_thought_needed": True,
            "thought_history_length": 0
        }
        self.assertEqual(node.prep(shared_s2), expected_prep_s2)

        # Scenario 3: Empty shared dictionary
        shared_s3 = {}
        expected_prep_s3 = {
            "thought_number": 1,
            "total_thoughts": 3,
            "branches": [],
            "question": "",
            "next_thought_needed": True,
            "thought_history_length": 0
        }
        self.assertEqual(node.prep(shared_s3), expected_prep_s3)

    @patch('nodes.search_answer_nodes.call_llm')
    def test_exec_method(self, mock_call_llm):
        node = ThinkingNode()

        # Scenario 1: Continue thinking
        context_s1 = {
            "thought_number": 1,
            "total_thoughts": 3,
            "branches": [],
            "question": "What is the first step?",
            "next_thought_needed": True,
            "thought_history_length": 0
        }
        mock_call_llm.return_value = "This is the first thought."
        
        result_s1 = node.exec(context_s1)
        
        mock_call_llm.assert_called_once()
        prompt_s1 = mock_call_llm.call_args[0][0]
        self.assertIn("You are a thought step in a multi-step thinking process.", prompt_s1)
        self.assertIn(context_s1["question"], prompt_s1)
        self.assertIn("【历史思考】\n无", prompt_s1) # No history yet
        
        self.assertTrue(result_s1["continue"])
        self.assertEqual(len(result_s1["branches"]), 1)
        self.assertEqual(result_s1["branches"][0]["thought_number"], 1)
        self.assertEqual(result_s1["branches"][0]["thought"], "This is the first thought.")
        self.assertTrue(result_s1["nextThoughtNeeded"])
        self.assertEqual(result_s1["thoughtHistoryLength"], 1)

        mock_call_llm.reset_mock()

        # Scenario 2: Stop thinking (thought_number > total_thoughts)
        context_s2 = {
            "thought_number": 4,
            "total_thoughts": 3,
            "branches": [{"thought_number": 1, "thought": "T1"}, {"thought_number": 2, "thought": "T2"}, {"thought_number": 3, "thought": "T3"}],
            "question": "What is the next step?",
            "next_thought_needed": True, # This would be True from previous step
            "thought_history_length": 3
        }
        result_s2 = node.exec(context_s2)
        
        mock_call_llm.assert_not_called()
        self.assertFalse(result_s2["continue"])
        self.assertEqual(result_s2["branches"], context_s2["branches"])
        self.assertFalse(result_s2["nextThoughtNeeded"]) # Should be set to False when stopping
        self.assertEqual(result_s2["thoughtHistoryLength"], context_s2["thought_history_length"])

        mock_call_llm.reset_mock()

        # Scenario 3: Stop thinking (nextThoughtNeeded is False)
        context_s3 = {
            "thought_number": 2,
            "total_thoughts": 3,
            "branches": [{"thought_number": 1, "thought": "T1"}],
            "question": "What is the next step?",
            "next_thought_needed": False,
            "thought_history_length": 1
        }
        result_s3 = node.exec(context_s3)

        mock_call_llm.assert_not_called()
        self.assertFalse(result_s3["continue"])
        self.assertEqual(result_s3["branches"], context_s3["branches"])
        self.assertFalse(result_s3["nextThoughtNeeded"])
        self.assertEqual(result_s3["thoughtHistoryLength"], context_s3["thought_history_length"])
        
        mock_call_llm.reset_mock()

        # Scenario 4: Formatting of history in prompt
        context_s4 = {
            "thought_number": 3,
            "total_thoughts": 3,
            "branches": [
                {"thought_number": 1, "thought": "First thought."}, # Dict style
                "Second thought, direct string." # String style (older format)
            ],
            "question": "What is the third step?",
            "next_thought_needed": True,
            "thought_history_length": 2 # length of branches
        }
        mock_call_llm.return_value = "This is the third thought."
        node.exec(context_s4)

        mock_call_llm.assert_called_once()
        prompt_s4 = mock_call_llm.call_args[0][0]
        expected_history_s4 = "【历史思考】\n【第1步】First thought.\n【第2步】Second thought, direct string."
        self.assertIn(expected_history_s4, prompt_s4)
        self.assertIn(context_s4["question"], prompt_s4)


    def test_post_method(self):
        node = ThinkingNode()

        # Scenario 1: exec_res indicates continue thinking
        shared_s1 = {"thoughtNumber": 1, "totalThoughts": 3, "branches": [], "nextThoughtNeeded": False, "thoughtHistoryLength": 0}
        # prep_res for ThinkingNode is a dict, not directly used by post in a way that needs complex mocking here
        prep_res_s1 = {"thought_number": 1, "total_thoughts": 3, "branches": [], "question": "Q", "next_thought_needed": True, "thought_history_length": 0}
        exec_res_s1 = {
            "continue": True, 
            "branches": [{"thought_number": 1, "thought": "new_thought"}], 
            "nextThoughtNeeded": True, 
            "thoughtHistoryLength": 1
        }
        
        result_s1 = node.post(shared_s1, prep_res_s1, exec_res_s1)

        self.assertEqual(shared_s1["branches"], exec_res_s1["branches"])
        self.assertTrue(shared_s1["nextThoughtNeeded"])
        self.assertEqual(shared_s1["thoughtHistoryLength"], 1)
        self.assertEqual(shared_s1["thoughtNumber"], 2) # Incremented
        self.assertEqual(result_s1, "continue")

        # Scenario 2: exec_res indicates stop thinking
        shared_s2 = {"thoughtNumber": 3, "totalThoughts": 3, "branches": [{"thought_number":1, "thought":"t1"}, {"thought_number":2, "thought":"t2"}], "nextThoughtNeeded": True, "thoughtHistoryLength": 2}
        prep_res_s2 = {"thought_number": 3, "total_thoughts": 3, "branches": shared_s2["branches"], "question": "Q", "next_thought_needed": True, "thought_history_length": 2}
        exec_res_s2 = {
            "continue": False, 
            "branches": [{"thought_number":1, "thought":"t1"}, {"thought_number":2, "thought":"t2"}, {"thought_number": 3, "thought": "final_thought"}], 
            "nextThoughtNeeded": False, 
            "thoughtHistoryLength": 3
        }
        
        result_s2 = node.post(shared_s2, prep_res_s2, exec_res_s2)

        self.assertEqual(shared_s2["branches"], exec_res_s2["branches"])
        self.assertFalse(shared_s2["nextThoughtNeeded"])
        self.assertEqual(shared_s2["thoughtHistoryLength"], 3)
        self.assertEqual(shared_s2["thought"], exec_res_s2["branches"]) # 'thought' key gets all branches
        self.assertEqual(shared_s2["thoughtNumber"], 3) # Not incremented as we stop
        self.assertEqual(result_s2, "default")


if __name__ == '__main__':    
    unittest.main()
