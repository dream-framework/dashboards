#!/usr/bin/env python3
"""
Update the mobile-menu (hamburger) link label from 'Demos' to 'Live Demos'
across index.html and blog/personalized-power-automate.html (the only 2
files with a mobile menu). Desktop navbar + footer links stay as 'Demos'
(short for layout density).
"""
import re

FILES = [
    '/home/z/insight-analytics/index.html',
    '/home/z/insight-analytics/blog/personalized-power-automate.html',
]

# Match the mobile-menu link only (has role="menuitem")
OLD = '<a href="/blog/" class="nav-link" role="menuitem" title="Demos \u2014 see it live. Production-ready pipelines.">Demos</a>'
NEW = '<a href="/blog/" class="nav-link" role="menuitem" title="Live Demos \u2014 see it live. Production-ready pipelines.">Live Demos</a>'

total = 0
for fp in FILES:
    s = open(fp).read()
    cnt = s.count(OLD)
    if cnt == 0:
        print(f"  {fp}: no match (already updated?)")
        continue
    s = s.replace(OLD, NEW)
    open(fp, 'w').write(s)
    print(f"  {fp.split('/')[-1]}: {cnt} mobile-menu link(s) updated 'Demos' → 'Live Demos'")
    total += cnt
print(f"\nTotal: {total} mobile-menu links updated")
