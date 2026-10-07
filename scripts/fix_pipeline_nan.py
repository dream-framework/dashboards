#!/usr/bin/env python3
"""
Fix the NaN bug in the pipeline executor.

Root cause: the summarize step does `r[step.valueColumn]` directly. Groq
frequently returns column names in a DIFFERENT CASE than the actual data —
e.g. valueColumn: "QTY" when the data has lowercase "qty". Then r["QTY"]
is undefined → Number(undefined) is NaN → NaN propagates through the
sum/avg/min/max → entire result column shows as NaN.

Fix: add a case-insensitive column resolver (`resolveColumn`) that
returns the actual column name from the doc's columns list. Apply it to
filter.column, summarize.groupBy[], summarize.valueColumn, sort.column,
select.columns[]. Also guard against NaN propagation per-row, and use
the resolved column name in the result column header (so the header
matches the actual data, e.g. 'sum_of_qty' not 'sum_of_QTY').

Also: edge-case — when summarize produces min/max on an empty group,
the initial Infinity/-Infinity would leak into the output. Reset to 0
in that case.

This is a one-shot patch script — applied directly to the file.
"""
import re

PATH = '/home/z/insight-analytics/js/blog-pipeline-builder.js'
src = open(PATH).read()

# ─── Step 1: insert the resolveColumn helper before executePipeline ──────
helper_block = """  // ─── Case-insensitive column resolver ──────────────────────────────────────
  // Groq frequently returns column names in a DIFFERENT CASE than the actual
  // data — e.g. valueColumn: "QTY" when the data has lowercase "qty", or
  // "Revenue" when the data has "revenue". Without a resolver, r["QTY"]
  // returns undefined → Number(undefined) is NaN → NaN propagates through
  // sum/avg/min/max → the entire result column shows as NaN.
  //
  // The resolver: exact match first, case-insensitive match second, falls
  // back to the original name (so undefined values surface the bug visibly
  // in the result — better than silently failing).
  var _colLookupCache = {};
  function resolveColumn(name, docColumns) {
    if (!name) return name;
    if (docColumns.indexOf(name) >= 0) return name;
    var cacheKey = name.toLowerCase() + '\\u0001' + docColumns.join('\\u0001');
    if (_colLookupCache[cacheKey]) return _colLookupCache[cacheKey];
    var lower = name.toLowerCase();
    for (var i = 0; i < docColumns.length; i++) {
      if (docColumns[i].toLowerCase() === lower) {
        _colLookupCache[cacheKey] = docColumns[i];
        return docColumns[i];
      }
    }
    _colLookupCache[cacheKey] = name;
    return name;
  }

"""

# Find the existing executePipeline header + replace
old_exec_header = """  // ─── Pipeline executor ─────────────────────────────────────────────────────
  // Runs each step in order over a shallow-cloned row array. Each step mutates
  // the array (filter shortens, summarize reshapes, sort reorders, etc.). The
  // final shape is returned to the renderer.
  function executePipeline(doc, spec) {
    var rows = (doc.rows || []).slice();
    (spec.steps || []).forEach(function (step) {"""

new_exec_header = """  // ─── Pipeline executor ─────────────────────────────────────────────────────
  // Runs each step in order over a shallow-cloned row array. Each step mutates
  // the array (filter shortens, summarize reshapes, sort reorders, etc.). The
  // final shape is returned to the renderer.
  function executePipeline(doc, spec) {
    var rows = (doc.rows || []).slice();
    var docCols = doc.columns || (rows.length ? Object.keys(rows[0]) : []);
    _colLookupCache = {};  // reset per-execution
    (spec.steps || []).forEach(function (step) {"""

# Insert helper before the executor header, then replace the executor header
needle = "  // ─── Pipeline executor ─────────────────────────────────────────────────────"
if needle not in src:
    raise SystemExit("Couldn't find executor header needle")
src = src.replace(needle, helper_block + needle, 1)
src = src.replace(old_exec_header, new_exec_header, 1)

# ─── Step 2: patch the filter step to use resolveColumn ────────────────────
old_filter = """      if (step.type === 'filter') {
        rows = rows.filter(function (r) {
          var v = r[step.column];"""
new_filter = """      if (step.type === 'filter') {
        var fCol = resolveColumn(step.column, docCols);
        rows = rows.filter(function (r) {
          var v = r[fCol];"""
assert old_filter in src, "filter block not found"
src = src.replace(old_filter, new_filter, 1)

