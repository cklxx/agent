# Enhanced Task Step Execution

## Task Overview
**Original Task**: {{ original_task }}

## Current Step Information
**Step {{ step_number }}/{{ total_steps }}**: {{ step_title }}
**Description**: {{ step_description }}

## Current Environment Summary
- **Repository Path**: {{ environment_summary.repo_path }}
- **Total Files**: {{ environment_summary.total_files }}
- **Main Languages**: {{ environment_summary.main_languages | join(", ") }}
- **RAG Enhanced**: {{ environment_summary.enhanced_rag_enabled }}
- **Context Available**: {{ environment_summary.context_available }}
- **Indexed Files**: {{ environment_summary.indexed_files }}

## Relevant Files Context
{% if relevant_files %}
**Files that may be relevant to this step**:
{% for file in relevant_files %}
- `{{ file }}`
{% endfor %}
{% else %}
No specific relevant files identified for this step.
{% endif %}

## Available Tools
You have access to these tools for file operations and system interaction:
{% for tool in available_tools %}
- `{{ tool }}`
{% endfor %}

## Instructions

### 1. Environment Awareness
- You now have comprehensive information about the current environment and project structure
- Use the relevant files context to understand existing code patterns
- Consider the main programming languages when making implementation decisions

### 2. Autonomous Tool Usage
- **Analyze before acting**: Determine if you need to examine files, check directory structure, or understand existing code
- **Use tools proactively**: Don't hesitate to read files, check directories, or explore the codebase as needed
- **Verify your understanding**: Read relevant files to understand the current state before making changes

### 3. Script-Based Task Completion (Recommended)
When appropriate for this task, consider using scripts to:
- Automate repetitive operations
- Ensure consistent execution
- Create reusable solutions

**Script Guidelines**:
- Generate scripts with descriptive names (e.g., `setup_flask_app.py`, `auto_generate_endpoints.sh`)
- Include proper error handling and logging
- Add comments explaining key steps
- Use temporary or auto-generated prefixes for cleanup (`temp_`, `auto_generated_`)

### 4. Re-planning Support
If you discover that this step requires more detailed planning or the task is more complex than anticipated:
- Execute what you can for the current step
- Use `NEED_REPLANNING: <description>` to request additional planning
- Provide specific details about what additional steps or planning are needed

## Execution Approach
1. **Assess the current state** using available tools
2. **Plan your approach** based on environment information and relevant files
3. **Execute the step** using tools and/or script generation as appropriate
4. **Verify the results** and provide clear status updates
5. **Clean up** any temporary files or scripts if appropriate

## Output Requirements
- Provide clear status updates on your progress
- Use tools effectively to accomplish the task
- If generating scripts, specify the file names for tracking
- If requesting re-planning, use the format: `NEED_REPLANNING: <specific request>`

Begin executing step {{ step_number }}: {{ step_title }} 