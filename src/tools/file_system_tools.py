# SPDX-License-Identifier: MIT

"""
File system tools for file and directory operations.
Based on modern tool specifications with support for absolute paths, glob patterns, and content search.
"""

import os
import glob
import re
import mimetypes
from typing import Optional, List
from pathlib import Path
from langchain_core.tools import tool
from PIL import Image
import json


@tool
def view_file(
    file_path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None
) -> str:
    """
    Reads a file from the local filesystem. The file_path parameter must be an absolute path, not a relative path. 
    By default, it reads up to 2000 lines starting from the beginning of the file. You can optionally specify 
    a line offset and limit (especially handy for long files), but it's recommended to read the whole file by 
    not providing these parameters. Any lines longer than 2000 characters will be truncated. For image files, 
    the tool will display the image for you.

    Args:
        file_path: The absolute path to the file to read
        offset: The line number to start reading from. Only provide if the file is too large to read at once
        limit: The number of lines to read. Only provide if the file is too large to read at once

    Returns:
        The file content as a string
    """
    try:
        # Validate absolute path
        if not os.path.isabs(file_path):
            return f"Error: file_path must be an absolute path, got: {file_path}"
        
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File does not exist: {file_path}"
        
        if not os.path.isfile(file_path):
            return f"Error: Path is not a file: {file_path}"
        
        # Check if it's an image file
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('image/'):
            try:
                with Image.open(file_path) as img:
                    return f"Image file: {file_path}\nDimensions: {img.size}\nFormat: {img.format}\nMode: {img.mode}"
            except Exception as e:
                return f"Error reading image file: {str(e)}"
        
        # Read text file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['gbk', 'gb2312', 'latin1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return f"Error: Cannot decode file with common encodings: {file_path}"
        
        # Apply offset and limit
        start_idx = (offset - 1) if offset else 0
        end_idx = (start_idx + limit) if limit else min(len(lines), 2000)
        
        # Ensure we don't exceed 2000 lines default limit
        if not limit and end_idx > 2000:
            end_idx = 2000
        
        selected_lines = lines[start_idx:end_idx]
        
        # Truncate long lines
        truncated_lines = []
        for line in selected_lines:
            if len(line) > 2000:
                truncated_lines.append(line[:2000] + "...[truncated]\n")
            else:
                truncated_lines.append(line)
        
        content = ''.join(truncated_lines)
        
        # Add metadata
        total_lines = len(lines)
        showing_lines = f"Lines {start_idx + 1}-{min(end_idx, total_lines)}"
        if total_lines > end_idx:
            showing_lines += f" of {total_lines}"
        
        return f"File: {file_path}\n{showing_lines}\n\n{content}"
        
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def list_files(path: str) -> str:
    """
    Lists files and directories in a given path. The path parameter must be an absolute path, not a relative path. 
    You should generally prefer the Glob and Grep tools, if you know which directories to search.

    Args:
        path: The absolute path to the directory to list (must be absolute, not relative)

    Returns:
        A formatted list of files and directories
    """
    try:
        # Validate absolute path
        if not os.path.isabs(path):
            return f"Error: path must be an absolute path, got: {path}"
        
        # Check if directory exists
        if not os.path.exists(path):
            return f"Error: Directory does not exist: {path}"
        
        if not os.path.isdir(path):
            return f"Error: Path is not a directory: {path}"
        
        # Get directory contents
        items = []
        try:
            entries = os.listdir(path)
            entries.sort()  # Sort alphabetically
            
            for entry in entries:
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    # Count items in subdirectory
                    try:
                        sub_count = len(os.listdir(full_path))
                        items.append(f"[dir]  {entry}/ ({sub_count} items)")
                    except PermissionError:
                        items.append(f"[dir]  {entry}/ (permission denied)")
                else:
                    # Get file size
                    try:
                        size = os.path.getsize(full_path)
                        if size < 1024:
                            size_str = f"{size}B"
                        elif size < 1024 * 1024:
                            size_str = f"{size/1024:.1f}KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f}MB"
                        
                        # Count lines for text files
                        line_count = ""
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                lines = sum(1 for _ in f)
                            line_count = f", {lines} lines"
                        except:
                            pass
                        
                        items.append(f"[file] {entry} ({size_str}{line_count})")
                    except OSError:
                        items.append(f"[file] {entry} (size unknown)")
            
        except PermissionError:
            return f"Error: Permission denied accessing directory: {path}"
        
        if not items:
            return f"Directory is empty: {path}"
        
        result = f"Contents of directory: {path}\n\n"
        result += "\n".join(items)
        
        return result
        
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def glob_search(pattern: str, path: Optional[str] = None) -> str:
    """
    Fast file pattern matching tool that works with any codebase size. Supports glob patterns like "**/*.js" 
    or "src/**/*.ts". Returns matching file paths sorted by modification time. Use this tool when you need 
    to find files by name patterns.

    Args:
        pattern: The glob pattern to match files against
        path: The directory to search in. Defaults to the current working directory

    Returns:
        A list of matching file paths
    """
    try:
        # Use current working directory if path not provided
        search_path = path if path else os.getcwd()
        
        # Validate that search_path is absolute
        if not os.path.isabs(search_path):
            return f"Error: search path must be absolute, got: {search_path}"
        
        # Check if search directory exists
        if not os.path.exists(search_path):
            return f"Error: Search directory does not exist: {search_path}"
        
        # Change to search directory for glob operation
        original_cwd = os.getcwd()
        os.chdir(search_path)
        
        try:
            # Perform glob search
            matches = glob.glob(pattern, recursive=True)
            
            if not matches:
                return f"No files found matching pattern '{pattern}' in {search_path}"
            
            # Convert to absolute paths and get file info
            file_info = []
            for match in matches:
                abs_path = os.path.abspath(match)
                if os.path.isfile(abs_path):
                    stat = os.stat(abs_path)
                    file_info.append((abs_path, stat.st_mtime))
            
            # Sort by modification time (newest first)
            file_info.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            result = f"Found {len(file_info)} files matching '{pattern}' in {search_path}:\n\n"
            for file_path, mtime in file_info:
                # Make path relative to search directory for cleaner output
                try:
                    rel_path = os.path.relpath(file_path, search_path)
                    result += f"{rel_path}\n"
                except ValueError:
                    result += f"{file_path}\n"
            
            return result
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        return f"Error during glob search: {str(e)}"


