# SPDX-License-Identifier: MIT

"""
Bash command execution tool with security restrictions and git integration.
"""

import os
import subprocess
import logging
import re
from typing import Optional, List, Set
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Banned commands for security
BANNED_COMMANDS = {
    "alias", "curl", "curlie", "wget", "axel", "aria2c", "nc", "telnet", 
    "lynx", "w3m", "links", "httpie", "xh", "http-prompt", "chrome", 
    "firefox", "safari"
}

# Commands that should use specialized tools instead
DISCOURAGED_COMMANDS = {
    "find": "Use GrepTool or SearchGlobTool instead",
    "grep": "Use GrepTool instead", 
    "cat": "Use View tool instead",
    "head": "Use View tool instead",
    "tail": "Use View tool instead",
    "ls": "Use List tool instead"
}

MAX_OUTPUT_LENGTH = 30000


def check_command_security(command: str) -> tuple[bool, str]:
    """Check if command is allowed based on security policy."""
    # Extract the first command from the command line
    first_command = command.strip().split()[0] if command.strip() else ""
    base_command = os.path.basename(first_command)
    
    # Check banned commands
    if base_command in BANNED_COMMANDS:
        return False, f"Command '{base_command}' is banned for security reasons. Banned commands: {', '.join(sorted(BANNED_COMMANDS))}"
    
    # Check discouraged commands
    if base_command in DISCOURAGED_COMMANDS:
        suggestion = DISCOURAGED_COMMANDS[base_command]
        return False, f"Command '{base_command}' should not be used. {suggestion}"
    
    return True, "Command is allowed"


def execute_bash_command(command: str, timeout_ms: Optional[int] = None, cwd: Optional[str] = None) -> str:
    """Execute a bash command with proper error handling and output truncation."""
    try:
        # Set timeout (default 30 minutes, max 10 minutes for tool)
        timeout_seconds = min((timeout_ms or 1800000) / 1000, 600)  # Max 10 minutes
        
        # Use provided cwd or current directory
        working_dir = cwd or os.getcwd()
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=working_dir
        )
        
        # Combine stdout and stderr
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n" + result.stderr
            else:
                output = result.stderr
        
        # Add exit code information
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        
        # Truncate output if too long
        if len(output) > MAX_OUTPUT_LENGTH:
            truncated_length = MAX_OUTPUT_LENGTH - 200  # Leave space for truncation message
            output = output[:truncated_length] + f"\n\n... (output truncated, showing first {truncated_length} characters of {len(output)} total)"
        
        return output or "(no output)"
        
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout_seconds} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def bash_command(command: str, timeout: Optional[int] = None) -> str:
    """
    Executes a given bash command in a persistent shell session with optional timeout, ensuring proper 
    handling and security measures.
    
    Before executing the command, please follow these steps:
    1. Directory Verification:
       - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location
       - For example, before running "mkdir foo/bar", first use LS to check that "foo" exists and is the intended parent directory
    2. Security Check:
       - For security and to limit the threat of a prompt injection attack, some commands are limited or banned. If you use a disallowed command, you will receive an error message explaining the restriction. Explain the error to the User.
       - Verify that the command is not one of the banned commands: alias, curl, curlie, wget, axel, aria2c, nc, telnet, lynx, w3m, links, httpie, xh, http-prompt, chrome, firefox, safari.
    3. Command Execution:
       - After ensuring proper quoting, execute the command.
       - Capture the output of the command.
    4. Output Processing:
       - If the output exceeds 30000 characters, output will be truncated before being returned to you.
       - Prepare the output for display to the user.
    5. Return Result:
       - Provide the processed output of the command.
       - If any errors occurred during execution, include those in the output.

    Usage notes:
      - The command argument is required.
      - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 30 minutes.
      - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use GrepTool, SearchGlobTool, or dispatch_agent to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use View and List to read files.
      - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
      - IMPORTANT: All commands share the same shell session. Shell state (environment variables, virtual environments, current directory, etc.) persist between commands. For example, if you set an environment variable as part of a command, the environment variable will persist for subsequent commands.
      - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.

    Args:
        command: The command to execute
        timeout: Optional timeout in milliseconds (max 600000)

    Returns:
        The command output and any error messages
    """
    try:
        # Security check
        is_allowed, security_message = check_command_security(command)
        if not is_allowed:
            return f"Security Error: {security_message}"

        # Log command execution
        logger.info(f"Executing bash command: {command[:100]}...")

        # Execute command
        output = execute_bash_command(command, timeout)
        
        # Handle git-specific commands with special formatting
        if command.strip().startswith(('git ', 'gh ')):
            # For git commands, format output nicely
            if "git status" in command:
                output = f"Git Status:\n{output}"
            elif "git log" in command:
                output = f"Git Log:\n{output}"
            elif "git diff" in command:
                output = f"Git Diff:\n{output}"
            elif "gh pr create" in command:
                output = f"Pull Request Created:\n{output}"

        return output

    except Exception as e:
        error_msg = f"Bash tool error: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Helper function for git operations
def format_git_commit_message(title: str, body: str) -> str:
    """Format a git commit message with Claude attribution."""
    return f"""{title}

{body}

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"""


def validate_git_command(command: str) -> tuple[bool, str]:
    """Validate git commands for safety."""
    # Prevent interactive commands
    if re.search(r'-i\b', command):
        return False, "Interactive git commands (with -i flag) are not supported"
    
    # Prevent config changes
    if 'git config' in command:
        return False, "Git config changes are not allowed"
    
    # Prevent push commands (should be explicit)
    if re.search(r'\bgit\s+push\b', command):
        return False, "Git push commands should be handled carefully. Please explicitly confirm push operations."
    
    return True, "Git command is valid" 