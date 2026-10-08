#!/usr/bin/env python3
"""Resolve merge conflicts in the main site files after pulling origin/main.

Conflict resolution strategy:
- service-worker.js: take MY new VERSION string (warm-recovery reword), but
  bump it ABOVE the remote's v4.74.1 to v4.75.0 so it's the newest.
- index.html line ~110 (CSS cache-bust): take the highest version string
  between local and remote (consolidate).
- index.html line ~1004 (JS cache-bust block): same — pick the higher
  version, ensure all <script src="./js/..."> tags share the same ?v=.
"""
import re

# ─── service-worker.js ────────────────────────────────────────────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    src = f.read()
# Replace the conflict block with a single merged line
src = re.sub(
    r"<<<<<<< HEAD\nconst VERSION = '[^']+';\n=======\nconst VERSION = '[^']+';\n>>>>>>> origin/main\n",
    "const VERSION = 'v4.75.0-20261008-ai-msg-warm-recovery';\n",
    src,
    count=1,
)
# Also bump the APP_SHELL cache-bust strings so they match index.html ?v=4.75.0
src = src.replace("?v=4.74.0", "?v=4.75.0")
src = src.replace("?v=4.72.0", "?v=4.75.0")
with open(SW, "w", encoding="utf-8") as f:
    f.write(src)
print(f"OK: resolved service-worker.js")

# ─── index.html ───────────────────────────────────────────────────────────
IDX = "/tmp/my-project/insight-analytics/index.html"
with open(IDX, "r", encoding="utf-8") as f:
    src = f.read()

# Show the conflict blocks for debugging
for m in re.finditer(r"<<<<<<< HEAD.*?>>>>>>> origin/main", src, re.DOTALL):
    print("--- conflict block ---")
    print(m.group(0)[:500])
    print("--- end ---")

# Resolution: replace each conflict block by picking the line that uses
# the highest version number. For ?v=4.50.x vs ?v=4.74.x, pick 4.74.x.
# For ?v=4.75.x (mine), keep mine.
# Simplest approach: pick whichever line has the LARGER numeric version.

def pick_higher_version(block):
    """Given a conflict block, return the resolved line."""
    # Extract HEAD section and origin/main section
    m = re.match(
        r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> origin/main",
        block,
        re.DOTALL,
    )
    if not m:
        return block
    head_lines = m.group(1)
    origin_lines = m.group(2)
    # Find ?v=N.N.N in each
    head_ver = re.search(r"\?v=(\d+\.\d+\.\d+)", head_lines)
    origin_ver = re.search(r"\?v=(\d+\.\d+\.\d+)", origin_lines)
    if head_ver and origin_ver:
        h = tuple(int(x) for x in head_ver.group(1).split("."))
        o = tuple(int(x) for x in origin_ver.group(1).split("."))
        if h >= o:
            return head_lines
        else:
            return origin_lines
    # If only one side has a version, prefer the one that does
    if head_ver:
        return head_lines
    if origin_ver:
        return origin_lines
    # Fallback — prefer HEAD (my new changes)
    return head_lines

# Replace each conflict block
def replace_block(m):
    return pick_higher_version(m.group(0))

src = re.sub(r"<<<<<<< HEAD.*?>>>>>>> origin/main", replace_block, src, flags=re.DOTALL)

with open(IDX, "w", encoding="utf-8") as f:
    f.write(src)
print(f"OK: resolved index.html")
# Verify no more conflict markers
remaining = re.findall(r"<<<<<<<|=======|>>>>>>>", src)
print(f"Remaining conflict markers: {len(remaining)}")
