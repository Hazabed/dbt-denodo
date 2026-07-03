{#
  Seed helpers for Denodo.

  Seeds are loaded into VDP materialized tables (requires the cache
  engine). Rows are inserted one INSERT statement at a time
  (basic_load_csv_rows with batch size 1): multi-row VALUES lists are not
  part of documented VQL grammar.
#}

{% macro denodo__create_csv_table(model, agate_table) %}
  {%- set column_override = model['config'].get('column_types', {}) -%}
  {%- set quote_seed_column = model['config'].get('quote_columns', None) -%}

  {% set sql %}
    create or replace materialized table {{ this.render() }} (
    {%- for col_name in agate_table.column_names -%}
      {%- set inferred_type = adapter.convert_type(agate_table, loop.index0) -%}
      {%- set type = column_override.get(col_name, inferred_type) -%}
      {%- set column_name = (col_name | string) -%}
      {{ adapter.quote_seed_column(column_name, quote_seed_column) }} {{ type }}
      {%- if not loop.last %}, {% endif -%}
    {%- endfor -%}
    )
  {% endset %}

  {% call statement('_') -%}
    {{ sql }}
  {%- endcall %}

  {{ return(sql) }}
{% endmacro %}

{% macro denodo__reset_csv_table(model, full_refresh, old_relation, agate_table) %}
  {# Drop and recreate in all cases: seeds are re-loaded from scratch and
     CREATE OR REPLACE after an explicit drop also covers type changes. #}
  {{ adapter.drop_relation(old_relation) }}
  {% set sql = create_csv_table(model, agate_table) %}
  {{ return(sql) }}
{% endmacro %}

{% macro denodo__get_batch_size() %}
  {# One row per INSERT: multi-row VALUES lists are not part of documented
     VQL grammar. The default load_csv_rows honors this batch size. #}
  {{ return(1) }}
{% endmacro %}
