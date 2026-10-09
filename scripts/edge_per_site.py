#!/usr/bin/env python3
"""
Separate visitor stats for main site vs dashboards site (currently combined).

Changes to the edge function (groq-proxy.js):

1. logVisit():
   - Read `site` query param (default 'main' for backward compat with
     pre-existing beacons that didn't send it)
   - Store `site` field in the visit log entry
   - Update cumulative.sites[site].{totalVisits, ips[ip], devices[device]}
     in addition to the existing combined counters

2. readCumulative():
   - One-time init: if cumulative.sites is missing, add the empty structure
     { main: {...}, dashboards: {...} }
   - Persist the new structure (existing combined counters stay untouched
     so the combined view keeps showing the all-time total)

3. op=stats (public):
   - Return per-site breakdown in addition to combined:
     {
       devices, ips, visits,  // combined (existing fields, unchanged)
       sites: {
         main: { devices, ips, visits },
         dashboards: { devices, ips, visits }
       }
     }

4. op=devices (admin):
   - Accept &site=main or &site=dashboards to filter
   - Default (no site param): combined view (existing behavior)

5. op=visits (admin):
   - Accept &site=main or &site=dashboards to filter 72h log
   - Default (no site param): all visits (existing behavior)
   - For visits with no `site` field (pre-existing log entries), bucket
     them as 'main' for backward compat — they'll age out within 72h
"""
import os

PATH = "/home/z/my-project/netlify/edge-functions/groq-proxy.js"
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ─── (1) logVisit: read site param + update per-site cumulative ──────────
OLD_LOG = """  var ua = headers.get('user-agent') || 'unknown';
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
  blobWritesPending++;"""

NEW_LOG = """  var ua = headers.get('user-agent') || 'unknown';
  var device = parseDeviceUA(ua);
  var country = geo.country?.name || geo.country || 'unknown';
  var city = geo.city?.name || geo.city || 'unknown';
  // Site: 'main' (insight-analytics.ca) or 'dashboards' (insightanalyticsca.github.io/dashboards).
  // Read from the ?site= query param; default 'main' for backward compat
  // with pre-existing beacons that didn't send it (those visits age out
  // within 72h, after which the per-site breakdown is fully accurate).
  var site = 'main';
  try { var _sp = new URL(request.url).searchParams; if (_sp.get('site')) site = _sp.get('site'); } catch(_) {}
  if (site !== 'main' && site !== 'dashboards') site = 'main';  // sanitize

  const visit = { ts: new Date().toISOString(), ip, country, city, page, method: request.method, ua, site };
  visitLog.push(visit);
  if (visitLog.length > MAX_VISITS) visitLog.shift();

  // Update cumulative stats (combined — existing behavior)
  cumulative.totalVisits++;
  cumulative.ips[ip] = (cumulative.ips[ip] || 0) + 1;
  cumulative.devices[device] = (cumulative.devices[device] || 0) + 1;
  // Also update per-site breakdown (new). Sites structure is lazily
  // initialized in readCumulative() — guard here in case the blob
  // hasn't loaded yet on a cold start.
  if (!cumulative.sites) cumulative.sites = { main: { totalVisits: 0, ips: {}, devices: {} }, dashboards: { totalVisits: 0, ips: {}, devices: {} } };
  if (!cumulative.sites[site]) cumulative.sites[site] = { totalVisits: 0, ips: {}, devices: {} };
  cumulative.sites[site].totalVisits++;
  cumulative.sites[site].ips[ip] = (cumulative.sites[site].ips[ip] || 0) + 1;
  cumulative.sites[site].devices[device] = (cumulative.sites[site].devices[device] || 0) + 1;
  blobWritesPending++;"""

if OLD_LOG in src:
    src = src.replace(OLD_LOG, NEW_LOG)
    print("OK: logVisit now reads site param + updates per-site cumulative")
else:
    print("WARN: logVisit pattern not found")

# ─── (2) readCumulative: init sites structure on cold start ──────────────
# Find the existing reconciliation block in readCumulative and add the
# sites init right after it.
OLD_RECON = """              if (corrected) {
                // Persist the corrected counts immediately so we don't
                // re-subtract on the next cold start (idempotent guard).
                blobWritesPending = 0;
                writeCumulative();
              }
            }
          }
        }
      }"""

