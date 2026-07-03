{#
  View materialization for Denodo.

  VQL has no RENAME, so the default create-swap-drop flow is replaced by
  CREATE OR REPLACE VIEW. If the existing relation is a materialized table,
  it is dropped first (CREATE OR REPLACE VIEW cannot replace a table).
#}

{% materialization view, adapter='denodo' %}

  {%- set target_relation = this.incorporate(type='view') -%}
  {%- set existing_relation = load_cached_relation(this) -%}

  {{ run_hooks(pre_hooks) }}

  {%- if existing_relation is not none and existing_relation.is_table -%}
    {{ adapter.drop_relation(existing_relation) }}
  {%- endif -%}

  {% call statement('main') -%}
    {{ get_create_view_as_sql(target_relation, sql) }}
  {%- endcall %}

  {{ run_hooks(post_hooks) }}

  {% do persist_docs(target_relation, model) %}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
