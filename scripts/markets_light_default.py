#!/usr/bin/env python3
"""
Make the markets dashboard load in LIGHT theme by default (was dark).

Three coordinated changes:
1. Set mount.setAttribute('data-bmd-theme', 'light') when the skeleton
   is first built, so the [data-bmd-theme="light"] CSS rules apply from
   the very first paint.
2. Change dashboardTheme default 'dark' → 'light' (used as fallback
   if the mount element can't be found).
3. Invert getTheme()'s fallback: when the attribute isn't set, default
   to 'light' instead of 'dark' (so any code path that reads the theme
   before the attribute is set also gets light).

Also bump SW + cache-bust so the change reaches the PWA immediately.
"""
import re

PATH = "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js"
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ─── (1) Set data-bmd-theme="light" on the mount when building the skeleton ─
# Find the buildSkeleton function and add a setAttribute call before innerHTML.
OLD_INIT = "  // ─── Build the dashboard HTML skeleton ───────────────────────────────────\n  function buildSkeleton(mount) {\n    mount.innerHTML = `"
NEW_INIT = ("  // ─── Build the dashboard HTML skeleton ───────────────────────────────────\n"
           "  function buildSkeleton(mount) {\n"
           "    // Default theme = LIGHT (user preference — was dark). Set BEFORE\n"
           "    // innerHTML so the [data-bmd-theme=\"light\"] CSS rules apply on\n"
           "    // first paint, not after a flash of dark theme.\n"
           "    if (!mount.getAttribute('data-bmd-theme')) mount.setAttribute('data-bmd-theme', 'light');\n"
           "    mount.innerHTML = `")

if OLD_INIT in src:
    src = src.replace(OLD_INIT, NEW_INIT)
    print("OK: buildSkeleton now sets data-bmd-theme='light' on first paint")
else:
    print("WARN: buildSkeleton init pattern not found")

# ─── (2) Default theme variable: 'dark' → 'light' ──────────────────────────
OLD_DEFAULT = "  var dashboardTheme = 'dark'; // default"
NEW_DEFAULT = "  var dashboardTheme = 'light'; // default — user prefers light"
if OLD_DEFAULT in src:
    src = src.replace(OLD_DEFAULT, NEW_DEFAULT)
    print("OK: dashboardTheme default → 'light'")
else:
    print("WARN: dashboardTheme default pattern not found")

# ─── (3) getTheme() fallback: dark → light ─────────────────────────────────
OLD_GET = "    if (mount) return mount.getAttribute('data-bmd-theme') === 'light' ? 'light' : 'dark';"
NEW_GET = "    if (mount) return mount.getAttribute('data-bmd-theme') === 'dark' ? 'dark' : 'light';"
if OLD_GET in src:
    src = src.replace(OLD_GET, NEW_GET)
    print("OK: getTheme() fallback → 'light' (was 'dark')")
else:
    print("WARN: getTheme() pattern not found")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

# ─── (4) Bump SW version + cache-bust ──────────────────────────────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.78.0-20261008-markets-light-theme-default';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.78.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.78.0, all ?v= → 4.78.0")

IDX = "/tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html"
with open(IDX, "r", encoding="utf-8") as f:
    idx = f.read()
idx_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.78.0", idx)
if idx_new != idx:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(idx_new)
    print("OK: blog/universal-dashboard-builder.html ?v= → 4.78.0")
