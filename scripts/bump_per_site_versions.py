#!/usr/bin/env python3
"""Bump SW + cache-bust on both sites so the per-site tab bar reaches the PWA."""
import re

for path, version_label in [
    ("/tmp/my-project/insight-analytics/service-worker.js", "v4.84.0-20261008-per-site-tabs"),
    ("/home/z/my-project/service-worker.js", "dashboards-v20"),
]:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if "insight-analytics" in path:
        new_src = re.sub(r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';", f"const VERSION = '{version_label}';", src, count=1)
        new_src = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.84.0", new_src)
    else:
        new_src = re.sub(r"var CACHE = 'dashboards-v\d+';", f"var CACHE = '{version_label}';", src, count=1)
        new_src = re.sub(r"\?v=\d{8}", "?v=20261009", new_src)
    if new_src != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_src)
        print(f"OK: {path} → {version_label}")

# Bump ?v= in both index.html files
for path, find, repl in [
    ("/tmp/my-project/insight-analytics/index.html", r"\?v=\d+\.\d+\.\d+", "?v=4.84.0"),
    ("/home/z/my-project/index.html", r"\?v=\d{8}", "?v=20261009"),
]:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    import re as _re
    new_src = _re.sub(find, repl, src)
    if new_src != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_src)
        print(f"OK: {path} cache-bust → {repl}")
