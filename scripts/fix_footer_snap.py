#!/usr/bin/env python3
"""
Fix: 'I never can reach footer in main site.'

Root cause: html { scroll-snap-type: y mandatory } forces the browser
to snap to .section starts on every scroll. The <footer class="footer">
is NOT a .section element and NOT a scroll-snap-align target — so when
the user scrolls past the last .section, the browser snaps them BACK
UP to the last section's start. The footer was unreachable.

Fix: add scroll-snap-align: start + scroll-margin-top: var(--nav-h)
to .footer (matching .section's snap configuration). Now the snap
algorithm treats the footer as a valid snap destination, so users
can scroll all the way to the bottom and the browser will settle on
the footer instead of bouncing back up.

Also bumps SW + cache-bust to 4.83.0 so the PWA picks up the fix
immediately.
"""
import re

CSS = "/tmp/my-project/insight-analytics/css/styles.css"
with open(CSS, "r", encoding="utf-8") as f:
    css = f.read()

OLD = """.footer {
  background: var(--bg);
  border-top: 1px solid var(--border);
  padding: 56px 0 32px;
}"""

NEW = """.footer {
  background: var(--bg);
  border-top: 1px solid var(--border);
  padding: 56px 0 32px;
  /* Make the footer a scroll-snap target so users can actually reach it.
     Without this, html's `scroll-snap-type: y mandatory` snaps the user
     back up to the last .section start when they try to scroll into the
     footer area — the footer was unreachable. Adding scroll-snap-align
     + scroll-margin-top (matching .section) lets the snap algorithm
     settle on the footer as a valid snap destination. */
  scroll-snap-align: start;
  scroll-margin-top: var(--nav-h);
}"""

if OLD in css:
    css = css.replace(OLD, NEW)
    with open(CSS, "w", encoding="utf-8") as f:
        f.write(css)
    print("OK: .footer now has scroll-snap-align: start + scroll-margin-top")
else:
    print("WARN: .footer pattern not found")

# Bump SW + cache-bust
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.83.0-20261008-footer-snap-target';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.83.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.83.0, all ?v= → 4.83.0")

IDX = "/tmp/my-project/insight-analytics/index.html"
with open(IDX, "r", encoding="utf-8") as f:
    idx = f.read()
idx_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.83.0", idx)
# Also bump the CSS link
idx_new = re.sub(r'href="\./css/styles\.css\?v=\d+\.\d+\.\d+"', 'href="./css/styles.css?v=4.83.0"', idx_new)
if idx_new != idx:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(idx_new)
    print("OK: index.html ?v= → 4.83.0 (incl. styles.css)")
