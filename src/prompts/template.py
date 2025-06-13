# SPDX-License-Identifier: MIT

import os
import dataclasses
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState
from src.config.configuration import Configuration


def basename_filter(path):
    """Extract basename from file path"""
    return Path(path).name


def selectattr_filter(objects, attr):
    """Select objects that have the specified attribute as True"""
    return [obj for obj in objects if obj.get(attr, False)]


# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Add custom filters
env.filters["basename"] = basename_filter
env.filters["selectattr"] = selectattr_filter


def get_prompt_template(prompt_name: str) -> str:
    """
    Load and return a prompt template using Jinja2.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name}: {e}")


def apply_prompt_template(
    prompt_name: str, state: AgentState, configurable: Configuration = None
) -> list:
    """
    Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute

    Returns:
        List of messages with the system prompt as the first message
    """
    # Convert state to dict for template rendering
    # Handle both dict and AddableValuesDict types
    if hasattr(state, 'keys'):
        # Convert AddableValuesDict or dict to regular dict
        state_dict = {key: state[key] for key in state.keys()}
    else:
        # Fallback for other types
        state_dict = dict(state) if state else {}
    
    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        **state_dict,
    }

    # Add configurable variables
    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        template = env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)
        
        # Safely extract messages from state
        messages = state_dict.get("messages", [])
        return [{"role": "system", "content": system_prompt}] + messages
    except Exception as e:
        raise ValueError(f"Error applying template {prompt_name}: {e}")
