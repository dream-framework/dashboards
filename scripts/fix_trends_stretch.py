#!/usr/bin/env python3
"""
Fix: 'Index & Crypto Trends do not stretch horizontally into the available
card viewport.'

Two changes:

1) ECharts grid margins were left:60, right:70 — reserving 130px for axis
   labels in a card that's only ~440px wide, leaving the plot at ~65% of
   the card width. Switched to containLabel:true with tight 8/8px margins
   so ECharts auto-computes the label gutter and the plot fills the rest.

2) CSS: make the trends card span the full row width (grid-column: 1/-1)
   so it gets ~2.3x more raw horizontal real estate than the previous
   1.1fr narrow column. FX heatmap moves below it on its own full-width
   row (still looks fine — FX is a square 8x8 matrix).

3) Bump SW version + cache-bust string so the PWA picks up the change
   immediately.

Files patched:
  /tmp/my-project/insight-analytics/js/blog-markets-dashboard.js
  /tmp/my-project/insight-analytics/service-worker.js
  /tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html
"""
import re

PATH = "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js"

with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ─── (1) Reduce ECharts grid margins for the trends chart ─────────────────
OLD_GRID = "      grid: { left: 60, right: 70, top: 30, bottom: 30 },"
NEW_GRID = "      // containLabel:true → ECharts auto-computes the axis-label gutter.\n" \
          "      // Small explicit margins (8/8/24/20) let the plot fill the card\n" \
          "      // width — previous 60/70 reserved 130px (~30% of the card) for\n" \
          "      // labels, making the line chart look narrow with empty gutters.\n" \
          "      grid: { left: 8, right: 8, top: 24, bottom: 20, containLabel: true },"

if OLD_GRID in src:
    src = src.replace(OLD_GRID, NEW_GRID)
    print("OK: trends chart grid → containLabel:true with 8/8 margins")
else:
    print("WARN: trends grid pattern not found")

# ─── (2) CSS: make trends card span full row1 width ────────────────────────
# Add a rule for .bmd-trends-card to span the full row.
OLD_CSS = "      .bmd-chart-card.bmd-wide { grid-column: 1 / -1; }\n      .bmd-chart-card.bmd-wide-2 { grid-column: span 2; }"
NEW_CSS = "      .bmd-chart-card.bmd-wide { grid-column: 1 / -1; }\n" \
          "      .bmd-chart-card.bmd-wide-2 { grid-column: span 2; }\n" \
          "      /* Trends chart spans the full row1 width — the line chart needs\n" \
          "         horizontal real estate to show 30 days × 4 series. Previous\n" \
          "         1.1fr narrow column made the chart cramped; FX (square 8x8\n" \
          "         matrix) moves to its own full-width row below. */\n" \
          "      .bmd-grid-row1 .bmd-trends-card { grid-column: 1 / -1; }\n" \
          "      .bmd-grid-row1 .bmd-fx-card { grid-column: 1 / -1; }"

if OLD_CSS in src:
    src = src.replace(OLD_CSS, NEW_CSS)
    print("OK: trends card CSS → grid-column: 1/-1 (full row width)")
else:
    print("WARN: CSS pattern not found")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

# ─── (3) Bump SW version + cache-bust ─────────────────────────────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw_src = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.77.0-20261008-trends-stretch-full-card';",
    sw_src,
    count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.77.0", sw_new)
if sw_new != sw_src:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.77.0, all ?v= → 4.77.0")

IDX = "/tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html"
with open(IDX, "r", encoding="utf-8") as f:
    idx_src = f.read()
idx_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.77.0", idx_src)
if idx_new != idx_src:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(idx_new)
    print("OK: blog/universal-dashboard-builder.html ?v= → 4.77.0")
