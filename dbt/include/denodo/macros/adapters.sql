{#
  Adapter macros for Denodo Virtual DataPort (Denodo Platform 8).

  All SQL here is VQL executed through VDP's PostgreSQL-compatible
  interface (port 9996), which passes VQL statements through verbatim.

  Documented behavior relied on:
    - CREATE [OR REPLACE] VIEW <name> AS <query>
    - CREATE [OR REPLACE] MATERIALIZED TABLE <name> AS <query>   (requires cache engine)
    - DROP { VIEW | TABLE } [IF EXISTS] <name> [CASCADE]
    - GET_VIEWS() / GET_VIEW_COLUMNS() predefined stored procedures
    - LIST DATABASES / CREATE DATABASE / DROP DATABASE
    - VQL has no RENAME statement: rename_relation raises.
#}

{% macro denodo__current_timestamp() -%}
  now()
{%- endmacro %}

{% macro denodo__list_schemas(database) %}
  {# Denodo "schemas" are virtual databases. LIST DATABASES returns one
     row per database; dbt only reads the first column of each row. #}
  {{ return(run_query('LIST DATABASES')) }}
{% endmacro %}

{% macro denodo__create_schema(relation) -%}
  {# Requires an administrator user. Most deployments pre-create the
     virtual database instead; see README. #}
  {%- call statement('create_schema') -%}
    CREATE DATABASE {{ relation.without_identifier() }} ''
  {%- endcall -%}
{% endmacro %}

{% macro denodo__drop_schema(relation) -%}
  {%- call statement('drop_schema') -%}
    DROP DATABASE IF EXISTS {{ relation.without_identifier() }}
  {%- endcall -%}
{% endmacro %}

{% macro denodo__list_relations_without_caching(schema_relation) %}
  {% call statement('list_relations_without_caching', fetch_result=True) -%}
    select
        {# echo the node-side database so cached relations match node
           relations exactly; it is never rendered in SQL #}
        '{{ schema_relation.database }}' as "database",
        name as "name",
        database_name as "schema",
        case when view_type in (1, 2) then 'view' else 'table' end as "type"
    from get_views()
    where input_database_name = '{{ schema_relation.schema }}'
  {%- endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}

{% macro denodo__get_columns_in_relation(relation) -%}
  {% call statement('get_columns_in_relation', fetch_result=True) %}
    select
        column_name,
        lower(column_vdp_type) as data_type,
        column_size as character_maximum_length,
        column_size as numeric_precision,
        column_decimals as numeric_scale
    from get_view_columns()
    where input_database_name = '{{ relation.schema }}'
      and input_view_name = '{{ relation.identifier }}'
  {% endcall %}
  {% set table = load_result('get_columns_in_relation').table %}
  {{ return(sql_convert_columns_in_relation(table)) }}
{% endmacro %}

{% macro denodo__create_view_as(relation, sql) -%}
  {%- set folder = config.get('folder') -%}
  create or replace view {{ relation }}
  {%- if folder %} folder = '{{ folder }}'{% endif %} as
  {{ sql }}
{%- endmacro %}

{% macro denodo__create_table_as(temporary, relation, sql) -%}
  {#-
    dbt `table` models become VDP materialized tables. This requires the
    cache engine to be configured on the server. `temporary` is ignored:
    VDP has no session-scoped CREATE TABLE AS; dbt temp relations get a
    unique suffix and are dropped by the calling materialization.
  -#}
  {%- set folder = config.get('folder') -%}
  create or replace materialized table {{ relation }}
  {%- if folder %} folder = '{{ folder }}'{% endif %} as
  {{ sql }}
{%- endmacro %}

{% macro denodo__drop_view(relation) -%}
  drop view if exists {{ relation }} cascade
{%- endmacro %}

{% macro denodo__drop_table(relation) -%}
  drop table if exists {{ relation }} cascade
{%- endmacro %}

{% macro denodo__drop_relation(relation) -%}
  {% call statement('drop_relation', auto_begin=False) -%}
    {%- if relation.is_table %}
      {{ denodo__drop_table(relation) }}
    {%- else %}
      {{ denodo__drop_view(relation) }}
    {%- endif %}
  {%- endcall %}
{% endmacro %}

{% macro denodo__truncate_relation(relation) -%}
  {# VQL has no TRUNCATE; materialized tables support DELETE. #}
  {% call statement('truncate_relation') -%}
    delete from {{ relation }}
  {%- endcall %}
{% endmacro %}

{% macro denodo__rename_relation(from_relation, to_relation) -%}
  {% do exceptions.raise_compiler_error(
      'Denodo VQL does not support renaming relations. dbt-denodo materializations '
      ~ 'use CREATE OR REPLACE and should never call rename_relation.'
  ) %}
{% endmacro %}

{% macro denodo__alter_column_type(relation, column_name, new_column_type) -%}
  {% do exceptions.raise_compiler_error('Denodo does not support altering column types via dbt.') %}
{% endmacro %}

{% macro denodo__get_empty_subquery_sql(select_sql, select_limit=none) %}
  select * from ( {{ select_sql }} ) dbt_sbq
  where 1 = 0
{% endmacro %}

{% macro denodo__get_binding_char() %}
  {{ return('%s') }}
{% endmacro %}

{# Grants: VDP privileges are managed per database/view by administrators
   through GRANT statements with a different grammar than the generic dbt
   implementation expects. Fail loudly if a model configures grants. #}
{% macro denodo__get_show_grant_sql(relation) %}
  {% do exceptions.raise_compiler_error('Model grants are not supported by dbt-denodo.') %}
{% endmacro %}

{% macro denodo__apply_grants(relation, grant_config, should_revoke=True) %}
  {% if grant_config %}
    {% do exceptions.raise_compiler_error('Model grants are not supported by dbt-denodo.') %}
  {% endif %}
{% endmacro %}

{# persist_docs: VDP element descriptions use ALTER ... DESCRIPTION with a
   grammar this adapter does not implement yet. Fail loudly if enabled. #}
{% macro denodo__alter_relation_comment(relation, relation_comment) %}
  {% do exceptions.raise_compiler_error(
      'persist_docs is not supported by dbt-denodo (set persist_docs: false).'
  ) %}
{% endmacro %}

{% macro denodo__alter_column_comment(relation, column_dict) %}
  {% do exceptions.raise_compiler_error(
      'persist_docs is not supported by dbt-denodo (set persist_docs: false).'
  ) %}
{% endmacro %}