NEW_RECON = """              if (corrected) {
                // Persist the corrected counts immediately so we don't
                // re-subtract on the next cold start (idempotent guard).
                blobWritesPending = 0;
                writeCumulative();
              }
            }
            // ─── Lazily init the per-site breakdown structure. The
            // combined counters (cumulative.totalVisits / ips / devices)
            // are preserved as-is — only the new `sites` sub-object is
            // added. New visits from this point onward are recorded in
            // BOTH the combined view AND the per-site breakdown. Old
            // visits (from before this deploy) only exist in the combined
            // view — they'll age out of the 72h visit log, but their
            // contribution to cumulative.totalVisits stays (it's the
            // all-time combined count, intentionally inclusive).
            if (!cumulative.sites) {
              cumulative.sites = {
                main: { totalVisits: 0, ips: {}, devices: {} },
                dashboards: { totalVisits: 0, ips: {}, devices: {} }
              };
              blobWritesPending = 0;
              writeCumulative();
            }
          }
        }
      }"""

if OLD_RECON in src:
    src = src.replace(OLD_RECON, NEW_RECON)
    print("OK: readCumulative now lazily inits cumulative.sites structure")
else:
    print("WARN: readCumulative reconciliation pattern not found")

# ─── (3) op=stats: return per-site breakdown ──────────────────────────────
OLD_STATS = """      return new Response(JSON.stringify({
        devices: Object.keys(cumulative.devices || {}).length,
        ips: Object.keys(cumulative.ips || {}).length,
        visits: cumulative.totalVisits || 0
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });"""

NEW_STATS = """      // Per-site breakdown (in addition to the combined view). The footer
      // pill on each site uses the combined `devices` count by default but
      // can switch to per-site via the activity panel's tab bar.
      var sites = cumulative.sites || {};
      var mainSite = sites.main || { totalVisits: 0, ips: {}, devices: {} };
      var dashSite = sites.dashboards || { totalVisits: 0, ips: {}, devices: {} };
      return new Response(JSON.stringify({
        devices: Object.keys(cumulative.devices || {}).length,
        ips: Object.keys(cumulative.ips || {}).length,
        visits: cumulative.totalVisits || 0,
        sites: {
          main: {
            devices: Object.keys(mainSite.devices || {}).length,
            ips: Object.keys(mainSite.ips || {}).length,
            visits: mainSite.totalVisits || 0
          },
          dashboards: {
            devices: Object.keys(dashSite.devices || {}).length,
            ips: Object.keys(dashSite.ips || {}).length,
            visits: dashSite.totalVisits || 0
          }
        }
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });"""

if OLD_STATS in src:
    src = src.replace(OLD_STATS, NEW_STATS)
    print("OK: op=stats now returns per-site breakdown")
else:
    print("WARN: op=stats pattern not found")

# ─── (4) op=devices: accept &site= filter ─────────────────────────────────
OLD_DEVICES = """    // op=devices — admin endpoint, returns full unique device + IP maps
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
          ip: ip.replace(/(\\d+\\.\\d+\\.\\d+)\\.\\d+/, '$1.xxx'),
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
    }"""

NEW_DEVICES = """    // op=devices — admin endpoint, returns full unique device + IP maps
    // across ALL history (not just 72h). Shows which specific devices/IPs
    // visited and how many times. Cumulative stats persist via Netlify Blobs.
    // Accepts optional &site=main or &site=dashboards to filter to one site
    // only (default: combined view across both sites).
    if (op === 'devices') {
      const pwd = url.searchParams.get('password') || url.searchParams.get('pwd') || '';
      if (pwd !== ADMIN_PASSWORD) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
        });
      }
      const siteFilter = url.searchParams.get('site');  // 'main' | 'dashboards' | null (combined)
      // Ensure cumulative is loaded from blob
      if (!blobLoaded) {
        await readCumulative();
      }
      // Write pending stats
      if (blobWritesPending > 0 && blobLoaded) {
        blobWritesPending = 0;
        writeCumulative();
      }
      // Pick the right stats bucket: combined (default) or per-site.
      var bucket = cumulative;
      var bucketLabel = 'combined';
      if (siteFilter === 'main' || siteFilter === 'dashboards') {
        var sites = cumulative.sites || {};
        bucket = sites[siteFilter] || { totalVisits: 0, ips: {}, devices: {} };
        bucketLabel = siteFilter;
      }
      // Build device list sorted by visit count descending
      const deviceList = Object.entries(bucket.devices || {})
        .map(([device, count]) => ({ device, visits: count }))
        .sort((a, b) => b.visits - a.visits);
      // Build IP list sorted by visit count (mask last octet for privacy).
      const ipList = Object.entries(bucket.ips || {})
        .filter(([ip]) => !EXCLUDED_IPS.has(ip))
        .map(([ip, count]) => ({
          ip: ip.replace(/(\\d+\\.\\d+\\.\\d+)\\.\\d+/, '$1.xxx'),
          visits: count
        }))
        .sort((a, b) => b.visits - a.visits);
      return new Response(JSON.stringify({
        site: bucketLabel,
        totalVisits: bucket.totalVisits || 0,
        distinctDevices: deviceList.length,
        distinctIPs: ipList.length,
        devices: deviceList,
        ips: ipList,
        capturedAt: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) }
      });
    }"""

