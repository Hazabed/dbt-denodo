{#
  Catalog query for `dbt docs generate`.

  Built from the GET_VIEWS() and GET_VIEW_COLUMNS() predefined stored
  procedures, invoked inside derived tables so each gets its input
  parameter. GET_VIEW_COLUMNS does not expose a documented ordinal
  position, so column_index is emitted as 0 (dbt falls back to a stable
  order; docs remain usable).
#}

{% macro denodo__get_catalog(information_schema, schemas) -%}
  {% set query %}
    {%- for schema in schemas %}
    select
        '{{ information_schema.database }}' as table_database,
        v.database_name as table_schema,
        v.name as table_name,
        case when v.view_type in (1, 2) then 'VIEW' else 'BASE TABLE' end as table_type,
        cast(null as text) as table_comment,
        c.column_name as column_name,
        0 as column_index,
        lower(c.column_vdp_type) as column_type,
        cast(null as text) as column_comment,
        cast(null as text) as table_owner
    from (
        select name, database_name, view_type
        from get_views()
        where input_database_name = '{{ schema }}'
    ) v
    join (
        select view_name, column_name, column_vdp_type
        from get_view_columns()
        where input_database_name = '{{ schema }}'
    ) c
      on v.name = c.view_name
    {%- if not loop.last %}
    union all
    {%- endif %}
    {%- endfor %}
  {% endset %}

  {{ return(run_query(query)) }}
{%- endmacro %}
