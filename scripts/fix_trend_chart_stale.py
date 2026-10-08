#!/usr/bin/env python3
"""
Fix: markets dashboard trend chart stops at Oct 2 (or earlier).

Root cause: renderTrends() reads historical closes from STATIC JSON files
committed to the repo (/data/historical/sp500.json, nasdaq.json). Those
files are stale (last scraped Oct 5 or earlier). The live markets-proxy
ALREADY returns fresh closes/timestamps/volumes arrays in every quote
response, but the dashboard throws them away and only stores price +
changePct.

Fix: modify fetchIndices() so when it stores each live quote, it ALSO
writes the closes/timestamps/volumes into liveData.sp500History (and
equivalent for nasdaq, dow, tsx, gold, etc.) — REPLACING the stale
static JSON as soon as the live fetch succeeds.

The existing renderTrends() function reads liveData.sp500History.closes
/ days / volumes, so we just need to convert the proxy's timestamps
(Unix seconds) to 'MM/DD' day labels and normalize volumes to the same
scale the static JSON used (billions for indices).

Files patched:
  /tmp/my-project/insight-analytics/js/blog-markets-dashboard.js
"""
import os

PATH = "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js"

# The fetchIndices() function. Find the inner forEach that stores each quote
# and replace it with one that ALSO stores the history arrays.
OLD = """      var keyMap = {};
      symbols.forEach(function (s) { keyMap[s.sym] = s.key; });
      var anyOk = false;
      d.quotes.forEach(function (q) {
        if (q.price != null && keyMap[q.symbol]) {
          liveData[keyMap[q.symbol]] = { price: q.price, change: q.changePct };
          anyOk = true;
        }
      });
      return anyOk;"""

NEW = """      var keyMap = {};
      symbols.forEach(function (s) { keyMap[s.sym] = s.key; });
      var anyOk = false;
      d.quotes.forEach(function (q) {
        if (q.price != null && keyMap[q.symbol]) {
          var k = keyMap[q.symbol];
          liveData[k] = { price: q.price, change: q.changePct };
          anyOk = true;
          // ─── ALSO store the proxy's closes/timestamps/volumes arrays
          // as liveData[k + 'History'] so renderTrends() uses fresh live
          // history through the most recent trading day, instead of the
          // stale static JSON in /data/historical/*.json (which was last
          // scraped days/weeks ago and made the trend chart stop at the
          // scrape date).
          //
          // Convert Yahoo's Unix-second timestamps to 'MM/DD' labels and
          // normalize volumes to billions (Yahoo returns raw share counts
          // for indices, e.g. 5_783_800_000 — divide by 1e9 to match the
          // scale the static JSON used so volume bars render correctly).
          if (Array.isArray(q.closes) && q.closes.length > 0 && Array.isArray(q.timestamps)) {
            var days = q.timestamps.map(function (t) {
              var d = new Date(t * 1000);
              return (d.getMonth() + 1) + '/' + d.getDate();
            });
            var vols = (Array.isArray(q.volumes) ? q.volumes : []).map(function (v) {
              // Yahoo index volumes are raw share counts (billions). Futures
              // volumes are small contract counts (thousands). Normalize to
              // 'billions' for indices, leave futures alone (volume bar will
              // just be a different scale — only sp500History is rendered
              // in the trend chart, so this only matters for ^GSPC/^IXIC).
              return v > 1e8 ? v / 1e9 : v;
            });
            liveData[k + 'History'] = {
              symbol: q.symbol,
              days: days,
              closes: q.closes.slice(),
              volumes: vols
            };
          }
        }
      });
      return anyOk;"""

with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if OLD not in src:
    if NEW in src:
        print("already applied")
    else:
        print("OLD pattern not found — aborting")
    raise SystemExit(1)

src = src.replace(OLD, NEW)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("OK: fetchIndices() now stores live closes/timestamps/volumes as liveData[k+'History']")
