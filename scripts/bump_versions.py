#!/usr/bin/env python3
"""
Bump cache-busting query strings and SW versions on both sites so the
reworded AI chat messages get served fresh (PWA staleness was a previous
pain point — without this, users keep seeing the old "AI is offline"
messages from the cached JS).

Files patched:
  /tmp/my-project/insight-analytics/service-worker.js   (VERSION bump)
  /tmp/my-project/insight-analytics/index.html            (?v=4.50.1 → ?v=4.50.2)
  /home/z/my-project/service-worker.js                    (dashboards-v18 → v19)
  /home/z/my-project/index.html                            (?v=20261007 → ?v=20261008)
"""
import re
import os

# ─── Main site: SW version bump ─────────────────────────────────────────
SW_MAIN = "/tmp/my-project/insight-analytics/service-worker.js"
if os.path.exists(SW_MAIN):
    with open(SW_MAIN, "r", encoding="utf-8") as f:
        src = f.read()
    new_src = re.sub(
        r"const VERSION = 'v4\.50\.1-[^']+';",
        "const VERSION = 'v4.50.2-20261008-ai-msg-warm-recovery';",
        src,
        count=1,
    )
    if new_src != src:
        with open(SW_MAIN, "w", encoding="utf-8") as f:
            f.write(new_src)
        print(f"OK: bumped VERSION in {SW_MAIN}")
    else:
        print(f"WARN: VERSION pattern not matched in {SW_MAIN}")
else:
    print(f"MISSING: {SW_MAIN}")

# ─── Main site: index.html cache-busting ────────────────────────────────
IDX_MAIN = "/tmp/my-project/insight-analytics/index.html"
if os.path.exists(IDX_MAIN):
    with open(IDX_MAIN, "r", encoding="utf-8") as f:
        src = f.read()
    # Bump ?v=4.50.1 → ?v=4.50.2 across all script + link tags
    new_src = src.replace("?v=4.50.1", "?v=4.50.2")
    if new_src != src:
        with open(IDX_MAIN, "w", encoding="utf-8") as f:
            f.write(new_src)
        n = src.count("?v=4.50.1")
        print(f"OK: bumped {n} ?v=4.50.1 → ?v=4.50.2 in {IDX_MAIN}")
    else:
        print(f"WARN: no ?v=4.50.1 found in {IDX_MAIN}")
else:
    print(f"MISSING: {IDX_MAIN}")

# ─── Dashboards site: SW version bump ────────────────────────────────────
SW_DASH = "/home/z/my-project/service-worker.js"
if os.path.exists(SW_DASH):
    with open(SW_DASH, "r", encoding="utf-8") as f:
        src = f.read()
    new_src = re.sub(
        r"var CACHE = 'dashboards-v\d+';",
        "var CACHE = 'dashboards-v19';",
        src,
        count=1,
    )
    if new_src != src:
        with open(SW_DASH, "w", encoding="utf-8") as f:
            f.write(new_src)
        print(f"OK: bumped CACHE → dashboards-v19 in {SW_DASH}")
    else:
        print(f"WARN: CACHE pattern not matched in {SW_DASH}")
else:
    print(f"MISSING: {SW_DASH}")

# ─── Dashboards site: index.html cache-busting ──────────────────────────
IDX_DASH = "/home/z/my-project/index.html"
if os.path.exists(IDX_DASH):
    with open(IDX_DASH, "r", encoding="utf-8") as f:
        src = f.read()
    # Bump ?v=20261007 → ?v=20261008
    new_src = src.replace("?v=20261007", "?v=20261008")
    if new_src != src:
        with open(IDX_DASH, "w", encoding="utf-8") as f:
            f.write(new_src)
        n = src.count("?v=20261007")
        print(f"OK: bumped {n} ?v=20261007 → ?v=20261008 in {IDX_DASH}")
    else:
        print(f"WARN: no ?v=20261007 found in {IDX_DASH}")
else:
    print(f"MISSING: {IDX_DASH}")
