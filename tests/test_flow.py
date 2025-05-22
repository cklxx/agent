import pytest

# Example test function
def test_example():
    assert 1 + 1 == 2

# You should add tests for your nodes and flow logic here.
# For example, you could test:
# - The output of individual node's exec methods
# - The state changes in the shared dictionary after a node runs
# - The overall flow logic for specific inputs

# Example (pseudo-code) for testing a node:
# def test_decide_tool_node():
#     shared = {"question": "What is the time?", "tool_info_for_prompt": "..."}
#     decide_node = DecideToolNode()
#     prompt = decide_node.prep(shared)
#     llm_response = """```yaml\nthinking: |\n  User is asking for the current time.\ntool: local_dummy.get_time\nreason: get_time tool can provide current time.\nparameters:\n  random_string: dummy\n```"""
#     action = decide_node.post(shared, prompt, llm_response)
#     assert action == "execute"
#     assert shared.get("tool_name") == "get_time"
#     assert shared.get("server_name") == "local_dummy" 