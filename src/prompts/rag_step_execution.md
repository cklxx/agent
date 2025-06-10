# {{ step_title }}

**Task**: {{ original_task }}
**Step**: {{ step_description }}

{% if relevant_files|length > 0 %}
{% set high_sim_files = relevant_files|selectattr('has_high_similarity')|list %}
{% if high_sim_files|length > 0 %}

**Reference Files**:
{% for file in high_sim_files[:2] %}
- {{ file.file_path|basename }}
{% endfor %}
{% endif %}
{% endif %}

{% if project_languages|length > 0 %}
**Languages**: {{ project_languages[:2]|join(', ') }}
{% endif %}

Execute the task step. Use available tools as needed. Follow patterns from reference files if provided. 