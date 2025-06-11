# Intelligent File Classification for RAG Indexing

You are an expert software engineer tasked with intelligently classifying files to determine which ones should be indexed for code retrieval and analysis.

## Task Context
**Repository Path**: {{repo_path}}
**Task Type**: {{task_context}}

## Files to Classify
The following files have been pre-filtered and need intelligent classification:

{% for file in files %}
- **Path**: {{file.path}}
  - **Type**: {{file.type}}
  - **Size**: {{file.size_kb}} KB
  - **Current Assessment**: {{file.current_relevance}}
{% endfor %}

## Classification Guidelines

### HIGH Relevance (Must Index)
- Core application/library source code
- Main configuration files (package.json, requirements.txt, etc.)
- API definitions and interfaces
- Database schemas and models
- Custom business logic implementations
- Project-specific utilities and helpers

### MEDIUM Relevance (Should Index)
- Documentation files (README, CHANGELOG)
- Configuration templates and examples
- Test files that demonstrate usage patterns
- Build and deployment scripts
- Project-specific configuration files

### LOW Relevance (Optional Index)
- Generic utility files
- Example code or tutorials
- Temporary or experimental files
- Large data files or assets

### EXCLUDE (Do Not Index)
- Third-party libraries and dependencies
- Virtual environment files
- Generated/compiled files
- IDE-specific files (.vscode, .idea)
- Cache and temporary files
- Binary files and assets
- Log files

## Special Considerations

### For {{task_context}}:
- Focus on files most relevant to the specific task type
- Consider dependencies and related files
- Prioritize files that contain patterns and examples

### File Size Considerations:
- Files > 100KB: Carefully evaluate necessity
- Files > 500KB: Generally exclude unless critical
- Very small files (<1KB): Often configuration or imports

## Response Format

Provide your classification for each file in the following format:

```
file_path: relevance_level - brief_reason
```

Examples:
```
src/main.py: HIGH - Core application entry point
config/settings.yaml: MEDIUM - Application configuration
tests/test_utils.py: MEDIUM - Test patterns and examples
node_modules/react/index.js: EXCLUDE - Third-party dependency
```

## Instructions

1. Analyze each file based on its path, type, and size
2. Consider the specific task context when making decisions
3. Be conservative with HIGH ratings - only for truly essential files
4. Explain your reasoning briefly for each classification
5. When in doubt, prefer MEDIUM over HIGH, and LOW over EXCLUDE

Focus on maximizing the signal-to-noise ratio for the code retrieval system. 