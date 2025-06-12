import pytest
from unittest.mock import patch, MagicMock, ANY

from src.agents.agents import create_agent
# AGENT_LLM_MAP will be patched where it's imported from in src.agents.agents

# Mock tools
mock_tool1 = MagicMock(name="Tool1")
mock_tool2 = MagicMock(name="Tool2")

@patch("src.agents.agents.AGENT_LLM_MAP", {"default_agent_type": "llm_service_x", "another_type": "llm_service_y"})
@patch("src.agents.agents.create_react_agent")
@patch("src.agents.agents.apply_prompt_template")
@patch("src.agents.agents.get_llm_by_type")
def test_create_agent_successful_creation(mock_get_llm, mock_apply_prompt, mock_react_agent_builder, mock_agent_llm_map_fixture): # mock_agent_llm_map_fixture is the patched object
    # Setup Mocks
    mock_llm_instance = MagicMock(name="MockedLLM")
    mock_get_llm.return_value = mock_llm_instance

    mock_react_agent_builder.return_value = "expected_agent_instance" # What create_react_agent returns
    mock_apply_prompt.return_value = "rendered_prompt_string"

    agent_name = "TestAgent"
    agent_type = "default_agent_type" # Use a key from our patched map
    # AGENT_LLM_MAP is patched in src.agents.agents, so use the fixture value or re-access the patched map for llm_service_type
    llm_service_type = mock_agent_llm_map_fixture[agent_type]
    tools = [mock_tool1, mock_tool2]
    prompt_template_name = "test_prompt"

    # Call the function
    agent_instance = create_agent(agent_name, agent_type, tools, prompt_template_name)

    # Assertions
    mock_get_llm.assert_called_once_with(llm_service_type)

    # Check create_react_agent call
    # The create_agent function passes 'model' as the kwarg for the llm instance
    mock_react_agent_builder.assert_called_once_with(
        name=agent_name,
        model=mock_llm_instance, # This corresponds to 'llm' in create_react_agent if it's the langgraph one
        tools=tools,
        prompt=ANY # Check the lambda separately
    )

    # Test the lambda passed to prompt
    # Retrieve the 'prompt' lambda function from the call_args of create_react_agent
    prompt_lambda_func = mock_react_agent_builder.call_args.kwargs['prompt']
    sample_state = {"key": "value"} # Example state, structure depends on what the prompt expects

    # Call the lambda
    rendered_prompt = prompt_lambda_func(sample_state)

    # Assert that apply_prompt_template was called correctly by the lambda
    mock_apply_prompt.assert_called_once_with(prompt_template_name, sample_state)
    assert rendered_prompt == "rendered_prompt_string"

    assert agent_instance == "expected_agent_instance"

@patch("src.agents.agents.AGENT_LLM_MAP", {"default_agent_type": "llm_service_x"}) # Patch map
@patch("src.agents.agents.create_react_agent")
@patch("src.agents.agents.apply_prompt_template")
@patch("src.agents.agents.get_llm_by_type")
def test_create_agent_invalid_agent_type(mock_get_llm, mock_apply_prompt, mock_react_agent_builder, mock_agent_llm_map_fixture): # mock_agent_llm_map_fixture is the patched object
    agent_name = "TestAgent"
    invalid_agent_type = "non_existent_agent_type"
    tools = []
    prompt_template_name = "test_prompt"

    with pytest.raises(KeyError) as excinfo:
        create_agent(agent_name, invalid_agent_type, tools, prompt_template_name)

    # Check that the error message contains the key that was not found
    assert invalid_agent_type in str(excinfo.value) or f"'{invalid_agent_type}'" in str(excinfo.value)

    # Ensure other mocks were not called due to early exit
    mock_get_llm.assert_not_called()
    mock_react_agent_builder.assert_not_called()
    mock_apply_prompt.assert_not_called() # apply_prompt_template is only called within the lambda


@patch("src.agents.agents.AGENT_LLM_MAP", {"type1": "llm_service_A", "type2": "llm_service_B"})
@patch("src.agents.agents.create_react_agent")
@patch("src.agents.agents.apply_prompt_template")
@patch("src.agents.agents.get_llm_by_type")
def test_create_agent_different_agent_types(mock_get_llm, mock_apply_prompt, mock_react_agent_builder, mock_agent_llm_map_fixture):
    mock_llm_A = MagicMock(name="LLM_A")
    mock_llm_B = MagicMock(name="LLM_B")

    # Configure get_llm_by_type to return different LLMs based on type
    def get_llm_side_effect(service_type):
        if service_type == "llm_service_A":
            return mock_llm_A
        elif service_type == "llm_service_B":
            return mock_llm_B
        return MagicMock() # Default mock if other types are requested
    mock_get_llm.side_effect = get_llm_side_effect
    mock_react_agent_builder.return_value = "agent_for_type"
    mock_apply_prompt.return_value = "prompt_for_type"

    tools = [mock_tool1]
    prompt_template_name = "common_prompt"

    # Test with 'type1'
    create_agent("Agent1", "type1", tools, prompt_template_name)
    mock_get_llm.assert_called_with("llm_service_A")
    mock_react_agent_builder.assert_called_with(
        name="Agent1", model=mock_llm_A, tools=tools, prompt=ANY
    )

    # Reset mocks for the next call if checking call_count=1, or use assert_any_call / assert_called_with
    # For simplicity, we'll rely on assert_called_with which checks the last call if not reset,
    # or use call_count if we want to be very specific about sequence and exclusivity.
    # Let's ensure calls are distinct. A simple way is to check call_count before and after.

    # Test with 'type2'
    create_agent("Agent2", "type2", tools, prompt_template_name)
    mock_get_llm.assert_called_with("llm_service_B") # Checks the latest call
    mock_react_agent_builder.assert_called_with(
        name="Agent2", model=mock_llm_B, tools=tools, prompt=ANY
    )

    assert mock_get_llm.call_count == 2 # Ensure it was called for each agent type
    assert mock_react_agent_builder.call_count == 2
    assert mock_apply_prompt.call_count == 2 # Lambda is created and called each time
```
