#!/usr/bin/env python3
"""Normalize ALL cache-bust query strings in main site SW APP_SHELL to
v4.75.0 so they match index.html (avoids SW precache misses)."""
import re

SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    src = f.read()

new_src = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.75.0", src)
new_src = re.sub(r"\?v=\d{8}", "?v=4.75.0", new_src)

if new_src != src:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"OK: normalized SW APP_SHELL to v4.75.0")
else:
    print("no changes")

# Print final APP_SHELL block
import re
m = re.search(r"const APP_SHELL = \[(.*?)\];", new_src, re.DOTALL)
if m:
    print(m.group(0))
