#!/usr/bin/env python3
"""Bump cache-bust version for blog-markets-dashboard.js + SW version
so the PWA picks up the trend-chart fix immediately."""
import re

# ─── service-worker.js: bump VERSION + APP_SHELL ?v= strings ──────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    src = f.read()
new_src = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.76.0-20261008-trend-chart-live-history';",
    src,
    count=1,
)
new_src = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.76.0", new_src)
if new_src != src:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"OK: SW VERSION → v4.76.0-20261008-trend-chart-live-history, all ?v= → 4.76.0")

# ─── blog/universal-dashboard-builder.html: bump script src cache-bust ──
IDX = "/tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html"
with open(IDX, "r", encoding="utf-8") as f:
    src = f.read()
new_src = src.replace("?v=4.48.0", "?v=4.76.0")
new_src = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.76.0", new_src)
if new_src != src:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"OK: blog/universal-dashboard-builder.html ?v= → 4.76.0")
