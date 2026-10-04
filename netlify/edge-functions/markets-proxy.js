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
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=5d`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' },
      signal: controller.signal
    });
    if (!r.ok) return null;
    const d = await r.json();
    const meta = d?.chart?.result?.[0]?.meta;
    if (!meta) return null;
    const price = meta.regularMarketPrice;
    const prev = meta.chartPreviousClose || meta.previousClose;
    if (!price || !prev) return null;
    return {
      symbol: symbol,
      price: price,
      change: price - prev,
      changePct: ((price - prev) / prev * 100),
      currency: meta.currency || 'USD',
      exchange: meta.exchangeName || '',
      lastTradeTime: meta.regularMarketTime || null
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
