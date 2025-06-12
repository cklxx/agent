# SPDX-License-Identifier: MIT

"""
Agent tools for conversation management.
Dispatch agent functionality has been moved to architect_tool.py.
"""

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Global conversation history for demonstration
# In a real implementation, this would be managed by the conversation system
CONVERSATION_HISTORY = []


@tool  
def clear_conversation() -> str:
    """
    Clear conversation history and free up context.
    
    This tool removes all conversation history to free up context window space.
    Use this when you want to start fresh or when context is getting too large.

    Returns:
        Confirmation that conversation history has been cleared
    """
    try:
        global CONVERSATION_HISTORY
        
        # Store count before clearing
        message_count = len(CONVERSATION_HISTORY)
        
        # Clear the conversation history
        CONVERSATION_HISTORY.clear()
        
        logger.info("Conversation history cleared")
        
        if message_count > 0:
            return f"Conversation history cleared. Removed {message_count} messages from context."
        else:
            return "Conversation history was already empty."

    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        return f"Error: Failed to clear conversation history: {str(e)}"


@tool
def compact_conversation() -> str:
    """
    Clear conversation history but keep a summary in context.
    
    This tool compacts the conversation history by creating a summary of the important 
    information and clearing the detailed history, helping to manage context window size
    while preserving key information.

    Returns:
        Summary of the conversation and confirmation of compacting
    """
    try:
        global CONVERSATION_HISTORY
        
        if not CONVERSATION_HISTORY:
            return "Conversation history is empty. Nothing to compact."

        # Use project's LLM infrastructure for summarization
        from src.llms.llm import get_llm_by_type
        from src.config.agents import AGENT_LLM_MAP
        
        try:
            llm = get_llm_by_type(AGENT_LLM_MAP["basic"])
        except Exception as e:
            logger.error(f"Failed to get LLM for conversation compacting: {e}")
            return f"Error: Unable to initialize LLM for conversation compacting: {str(e)}"

        # Create summary prompt
        conversation_text = "\n".join([
            f"Message {i+1}: {msg}" for i, msg in enumerate(CONVERSATION_HISTORY[-20:])  # Last 20 messages
        ])
        
        summary_prompt = f"""Please create a concise summary of this conversation that preserves the key information, decisions made, and current context. Focus on:

1. Main topics discussed
2. Important decisions or conclusions
3. Current state/progress
4. Any ongoing tasks or next steps

Conversation to summarize:
{conversation_text}

Provide a clear, structured summary that can serve as context for continuing the conversation."""

        try:
            # Generate summary using project's LLM infrastructure
            messages = [
                {"role": "system", "content": "You are a helpful assistant that creates concise conversation summaries."},
                {"role": "user", "content": summary_prompt}
            ]
            
            response = llm.invoke(messages)
            summary = response.content.strip()
            
            # Store message count before clearing
            message_count = len(CONVERSATION_HISTORY)
            
            # Clear history and replace with summary
            CONVERSATION_HISTORY.clear()
            CONVERSATION_HISTORY.append(f"CONVERSATION_SUMMARY: {summary}")
            
            logger.info(f"Conversation history compacted: {message_count} messages -> summary")
            
            result = f"""# Conversation Compacted

Successfully compacted {message_count} messages into a summary.

## Summary:
{summary}

---
*Conversation history has been compacted to preserve context while reducing size.*"""
            
            return result

        except Exception as e:
            logger.error(f"Failed to generate conversation summary: {e}")
            return f"Error: Failed to generate conversation summary: {str(e)}"

    except Exception as e:
        logger.error(f"Error compacting conversation: {e}")
        return f"Error: Failed to compact conversation: {str(e)}"


# Utility functions for conversation management
def add_to_conversation_history(message: str, role: str = "user"):
    """Add a message to conversation history."""
    global CONVERSATION_HISTORY
    CONVERSATION_HISTORY.append(f"{role}: {message}")
    logger.debug(f"Added to conversation history: {role}: {message[:100]}...")


def get_conversation_context() -> str:
    """Get current conversation context as a string."""
    global CONVERSATION_HISTORY
    if not CONVERSATION_HISTORY:
        return "No conversation history available."
    
    return "\n".join(CONVERSATION_HISTORY) 