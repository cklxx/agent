{% if relevant_code|length == 0 %}
# Code Context
No directly relevant code found. Proceed with task implementation following best practices.
{% else %}
# Code Context
Found {{ relevant_code|length }} relevant files in {{ project_languages[:2]|join(', ') }} project.

{% for code_info in relevant_code[:3] %}
## {{ loop.index }}. {{ code_info.file_path|basename }}
{% if code_info.best_chunk %}
```
{{ code_info.best_chunk.content[:300] }}{% if code_info.best_chunk.content|length > 300 %}...{% endif %}
```
{% else %}
Path: {{ code_info.file_path }}
{% endif %}

{% endfor %}
## Guidelines
- Follow patterns from above code examples
- Maintain consistency with existing code style
- Use similar naming conventions and structure

{% endif %} 