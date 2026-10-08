#!/usr/bin/env python3
"""
Fix: BTC trend line + right y-axis not showing on Windows.

Root cause: fetchCrypto() used api.binance.com directly. On Windows
desktop browsers, ad blockers (uBlock Origin, AdGuard), privacy
extensions, or DNS-level filters (NextDNS, Cloudflare for Families)
commonly block api.binance.com — even though it's just market data,
ad-block lists flag it as a 'crypto tracker'. Mobile browsers and PWAs
don't usually have these blockers installed, so BTC loads there.

When BTC fetch fails, btcSeries stays null, no series uses yAxisIndex:1,
and ECharts auto-hides the unused right y-axis — so the chart shows
only 1 axis (left) and no BTC line.

Fix: try data-api.binance.vision FIRST (Binance's PUBLIC market-data
endpoint, not geo-blocked, not on common ad-block lists), then fall
back to api.binance.com if that fails. Both endpoints return identical
JSON shapes and accept the same query string.

Also bumps SW + cache-bust to 4.81.0 so the PWA picks up the fix
immediately.
"""
import re

PATH = "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js"
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

OLD = """  // ─── Fetch LIVE crypto from Binance ──────────────────────────────────────
  async function fetchCrypto() {
    try {
      var r = await fetch('https://api.binance.com/api/v3/ticker/24hr?symbols=%5b%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22%5d');
      if (!r.ok) return false;
      var d = await r.json();
      d.forEach(function (t) {
        var sym = t.symbol.replace('USDT', '');
        liveData[sym.toLowerCase()] = {
          price: parseFloat(t.lastPrice),
          change: parseFloat(t.priceChangePercent)
        };
      });
      // Also fetch 30-day BTC klines (daily candles) for the trend chart.
      // Binance has CORS — can fetch directly without a proxy.
      try {
        var kUrl = 'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=30';
        var kr = await fetch(kUrl);
        if (kr.ok) {
          var kd = await kr.json();
          if (Array.isArray(kd) && kd.length > 0) {
            // Each kline: [openTime, open, high, low, close, volume, ...]
            liveData.btc.history = kd.map(function (k) {
              return parseFloat(k[4]); // close price
            });
          }
        }
      } catch (e) { /* BTC history not available — trend chart skips BTC series */ }
      return true;
    } catch (e) { return false; }
  }"""

NEW = """  // ─── Fetch LIVE crypto from Binance ──────────────────────────────────────
  // Uses two Binance endpoints in fallback order:
  //   1. data-api.binance.vision  — Binance's PUBLIC market-data API, NOT
  //      geo-blocked, NOT on common ad-block lists. PRIMARY now because
  //      Windows desktop users frequently have api.binance.com blocked
  //      by uBlock Origin / AdGuard / NextDNS (flagged as a 'crypto
  //      tracker' even though it's just market data, not trading). Mobile
  //      browsers and PWAs usually don't have these blockers, so BTC
  //      was loading fine there but failing on Windows.
  //   2. api.binance.com          — Binance's main API. May be blocked
  //      by ad blockers / DNS filters on some networks. Fallback only.
  // Both endpoints return identical JSON shape and accept the same query
  // string. Binance supports CORS for read-only market data.
  var BINANCE_ENDPOINTS = [
    'https://data-api.binance.vision',
    'https://api.binance.com'
  ];

  async function fetchCrypto() {
    // Try each Binance endpoint in fallback order. First one that
    // succeeds is used for BOTH the 24hr ticker AND the 30-day klines
    // (so we don't re-test all endpoints for the klines call).
    var base = null;
    for (var i = 0; i < BINANCE_ENDPOINTS.length; i++) {
      try {
        var tr = await fetch(BINANCE_ENDPOINTS[i] + '/api/v3/ping');
        if (tr.ok) { base = BINANCE_ENDPOINTS[i]; break; }
      } catch (e) { /* endpoint blocked or unreachable — try next */ }
    }
    if (!base) {
      // All endpoints failed (e.g., user behind a strict corporate
      // firewall that blocks all crypto domains). Bail out — the trend
      // chart will skip the BTC series, which is the existing behavior.
      return false;
    }
    try {
      var r = await fetch(base + '/api/v3/ticker/24hr?symbols=%5b%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22%5d');
      if (!r.ok) return false;
      var d = await r.json();
      d.forEach(function (t) {
        var sym = t.symbol.replace('USDT', '');
        liveData[sym.toLowerCase()] = {
          price: parseFloat(t.lastPrice),
          change: parseFloat(t.priceChangePercent)
        };
      });
      // 30-day BTC klines for the trend chart — same endpoint that just
      // succeeded for the ticker, reuses the working base URL.
      try {
        var kUrl = base + '/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=30';
        var kr = await fetch(kUrl);
        if (kr.ok) {
          var kd = await kr.json();
          if (Array.isArray(kd) && kd.length > 0) {
            // Each kline: [openTime, open, high, low, close, volume, ...]
            liveData.btc.history = kd.map(function (k) {
              return parseFloat(k[4]); // close price
            });
          }
        }
      } catch (e) { /* BTC history not available — trend chart skips BTC series */ }
      return true;
    } catch (e) { return false; }
  }"""

if OLD in src:
    src = src.replace(OLD, NEW)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: fetchCrypto now tries data-api.binance.vision FIRST, falls back to api.binance.com")
else:
    print("WARN: fetchCrypto pattern not found — was it already patched?")

# Bump SW + cache-bust
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.81.0-20261008-binance-vision-fallback';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.81.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.81.0, all ?v= → 4.81.0")

IDX = "/tmp/my-project/insight-analytics/blog/universal-dashboard-builder.html"
with open(IDX, "r", encoding="utf-8") as f:
    idx = f.read()
idx_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.81.0", idx)
if idx_new != idx:
    with open(IDX, "w", encoding="utf-8") as f:
        f.write(idx_new)
    print("OK: blog/universal-dashboard-builder.html ?v= → 4.81.0")
