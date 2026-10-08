#!/usr/bin/env python3
"""
Replace 'Demos' with 'Live Demos' across ALL blog HTML files.

Updates 7 files:
  blog/index.html                          (desktop nav, footer, H1, <title>)
  blog/weather-load-forecast.html          (desktop nav, footer)
  blog/universal-time-series-prediction.html (desktop nav, footer)
  blog/universal-dashboard-builder.html    (desktop nav, footer)
  blog/personalized-power-automate.html    (desktop nav, footer)
  blog/database-archaeology.html           (desktop nav, footer)
  blog/fuzzy-address-matching.html        (desktop nav, footer)

Mobile menu links already say 'Live Demos' — these were updated in a
previous pass. This script catches the desktop nav + footer that were
missed.

Three patterns to replace per file:
  1) `>Demos</a>`                  → `>Live Demos</a>`                  (nav-link + footer anchor text)
  2) `title="Demos — see it live…"` → `title="Live Demos — see it live…"` (title attribute)

Plus special cases on blog/index.html:
  3) `<h1>Demos <span…`            → `<h1>Live Demos <span…`
  4) `<title>Demos — Production…`  → `<title>Live Demos — Production…`
"""
import os
import glob

BLOG_DIR = "/tmp/my-project/insight-analytics/blog"
HTML_FILES = sorted(glob.glob(os.path.join(BLOG_DIR, "*.html")))

# Patterns applied to every blog HTML file (replace_all = True)
GLOBAL_PATTERNS = [
    # 1) Anchor text: >Demos</a>  →  >Live Demos</a>
    (">Demos</a>", ">Live Demos</a>"),
    # 2) Title attribute: title="Demos — see it live... → title="Live Demos — see it live...
    (
        'title="Demos — see it live. Production-ready pipelines."',
        'title="Live Demos — see it live. Production-ready pipelines."',
    ),
]

# Special-case patterns for blog/index.html only
SPECIAL_PATTERNS = {
    "/tmp/my-project/insight-analytics/blog/index.html": [
        # H1 on the blog landing page
        (
            "<h1>Demos <span class=\"grad\">— Production-Ready Pipelines</span></h1>",
            "<h1>Live Demos <span class=\"grad\">— Production-Ready Pipelines</span></h1>",
        ),
        # <title> tag in <head>
        (
            "<title>Demos — Production-Ready Pipelines | Insight Analytics</title>",
            "<title>Live Demos — Production-Ready Pipelines | Insight Analytics</title>",
        ),
    ],
}

changed_files = []
for path in HTML_FILES:
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    orig = src

    # Apply global patterns
    n_global = 0
    for old, new in GLOBAL_PATTERNS:
        n_global += src.count(old)
        src = src.replace(old, new)

    # Apply special patterns (blog/index.html only)
    n_special = 0
    if path in SPECIAL_PATTERNS:
        for old, new in SPECIAL_PATTERNS[path]:
            n_special += src.count(old)
            src = src.replace(old, new)

    if src != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        changed_files.append(f"  {os.path.basename(path)}: {n_global} global + {n_special} special")
    else:
        changed_files.append(f"  {os.path.basename(path)}: NO CHANGES")

print("=== CHANGED ===")
print("\n".join(changed_files))
