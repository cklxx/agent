# SPDX-License-Identifier: MIT

"""
Tools specifically designed for creative writing, inspiration, and content generation.
"""

import os
import json
import datetime
import logging
from typing import List, Optional, Dict, Any

from langchain_core.tools import tool

from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.rag.inspiration_retriever import InspirationRetriever # Added import

logger = logging.getLogger(__name__)

BASE_SAVE_DIR = "user_generated_content"
INSPIRATION_DB_PATH = "temp/rag_data/rag_inspirations.db" # Added constant for DB path


@tool
def get_current_datetime() -> str:
    """
    Returns the current date and time formatted as a string.
    Format: YYYY-MM-DD HH:MM:SS
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def generate_random_inspiration_theme(user_prompt: Optional[str] = None) -> str:
    """
    Generates a random creative writing theme.
    If a user_prompt is provided, it's used as inspiration for the theme.
    Otherwise, a completely random theme is generated.
    The theme is concise, typically 1-2 sentences.
    """
    llm = get_llm_by_type("basic")
    prompt = "Generate a random creative writing theme. "
    if user_prompt:
        prompt += f"Use the following user input as inspiration: '{user_prompt}'. "
    else:
        prompt += "Generate a completely random theme. "
    prompt += "Keep the theme concise (1-2 sentences)."

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Error generating random inspiration theme: {e}")
        return "Error: Could not generate a theme at this time."


@tool
def save_content_to_file(content: str, filename_prefix: str, category: str = "inspirations") -> str:
    """
    Saves the given textual content to a new file in a specified category.
    A timestamp is appended to the filename to ensure uniqueness.

    Args:
        content: The text content to save.
        filename_prefix: A prefix for the filename (e.g., "my_story_idea").
        category: The category subdirectory to save the file under (e.g., "inspirations", "characters", "plots").
                  Defaults to "inspirations".

    Returns:
        A success message with the full path to the saved file, or an error message.
    """
    try:
        category_dir = os.path.join(BASE_SAVE_DIR, category)
        os.makedirs(category_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix.replace(' ', '_')}_{timestamp}.txt"
        filepath = os.path.join(category_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Content saved to file: {filepath}")
        return f"Content successfully saved to: {filepath}"
    except OSError as e:
        logger.error(f"File system error while saving content: {e}")
        return f"Error: Could not save content due to a file system error: {e.strerror}"
    except Exception as e:
        logger.error(f"Unexpected error while saving content: {e}")
        return f"Error: An unexpected error occurred: {e}"


@tool
def list_saved_content(category: str = "inspirations", count: int = 5) -> List[str]:
    """
    Lists recently saved content from a specified category, showing a preview of each.

    Args:
        category: The category subdirectory to list files from. Defaults to "inspirations".
        count: The maximum number of recent files to list. Defaults to 5.

    Returns:
        A list of strings, where each string is "filename: preview_content".
        Returns an empty list if the category doesn't exist or contains no .txt files.
    """
    category_dir = os.path.join(BASE_SAVE_DIR, category)
    if not os.path.exists(category_dir) or not os.path.isdir(category_dir):
        return [f"Category '{category}' not found or is not a directory."]

    try:
        files = [
            os.path.join(category_dir, f)
            for f in os.listdir(category_dir)
            if f.endswith(".txt") and os.path.isfile(os.path.join(category_dir, f))
        ]

        if not files:
            return [f"No .txt files found in category '{category}'."]

        # Sort files by modification time (most recent first)
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        results = []
        for i, filepath in enumerate(files):
            if i >= count:
                break
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    preview = f.read(200).replace('\n', ' ') + "..."
                results.append(f"{os.path.basename(filepath)}: {preview}")
            except Exception as e:
                logger.warning(f"Error reading file {filepath} for preview: {e}")
                results.append(f"{os.path.basename(filepath)}: Error reading preview.")

        return results
    except OSError as e:
        logger.error(f"File system error while listing content in '{category}': {e}")
        return [f"Error: Could not list content due to a file system error: {e.strerror}"]
    except Exception as e:
        logger.error(f"Unexpected error while listing content: {e}")
        return [f"Error: An unexpected error occurred: {e}"]


@tool
def generate_character_elements(description: Optional[str] = None, genre: Optional[str] = None, count: int = 1) -> List[Dict[str, Any]]:
    """
    Generates a list of character ideas/elements based on optional description, genre, and desired count.
    Uses the 'writing/tool_generate_character_prompt' template.

    Args:
        description: Optional user-provided details or concepts for the characters.
        genre: Optional genre to tailor characters to (e.g., "Fantasy", "Sci-Fi").
        count: Number of unique character profiles to generate.

    Returns:
        A list of dictionaries, where each dictionary represents a character.
        Returns raw LLM output or error message if JSON parsing fails.
    """
    llm = get_llm_by_type("reasoning") # Good for structured output
    prompt_messages = apply_prompt_template(
        "writing/tool_generate_character_prompt",
        state={"description": description, "genre": genre, "count": count}
    )

    try:
        response = llm.invoke(prompt_messages)
        raw_response_content = response.content

        # Attempt to parse the JSON response
        # The prompt asks for a JSON list, so we expect `[` at the start.
        # Sometimes LLMs wrap JSON in ```json ... ```
        if "```json" in raw_response_content:
            json_str = raw_response_content.split("```json")[1].split("```")[0].strip()
        else:
            json_str = raw_response_content

        # Ensure it's a list
        if not json_str.startswith('['): # A simple check, might need more robust parsing
            logger.warning(f"LLM output for character generation was not a JSON list: {json_str[:200]}")
            # Try to find the list within the string
            list_start_index = json_str.find('[')
            list_end_index = json_str.rfind(']')
            if list_start_index != -1 and list_end_index != -1 and list_start_index < list_end_index:
                json_str = json_str[list_start_index : list_end_index+1]
            else: # Fallback if no list found
                 return [{"error": "LLM output was not a valid JSON list.", "raw_output": raw_response_content[:500]}]


        parsed_json = json.loads(json_str)
        if isinstance(parsed_json, list):
            return parsed_json
        else:
            logger.error(f"Parsed JSON is not a list: {type(parsed_json)}")
            return [{"error": "Parsed JSON from LLM is not a list.", "parsed_type": str(type(parsed_json)), "raw_output": raw_response_content[:500]}]

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed for character generation: {e}")
        logger.error(f"Raw LLM output: {raw_response_content[:500]}") # Log first 500 chars
        return [{"error": "Failed to parse LLM response as JSON.", "details": str(e), "raw_output": raw_response_content[:500]}]
    except Exception as e:
        logger.error(f"Error generating character elements: {e}")
        return [{"error": f"An unexpected error occurred: {e}"}]


@tool
def generate_plot_outline_elements(theme: Optional[str] = None, genre: Optional[str] = None, length: str = "short story", count: int = 1) -> List[Dict[str, Any]]:
    """
    Generates a list of plot outline ideas based on optional theme, genre, length, and desired count.
    Uses the 'writing/tool_generate_plot_outline_prompt' template.

    Args:
        theme: Optional central theme or concept to explore.
        genre: Optional genre to tailor the plot to.
        length: Desired length/scope of the story (e.g., "short story", "novel chapter"). Defaults to "short story".
        count: Number of unique plot outlines to generate.

    Returns:
        A list of dictionaries, where each dictionary represents a plot outline.
        Returns raw LLM output or error message if JSON parsing fails.
    """
    llm = get_llm_by_type("reasoning") # Good for structured output
    prompt_messages = apply_prompt_template(
        "writing/tool_generate_plot_outline_prompt",
        state={"theme": theme, "genre": genre, "length": length, "count": count}
    )

    try:
        response = llm.invoke(prompt_messages)
        raw_response_content = response.content

        if "```json" in raw_response_content:
            json_str = raw_response_content.split("```json")[1].split("```")[0].strip()
        else:
            json_str = raw_response_content

        # Ensure it's a list
        if not json_str.startswith('['): # A simple check
            logger.warning(f"LLM output for plot generation was not a JSON list: {json_str[:200]}")
            list_start_index = json_str.find('[')
            list_end_index = json_str.rfind(']')
            if list_start_index != -1 and list_end_index != -1 and list_start_index < list_end_index:
                json_str = json_str[list_start_index : list_end_index+1]
            else: # Fallback
                return [{"error": "LLM output was not a valid JSON list.", "raw_output": raw_response_content[:500]}]


        parsed_json = json.loads(json_str)
        if isinstance(parsed_json, list):
            return parsed_json
        else:
            logger.error(f"Parsed JSON is not a list: {type(parsed_json)}")
            return [{"error": "Parsed JSON from LLM is not a list.", "parsed_type": str(type(parsed_json)), "raw_output": raw_response_content[:500]}]

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed for plot outline generation: {e}")
        logger.error(f"Raw LLM output: {raw_response_content[:500]}")
        return [{"error": "Failed to parse LLM response as JSON.", "details": str(e), "raw_output": raw_response_content[:500]}]
    except Exception as e:
        logger.error(f"Error generating plot outline elements: {e}")
        return [{"error": f"An unexpected error occurred: {e}"}]


@tool
def retrieve_relevant_inspirations(query: str, count: int = 3) -> List[str]:
    """
    Retrieves relevant past inspirations or notes based on a query.
    This tool helps find related ideas that might have been saved previously.

    Args:
        query: The search query to find relevant inspirations.
        count: The maximum number of inspirations to retrieve. Defaults to 3.

    Returns:
        A list of strings, where each string is a formatted inspiration snippet
        (e.g., "From [filepath]: [chunk_text_preview]...").
        Returns an empty list if no relevant inspirations are found or an error occurs.
    """
    logger.debug(f"Attempting to retrieve {count} inspirations for query: '{query}'")
    try:
        # Ensure the retriever is initialized with the correct DB path
        retriever = InspirationRetriever(db_path=INSPIRATION_DB_PATH)
        results = retriever.retrieve_inspirations(query, count)

        if not results:
            logger.info(f"No relevant inspirations found for query: '{query}'")
            return ["No relevant inspirations found."]

        formatted_results = [
            f"From {res['filepath']}: {res['chunk_text'][:200].replace(chr(10), ' ')}..."
            for res in results
        ]
        logger.info(f"Retrieved {len(formatted_results)} formatted inspirations for query '{query}'.")
        return formatted_results
    except Exception as e:
        logger.error(f"Error retrieving relevant inspirations: {e}", exc_info=True)
        return ["Error: Could not retrieve inspirations at this time."]


# Example usage (for local testing, not part of the toolset)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Testing get_current_datetime:")
    print(get_current_datetime())
    print("-" * 20)

    print("Testing generate_random_inspiration_theme:")
    print(generate_random_inspiration_theme())
    print(generate_random_inspiration_theme(user_prompt="space opera"))
    print("-" * 20)

    print("Testing save_content_to_file and list_saved_content:")
    save_msg = save_content_to_file("This is a test inspiration.", "test_inspiration", category="tests")
    print(save_msg)
    save_msg_char = save_content_to_file("Character: Bob the Builder.", "bob", category="characters_test")
    print(save_msg_char)

    print("\nListing 'tests' category:")
    print(list_saved_content(category="tests", count=2))
    print("\nListing 'characters_test' category:")
    print(list_saved_content(category="characters_test", count=2))
    print("\nListing non-existent category:")
    print(list_saved_content(category="non_existent", count=2))
    print("-" * 20)

    # Note: LLM-dependent tools require proper environment setup for API keys
    # print("Testing generate_character_elements (requires LLM setup):")
    # characters = generate_character_elements(description="a brave knight", genre="Fantasy", count=1)
    # print(json.dumps(characters, indent=2))
    # print("-" * 20)

    # print("Testing generate_plot_outline_elements (requires LLM setup):")
    # plots = generate_plot_outline_elements(theme="betrayal", genre="Thriller", length="short story", count=1)
    # print(json.dumps(plots, indent=2))
    # print("-" * 20)

    # print("Testing retrieve_relevant_inspirations (requires RAG DB setup):")
    # # To test this, you'd first need to run the inspiration_indexer.py example
    # # to populate temp/rag_data/test_rag_inspirations.db (or adjust INSPIRATION_DB_PATH)
    # if os.path.exists(INSPIRATION_DB_PATH) or os.path.exists("temp/rag_data/test_rag_inspirations.db"):
    #     # Adjust path if your test indexer uses a different DB name
    #     # For this example, let's assume INSPIRATION_DB_PATH is the one to test against
    #     # or we temporarily change it for the test.
    #     # For a real test, you'd populate the INSPIRATION_DB_PATH.
    #     # Here, we'll assume the test_rag_inspirations.db from indexer example is relevant.
    #     # This part of the test is more conceptual without running the indexer from here.
    #     original_db_path_for_tool = INSPIRATION_DB_PATH
    #     # global INSPIRATION_DB_PATH # Not ideal for testing, but for a quick check
    #     # INSPIRATION_DB_PATH = "temp/rag_data/test_rag_inspirations.db" # Temporarily point to test DB if needed.
    #     # print(f"Temporarily using DB: {INSPIRATION_DB_PATH} for retrieve_relevant_inspirations test")

    #     retrieved = retrieve_relevant_inspirations(query="idea", count=2)
    #     print(f"Retrieved inspirations for 'idea': {retrieved}")
    #     retrieved_color = retrieve_relevant_inspirations(query="color", count=2)
    #     print(f"Retrieved inspirations for 'color': {retrieved_color}")

    #     # INSPIRATION_DB_PATH = original_db_path_for_tool # Reset if changed
    # else:
    #     print(f"Skipping retrieve_relevant_inspirations test as DB ({INSPIRATION_DB_PATH} or test_rag_inspirations.db) not found.")
    # print("-" * 20)


    # Cleanup test files and directories
    try:
        if os.path.exists(os.path.join(BASE_SAVE_DIR, "tests")):
            for f in os.listdir(os.path.join(BASE_SAVE_DIR, "tests")):
                os.remove(os.path.join(BASE_SAVE_DIR, "tests", f))
            os.rmdir(os.path.join(BASE_SAVE_DIR, "tests"))
        if os.path.exists(os.path.join(BASE_SAVE_DIR, "characters_test")):
            for f in os.listdir(os.path.join(BASE_SAVE_DIR, "characters_test")):
                os.remove(os.path.join(BASE_SAVE_DIR, "characters_test", f))
            os.rmdir(os.path.join(BASE_SAVE_DIR, "characters_test"))
        # if os.path.exists(BASE_SAVE_DIR) and not os.listdir(BASE_SAVE_DIR):
        # os.rmdir(BASE_SAVE_DIR) # Only remove if empty, but other tests might use it
    except Exception as e:
        print(f"Error during cleanup: {e}")

```
