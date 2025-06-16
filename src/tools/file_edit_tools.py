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
    Replace exact text in file or create new file.

    Args:
        file_path: Absolute path to file
        old_string: Exact text to replace (empty for new file)
        new_string: Replacement text

    Returns:
        Success or error message
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
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_string)

            return f"Successfully created new file: {file_path}"

        # Handle existing file editing
        if not os.path.exists(file_path):
            return f"Error: File does not exist: {file_path}"

        if not os.path.isfile(file_path):
            return f"Error: Path is not a file: {file_path}"

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ["gbk", "gb2312", "latin1"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
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
        new_content = content.replace(
            old_string, new_string, 1
        )  # Replace only first occurrence

        # Verify the replacement actually changed something
        if new_content == content:
            return f"Warning: No changes made. old_string and new_string are identical."

        # Write updated content back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Provide informative success message
        lines_added = new_string.count("\n") - old_string.count("\n")
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
    Write complete content to file, overwriting existing file.

    Args:
        file_path: Absolute path to file
        content: Complete file content to write

    Returns:
        Success or error message
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
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Get new file info
        new_size = os.path.getsize(file_path)
        new_lines = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )

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
