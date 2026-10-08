#!/usr/bin/env python3
"""
Make the Index & Crypto Trends source-pill label consistent on desktop
and mobile.

Bug: the label was 'S&P/NASDAQ: Yahoo history+live · BTC: Binance live'
(43 chars) when BTC was loaded, which wraps to 2 lines on mobile and
doesn't fit in the chart-title's source-pill slot. On desktop, BTC
was sometimes not loaded yet (race), so the short 'Yahoo history+live'
showed — making the labels inconsistent across viewports.

Fix: always use the short version ('Yahoo history+live' or 'Yahoo live')
regardless of whether BTC loaded. The BTC source is already indicated
by the BTC ($) legend entry in the chart itself, so qualifying it in
the source pill is redundant.

Also bumps SW + cache-bust to 4.80.0.
"""
import re

PATH = "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js"
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

OLD = """    var srcEl3 = document.getElementById('bmd-src-trends');
    setSrcLabel('bmd-src-trends',
      hasHist
        ? (btcSeries ? 'S&P/NASDAQ: Yahoo history+live · BTC: Binance live' : 'Yahoo history+live')
        : (btcSeries ? 'S&P/NASDAQ: Yahoo live · BTC: Binance live' : 'Yahoo live'),
      true
    );"""

NEW = """    var srcEl3 = document.getElementById('bmd-src-trends');
    // Use the SHORT label on all viewports — the long version
    // ('S&P/NASDAQ: Yahoo history+live · BTC: Binance live') wraps to 2
    // lines on mobile and doesn't fit in the chart-title's source-pill
    // slot. The BTC source is already indicated by the BTC ($) legend
    // entry, so qualifying it in the source pill is redundant.
    setSrcLabel('bmd-src-trends',
      hasHist ? 'Yahoo history+live' : 'Yahoo live',
      true
    );"""

if OLD in src:
    src = src.replace(OLD, NEW)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: trends source label → always short version")
else:
    print("WARN: pattern not found — was it already patched?")

# Bump SW + cache-bust
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.80.0-20261008-trends-label-consistent';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.80.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.80.0, all ?v= → 4.80.0")

IDX = "/tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html"
with open(IDX, "r", encoding="utf-8") as f:
    idx = f.read()
idx_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.80.0", idx)
if idx_new != idx:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(idx_new)
    print("OK: blog/universal-dashboard-builder.html ?v= → 4.80.0")
