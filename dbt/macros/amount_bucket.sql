{% macro amount_bucket(column) -%}
    multiIf({{ column }} < 100, 'SMALL', {{ column }} < 500, 'MEDIUM', 'LARGE')
{%- endmacro %}