if OLD_DEVICES in src:
    src = src.replace(OLD_DEVICES, NEW_DEVICES)
    print("OK: op=devices now accepts &site= filter")
else:
    print("WARN: op=devices pattern not found")

# ─── (5) op=visits: accept &site= filter for 72h log ──────────────────────
# Find the section that filters the 72h log and add a site filter.
OLD_VISITS_FILTER = """      // Filter by 72-hour retention
      const cutoff = Date.now() - VISIT_RETENTION_MS;
      const recent72h = deduped.filter(v => new Date(v.ts).getTime() > cutoff);
      // Filter out excluded IPs from the 72h detail view too — the
      // owner shouldn't see their own polling/heartbeats in this list.
      const filtered72h = EXCLUDED_IPS.size > 0
        ? recent72h.filter(v => !EXCLUDED_IPS.has(v.ip))
        : recent72h;"""

NEW_VISITS_FILTER = """      // Filter by 72-hour retention
      const cutoff = Date.now() - VISIT_RETENTION_MS;
      const recent72h = deduped.filter(v => new Date(v.ts).getTime() > cutoff);
      // Filter out excluded IPs from the 72h detail view too — the
      // owner shouldn't see their own polling/heartbeats in this list.
      const filtered72h = EXCLUDED_IPS.size > 0
        ? recent72h.filter(v => !EXCLUDED_IPS.has(v.ip))
        : recent72h;
      // Optional site filter: &site=main or &site=dashboards narrows the
      // 72h log to visits from that site only. Default (no param) returns
      // all visits (combined view). For visits logged before this deploy
      // (no `site` field), treat them as 'main' for backward compat — they
      // age out within 72h so the per-site breakdown becomes fully accurate.
      const siteFilter = url.searchParams.get('site');
      let filteredBySite = filtered72h;
      if (siteFilter === 'main' || siteFilter === 'dashboards') {
        filteredBySite = filtered72h.filter(function(v) {
          var s = v.site || 'main';  // backward compat: old visits → main
          return s === siteFilter;
        });
      }"""

if OLD_VISITS_FILTER in src:
    src = src.replace(OLD_VISITS_FILTER, NEW_VISITS_FILTER)
    print("OK: op=visits now accepts &site= filter for 72h log")
else:
    print("WARN: op=visits filter pattern not found")

# Now also need to make the rest of op=visits use `filteredBySite` instead
# of `filtered72h`. Find the sort + return statement.
OLD_VISITS_RETURN = """      // Sort newest first
      filtered72h.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
      return new Response(JSON.stringify({
        count: filtered72h.length,
        visits: filtered72h,"""

NEW_VISITS_RETURN = """      // Sort newest first
      filteredBySite.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
      // Site label for the response (so the UI can confirm which filter is active)
      const siteLabel = siteFilter || 'combined';
      return new Response(JSON.stringify({
        count: filteredBySite.length,
        visits: filteredBySite,
        site: siteLabel,"""

if OLD_VISITS_RETURN in src:
    src = src.replace(OLD_VISITS_RETURN, NEW_VISITS_RETURN)
    print("OK: op=visits return statement now uses filteredBySite + site label")
else:
    print("WARN: op=visits return pattern not found")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("\nAll edge function changes applied.")
