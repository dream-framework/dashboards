#!/usr/bin/env python3
"""Add &site=main to the main site's beacon ping."""
import re

PATH = "/tmp/my-project/insight-analytics/index.html"
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

OLD = "  // Page-load signal ping\n  new Image().src = EP + '?op=beacon&page=' + encodeURIComponent(window.location.pathname) + '&cb=' + Date.now();"
NEW = "  // Page-load signal ping (site=main so the activity panel can filter by site)\n  new Image().src = EP + '?op=beacon&page=' + encodeURIComponent(window.location.pathname) + '&site=main&cb=' + Date.now();"

if OLD in src:
    src = src.replace(OLD, NEW)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: main site beacon now sends &site=main")
else:
    print("WARN: main site beacon pattern not found")
