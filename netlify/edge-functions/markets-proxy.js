// ════════════════════════════════════════════════════════════════════════════
//  markets-proxy — Netlify Edge Function
//
//  Server-side proxy for Yahoo Finance (indices + gold) and Frankfurter (FX).
//  Both upstreams don't support CORS, so the browser can't fetch them
//  directly. This edge function fetches server-side and returns the data
//  with proper CORS headers.
//
//  Endpoints:
//    GET /markets-proxy?symbols=^GSPC,^IXIC,^DJI,^GSPTSE,GC=F
//      → fetches Yahoo Finance quotes for each symbol in parallel
//      → returns JSON: { quotes: [{ symbol, price, change, changePct, currency, exchange }, ...] }
//
//    GET /markets-proxy?fx=1
//      → fetches Frankfurter FX rates (USD → EUR,GBP,JPY,CAD,AUD,CHF,CNY)
//      → returns JSON: { rates: { EUR: 0.89, ... }, date: "2026-10-02" }
//
//  Cache: 60 seconds (in-memory, per-edge-instance). Yahoo data is delayed
//  10-15 min anyway, so 60s cache is plenty.
//
//  ⚠️ changePct comes from Yahoo's own regularMarketChangePercent field,
//  NOT computed by us — Yahoo calculates it against the previous regular
//  session close (yesterday). Computing it ourselves from chartPreviousClose
//  gives the 30-day cumulative change (since chartPreviousClose is the
//  close ~31 days ago for a range=1mo chart), which made every delta on
//  the dashboard look misleadingly green/red. See fetchYahooQuote().
//
//  Allowed origins: insight-analytics.ca, insightanalyticsca.github.io,
//  localhost for dev.
// ════════════════════════════════════════════════════════════════════════════

const CACHE_TTL_MS = 60 * 1000; // 60 seconds
const FETCH_TIMEOUT_MS = 8000;

const ALLOWED_ORIGINS = [
  'https://insight-analytics.ca',
  'https://www.insight-analytics.ca',
  'https://insightanalyticsca.github.io',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:5173',
  'http://127.0.0.1:5173',
  'http://localhost:8765',
  'http://127.0.0.1:8765',
  'http://localhost:8766',
  'http://127.0.0.1:8766'
];

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
    'Content-Type': 'application/json; charset=utf-8'
  };
}

// In-memory cache (per-edge-instance)
const cache = new Map();

async function fetchYahooQuote(symbol) {
  // range=1mo — 30 calendar days of daily candles. Was 5d (only gave
  // current + previous close, not enough for a 30-day trend chart).
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=1mo`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' },
      signal: controller.signal
    });
    if (!r.ok) return null;
    const d = await r.json();
    const result = d?.chart?.result?.[0];
    const meta = result?.meta;
    if (!meta) return null;
    const price = meta.regularMarketPrice;
    // ⚠️ chartPreviousClose for a range=1mo chart is the close ~31 days
    // ago (the close BEFORE the first candle in the chart), NOT yesterday's
    // close. previousClose is yesterday's regular close — but Yahoo returns
    // null for futures and indices, so we can't rely on it. Yahoo pre-
    // calculates the correct daily change in regularMarketChangePercent
    // (vs previous regular session close) — prefer this whenever available.
    // The old code computed changePct itself using chartPreviousClose,
    // which made the dashboard show the 30-day cumulative change as today's
    // daily change (everything looked misleadingly green/red).
    const prev = meta.previousClose || meta.chartPreviousClose;
    if (!price || !prev) return null;
    // Extract 30-day historical closes + volumes for the trend chart.
    // Yahoo returns timestamps + indicators.quote[0].{close,volume} arrays.
    const closes = result?.indicators?.quote?.[0]?.close || [];
    const volumes = result?.indicators?.quote?.[0]?.volume || [];
    const timestamps = result?.timestamp || [];
    // Prefer Yahoo's own pre-calculated daily change (correct: vs previous
    // regular session close, not the 30-day-ago close). The fallback below
    // only triggers for the rare symbol where Yahoo doesn't expose
    // regularMarketChangePercent — note the fallback uses chartPreviousClose
    // (the 30-day-ago baseline), which is the best we can do without a
    // separate fetch.
    const changePct = (typeof meta.regularMarketChangePercent === 'number')
      ? meta.regularMarketChangePercent
      : ((price - prev) / prev * 100);
    const change = (typeof meta.regularMarketChange === 'number')
      ? meta.regularMarketChange
      : (price - prev);
    return {
      symbol: symbol,
      price: price,
      change: change,
      changePct: changePct,
      currency: meta.currency || 'USD',
      exchange: meta.exchangeName || '',
      lastTradeTime: meta.regularMarketTime || null,
      closes: closes,        // 30 daily close prices (for trend chart)
      volumes: volumes,      // 30 daily volumes (for volume bars)
      timestamps: timestamps  // 30 daily timestamps (for x-axis labels)
    };
  } catch (e) {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchFrankfurter() {
  const url = 'https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY,CAD,AUD,CHF,CNY';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, { signal: controller.signal });
    if (!r.ok) return null;
    const d = await r.json();
    return { rates: d.rates || {}, date: d.date || '' };
  } catch (e) {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export default async (req, ctx) => {
  const url = new URL(req.url);
  const origin = req.headers.get('origin') || '';

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('', { status: 204, headers: corsHeaders(origin) });
  }

  if (req.method !== 'GET') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: corsHeaders(origin)
    });
  }

  // FX endpoint: /markets-proxy?fx=1
  if (url.searchParams.get('fx')) {
    const cacheKey = 'fx';
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
      return new Response(JSON.stringify(cached.data), { headers: corsHeaders(origin) });
    }
    const fxData = await fetchFrankfurter();
    if (!fxData) {
      return new Response(JSON.stringify({ error: 'Frankfurter fetch failed' }), {
        status: 502,
        headers: corsHeaders(origin)
      });
    }
    cache.set(cacheKey, { ts: Date.now(), data: fxData });
    return new Response(JSON.stringify(fxData), { headers: corsHeaders(origin) });
  }

  // Indices endpoint: /markets-proxy?symbols=^GSPC,^IXIC,...
  const symbolsParam = url.searchParams.get('symbols');
  if (!symbolsParam) {
    return new Response(JSON.stringify({
      error: 'Missing symbols parameter',
      usage: 'GET /markets-proxy?symbols=^GSPC,^IXIC,^DJI  OR  /markets-proxy?fx=1'
    }), { status: 400, headers: corsHeaders(origin) });
  }

  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const cacheKey = 'symbols:' + symbolsParam;
  const cached = cache.get(cacheKey);
  if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
    return new Response(JSON.stringify(cached.data), { headers: corsHeaders(origin) });
  }

  // Fetch all symbols in parallel (server-side, no CORS issues)
  const quotes = await Promise.all(symbols.map(fetchYahooQuote));

  const data = {
    ok: true,
    fetchedAt: new Date().toISOString(),
    quotes: quotes.map((q, i) => q || { symbol: symbols[i], error: 'fetch failed' })
  };

  cache.set(cacheKey, { ts: Date.now(), data });
  return new Response(JSON.stringify(data), { headers: corsHeaders(origin) });
};
