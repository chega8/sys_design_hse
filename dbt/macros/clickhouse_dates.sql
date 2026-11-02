{# dbt_date не содержит реализации day_of_week для ClickHouse. #}
{% macro clickhouse__day_of_week(date, isoweek) -%}
    toDayOfWeek({{ date }}{% if not isoweek %}, 3{% endif %}){% if not isoweek %} + 1{% endif %}
{%- endmacro %}
