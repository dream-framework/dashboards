#!/usr/bin/env python3
"""
Rename 'Blog' → 'Demos' across the site nav + reframe the blog index hero
to communicate that these are PRODUCTION-READY pipelines, not toy demos.

User brief:
- Label: 'Demos — See it Live'
- Critical framing: these aren't just demos, they're ready production pipelines

Implementation:
1. Navbar + mobile menu + footer links: 'Blog' → 'Demos' (14 sites)
2. Navbar link gets a title='Demos — see it live. Production-ready pipelines.'
   tooltip so the 'see it live' framing surfaces on hover.
3. Blog index hero:
   - Eyebrow: 'Blog' → 'Production-ready · See it live'
   - H1: 'Articles & Insights' → 'Demos — Production-Ready Pipelines'
   - Subtitle: replace 'Practical perspectives...' with copy that emphasizes
     'same code, same data flow, same KPIs as production deployments'
4. Blog index page <title>: add 'Demos — Production-Ready Pipelines'
5. Add a small 'Production-ready' badge near the H1 for visual emphasis
"""
import os
import re

FILES = [
    '/home/z/insight-analytics/index.html',
    '/home/z/insight-analytics/blog/index.html',
    '/home/z/insight-analytics/blog/personalized-power-automate.html',
    '/home/z/insight-analytics/blog/universal-dashboard-builder.html',
    '/home/z/insight-analytics/blog/database-archaeology.html',
    '/home/z/insight-analytics/blog/universal-time-series-prediction.html',
]

# Patterns to replace:
# 1. Navbar link: <a href="/blog/" class="nav-link">Blog</a>
#    → <a href="/blog/" class="nav-link" title="Demos — see it live. Production-ready pipelines.">Demos</a>
NAVBAR_LINK = '<a href="/blog/" class="nav-link">Blog</a>'
NAVBAR_LINK_NEW = '<a href="/blog/" class="nav-link" title="Demos \u2014 see it live. Production-ready pipelines.">Demos</a>'

# 2. Mobile menu link: <a href="/blog/" class="nav-link" role="menuitem">Blog</a>
#    → same + title attr
MOBILE_LINK = '<a href="/blog/" class="nav-link" role="menuitem">Blog</a>'
MOBILE_LINK_NEW = '<a href="/blog/" class="nav-link" role="menuitem" title="Demos \u2014 see it live. Production-ready pipelines.">Demos</a>'

# 3. Footer link: <a href="/blog/">Blog</a>
#    → <a href="/blog/" title="Demos — see it live. Production-ready pipelines.">Demos</a>
FOOTER_LINK = '<a href="/blog/">Blog</a>'
FOOTER_LINK_NEW = '<a href="/blog/" title="Demos \u2014 see it live. Production-ready pipelines.">Demos</a>'

# Apply across all files
total_replacements = 0
for fp in FILES:
    s = open(fp).read()
    orig = s
    cnt_navbar = s.count(NAVBAR_LINK)
    cnt_mobile = s.count(MOBILE_LINK)
    cnt_footer = s.count(FOOTER_LINK)
    s = s.replace(NAVBAR_LINK, NAVBAR_LINK_NEW)
    s = s.replace(MOBILE_LINK, MOBILE_LINK_NEW)
    s = s.replace(FOOTER_LINK, FOOTER_LINK_NEW)
    if s != orig:
        open(fp, 'w').write(s)
        total = cnt_navbar + cnt_mobile + cnt_footer
        print(f"  {fp.split('/')[-2]}/{fp.split('/')[-1]}: {cnt_navbar} navbar + {cnt_mobile} mobile + {cnt_footer} footer = {total} replacements")
        total_replacements += total
    else:
        print(f"  {fp}: no changes")
print(f"\nTotal: {total_replacements} 'Blog' → 'Demos' label replacements across {len(FILES)} files")

# ─── Blog index hero overhaul ──────────────────────────────────────────────
BLOG_IDX = '/home/z/insight-analytics/blog/index.html'
s = open(BLOG_IDX).read()

# Hero eyebrow + H1 + subtitle
OLD_HERO = """  <section class="blog-index-head">
    <div class="container">
      <span class="eyebrow"><span class="dot"></span> Blog</span>
      <h1>Articles & Insights</h1>
      <p>Practical perspectives on data architecture, AI-assisted analytics, and building systems that explain themselves.</p>
    </div>
  </section>"""

NEW_HERO = """  <section class="blog-index-head">
    <div class="container">
      <span class="eyebrow"><span class="dot"></span> Production-ready &middot; See it live</span>
      <h1>Demos <span class="grad">— Production-Ready Pipelines</span></h1>
      <p>These aren't toy demos. Each one runs the same code, the same data flow, the same KPI definitions, and the same AI brief as our production deployments &mdash; 50+ across utilities, retail, and IT operations. Click through, interact with the live data, and judge for yourself.</p>
      <div class="blog-prod-badges">
        <span class="blog-prod-badge"><i class="fas fa-circle-check"></i> Same code as production</span>
        <span class="blog-prod-badge"><i class="fas fa-circle-check"></i> Live data, not screenshots</span>
        <span class="blog-prod-badge"><i class="fas fa-circle-check"></i> Built from 50+ deployments</span>
      </div>
    </div>
  </section>"""

assert OLD_HERO in s, "blog index hero block not found"
s = s.replace(OLD_HERO, NEW_HERO, 1)

# Update page <title>
OLD_TITLE_TAG = "<title>Blog \u2014 Insight Analytics</title>"
NEW_TITLE_TAG = "<title>Demos \u2014 Production-Ready Pipelines | Insight Analytics</title>"
assert OLD_TITLE_TAG in s, "blog index <title> not found"
s = s.replace(OLD_TITLE_TAG, NEW_TITLE_TAG, 1)

# Update meta description
OLD_META_DESC = '<meta name="description" content="Practical perspectives on data architecture, AI-assisted analytics, and building systems that explain themselves." />'
NEW_META_DESC = '<meta name="description" content="Production-ready demos — same code, same data flow, same KPIs as our 50+ production deployments. Click, interact, judge for yourself. Live dashboards, AI pipeline constructor, database archaeology, time series prediction." />'
assert OLD_META_DESC in s, "blog index meta description not found"
s = s.replace(OLD_META_DESC, NEW_META_DESC, 1)

# Add CSS for the new badges — find the existing blog-index-head CSS block and append
# after it
OLD_HEAD_CSS = ".blog-index-head p { font-size: 1.1rem; color: var(--text-muted); max-width: 720px; margin: 0 auto; line-height: 1.7; }"
NEW_HEAD_CSS = OLD_HEAD_CSS + """
    .blog-prod-badges { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin-top: 24px; }
    .blog-prod-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px; font-size: 0.82rem; font-weight: 600; color: var(--text-soft); background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.06)); border: 1px solid var(--border); }
    .blog-prod-badge i { color: #10b981; font-size: 0.78rem; }
    [data-theme="dark"] .blog-prod-badge { color: var(--text-muted); background: linear-gradient(135deg, rgba(99,102,241,0.14), rgba(6,182,212,0.10)); }"""
assert OLD_HEAD_CSS in s, "blog-index-head CSS not found"
s = s.replace(OLD_HEAD_CSS, NEW_HEAD_CSS, 1)

open(BLOG_IDX, 'w').write(s)
print(f"\n  Blog index hero reframed: 'Production-ready · See it live' eyebrow + 3 badges + new subtitle")
print(f"  Page <title> + meta description updated")
