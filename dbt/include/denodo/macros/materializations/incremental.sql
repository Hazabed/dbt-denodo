{#
  Incremental materialization for Denodo.

  Strategies:
    - append (default): INSERT INTO target SELECT ... FROM staging view
    - delete+insert:    DELETE matching unique_key rows, then INSERT

  The staging relation is a plain derived view (cheap on Denodo — views are
  virtual), created with a temp suffix and dropped afterwards. DML runs
  against the materialized table, which VDP supports for INSERT and DELETE.

  Statements are issued one at a time: the pg-wire interface is not assumed
  to support multi-statement batches.
#}

{% macro dbt_denodo_get_incremental_sql(strategy, tmp_relation, target_relation, unique_key, dest_columns) %}
  {%- set dest_cols_csv = get_quoted_csv(dest_columns | map(attribute='name')) -%}
  insert into {{ target_relation }} ({{ dest_cols_csv }})
  select {{ dest_cols_csv }}
  from {{ tmp_relation }}
{% endmacro %}

{% macro dbt_denodo_get_delete_sql(tmp_relation, target_relation, unique_key) %}
  {%- if unique_key is string -%}
    delete from {{ target_relation }}
    where {{ unique_key }} in (select {{ unique_key }} from {{ tmp_relation }})
  {%- else -%}
    {% do exceptions.raise_compiler_error(
        'dbt-denodo delete+insert requires a single-column unique_key (got a list).'
    ) %}
  {%- endif -%}
{% endmacro %}

{% materialization incremental, adapter='denodo' -%}

  {%- set strategy = config.get('incremental_strategy') or 'append' -%}
  {%- if strategy not in ['append', 'delete+insert'] -%}
    {% do exceptions.raise_compiler_error(
        "Invalid incremental strategy for dbt-denodo: '" ~ strategy ~ "'. "
        ~ "Expected one of: 'append', 'delete+insert'."
    ) %}
  {%- endif -%}
  {%- set unique_key = config.get('unique_key') -%}
  {%- if strategy == 'delete+insert' and not unique_key -%}
    {% do exceptions.raise_compiler_error(
        "dbt-denodo incremental strategy 'delete+insert' requires a unique_key config."
    ) %}
  {%- endif -%}
  {%- if config.get('incremental_predicates') -%}
    {% do exceptions.raise_compiler_error('incremental_predicates is not supported by dbt-denodo.') %}
  {%- endif -%}

  {%- set target_relation = this.incorporate(type='table') -%}
  {%- set existing_relation = load_cached_relation(this) -%}
  {%- set tmp_relation = make_temp_relation(target_relation).incorporate(type='view') -%}
  {%- set full_refresh_mode = (should_full_refresh()) -%}

  {{ run_hooks(pre_hooks) }}

  {% if existing_relation is none or full_refresh_mode or existing_relation.is_view %}
    {#- initial build, full refresh, or type change: rebuild in place -#}
    {%- if existing_relation is not none and existing_relation.is_view -%}
      {{ adapter.drop_relation(existing_relation) }}
    {%- endif -%}
    {% call statement('main') -%}
      {{ get_create_table_as_sql(False, target_relation, sql) }}
    {%- endcall %}
  {% else %}
    {#- incremental run: stage new rows in a temporary derived view -#}
    {% do adapter.drop_relation(tmp_relation) %}
    {% do run_query(create_view_as(tmp_relation, sql)) %}
    {%- set dest_columns = adapter.get_columns_in_relation(target_relation) -%}

    {% if strategy == 'delete+insert' %}
      {% do run_query(dbt_denodo_get_delete_sql(tmp_relation, target_relation, unique_key)) %}
    {% endif %}

    {% call statement('main') -%}
      {{ dbt_denodo_get_incremental_sql(strategy, tmp_relation, target_relation, unique_key, dest_columns) }}
    {%- endcall %}

    {% do adapter.drop_relation(tmp_relation) %}
  {% endif %}

  {{ run_hooks(post_hooks) }}

  {% do persist_docs(target_relation, model) %}

  {{ return({'relations': [target_relation]}) }}

{%- endmaterialization %}
