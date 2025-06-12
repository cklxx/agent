# SPDX-License-Identifier: MIT

"""
File editing and replacement tools.
Provides precise string replacement and file overwriting capabilities.
"""

import os
from typing import Dict, Any
from langchain_core.tools import tool


@tool
def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """
    This is a tool for editing files. For moving or renaming files, you should generally use the Bash tool 
    with the 'mv' command instead. For larger edits, use the Write tool to overwrite files. For Jupyter 
    notebooks (.ipynb files), use the NotebookEditCellTool instead.

    Before using this tool:
    1. Use the View tool to understand the file's contents and context
    2. Verify the directory path is correct (only applicable when creating new files):
       - Use the LS tool to verify the parent directory exists and is the correct location

    To make a file edit, provide the following:
    1. file_path: The absolute path to the file to modify (must be absolute, not relative)
    2. old_string: The text to replace (must be unique within the file, and must match the file contents exactly, including all whitespace and indentation)
    3. new_string: The edited text to replace the old_string

    The tool will replace ONE occurrence of old_string with new_string in the specified file.

    CRITICAL REQUIREMENTS FOR USING THIS TOOL:
    1. UNIQUENESS: The old_string MUST uniquely identify the specific instance you want to change. This means:
       - Include AT LEAST 3-5 lines of context BEFORE the change point
       - Include AT LEAST 3-5 lines of context AFTER the change point
       - Include all whitespace, indentation, and surrounding code exactly as it appears in the file
    2. SINGLE INSTANCE: This tool can only change ONE instance at a time. If you need to change multiple instances:
       - Make separate calls to this tool for each instance
       - Each call must uniquely identify its specific instance using extensive context
    3. VERIFICATION: Before using this tool:
       - Check how many instances of the target text exist in the file
       - If multiple instances exist, gather enough context to uniquely identify each one
       - Plan separate tool calls for each instance

    WARNING: If you do not follow these requirements:
       - The tool will fail if old_string matches multiple locations
       - The tool will fail if old_string doesn't match exactly (including whitespace)
       - You may change the wrong instance if you don't include enough context

    When making edits:
       - Ensure the edit results in idiomatic, correct code
       - Do not leave the code in a broken state
       - Always use absolute file paths (starting with /)

    If you want to create a new file, use:
       - A new file path, including dir name if needed
       - An empty old_string
       - The new file's contents as new_string

    Args:
        file_path: The absolute path to the file to modify
        old_string: The text to replace
        new_string: The text to replace it with

    Returns:
        Success or error message describing the result
    """
    try:
        # Validate absolute path
        if not os.path.isabs(file_path):
            return f"Error: file_path must be an absolute path, got: {file_path}"

        # Handle new file creation
        if old_string == "":
            # Creating a new file
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                return f"Error: Parent directory does not exist: {parent_dir}"
            
            # Check if file already exists
            if os.path.exists(file_path):
                return f"Error: File already exists. Use non-empty old_string to edit existing files or use Replace tool to overwrite: {file_path}"
            
            # Create new file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_string)
            
            return f"Successfully created new file: {file_path}"

        # Handle existing file editing
        if not os.path.exists(file_path):
            return f"Error: File does not exist: {file_path}"

        if not os.path.isfile(file_path):
            return f"Error: Path is not a file: {file_path}"

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['gbk', 'gb2312', 'latin1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return f"Error: Cannot decode file with common encodings: {file_path}"

        # Check if old_string exists in content
        if old_string not in content:
            return f"Error: old_string not found in file. Make sure to include exact whitespace and indentation."

        # Count occurrences of old_string
        occurrences = content.count(old_string)
        if occurrences == 0:
            return f"Error: old_string not found in file: {file_path}"
        elif occurrences > 1:
            return f"Error: old_string found {occurrences} times in file. Please provide more context to uniquely identify the instance to replace."

        # Perform replacement
        new_content = content.replace(old_string, new_string, 1)  # Replace only first occurrence

        # Verify the replacement actually changed something
        if new_content == content:
            return f"Warning: No changes made. old_string and new_string are identical."

        # Write updated content back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # Provide informative success message
        lines_added = new_string.count('\n') - old_string.count('\n')
        if lines_added > 0:
            change_desc = f"(+{lines_added} lines)"
        elif lines_added < 0:
            change_desc = f"({lines_added} lines)"
        else:
            change_desc = "(same line count)"

        return f"Successfully edited {file_path} {change_desc}"

    except Exception as e:
        return f"Error editing file: {str(e)}"


@tool  
def replace_file(file_path: str, content: str) -> str:
    """
    Write a file to the local filesystem. Overwrites the existing file if there is one.
    
    Before using this tool:
    1. Use the ReadFile tool to understand the file's contents and context
    2. Directory Verification (only applicable when creating new files):
       - Use the LS tool to verify the parent directory exists and is the correct location

    Args:
        file_path: The absolute path to the file to write (must be absolute, not relative)
        content: The content to write to the file

    Returns:
        Success or error message with file information
    """
    try:
        # Validate absolute path
        if not os.path.isabs(file_path):
            return f"Error: file_path must be an absolute path, got: {file_path}"

        # Check parent directory exists (for new files)
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            return f"Error: Parent directory does not exist: {parent_dir}"

        # Check if this is creating a new file or updating existing
        is_new_file = not os.path.exists(file_path)
        
        # Get original file size if it exists
        original_size = 0
        if not is_new_file:
            try:
                original_size = os.path.getsize(file_path)
            except OSError:
                pass

        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Get new file info
        new_size = os.path.getsize(file_path)
        new_lines = content.count('\n') + (1 if content and not content.endswith('\n') else 0)

        # Format success message
        if is_new_file:
            return f"Successfully created {file_path} ({new_size} bytes, {new_lines} lines)"
        else:
            size_change = new_size - original_size
            if size_change > 0:
                size_desc = f"(+{size_change} bytes)"
            elif size_change < 0:
                size_desc = f"({size_change} bytes)"
            else:
                size_desc = "(same size)"
            
            return f"Successfully updated {file_path} {size_desc}, now {new_size} bytes, {new_lines} lines"

    except Exception as e:
        return f"Error writing file: {str(e)}" 