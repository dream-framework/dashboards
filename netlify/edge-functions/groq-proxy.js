// ════════════════════════════════════════════════════════════════════════════
//  groq-proxy — Netlify Edge Function (Groq upstream + in-memory cache)
//
//  Switched back to Groq after OpenRouter's poolside/laguna-s-2.1:free
//  turned out to be too rate-limited (429 upstream). Groq's qwen-3.8-27b
//  was working fine before — just needs the cache layer to stay under
//  the 200K TPD free-tier cap.
//
//  In-memory cache (per-edge-instance, no netlify:blobs import needed):
//    - Keyed by SHA-256 of request body
//    - TTL: 24 hours
//    - Cache hit: stream the cached text back as simulated SSE
//    - Cache miss: call Groq, stream to client, store in memory
//    - Lower hit rate than Netlify Blobs (per-instance, not shared across
//      edges) but works without the bundler issues that blocked Blobs
//
//  Verify pings (max_tokens <= 5) SKIP the cache — real health checks.
//  ════════════════════════════════════════════════════════════════════════════

const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions';
const DEFAULT_MODEL = 'qwen/qwen3.8-27b';
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;  // 24 hours
const VERIFY_MAX_TOKENS = 5;

// Allowed origins for CORS. The first entry is the FALLBACK returned when
// the request origin isn't in the list — keep 'https://insight-analytics.ca'
// as [0] so production always works even if a new origin slips through.
// IMPORTANT: when adding a new origin, also verify the deployed Netlify
// edge function actually has this list (a stale deployed version was the
// root cause of the personalized-power-automate demo failing with
// "Couldn't reach the AI service" on insight-analytics.ca — Oct 2026).
const ALLOWED_ORIGINS = [
  'https://insight-analytics.ca',
  'https://www.insight-analytics.ca',
  'https://insightanalyticsca.github.io',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:5173',
  'http://127.0.0.1:5173'
];

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
    'Access-Control-Allow-Headers': 'Content-Type, X-Page, X-Page-Url',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin'
  };
}

// ─── In-memory cache (per-edge-instance) ─────────────────────────────────
// Netlify Blobs would be shared across edges, but the import failed the
// local bundler. In-memory is per-instance but still saves tokens within
// a single edge — most users in the same region hit the same instance.
const memCache = new Map();

// ─── Persistent visit log via netlify:blobs (shared across all edges) ──────
// The in-memory visitLog is per-instance and lost when the edge recycles.
// netlify:blobs provides persistent, shared storage that survives edge
// restarts. We initialize it lazily (inside an async function) because
// top-level await is not supported by Netlify's CJS bundler.
let visitStore = null;
let visitStoreInitDone = false;
const VISIT_RETENTION_MS = 72 * 60 * 60 * 1000; // 72 hours
const MAX_VISITS_BLOB = 2000; // cap blob size
let visitBlobWritesPending = 0;

async function ensureVisitStore() {
  if (visitStoreInitDone) return visitStore;
  visitStoreInitDone = true;
  try {
    const blobs = await import('netlify:blobs');
    visitStore = blobs.getStore('visit-stats');
  } catch (e) {
    // netlify:blobs not available — in-memory only (same as before)
    visitStore = null;
  }
  return visitStore;
}

async function readVisitLogBlob() {
  await ensureVisitStore();
  if (!visitStore) return [];
  try {
    const data = await visitStore.get('visits-72h');
    if (!data) return [];
    const visits = JSON.parse(data);
    if (!Array.isArray(visits)) return [];
    // Filter by 72-hour retention
    const cutoff = Date.now() - VISIT_RETENTION_MS;
    return visits.filter(v => new Date(v.ts).getTime() > cutoff);
  } catch (e) {
    return [];
  }
}