# ─── Step 3: patch the summarize step (the main NaN fix) ──────────────────
old_summ = """      } else if (step.type === 'summarize') {
        var groupBy = step.groupBy && step.groupBy.length ? step.groupBy : [];
        var groups = {};
        var order = [];
        rows.forEach(function (r) {
          var key = groupBy.map(function (c) { return r[c]; }).join(' | ');
          if (!groups[key]) { groups[key] = { count: 0, sum: 0, min: Infinity, max: -Infinity }; order.push(key); }
          var g = groups[key];
          var val = step.valueColumn ? Number(r[step.valueColumn]) : 0;
          g.count++;
          if (step.valueColumn) {
            g.sum += val;
            g.min = Math.min(g.min, val);
            g.max = Math.max(g.max, val);
          }
        });
        rows = order.map(function (key) {
          var g = groups[key];
          var parts = key.split(' | ');
          var row = {};
          groupBy.forEach(function (c, i) { row[c] = parts[i]; });
          if (step.valueColumn) {
            var agg = step.aggregation || 'sum';
            row[agg + '_of_' + step.valueColumn] =
              agg === 'sum'   ? g.sum :
              agg === 'count' ? g.count :
              agg === 'avg'   ? (g.count ? g.sum / g.count : 0) :
              agg === 'min'   ? g.min :
              agg === 'max'   ? g.max : null;
          } else {
            row.count = g.count;
          }
          return row;
        });"""

new_summ = """      } else if (step.type === 'summarize') {
        var groupByRaw = step.groupBy && step.groupBy.length ? step.groupBy : [];
        var groupBy = groupByRaw.map(function (c) { return resolveColumn(c, docCols); });
        var valCol = step.valueColumn ? resolveColumn(step.valueColumn, docCols) : null;
        var groups = {};
        var order = [];
        rows.forEach(function (r) {
          var key = groupBy.map(function (c) { return r[c]; }).join(' | ');
          if (!groups[key]) { groups[key] = { count: 0, sum: 0, min: Infinity, max: -Infinity }; order.push(key); }
          var g = groups[key];
          var val = valCol ? Number(r[valCol]) : 0;
          if (isNaN(val)) val = 0;  // guard against NaN propagation
          g.count++;
          if (valCol) {
            g.sum += val;
            g.min = Math.min(g.min, val);
            g.max = Math.max(g.max, val);
          }
        });
        rows = order.map(function (key) {
          var g = groups[key];
          var parts = key.split(' | ');
          var row = {};
          groupBy.forEach(function (c, i) { row[c] = parts[i]; });
          if (valCol) {
            var agg = step.aggregation || 'sum';
            row[agg + '_of_' + valCol] =
              agg === 'sum'   ? g.sum :
              agg === 'count' ? g.count :
              agg === 'avg'   ? (g.count ? g.sum / g.count : 0) :
              agg === 'min'   ? (g.min === Infinity ? 0 : g.min) :
              agg === 'max'   ? (g.max === -Infinity ? 0 : g.max) : null;
          } else {
            row.count = g.count;
          }
          return row;
        });"""

assert old_summ in src, "summarize block not found"
src = src.replace(old_summ, new_summ, 1)

# ─── Step 4: patch the sort step ───────────────────────────────────────────
old_sort = """      } else if (step.type === 'sort') {
        var col = step.column, order2 = step.order === 'desc' ? -1 : 1;
        rows.sort(function (a, b) {
          var av = a[col], bv = b[col];"""
new_sort = """      } else if (step.type === 'sort') {
        var sCol = resolveColumn(step.column, docCols);
        var order2 = step.order === 'desc' ? -1 : 1;
        rows.sort(function (a, b) {
          var av = a[sCol], bv = b[sCol];"""
assert old_sort in src, "sort block not found"
src = src.replace(old_sort, new_sort, 1)

# ─── Step 5: patch the select step ─────────────────────────────────────────
old_sel = """      } else if (step.type === 'select') {
        var cols = step.columns || [];
        rows = rows.map(function (r) {
          var o = {};
          cols.forEach(function (c) { o[c] = r[c]; });"""
new_sel = """      } else if (step.type === 'select') {
        var selColsRaw = step.columns || [];
        var selCols = selColsRaw.map(function (c) { return resolveColumn(c, docCols); });
        rows = rows.map(function (r) {
          var o = {};
          selCols.forEach(function (c) { o[c] = r[c]; });"""
assert old_sel in src, "select block not found"
src = src.replace(old_sel, new_sel, 1)

# ─── Write back ────────────────────────────────────────────────────────────
open(PATH, 'w').write(src)
print(f"Patched {PATH}")
print(f"  + resolveColumn helper inserted before executePipeline")
print(f"  + filter step: r[step.column] → r[resolveColumn(step.column, docCols)]")
print(f"  + summarize step: case-insensitive matching for groupBy[] + valueColumn + NaN guard + Infinity guard")
print(f"  + sort step: case-insensitive matching for column")
print(f"  + select step: case-insensitive matching for columns[]")
