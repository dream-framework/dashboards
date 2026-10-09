#!/usr/bin/env python3
"""
Apply the scroll-snap-disable fix to ALL 6 blog post pages (the blog
index was already fixed in the previous commit).

Each blog post page inherits `html { scroll-snap-type: y mandatory }`
from the shared styles.css. The blog posts use <section> elements with
classes like .blog-hero, .blog-body, etc. — NOT the .section class
that styles.css targets for scroll-snap-align. So there are no valid
snap targets on blog posts, and `mandatory` snap with no targets
traps the scroll on mobile/PWA (page loads at the bottom and won't
let the user scroll up).

Fix: inject `html { scroll-snap-type: none !important; }` at the top
of each blog post's inline <style> block. The inline <style> comes
after the <link> to styles.css in <head>, and !important wins.
"""
import os
import glob

BLOG_DIR = "/tmp/my-project/insight-analytics/blog"

# The fix to inject at the top of each blog post's <style> block.
SNAP_DISABLE = """  <style>
    /* Disable scroll-snap on blog pages. The shared styles.css sets
       `html { scroll-snap-type: y mandatory }` which works on the main
       landing page (where every .section is a snap target). But blog
       pages use <section class='blog-hero'>, <section class='blog-body'>,
       etc. — NOT the .section class that styles.css targets for
       scroll-snap-align. So there are no valid snap targets on blog
       pages, and `mandatory` snap with no targets traps the scroll on
       mobile/PWA (page loads at the bottom and won't let the user
       scroll up). This override disables snap for blog pages only. */
    html { scroll-snap-type: none !important; }
"""

count = 0
for path in sorted(glob.glob(os.path.join(BLOG_DIR, "*.html"))):
    fname = os.path.basename(path)
    if fname == "index.html":
        continue  # already fixed in previous commit

    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Skip if already patched
    if "scroll-snap-type: none !important" in src:
        print(f"SKIP (already patched): {fname}")
        continue

    # Find the inline <style> tag and inject the snap-disable rule
    # right after it.
    if "  <style>\n" not in src:
        print(f"WARN: no <style> tag found in {fname}")
        continue

    # Replace the FIRST occurrence of "  <style>\n" with the snap-disable
    # block (which itself starts with "  <style>\n" + the comment + the
    # rule). This effectively prepends the rule to the existing style block.
    new_src = src.replace("  <style>\n", SNAP_DISABLE, 1)

    if new_src != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_src)
        count += 1
        print(f"OK: {fname}")

print(f"\n{count} blog post pages patched.")