@tool
def grep_search(
    pattern: str, 
    path: Optional[str] = None, 
    include: Optional[str] = None
) -> str:
    """
    Fast content search tool that works with any codebase size. Searches file contents using regular expressions. 
    Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.). Filter files by pattern with the 
    include parameter (eg. "*.js", "*.{ts,tsx}"). Returns matching file paths sorted by modification time. 
    Use this tool when you need to find files containing specific patterns.

    Args:
        pattern: The regular expression pattern to search for in file contents
        path: The directory to search in. Defaults to the current working directory
        include: File pattern to include in the search (e.g. "*.js", "*.{ts,tsx}")

    Returns:
        Files containing the pattern with line numbers and context
    """
    try:
        # Use current working directory if path not provided
        search_path = path if path else os.getcwd()
        
        # Validate that search_path is absolute  
        if not os.path.isabs(search_path):
            return f"Error: search path must be absolute, got: {search_path}"
        
        # Check if search directory exists
        if not os.path.exists(search_path):
            return f"Error: Search directory does not exist: {search_path}"
        
        # Compile regex pattern
        try:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            return f"Error: Invalid regex pattern '{pattern}': {str(e)}"
        
        # Get list of files to search
        files_to_search = []
        
        if include:
            # Use glob pattern to filter files
            original_cwd = os.getcwd()
            os.chdir(search_path)
            try:
                # Handle complex patterns like "*.{ts,tsx}"
                if '{' in include and '}' in include:
                    # Extract extensions from pattern like "*.{ts,tsx}"
                    base_pattern = include.split('{')[0]
                    extensions = include.split('{')[1].split('}')[0].split(',')
                    for ext in extensions:
                        pattern_to_use = base_pattern + ext.strip()
                        matches = glob.glob(f"**/{pattern_to_use}", recursive=True)
                        files_to_search.extend(matches)
                else:
                    matches = glob.glob(f"**/{include}", recursive=True)
                    files_to_search.extend(matches)
            finally:
                os.chdir(original_cwd)
        else:
            # Search all text files
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Skip binary files
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            f.read(1)  # Try to read one character
                        files_to_search.append(os.path.relpath(file_path, search_path))
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # Search for pattern in files
        matches = []
        for file_rel in files_to_search:
            file_path = os.path.join(search_path, file_rel) if not os.path.isabs(file_rel) else file_rel
            
            if not os.path.isfile(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                file_matches = []
                for line_num, line in enumerate(lines, 1):
                    if regex.search(line):
                        file_matches.append((line_num, line.rstrip()))
                
                if file_matches:
                    stat = os.stat(file_path)
                    matches.append((file_path, file_matches, stat.st_mtime))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if not matches:
            search_desc = f" in files matching '{include}'" if include else ""
            return f"No matches found for pattern '{pattern}'{search_desc} in {search_path}"
        
        # Sort by modification time
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # Format results
        result = f"Found {len(matches)} files containing pattern '{pattern}'"
        if include:
            result += f" in files matching '{include}'"
        result += f" in {search_path}:\n\n"
        
        for file_path, file_matches, _ in matches:
            try:
                rel_path = os.path.relpath(file_path, search_path)
            except ValueError:
                rel_path = file_path
                
            result += f"File: {rel_path}\n"
            for line_num, line in file_matches[:5]:  # Show first 5 matches per file
                result += f"Line {line_num}: {line}\n"
            
            if len(file_matches) > 5:
                result += f"... and {len(file_matches) - 5} more matches\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"Error during grep search: {str(e)}"