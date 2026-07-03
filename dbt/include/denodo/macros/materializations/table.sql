{#
  Table materialization for Denodo.

  dbt `table` models become VDP materialized tables, whose data lives in
  the cache data source and is fully managed by Virtual DataPort. Requires
  the cache engine to be enabled on the server.

  VQL has no RENAME, so the default create-swap-drop flow is replaced by
  CREATE OR REPLACE MATERIALIZED TABLE. If the existing relation is a view,
  it is dropped first.
#}

{% materialization table, adapter='denodo' %}

  {%- set target_relation = this.incorporate(type='table') -%}
  {%- set existing_relation = load_cached_relation(this) -%}

  {{ run_hooks(pre_hooks) }}

  {%- if existing_relation is not none and existing_relation.is_view -%}
    {{ adapter.drop_relation(existing_relation) }}
  {%- endif -%}

  {% call statement('main') -%}
    {{ get_create_table_as_sql(False, target_relation, sql) }}
  {%- endcall %}

  {{ run_hooks(post_hooks) }}

  {% do persist_docs(target_relation, model) %}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
