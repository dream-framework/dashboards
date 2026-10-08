#!/usr/bin/env python3
"""
Real fix for 'markets dashboard loads dark by default'.

Previous fix set data-bmd-theme='light' inside buildSkeleton(), but
boot() immediately OVERRODE it on line 1700 with:
    mount.setAttribute('data-bmd-theme', 'dark');

This patch:
1. Changes line 1700 to set 'light' (matching the new default).
2. Changes the icon to 'fas fa-sun' (the light-theme icon — current
   convention: icon reflects current theme, sun for light, moon for dark).
3. Changes the toggle handler's fallback from 'dark' to 'light'.
4. Bumps SW version + cache-bust to 4.79.0 so the PWA picks up the
   fix immediately (the previous 4.78.0 bump shipped the broken
   buildSkeleton-only fix).
"""
import re

PATH = "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js"
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ─── (1) boot() — set initial theme to LIGHT, icon to SUN ──────────────────
OLD_BOOT = """    if (bmdToggle) {
      // Set initial icon + mount attribute based on default theme (dark)
      mount.setAttribute('data-bmd-theme', 'dark');
      if (bmdIcon) bmdIcon.className = 'fas fa-moon';
      bmdToggle.addEventListener('click', function () {
        var current = mount.getAttribute('data-bmd-theme') || 'dark';
        var next = current === 'dark' ? 'light' : 'dark';
        mount.setAttribute('data-bmd-theme', next);
        // The MutationObserver will handle re-rendering charts + updating the icon
      });
    }"""

NEW_BOOT = """    if (bmdToggle) {
      // Set initial icon + mount attribute based on default theme (LIGHT).
      // User preference: dashboard loads in light theme by default; the
      // theme toggle button still lets users switch to dark if they want.
      // Previous code forced 'dark' here, overriding buildSkeleton()'s
      // light default.
      mount.setAttribute('data-bmd-theme', 'light');
      if (bmdIcon) bmdIcon.className = 'fas fa-sun';
      bmdToggle.addEventListener('click', function () {
        var current = mount.getAttribute('data-bmd-theme') || 'light';
        var next = current === 'dark' ? 'light' : 'dark';
        mount.setAttribute('data-bmd-theme', next);
        // The MutationObserver will handle re-rendering charts + updating the icon
      });
    }"""

if OLD_BOOT in src:
    src = src.replace(OLD_BOOT, NEW_BOOT)
    print("OK: boot() now sets data-bmd-theme='light' + fa-sun icon (was dark/fa-moon)")
else:
    print("WARN: boot() pattern not found — was it already patched?")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

# ─── (2) Bump SW + cache-bust to 4.79.0 ────────────────────────────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.79.0-20261008-markets-light-default-boot-fix';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.79.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.79.0, all ?v= → 4.79.0")

IDX = "/tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html"
with open(IDX, "r", encoding="utf-8") as f:
    idx = f.read()
idx_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.79.0", idx)
if idx_new != idx:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(idx_new)
    print("OK: blog/universal-dashboard-builder.html ?v= → 4.79.0")
