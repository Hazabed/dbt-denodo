{#
  Snapshots require MERGE/UPDATE semantics and a rename-based bootstrap
  that Denodo VQL does not provide. Fail with a clear message instead of
  producing invalid VQL.
#}

{% materialization snapshot, adapter='denodo' %}
  {% do exceptions.raise_compiler_error(
      'Snapshots are not supported by dbt-denodo: Denodo VQL has no MERGE and '
      ~ 'no relation RENAME. Consider building snapshots in an underlying '
      ~ 'writable source instead.'
  ) %}
{% endmaterialization %}
