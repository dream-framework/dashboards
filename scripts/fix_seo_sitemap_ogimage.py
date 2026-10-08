#!/usr/bin/env python3
"""
Two SEO fixes the user implicitly asked about:

1) sitemap.xml is missing 3 of the 7 blog posts (the ones added during
   the recent origin/main merge — personalized-power-automate,
   fuzzy-address-matching, weather-load-forecast). Add them with
   correct lastmod dates. Also refresh the existing entries' lastmod
   to today (2026-10-08) since we've been actively editing these posts.

2) No blog post has og:image / twitter:image tags — social shares
   (Twitter/X, Facebook, LinkedIn, Slack) show no preview image.
   Add og:image + og:image:width/height/alt + twitter:image +
   twitter:image:alt to every blog post. Use:
     - dashboards-preview/screenshots/markets.png for universal-dashboard-builder
     - icons/icon-512.png as fallback for the rest (no per-post preview
       art exists yet)

Files patched:
  /tmp/my-project/insight-analytics/sitemap.xml
  /tmp/my-project/insight-analytics/blog/*.html (6 blog posts + index)
"""
import os
import re

TODAY = "2026-10-08"

# ─── (1) Rewrite sitemap.xml with all 7 blog posts ────────────────────────
SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://insight-analytics.ca/</loc>
    <lastmod>TODAY</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/</loc>
    <lastmod>TODAY</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/universal-dashboard-builder</loc>
    <lastmod>2026-10-04</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/personalized-power-automate</loc>
    <lastmod>2026-10-07</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/fuzzy-address-matching</loc>
    <lastmod>2026-10-07</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/weather-load-forecast</loc>
    <lastmod>2026-10-07</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/database-archaeology</loc>
    <lastmod>2026-10-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://insight-analytics.ca/blog/universal-time-series-prediction</loc>
    <lastmod>2026-10-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
</urlset>
""".replace("TODAY", TODAY)

SM_PATH = "/tmp/my-project/insight-analytics/sitemap.xml"
with open(SM_PATH, "w", encoding="utf-8") as f:
    f.write(SITEMAP)
print(f"OK: sitemap.xml — 8 URLs (homepage + blog index + 6 posts, was 5)")

# ─── (2) Add og:image + twitter:image to every blog post ─────────────────
# Each blog post has a Twitter Card block already (twitter:card /
# twitter:title / twitter:description). Insert og:image + twitter:image
# after the twitter:description line.

# Map of blog file → image to use for og:image / twitter:image
IMAGE_MAP = {
    "universal-dashboard-builder.html": (
        "https://insight-analytics.ca/dashboards-preview/screenshots/markets.png",
        "Markets & Finance dashboard — live Yahoo + Binance + Frankfurter data with AI narrative",
        "1200", "750"  # markets.png is roughly 1200×750 (16:10) — safe dims
    ),
}
# Fallback for the rest
FALLBACK = (
    "https://insight-analytics.ca/icons/icon-512.png",
    "Insight Analytics — Live truth on every desk",
    "512", "512"
)

# Blog files to patch (skip index.html — it has its own og:image already)
BLOG_DIR = "/tmp/my-project/insight-analytics/blog"
for fname in sorted(os.listdir(BLOG_DIR)):
    if not fname.endswith(".html") or fname == "index.html":
        continue
    path = os.path.join(BLOG_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Skip if already patched
    if 'property="og:image"' in src:
        print(f"SKIP (already has og:image): {fname}")
        continue

    img_url, img_alt, img_w, img_h = IMAGE_MAP.get(fname, FALLBACK)

    # Find the twitter:description line and insert og:image + twitter:image
    # blocks AFTER it.
    pattern = r'(<meta name="twitter:description" content="[^"]*" />)'
    m = re.search(pattern, src)
    if not m:
        print(f"WARN: no twitter:description line in {fname}")
        continue

    insert_after = m.group(1)
    new_block = (
        f'\n  <meta property="og:image" content="{img_url}" />\n'
        f'  <meta property="og:image:width" content="{img_w}" />\n'
        f'  <meta property="og:image:height" content="{img_h}" />\n'
        f'  <meta property="og:image:alt" content="{img_alt}" />\n'
        f'  <meta name="twitter:image" content="{img_url}" />\n'
        f'  <meta name="twitter:image:alt" content="{img_alt}" />'
    )
    src = src.replace(insert_after, insert_after + new_block, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"OK: {fname} → og:image + twitter:image added")
