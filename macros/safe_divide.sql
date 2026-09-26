{% macro safe_divide(numerator, denominator) -%}
    ({{ numerator }}) * 1.0 / nullif(({{ denominator }}), 0)
{%- endmacro %}
