#!/usr/bin/env python3
"""Bump all cache-busting query strings in main site index.html to v4.75.0
so they match the SW APP_SHELL (which I also bumped to v4.75.0)."""
import re

IDX = "/tmp/my-project/insight-analytics/index.html"
with open(IDX, "r", encoding="utf-8") as f:
    src = f.read()

# Replace ALL ?v=N.N.N (or ?v=YYYYMMDD) patterns with ?v=4.75.0
new_src = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.75.0", src)
new_src = re.sub(r"\?v=\d{8}", "?v=4.75.0", new_src)

n = src.count("?v=") - new_src.count("?v=4.75.0")  # how many changed
n_changed = sum(1 for a, b in zip(src.split("\n"), new_src.split("\n")) if a != b)

with open(IDX, "w", encoding="utf-8") as f:
    f.write(new_src)

print(f"OK: bumped {n_changed} lines in {IDX}")
print("\n=== final ?v= usage ===")
for line in new_src.split("\n"):
    if "?v=" in line:
        print(line.strip()[:100])
