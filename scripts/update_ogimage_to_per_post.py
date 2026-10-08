#!/usr/bin/env python3
"""
Update each blog post's og:image + twitter:image to point to its dedicated
per-post OG image (was: icon-512.png fallback, or markets.png screenshot
for universal-dashboard-builder).

New OG images live at /blog/og-images/<post-slug>.png — generated with
the image-generation skill (1344×768, branded cyan-to-blue gradient,
topic-specific visuals, no text since og:title carries the title).

Also update og:image:width / og:image:height to 1344 / 768.
"""
import os
import re

BLOG_DIR = "/tmp/my-project/insight-analytics/blog"

# Map of filename → (slug, alt_text)
POSTS = [
    ("database-archaeology.html",         "Database Archaeology — Turning Legacy Systems into Self-Explaining Maps"),
    ("fuzzy-address-matching.html",       "Fuzzy Address Matching — Turning Siloed Systems into One Map"),
    ("personalized-power-automate.html",  "Personalized Power Automate — AI Builds the Pipeline, You Approve It"),
    ("universal-dashboard-builder.html",  "The Universal Dashboard Builder — From Data to Dazzling Executive Dashboards"),
    ("universal-time-series-prediction.html", "Universal Time Series Prediction — From Earthquakes to Bitcoin"),
    ("weather-load-forecast.html",        "Weather-Driven Electricity Load Forecasting & Operational Planning"),
]

for fname, alt in POSTS:
    path = os.path.join(BLOG_DIR, fname)
    slug = fname.replace(".html", "")
    img_url = f"https://insight-analytics.ca/blog/og-images/{slug}.png"
    img_path_local = f"/blog/og-images/{slug}.png"

    if not os.path.exists(os.path.join(BLOG_DIR, "og-images", f"{slug}.png")):
        print(f"WARN: local image missing for {fname}")
        continue

    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Pattern: find the existing og:image block (og:image + og:image:width
    # + og:image:height + og:image:alt + twitter:image + twitter:image:alt)
    # and replace the URLs + dimensions.
    # The block was inserted by the previous fix_seo_sitemap_ogimage.py
    # script, so we know the exact shape.

    # Use a regex that matches the whole inserted block (handles both
    # icon-512.png fallback and markets.png for universal-dashboard-builder)
    pattern = re.compile(
        r'<meta property="og:image" content="[^"]*" />\s*\n'
        r'\s*<meta property="og:image:width" content="[^"]*" />\s*\n'
        r'\s*<meta property="og:image:height" content="[^"]*" />\s*\n'
        r'\s*<meta property="og:image:alt" content="[^"]*" />\s*\n'
        r'\s*<meta name="twitter:image" content="[^"]*" />\s*\n'
        r'\s*<meta name="twitter:image:alt" content="[^"]*" />'
    )

    replacement = (
        f'<meta property="og:image" content="{img_url}" />\n'
        f'  <meta property="og:image:width" content="1344" />\n'
        f'  <meta property="og:image:height" content="768" />\n'
        f'  <meta property="og:image:alt" content="{alt}" />\n'
        f'  <meta name="twitter:image" content="{img_url}" />\n'
        f'  <meta name="twitter:image:alt" content="{alt}" />'
    )

    new_src, n = pattern.subn(replacement, src)
    if n == 0:
        print(f"WARN: OG image block pattern not matched in {fname}")
        continue

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"OK: {fname} → og:image = {img_path_local}")
