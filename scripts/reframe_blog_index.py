#!/usr/bin/env python3
"""
Phase 2: reframe the blog index hero + update title + meta + CSS.
Navbar renames already done in phase 1.
"""
BLOG_IDX = '/home/z/insight-analytics/blog/index.html'
s = open(BLOG_IDX).read()

# ─── Hero reframe ──────────────────────────────────────────────────────────
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
print("  [1] Hero reframed: 'Production-ready · See it live' eyebrow + badges + new subtitle")

# ─── Page title ────────────────────────────────────────────────────────────
OLD_TITLE = "<title>Blog \u2014 Insight Analytics</title>"
NEW_TITLE = "<title>Demos \u2014 Production-Ready Pipelines | Insight Analytics</title>"
assert OLD_TITLE in s, "blog index <title> not found"
s = s.replace(OLD_TITLE, NEW_TITLE, 1)
print("  [2] Page <title> updated")

# ─── Meta description ──────────────────────────────────────────────────────
OLD_META = '<meta name="description" content="Articles on data architecture, AI-assisted analytics, database discovery, and building self-explaining enterprise systems." />'
NEW_META = '<meta name="description" content="Production-ready demos \u2014 same code, same data flow, same KPIs as our 50+ production deployments. Click, interact, judge for yourself. Live dashboards, AI pipeline constructor, database archaeology, time series prediction." />'
assert OLD_META in s, "blog index meta description not found"
s = s.replace(OLD_META, NEW_META, 1)
print("  [3] Meta description updated")

# ─── CSS for badges ───────────────────────────────────────────────────────
OLD_CSS = "    .blog-index-head p { font-size: 1.1rem; color: var(--text-muted); max-width: 560px; margin: 0 auto; line-height: 1.6; }"
NEW_CSS = OLD_CSS + """
    .blog-prod-badges { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin-top: 24px; }
    .blog-prod-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px; font-size: 0.82rem; font-weight: 600; color: var(--text-soft); background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.06)); border: 1px solid var(--border); }
    .blog-prod-badge i { color: #10b981; font-size: 0.78rem; }
    [data-theme="dark"] .blog-prod-badge { color: var(--text-muted); background: linear-gradient(135deg, rgba(99,102,241,0.14), rgba(6,182,212,0.10)); }"""
assert OLD_CSS in s, "blog-index-head CSS not found"
s = s.replace(OLD_CSS, NEW_CSS, 1)
print("  [4] CSS for .blog-prod-badges + .blog-prod-badge added")

# ─── Update Open Graph title/description to match ─────────────────────────
OLD_OG_TITLE = '<meta property="og:title" content="Blog | Insight Analytics" />'
NEW_OG_TITLE = '<meta property="og:title" content="Demos \u2014 Production-Ready Pipelines | Insight Analytics" />'
if OLD_OG_TITLE in s:
    s = s.replace(OLD_OG_TITLE, NEW_OG_TITLE, 1)
    print("  [5] Open Graph title updated")

open(BLOG_IDX, 'w').write(s)
print(f"\nDone. Wrote {BLOG_IDX}")