async function writeVisitLogBlob(newVisits) {
  await ensureVisitStore();
  if (!visitStore || newVisits.length === 0) return;
  try {
    // Read existing blob visits, merge with new, dedupe, trim, write back
    const existing = await readVisitLogBlob();
    const merged = [...existing, ...newVisits];
    // Deduplicate by ts + ip
    const seen = new Set();
    const deduped = merged.filter(v => {
      const key = v.ts + '|' + v.ip;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    // Sort newest first
    deduped.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
    // Trim to max
    const trimmed = deduped.slice(0, MAX_VISITS_BLOB);
    await visitStore.set('visits-72h', JSON.stringify(trimmed));
  } catch (e) {
    // silent — don't break the edge function
  }
}

// ─── Visit logging + persistent cumulative stats ───────────────────────────
const visitLog = [];
const MAX_VISITS = 500;
const ADMIN_PASSWORD = 'Domino88!!';
const BLOB_STORE = 'visit-stats';
const BLOB_KEY = 'cumulative';

// In-memory cumulative stats (restored from Blob on startup)
var cumulative = { totalVisits: 0, ips: {}, devices: {} };
var blobLoaded = false;
var blobWritesPending = 0;

// ─── IP blocklist ────────────────────────────────────────────────────────
// Visits from these IPs are NOT counted toward totalVisits / device / IP maps.
// Used to exclude the owner's own IP (and any other internal/synthetic
// traffic) so admin stats reflect real external visitors only.
// NOTE: on blob read, prior counts for these IPs are also subtracted from
// cumulative.totalVisits and removed from cumulative.ips — a one-time
// reconciliation pass that runs in readCumulative() so old inflated
// counts get corrected automatically on the next deploy.
const EXCLUDED_IPS = new Set([
  '70.54.144.197',    // owner — do not self-count
  '216.16.231.122',   // owner's secondary IP — do not self-count
  '8.8.8.8',          // test artifact (Google DNS — used in HTTP header injection tests)
  '9.9.9.9'           // test artifact (Quad9 DNS — used in HTTP header injection tests)
]);

function logVisit(request, context) {
  const headers = request.headers;
  const geo = context.geo || {};
  var referrer = headers.get('referer') || headers.get('referrer') || 'direct';
  // Page the visitor was on — try explicit headers first (X-Page), then query
  // param (beacon sends ?page=...), then derive from Referer (may be stripped
  // to origin by browser Referrer-Policy for cross-origin requests)
  var page = headers.get('x-page') || '';
  if (!page) {
    try { page = new URL(request.url).searchParams.get('page') || ''; } catch(_) {}
  }
  if (!page) {
    page = 'direct';
    if (referrer && referrer !== 'direct') {
      try {
        var refUrl = new URL(referrer);
        page = refUrl.pathname.replace(/^\/dashboards\/?/, '') || 'index.html';
        if (refUrl.hash) page += refUrl.hash;
      } catch(e) {
        page = referrer.slice(0, 80);
      }
    }
  }

  // ─── Extract the REAL visitor IP (not CDN/proxy IP) ──────────────────────
  // Priority order (per Fastly/CDN best practices):
  //   1. Fastly-Client-IP — Fastly's locked copy of the first client IP
  //   2. X-Forwarded-For — first (leftmost) IP is the real visitor
  //   3. X-Real-IP — clean copy of the original IP
  //   4. x-nf-client-connection-ip — Netlify's own IP detection
  //   5. cf-connecting-ip — Cloudflare's IP (if behind CF)
  //   6. Raw socket IP (fallback — may be a CDN/proxy IP, not the real visitor)
  // NOTE: Apple iCloud Private Relay masks the IP at the device level via
  // Fastly — in that case, even Fastly-Client-IP will be a Fastly-owned IP
  // (typically 2a04:4e41:...). This is mathematically impossible to bypass.
  var ip = headers.get('fastly-client-ip') ||
           (headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
           headers.get('x-real-ip') ||
           headers.get('x-nf-client-connection-ip') ||
           headers.get('cf-connecting-ip') ||
           'unknown';
  // Validate: strip brackets from IPv6, trim whitespace
  ip = ip.replace(/^\[|\]$/g, '').trim();

  // ─── Skip excluded IPs (owner / internal / synthetic traffic) ────────
  // These IPs are not counted as visits at all — return early so neither
  // the visit log nor cumulative stats see them.
  if (EXCLUDED_IPS.has(ip)) {
    return null;
  }

  var ua = headers.get('user-agent') || 'unknown';
  var device = parseDeviceUA(ua);
  var country = geo.country?.name || geo.country || 'unknown';
  var city = geo.city?.name || geo.city || 'unknown';

  const visit = { ts: new Date().toISOString(), ip, country, city, page, method: request.method, ua };
  visitLog.push(visit);
  if (visitLog.length > MAX_VISITS) visitLog.shift();

  // Update cumulative stats
  cumulative.totalVisits++;
  cumulative.ips[ip] = (cumulative.ips[ip] || 0) + 1;
  cumulative.devices[device] = (cumulative.devices[device] || 0) + 1;
  blobWritesPending++;

  // Write to Blob every 5 visits (reduces API calls)
  // Guard: don't write until the initial read has completed — otherwise
  // we overwrite the persistent blob with empty stats on every deploy
  if (blobWritesPending >= 5 && blobLoaded) {
    blobWritesPending = 0;
    writeCumulative();
  }

  // Also flush the visit log to the persistent blob every 5 visits
  visitBlobWritesPending++;
  if (visitBlobWritesPending >= 5) {
    visitBlobWritesPending = 0;
    // Flush the last 10 in-memory visits to the blob
    const recent = visitLog.slice(-10);
    writeVisitLogBlob(recent);
  }
  return visit;
}

function parseDeviceUA(ua) {
  if (!ua || ua === 'unknown') return 'unknown';
  var browser = 'Other';
  if (ua.indexOf('Edg/') >= 0) browser = 'Edge';
  else if (ua.indexOf('OPR/') >= 0) browser = 'Opera';
  else if (ua.indexOf('Chrome/') >= 0) browser = 'Chrome';
  else if (ua.indexOf('Firefox/') >= 0) browser = 'Firefox';
  else if (ua.indexOf('Safari/') >= 0 && ua.indexOf('Chrome/') < 0) browser = 'Safari';
  else if (ua.indexOf('curl') >= 0 || ua.indexOf('python') >= 0) browser = 'Bot';
  var os = 'Other';
  if (ua.indexOf('iPhone') >= 0) os = 'iPhone';
  else if (ua.indexOf('iPad') >= 0) os = 'iPad';
  else if (ua.indexOf('Android') >= 0) os = 'Android';
  else if (ua.indexOf('Mac OS') >= 0 || ua.indexOf('Macintosh') >= 0) os = 'macOS';
  else if (ua.indexOf('Windows') >= 0) os = 'Windows';
  else if (ua.indexOf('Linux') >= 0) os = 'Linux';
  return browser + ' · ' + os;
}

// ─── Netlify Blobs REST API (two-step: API → pre-signed S3 URL) ───────────
async function readCumulative() {
  var siteId = Deno.env.get('NETLIFY_SITE_ID');
  var token = Deno.env.get('NETLIFY_API_TOKEN');
  if (!siteId || !token) { blobLoaded = true; return; }
  var apiUrl = 'https://api.netlify.com/api/v1/sites/' + siteId + '/blobs/' + BLOB_STORE + '/' + BLOB_KEY;
  try {
    // Step 1: GET the API → returns a pre-signed S3 URL
    var apiRes = await fetch(apiUrl, { headers: { 'Authorization': 'Bearer ' + token } });
    if (apiRes.status === 200) {
      var apiData = await apiRes.json();
      var s3Url = apiData.url;
      if (s3Url) {
        // Step 2: GET the actual data from S3
        var s3Res = await fetch(s3Url);
        if (s3Res.status === 200) {
          var data = await s3Res.json();
          if (data && typeof data.totalVisits === 'number') {
            cumulative = data;
            // ─── One-time reconciliation: subtract prior counts for any
            // IP that is now in EXCLUDED_IPS but was counted before this
            // fix shipped. Without this, the owner's old self-visits stay
            // baked into totalVisits / ips forever. The corrected cumulative
            // is persisted on the next writeCumulative() call.
            if (cumulative.ips && EXCLUDED_IPS.size > 0) {
              var corrected = false;
              for (var excludedIp of EXCLUDED_IPS) {
                if (cumulative.ips[excludedIp]) {
                  var stale = cumulative.ips[excludedIp];
                  cumulative.totalVisits = Math.max(0, cumulative.totalVisits - stale);
                  delete cumulative.ips[excludedIp];
                  corrected = true;
                }
              }
              if (corrected) {
                // Persist the corrected counts immediately so we don't
                // re-subtract on the next cold start (idempotent guard).
                blobWritesPending = 0;
                writeCumulative();
              }
            }
          }
        }
      }
    }
  } catch(e) { /* first run — blob doesn't exist yet */ }
  blobLoaded = true;
}

async function writeCumulative() {
  var siteId = Deno.env.get('NETLIFY_SITE_ID');
  var token = Deno.env.get('NETLIFY_API_TOKEN');
  if (!siteId || !token) return;
  var apiUrl = 'https://api.netlify.com/api/v1/sites/' + siteId + '/blobs/' + BLOB_STORE + '/' + BLOB_KEY;
  try {
    // Step 1: PUT to the API → returns a pre-signed S3 URL
    var apiRes = await fetch(apiUrl, {
      method: 'PUT',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (apiRes.status === 200) {
      var apiData = await apiRes.json();
      var s3Url = apiData.url;
      if (s3Url) {
        // Step 2: PUT the actual JSON data to S3
        await fetch(s3Url, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cumulative)
        });
      }
    }
  } catch(e) { /* silent — retry on next batch */ }
}

// Restore cumulative stats from Blob on startup (fire-and-forget, but
// guarded by blobLoaded — no writes happen until this completes)
readCumulative().then(function() {
  // Once loaded, flush any pending writes that were blocked
  if (blobWritesPending > 0) {
    blobWritesPending = 0;
    writeCumulative();
  }
});

async function sha256(text) {
  const data = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

// Simulate SSE streaming from a cached text — preserves the streaming UX
function simulatedSSEStream(fullText, model) {
  const id = 'cache-' + Date.now();
  const encoder = new TextEncoder();
  return new ReadableStream({
    async start(controller) {
      const chunks = fullText.match(/\S+\s*/g) || [fullText];
      for (const chunk of chunks) {
        const openaiChunk = {
          id,
          object: 'chat.completion.chunk',
          created: Math.floor(Date.now() / 1000),
          model,
          choices: [{
            index: 0,
            delta: { content: chunk },
            finish_reason: null
          }]
        };
        controller.enqueue(encoder.encode('data: ' + JSON.stringify(openaiChunk) + '\n\n'));
        await new Promise(r => setTimeout(r, 8));
      }
      const finalChunk = {
        id,
        object: 'chat.completion.chunk',
        created: Math.floor(Date.now() / 1000),
        model,
        choices: [{ index: 0, delta: {}, finish_reason: 'stop' }]
      };
      controller.enqueue(encoder.encode('data: ' + JSON.stringify(finalChunk) + '\n\n'));
      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      controller.close();
    }
  });
}

export default async (request, context) => {
  const origin = request.headers.get('origin') || '';

  // ─── Log every visit (IP, geo, UA, timestamp) ──────────────────────────
  // Skip logging for polling/admin endpoints — otherwise the 5-second
  // auto-poll (op=visits, op=devices) and the footer pill (op=stats)
  // create self-referential loops where every poll logs itself as a
  // "visit", inflating the count with heartbeats. Only op=beacon (real
  // page load via GET image ping) is logged as a visit. POST chat
  // completion requests (verify pings with max_tokens=1 AND real chat
  // messages) are ALSO skipped — they're API calls, not page views.
  // Previously every page load fired BOTH a beacon AND an assistant.js
  // verify POST, double-counting each visit; plus every chat message
  // inflated the count further. POSTs are now excluded from visit
  // logging entirely.
  const _url = new URL(request.url);
  const _op = _url.searchParams.get('op');
  const _isPost = request.method === 'POST';
  if (!_isPost && _op !== 'visits' && _op !== 'models' && _op !== 'stats' && _op !== 'devices') {
    logVisit(request, context);
  }

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }

  // GET endpoints
  if (request.method === 'GET') {
    const url = new URL(request.url);
    const op = url.searchParams.get('op');

    // op=beacon — lightweight visit logger called from the lander on page load
    // Returns a 1x1 transparent pixel so it can be used as an image beacon
    if (op === 'beacon') {
      return new Response(
        new Uint8Array([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff, 0x21, 0xf9, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44, 0x01, 0x00, 0x3b]),
        { status: 200, headers: { 'Content-Type': 'image/gif', ...corsHeaders(origin) } }
      );
    }

    // op=stats — PUBLIC endpoint (no password) for the lander footer pill
    // Returns cumulative distinct device count (persistent across deploys)
    if (op === 'stats') {
      // If blob hasn't loaded yet, try a synchronous read
      if (!blobLoaded) {
        await readCumulative();
      }
      // Also write pending stats
      if (blobWritesPending > 0 && blobLoaded) {
        blobWritesPending = 0;
        writeCumulative();
      }
      return new Response(JSON.stringify({
        devices: Object.keys(cumulative.devices || {}).length,
        ips: Object.keys(cumulative.ips || {}).length,
        visits: cumulative.totalVisits || 0
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });
    }

    // op=devices — admin endpoint, returns full unique device + IP maps
    // across ALL history (not just 72h). Shows which specific devices/IPs
    // visited and how many times. Cumulative stats persist via Netlify Blobs.
    if (op === 'devices') {
      const pwd = url.searchParams.get('password') || url.searchParams.get('pwd') || '';
      if (pwd !== ADMIN_PASSWORD) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
        });
      }
      // Ensure cumulative is loaded from blob
      if (!blobLoaded) {
        await readCumulative();
      }
      // Write pending stats
      if (blobWritesPending > 0 && blobLoaded) {
        blobWritesPending = 0;
        writeCumulative();
      }
      // Build device list sorted by visit count descending
      const deviceList = Object.entries(cumulative.devices || {})
        .map(([device, count]) => ({ device, visits: count }))
        .sort((a, b) => b.visits - a.visits);
      // Build IP list sorted by visit count (mask last octet for privacy).
      // Filter out excluded IPs — even after the reconciliation pass in
      // readCumulative removes them from the blob, this guards against
      // any in-memory race where the IP was re-added before the blob
      // write flushed.
      const ipList = Object.entries(cumulative.ips || {})
        .filter(([ip]) => !EXCLUDED_IPS.has(ip))
        .map(([ip, count]) => ({
          ip: ip.replace(/(\d+\.\d+\.\d+)\.\d+/, '$1.xxx'),
          visits: count
        }))
        .sort((a, b) => b.visits - a.visits);
      return new Response(JSON.stringify({
        totalVisits: cumulative.totalVisits || 0,
        distinctDevices: deviceList.length,
        distinctIPs: ipList.length,
        devices: deviceList,
        ips: ipList,
        capturedAt: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });
    }

    // op=visits — admin endpoint, requires password
    if (op === 'visits') {
      const pwd = url.searchParams.get('password') || url.searchParams.get('pwd') || '';
      if (pwd !== ADMIN_PASSWORD) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
        });
      }
      // Write pending stats on admin poll
      if (blobWritesPending > 0 && blobLoaded) {
        blobWritesPending = 0;
        writeCumulative();
      }
      // Also flush any pending visit log entries to the blob
      if (visitBlobWritesPending > 0) {
        visitBlobWritesPending = 0;
        await writeVisitLogBlob(visitLog.slice(-10));
      }
      // Read persistent visits from blob (survives edge restarts, 72h retention)
      const blobVisits = await readVisitLogBlob();
      // Merge blob visits with in-memory visits (current instance, not yet flushed)
      const merged = [...blobVisits, ...visitLog];
      // Deduplicate by ts + ip
      const seen = new Set();
      const deduped = merged.filter(v => {
        const key = v.ts + '|' + v.ip;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      // Filter by 72-hour retention
      const cutoff = Date.now() - VISIT_RETENTION_MS;
      const recent72h = deduped.filter(v => new Date(v.ts).getTime() > cutoff);
      // Filter out excluded IPs from the 72h detail view too — the
      // owner shouldn't see their own polling/heartbeats in this list.
      const filtered72h = EXCLUDED_IPS.size > 0
        ? recent72h.filter(v => !EXCLUDED_IPS.has(v.ip))
        : recent72h;
      // Sort newest first
      filtered72h.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
      return new Response(JSON.stringify({
        count: filtered72h.length,
        visits: filtered72h,
        retentionHours: 72,
        source: visitStore ? 'netlify:blobs (persistent)' : 'in-memory (per-instance)',
        cumulative: {
          totalVisits: cumulative.totalVisits || 0,
          distinctIPs: Object.keys(cumulative.ips || {}).length,
          distinctDevices: Object.keys(cumulative.devices || {}).length,
          // Return the full maps so the client can render an all-history table
          ipCounts: cumulative.ips || {},
          deviceCounts: cumulative.devices || {}
        },
        edge: context.geo?.country?.name || 'unknown',
        capturedAt: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });
    }

    // op=models → list Groq models (existing)
    if (op === 'models') {
      const GROQ_KEY = Deno.env.get('GROQ_API_KEY') || Deno.env.get('GROQ_KEY');
      if (!GROQ_KEY) {
        return new Response(
          JSON.stringify({ error: 'GROQ_API_KEY env var not set on the edge function' }),
          { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
        );
      }
      try {
        const res = await fetch('https://api.groq.com/openai/v1/models', {
          headers: { 'Authorization': 'Bearer ' + GROQ_KEY }
        });
        const body = await res.text();
        return new Response(body, {
          status: res.status,
          headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
        });
      } catch (e) {
        return new Response(
          JSON.stringify({ error: 'Failed to reach Groq', detail: e.message }),
          { status: 502, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
        );
      }
    }

    // Health check
    return new Response(JSON.stringify({ ok: true, service: 'groq-proxy', cache: 'memory' }), {
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // For POST requests, check GROQ_KEY
  const GROQ_KEY = Deno.env.get('GROQ_API_KEY') || Deno.env.get('GROQ_KEY');
  if (!GROQ_KEY) {
    return new Response(
      JSON.stringify({ error: 'GROQ_API_KEY env var not set on the edge function' }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
    );
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return new Response(JSON.stringify({ error: 'messages[] required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  const requestedModel = body.model || DEFAULT_MODEL;
  const isStreaming = body.stream ?? true;
  const maxTokens = body.max_tokens ?? 800;
  const isVerifyPing = maxTokens <= VERIFY_MAX_TOKENS;

  // ─── CACHE CHECK (skip for verify pings) ─────────────────────────────────
  if (!isVerifyPing) {
    const cacheKey = 'chat:' + await sha256(JSON.stringify({
      model: requestedModel,
      messages: body.messages,
      temperature: body.temperature ?? 0.3,
      max_tokens: maxTokens,
      stream: isStreaming
    }));
    const cached = memCache.get(cacheKey);
    if (cached && (Date.now() - cached.ts < CACHE_TTL_MS)) {
      // Cache hit! Stream the cached text back as simulated SSE
      if (isStreaming) {
        return new Response(simulatedSSEStream(cached.text, requestedModel), {
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Cache': 'HIT',
            ...corsHeaders(origin)
          }
        });
      }
      // Non-streaming cache hit
      const openaiResponse = {
        id: 'cache-' + cached.ts,
        object: 'chat.completion',
        created: Math.floor(cached.ts / 1000),
        model: requestedModel,
        choices: [{
          index: 0,
          message: { role: 'assistant', content: cached.text },
          finish_reason: 'stop'
        }],
        usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
      };
      return new Response(JSON.stringify(openaiResponse), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-Cache': 'HIT',
          ...corsHeaders(origin)
        }
      });
    }
  }

  // ─── CACHE MISS — call Groq ──────────────────────────────────────────────
  let groqRes;
  try {
    groqRes = await fetch(GROQ_URL, {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + GROQ_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: requestedModel,
        messages: body.messages,
        temperature: body.temperature ?? 0.3,
        max_tokens: maxTokens,
        stream: isStreaming
      })
    });
  } catch (e) {
    return new Response(
      JSON.stringify({ error: 'Failed to reach Groq', detail: e.message }),
      { status: 502, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
    );
  }

  if (!groqRes.ok) {
    const errBody = await groqRes.text();
    return new Response(errBody, {
      status: groqRes.status,
      headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
    });
  }

  // ─── STREAMING: stream to client AND collect for caching ────────────────
  if (isStreaming) {
    const groqReader = groqRes.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    const transformedStream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();
        try {
          while (true) {
            const { done, value } = await groqReader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            controller.enqueue(encoder.encode(chunk));
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith('data:')) continue;
              const data = trimmed.slice(5).trim();
              if (data === '[DONE]') continue;
              try {
                const evt = JSON.parse(data);
                const delta = evt.choices?.[0]?.delta?.content || '';
                if (delta) fullText += delta;
              } catch (_) {}
            }
          }
          if (buffer) controller.enqueue(encoder.encode(buffer));
        } finally {
          controller.close();
          // Store in memory cache for next time
          if (!isVerifyPing && fullText.length > 20) {
            const cacheKey = 'chat:' + await sha256(JSON.stringify({
              model: requestedModel,
              messages: body.messages,
              temperature: body.temperature ?? 0.3,
              max_tokens: maxTokens,
              stream: isStreaming
            }));
            memCache.set(cacheKey, { ts: Date.now(), text: fullText });
            // Garbage-collect old entries (keep cache under 100 entries)
            if (memCache.size > 100) {
              const oldest = [...memCache.entries()].sort((a, b) => a[1].ts - b[1].ts)[0];
              if (oldest) memCache.delete(oldest[0]);
            }
          }
        }
      }
    });

    return new Response(transformedStream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Cache': 'MISS',
        ...corsHeaders(origin)
      }
    });
  }

  // ─── NON-STREAMING: parse, cache, return ────────────────────────────────
  const groqJson = await groqRes.json();
  if (!isVerifyPing) {
    const text = groqJson.choices?.[0]?.message?.content || '';
    if (text.length > 20) {
      const cacheKey = 'chat:' + await sha256(JSON.stringify({
        model: requestedModel,
        messages: body.messages,
        temperature: body.temperature ?? 0.3,
        max_tokens: maxTokens,
        stream: isStreaming
      }));
      memCache.set(cacheKey, { ts: Date.now(), text });
      if (memCache.size > 100) {
        const oldest = [...memCache.entries()].sort((a, b) => a[1].ts - b[1].ts)[0];
        if (oldest) memCache.delete(oldest[0]);
      }
    }
  }
  return new Response(JSON.stringify(groqJson), {
    status: groqRes.status,
    headers: {
      'Content-Type': 'application/json',
      'X-Cache': 'MISS',
      ...corsHeaders(origin)
    }
  });
};

export const config = {
  path: '/groq-proxy'
};
