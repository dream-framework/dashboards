#!/usr/bin/env python3
"""
Fix: blog index page loads at the last card and won't let user scroll up
on mobile/PWA.

Root cause: the shared styles.css sets `html { scroll-snap-type: y
mandatory }`. This works on the main landing page where every .section
is a snap target. But the blog index page has NO .section elements —
it uses <section class="blog-index-head"> + <a class="blog-card"> — so
there are no valid snap targets. On mobile/PWA, `mandatory` snap with
no targets traps the scroll: the browser can't find a valid snap
point and won't let the user scroll up from wherever the page landed.

Fix: add `html { scroll-snap-type: none !important; }` to the blog
index page's inline <style> block. This overrides the shared CSS
(this inline <style> comes after the <link> in <head>, and !important
wins).

Also bumps SW + cache-bust to 4.85.0 so the PWA picks up the fix.
"""
import re

# ─── (1) Blog index.html — disable scroll-snap ───────────────────────────
BLOG = "/tmp/my-project/insight-analytics/blog/index.html"
with open(BLOG, "r", encoding="utf-8") as f:
    src = f.read()

OLD = "  <style>\n    .blog-index-head {"
NEW = """  <style>
    /* Disable scroll-snap on the blog index page. The shared styles.css
       sets `html { scroll-snap-type: y mandatory }` which works on the
       main landing page (where every .section is a snap target). But the
       blog index has NO .section elements — it uses .blog-index-head +
       .blog-card — so there are no valid snap targets. On mobile/PWA,
       `mandatory` snap with no targets traps the scroll: the page loads
       at the last card and won't let the user scroll up. Setting
       scroll-snap-type: none here overrides the shared CSS (this inline
       <style> comes after the <link> in <head>, and !important wins). */
    html { scroll-snap-type: none !important; }

    .blog-index-head {"""

if OLD in src:
    src = src.replace(OLD, NEW)
    with open(BLOG, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: blog/index.html — scroll-snap disabled")
else:
    print("WARN: blog/index.html pattern not found")

# ─── (2) Bump SW + cache-bust ─────────────────────────────────────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.85.0-20261009-blog-no-snap';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.85.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.85.0, all ?v= → 4.85.0")
