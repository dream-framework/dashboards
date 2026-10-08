#!/usr/bin/env python3
"""
Build the same live-visitor-feed toolkit on the MAIN site
(insight-analytics.ca) that's already on the dashboards site.

Toolkit pieces (mirroring the dashboards site):
  - Tiny footer pill showing cumulative device count
  - Hidden gear button (bottom-left, fixed) → password modal → full-screen
    activity panel with visit table + device breakdown
  - Beacon ping on page load → groq-proxy edge function
  - Stats fetch for the footer pill
  - Auto-polling when the panel is open (5s)

Stealth requirement (per user):
  When inspected in dev tools, the counter must NOT reveal its purpose.
  So all element IDs, variable names, function names, and visible labels
  use innocuous 'settings' / 'signal' / 'activity' framing — no
  'visitor', 'tracking', 'admin', 'stats' anywhere.

Files patched:
  /tmp/my-project/insight-analytics/index.html
  /tmp/my-project/insight-analytics/service-worker.js  (version bump)
"""
import re

IDX = "/tmp/my-project/insight-analytics/index.html"
with open(IDX, "r", encoding="utf-8") as f:
    src = f.read()

# ─── (1) Insert the footer signal pill into footer-bottom ────────────────
# Insert AFTER the opening <div class="footer-bottom"> tag, BEFORE the
# tagline span. Pill shows just a dot + number — no label, no tooltip.
FOOTER_OLD = '      <div class="footer-bottom">\n        <span class="footer-tagline">Insight Analytics · <em>Live truth on every desk.</em></span>'
FOOTER_NEW = (
    '      <div class="footer-bottom">\n'
    '        <span id="signalStrip" style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;border:1px solid rgba(99,102,241,0.20);background:rgba(99,102,241,0.06);font-size:11px;font-weight:700;color:var(--primary,#6366f1);margin-bottom:6px;" title="System status">\n'
    '          <span style="width:6px;height:6px;border-radius:50%;background:#10b981;box-shadow:0 0 6px #10b981;animation:cfgPulse 2s ease-in-out infinite;"></span>\n'
    '          <span id="signalValue">—</span>\n'
    '        </span>\n'
    '        <span class="footer-tagline">Insight Analytics · <em>Live truth on every desk.</em></span>'
)

if FOOTER_OLD in src:
    src = src.replace(FOOTER_OLD, FOOTER_NEW)
    print("OK: footer pill inserted")
else:
    print("WARN: footer pattern not found")

# ─── (2) Insert gear + modal + panel + script BEFORE </body> ─────────────
# Use innocuous names: cfgGear / cfgModal / cfgPanel / cfgTable / EP /
# parseClient / renderState / fetchState / startRefresh / stopRefresh.
# Visible labels: 'Settings', 'Activity', 'Enter access key'.

TOOLKIT_BLOCK = """<!-- ════════════════════════════════════════════════════════════════════════
     CONFIG BUTTON — access-key-protected settings panel
     ════════════════════════════════════════════════════════════════════════ -->
<button id="cfgGear" title="Settings" style="position:fixed;bottom:14px;left:14px;z-index:9996;width:24px;height:24px;border:0;border-radius:6px;background:transparent;color:var(--muted,#94a3b8);cursor:pointer;display:grid;place-items:center;opacity:0.3;transition:opacity 200ms;">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
</button>

<div id="cfgModal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);backdrop-filter:blur(8px);align-items:center;justify-content:center;">
  <div style="background:var(--bg,#fff);border:1px solid var(--card-border,rgba(0,0,0,0.1));border-radius:14px;padding:24px;width:320px;max-width:calc(100vw - 32px);box-shadow:0 24px 64px rgba(0,0,0,0.3);">
    <div style="font-size:14px;font-weight:700;margin-bottom:12px;color:var(--text,#0f172a);">⚙ Settings</div>
    <input id="cfgInput" type="password" placeholder="Enter access key" style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;font-size:13px;outline:none;margin-bottom:12px;background:var(--bg-soft,rgba(0,0,0,0.03));color:var(--text,#0f172a);">
    <div style="display:flex;gap:8px;">
      <button id="cfgSubmit" style="flex:1;padding:8px;border:0;border-radius:8px;background:linear-gradient(135deg,var(--primary,#6366f1),var(--accent,#06b6d4));color:#fff;font-size:12px;font-weight:600;cursor:pointer;">Enter</button>
      <button id="cfgCancel" style="padding:8px 14px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;background:transparent;color:var(--text-soft,#64748b);font-size:12px;cursor:pointer;">Cancel</button>
    </div>
    <div id="cfgError" style="color:var(--danger,#ef4444);font-size:11px;margin-top:8px;display:none;">Wrong access key</div>
  </div>
</div>

<div id="cfgPanel" style="display:none;position:fixed;inset:0;z-index:9999;background:var(--bg,#f8fafc);overflow-y:auto;">
  <div style="max-width:1100px;margin:0 auto;padding:20px;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981;animation:cfgPulse 2s ease-in-out infinite;"></span>
        <span style="font-size:16px;font-weight:700;color:var(--text,#0f172a);">Activity</span>
        <span id="cfgUpdated" style="font-size:10px;color:var(--muted,#94a3b8);"></span>
      </div>
      <button id="cfgClose" style="padding:6px 14px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;background:transparent;color:var(--text-soft,#64748b);font-size:12px;cursor:pointer;">✕ Close</button>
    </div>
    <style>@keyframes cfgPulse{0%,100%{opacity:0.7;transform:scale(1)}50%{opacity:1;transform:scale(1.3)}}</style>

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;">
      <div style="padding:16px 20px;border-radius:12px;border:1px solid rgba(99,102,241,0.15);background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(6,182,212,0.04));">
        <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted,#94a3b8);margin-bottom:4px;">Total</div>
        <div id="cfgTotal" style="font-size:28px;font-weight:800;color:var(--text,#0f172a);line-height:1;">—</div>
      </div>
      <div style="padding:16px 20px;border-radius:12px;border:1px solid rgba(16,185,129,0.15);background:linear-gradient(135deg,rgba(16,185,129,0.06),rgba(34,197,94,0.04));">
        <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted,#94a3b8);margin-bottom:4px;">Endpoints</div>
        <div id="cfgIPs" style="font-size:28px;font-weight:800;color:#10b981;line-height:1;">—</div>
      </div>
      <div style="padding:16px 20px;border-radius:12px;border:1px solid rgba(245,158,11,0.15);background:linear-gradient(135deg,rgba(245,158,11,0.06),rgba(239,68,68,0.04));">
        <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted,#94a3b8);margin-bottom:4px;">Clients</div>
        <div id="cfgDevices" style="font-size:28px;font-weight:800;color:#f59e0b;line-height:1;">—</div>
      </div>
    </div>

    <div id="cfgTable"></div>
    <div id="cfgHistory"></div>
    <div id="cfgError2" style="color:var(--danger,#ef4444);font-size:12px;display:none;"></div>
  </div>
</div>

<script>
// Lazy-load footer signal badge + settings panel.
// Uses innocuous identifiers — no reveal of purpose in dev tools.
(function() {
  var EP = 'https://startling-belekoy-b0ec70.netlify.app/groq-proxy';
  var ORIGIN = 'https://insight-analytics.ca';
  var REFRESH_MS = 5000;

  // Page-load signal ping
  new Image().src = EP + '?op=beacon&page=' + encodeURIComponent(window.location.pathname) + '&cb=' + Date.now();

  // Footer badge fetch
  fetch(EP + '?op=stats', { headers: { 'Origin': ORIGIN } })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var el = document.getElementById('signalValue');
      if (el) el.textContent = d.devices || 0;
    })
    .catch(function() {});

  function parseClient(ua) {
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

  function parseClientOS(ua) {
    if (!ua || ua === 'unknown') return 'unknown';
    if (ua.indexOf('iPhone') >= 0) return 'iPhone';
    if (ua.indexOf('iPad') >= 0) return 'iPad';
    if (ua.indexOf('Android') >= 0) return 'Android';
    if (ua.indexOf('Mac OS') >= 0 || ua.indexOf('Macintosh') >= 0) return 'macOS';
    if (ua.indexOf('Windows') >= 0) return 'Windows';
    if (ua.indexOf('Linux') >= 0) return 'Linux';
    return 'Other';
  }

  var gear = document.getElementById('cfgGear');
  var modal = document.getElementById('cfgModal');
  var input = document.getElementById('cfgInput');
  var submit = document.getElementById('cfgSubmit');
  var cancel = document.getElementById('cfgCancel');
  var error = document.getElementById('cfgError');
  var panel = document.getElementById('cfgPanel');
  var table = document.getElementById('cfgTable');
  var error2 = document.getElementById('cfgError2');
  var closeBtn = document.getElementById('cfgClose');
  var timer = null;
  var key = null;

  gear.addEventListener('mouseenter', function() { gear.style.opacity = '0.6'; });
  gear.addEventListener('mouseleave', function() { gear.style.opacity = '0.3'; });
  gear.addEventListener('click', function() {
    modal.style.display = 'flex';
    input.value = '';
    error.style.display = 'none';
    setTimeout(function() { input.focus(); }, 100);
  });

  function closeModal() { modal.style.display = 'none'; }
  cancel.addEventListener('click', closeModal);
  modal.addEventListener('click', function(e) { if (e.target === modal) closeModal(); });

  function fetchState() {
    var url = EP + '?op=visits&password=' + encodeURIComponent(key);
    fetch(url, { headers: { 'Origin': ORIGIN } })
      .then(function(r) { return r.status === 403 ? null : r.json(); })
      .then(function(data) {
        if (!data) { stopRefresh(); panel.style.display = 'none'; return; }
        renderState(data);
      })
      .catch(function() {});
    var devUrl = EP + '?op=devices&password=' + encodeURIComponent(key);
    fetch(devUrl, { headers: { 'Origin': ORIGIN } })
      .then(function(r) { return r.status === 403 ? null : r.json(); })
      .then(function(d) {
        if (d) renderAllHistory(d);
      })
      .catch(function() {});
  }

  function renderAllHistory(data) {
    var container = document.getElementById('cfgHistory');
    if (!container) return;
    var devices = data.devices || [];
    var ips = data.ips || [];
    var total = data.totalVisits || 0;
    if (devices.length === 0 && ips.length === 0) {
      container.innerHTML = '<div style="padding:12px;font-size:11px;color:var(--muted,#94a3b8);">No cumulative data yet.</div>';
      return;
    }
    var html = '<div style="margin-top:16px;padding:14px;border-radius:12px;border:1px solid var(--card-border,rgba(0,0,0,0.10));background:linear-gradient(135deg,rgba(99,102,241,0.04),rgba(6,182,212,0.03));">';
    html += '<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted,#94a3b8);margin-bottom:10px;">All-time (' + devices.length + ' types, ' + ips.length + ' endpoints, ' + total + ' total)</div>';
    html += '<table style="width:100%;border-collapse:collapse;font-size:11px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">';
    html += '<thead><tr style="border-bottom:1px solid rgba(0,0,0,0.06);color:var(--muted,#94a3b8);font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:0.03em;"><th style="padding:5px 8px;text-align:left;">Client</th><th style="padding:5px 8px;text-align:right;white-space:nowrap;">Count</th><th style="padding:5px 8px;text-align:right;white-space:nowrap;">% of total</th></tr></thead><tbody>';
    devices.forEach(function(d, i) {
      var bg = i % 2 === 0 ? 'transparent' : 'rgba(99,102,241,0.03)';
      var pct = total > 0 ? ((d.visits / total) * 100).toFixed(1) + '%' : '—';
      var bar = total > 0 ? Math.min(100, (d.visits / total) * 100) : 0;
      html += '<tr style="border-bottom:1px solid rgba(0,0,0,0.03);background:' + bg + ';"><td style="padding:5px 8px;color:var(--text,#0f172a);font-weight:500;">' + (d.device || 'Unknown') + '</td><td style="padding:5px 8px;text-align:right;font-weight:700;color:#f59e0b;white-space:nowrap;">' + d.visits + '</td><td style="padding:5px 8px;text-align:right;color:var(--text-soft,#475569);white-space:nowrap;">' + pct + ' <span style="display:inline-block;width:' + (bar * 0.6) + 'px;height:8px;border-radius:4px;background:linear-gradient(90deg,#6366f1,#06b6d4);vertical-align:middle;margin-left:2px;"></span></td></tr>';
    });
    html += '</tbody></table>';
    html += '<details style="margin-top:10px;"><summary style="cursor:pointer;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted,#94a3b8);padding:4px 0;">Endpoints (' + ips.length + ') — click to expand</summary><table style="width:100%;border-collapse:collapse;font-size:11px;font-family:monospace;margin-top:4px;"><thead><tr style="border-bottom:1px solid rgba(0,0,0,0.06);color:var(--muted,#94a3b8);font-weight:600;font-size:9px;text-transform:uppercase;"><th style="padding:5px 8px;text-align:left;">ID (masked)</th><th style="padding:5px 8px;text-align:right;">Count</th></tr></thead><tbody>';
    ips.forEach(function(ip, i) {
      var bg = i % 2 === 0 ? 'transparent' : 'rgba(99,102,241,0.03)';
      html += '<tr style="border-bottom:1px solid rgba(0,0,0,0.03);background:' + bg + ';"><td style="padding:5px 8px;color:var(--text-soft,#475569);">' + (ip.ip || '—') + '</td><td style="padding:5px 8px;text-align:right;font-weight:700;color:#f59e0b;">' + ip.visits + '</td></tr>';
    });
    html += '</tbody></table></details></div>';
    container.innerHTML = html;
  }

  function renderState(data) {
    var rows = data.visits.map(function(v) {
      return {
        ts: v.ts ? new Date(v.ts).getTime() : 0,
        tsLabel: v.ts ? new Date(v.ts).toLocaleTimeString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—',
        ip: v.ip || 'unknown',
        loc: (v.city && v.city !== 'unknown' ? v.city + ', ' : '') + (v.country || 'unknown'),
        page: v.page || '—',
        client: parseClient(v.ua),
        os: parseClientOS(v.ua)
      };
    });

    var SESSION_MS = 5 * 60 * 1000;
    var groups = {};
    rows.forEach(function(v) {
      var k = v.ip + '|' + v.client + '|' + v.page;
      if (!groups[k]) groups[k] = [];
      groups[k].push(v);
    });
    var sessions = [];
    Object.keys(groups).forEach(function(k) {
      var arr = groups[k].sort(function(a, b) { return b.ts - a.ts; });
      var cur = null;
      arr.forEach(function(v) {
        if (cur && (cur.ts - v.ts) <= SESSION_MS) {
          cur.reloads++;
          cur.lastTs = v.ts;
          cur.lastLabel = v.tsLabel;
        } else {
          if (cur) sessions.push(cur);
          cur = { ts: v.ts, tsLabel: v.tsLabel, ip: v.ip, loc: v.loc, page: v.page, client: v.client, reloads: 1, lastTs: v.ts, lastLabel: v.tsLabel };
        }
      });
      if (cur) sessions.push(cur);
    });
    sessions.sort(function(a, b) { return b.ts - a.ts; });

    var ipMap = {}, devMap = {};
    rows.forEach(function(v) {
      ipMap[v.ip] = (ipMap[v.ip] || 0) + 1;
      devMap[v.os] = (devMap[v.os] || 0) + 1;
    });

    var cum = data.cumulative || {};
    var recentIPs = Object.keys(ipMap).length;
    var recentDevs = Object.keys(devMap).length;
    var recentTotal = rows.length;
    document.getElementById('cfgTotal').textContent = recentTotal;
    document.getElementById('cfgIPs').textContent = recentIPs;
    document.getElementById('cfgDevices').textContent = recentDevs;
    document.getElementById('cfgUpdated').textContent = '· ' + new Date().toLocaleTimeString() + ' · all-time: ' + (cum.totalVisits || 0) + ' total, ' + (cum.distinctIPs || 0) + ' endpoints, ' + (cum.distinctDevices || 0) + ' clients';

    var breakdown = '<div style="margin-top:16px;padding:14px;border-radius:12px;border:1px solid var(--card-border,rgba(0,0,0,0.10));background:rgba(99,102,241,0.03);">';
    breakdown += '<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted,#94a3b8);margin-bottom:8px;">Recent (' + recentIPs + ' unique, last 72h)</div>';
    var all = data.visits || [];
    var ipOs = {};
    all.forEach(function(v) {
      var ip = v.ip || 'unknown';
      var os = parseClientOS(v.ua || '');
      var k = ip + '|' + os;
      if (!ipOs[k]) ipOs[k] = { ip: ip, os: os, count: 0, lastTs: '', country: v.country || '' };
      ipOs[k].count++;
      if (v.ts > ipOs[k].lastTs) { ipOs[k].lastTs = v.ts; ipOs[k].country = v.country || ''; }
    });
    Object.values(ipOs).sort(function(a, b) { return b.count - a.count; }).forEach(function(e) {
      var time = e.lastTs ? new Date(e.lastTs).toLocaleDateString(undefined, {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
      breakdown += '<div style="display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px solid rgba(0,0,0,0.03);line-height:1.4;font-size:11px;">';
      breakdown += '<span style="font-family:monospace;font-weight:600;color:var(--text,#0f172a);">' + e.ip + '</span>';
      breakdown += '<span style="color:var(--text-soft,#475569);">' + e.os + '</span>';
      breakdown += '<span style="font-weight:700;color:#f59e0b;">' + e.count + '×</span>';
      breakdown += '<span style="color:var(--text-soft,#475569);font-size:10px;white-space:nowrap;">' + (e.country || '?') + ' · ' + time + '</span>';
      breakdown += '</div>';
    });
    breakdown += '</div>';

    // All-time unique devices from cumulative blob
    var ipCounts = cum.ipCounts || {};
    var deviceCounts = cum.deviceCounts || {};
    var totalCum = cum.totalVisits || 0;
    breakdown += '<div style="margin-top:12px;padding:14px;border-radius:12px;border:1px solid var(--card-border,rgba(0,0,0,0.10));background:rgba(34,197,94,0.03);">';
    breakdown += '<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted,#94a3b8);margin-bottom:10px;">All-time unique — ' + Object.keys(deviceCounts).length + ' types · ' + Object.keys(ipCounts).length + ' endpoints · ' + totalCum + ' total</div>';
    breakdown += '<table style="border-collapse:collapse;font-size:11px;width:100%;font-family:-apple-system,sans-serif;">';
    breakdown += '<thead><tr style="background:rgba(34,197,94,0.06);color:var(--muted,#94a3b8);font-weight:700;text-transform:uppercase;letter-spacing:0.04em;font-size:9px;"><th style="padding:6px 10px;text-align:left;">Client</th><th style="padding:6px 10px;text-align:right;">Count</th><th style="padding:6px 10px;text-align:right;">%</th></tr></thead><tbody>';
    Object.entries(deviceCounts).sort(function(a, b) { return b[1] - a[1]; }).forEach(function(entry, i) {
      var dev = entry[0]; var cnt = entry[1];
      var pct = totalCum > 0 ? ((cnt / totalCum) * 100).toFixed(1) : '0.0';
      var bg = i % 2 === 0 ? 'transparent' : 'rgba(34,197,94,0.02)';
      breakdown += '<tr style="border-bottom:1px solid rgba(0,0,0,0.04);background:' + bg + ';"><td style="padding:5px 10px;color:var(--text,#0f172a);font-weight:500;">' + dev + '</td><td style="padding:5px 10px;text-align:right;font-weight:700;color:#16a34a;">' + cnt + '</td><td style="padding:5px 10px;text-align:right;color:var(--muted,#94a3b8);">' + pct + '%</td></tr>';
    });
    breakdown += '</tbody></table>';
    breakdown += '<div style="margin-top:12px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted,#94a3b8);margin-bottom:6px;">Top endpoints (all-time)</div>';
    breakdown += '<table style="border-collapse:collapse;font-size:10px;width:100%;font-family:monospace;">';
    Object.entries(ipCounts).sort(function(a, b) { return b[1] - a[1]; }).slice(0, 20).forEach(function(entry, i) {
      var ip = entry[0]; var cnt = entry[1];
      var bg = i % 2 === 0 ? 'transparent' : 'rgba(34,197,94,0.02)';
      breakdown += '<tr style="border-bottom:1px solid rgba(0,0,0,0.04);background:' + bg + ';"><td style="padding:3px 10px;color:var(--text,#0f172a);font-weight:600;">' + ip + '</td><td style="padding:3px 10px;text-align:right;color:#16a34a;font-weight:700;">' + cnt + '×</td></tr>';
    });
    breakdown += '</table></div>';

    var html = '<div style="overflow-x:auto;border:1px solid var(--card-border,rgba(0,0,0,0.12));border-radius:10px;"><table style="border-collapse:collapse;font-size:11px;width:100%;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">';
    html += '<thead><tr style="background:rgba(99,102,241,0.06);border-bottom:2px solid var(--card-border,rgba(0,0,0,0.12));color:var(--muted,#94a3b8);font-weight:700;text-transform:uppercase;letter-spacing:0.04em;font-size:9px;"><th style="padding:10px 14px;text-align:left;white-space:nowrap;">When</th><th style="padding:10px 14px;text-align:left;white-space:nowrap;">ID</th><th style="padding:10px 14px;text-align:left;white-space:nowrap;">From</th><th style="padding:10px 14px;text-align:left;white-space:nowrap;">Page</th><th style="padding:10px 14px;text-align:left;white-space:nowrap;">Client</th><th style="padding:10px 14px;text-align:center;white-space:nowrap;">Reloads</th></tr></thead><tbody>';
    sessions.forEach(function(s, i) {
      var bg = i % 2 === 0 ? 'transparent' : 'rgba(99,102,241,0.025)';
      html += '<tr style="border-bottom:1px solid rgba(0,0,0,0.04);background:' + bg + ';"><td style="padding:7px 14px;white-space:nowrap;color:var(--text,#0f172a);font-weight:600;">' + s.tsLabel + '</td><td style="padding:7px 14px;white-space:nowrap;font-family:monospace;color:var(--text-soft,#475569);">' + (s.ip || '—') + '</td><td style="padding:7px 14px;white-space:nowrap;color:var(--text-soft,#475569);">' + (s.loc || '—') + '</td><td style="padding:7px 14px;white-space:nowrap;color:var(--primary,#6366f1);font-weight:500;">' + (s.page || '—') + '</td><td style="padding:7px 14px;white-space:nowrap;color:var(--muted,#94a3b8);">' + s.client + '</td>';
      var rs = s.reloads > 1 ? 'color:#f59e0b;font-weight:700;background:rgba(245,158,11,0.08);border-radius:12px;padding:2px 8px;display:inline-block;' : 'color:var(--muted,#94a3b8);';
      var rt = s.reloads > 1 ? s.reloads + '×' : '1';
      html += '<td style="padding:7px 14px;text-align:center;white-space:nowrap;"><span style="' + rs + '">' + rt + '</span></td></tr>';
    });
    html += '</tbody></table></div>';
    html += breakdown;
    table.innerHTML = html;
    error2.style.display = 'none';
  }

  function startRefresh(k) {
    key = k;
    fetchState();
    timer = setInterval(fetchState, REFRESH_MS);
  }
  function stopRefresh() {
    if (timer) { clearInterval(timer); timer = null; }
    key = null;
  }

  submit.addEventListener('click', function() {
    var k = input.value;
    if (!k) { error.textContent = 'Enter access key'; error.style.display = 'block'; return; }
    var url = EP + '?op=visits&password=' + encodeURIComponent(k);
    fetch(url, { headers: { 'Origin': ORIGIN } })
      .then(function(r) {
        if (r.status === 403) { error.textContent = 'Wrong access key'; error.style.display = 'block'; return null; }
        return r.json();
      })
      .then(function(data) {
        if (!data) return;
        closeModal();
        panel.style.display = 'block';
        renderState(data);
        startRefresh(k);
      })
      .catch(function(e) {
        error.textContent = 'Error: ' + e.message;
        error.style.display = 'block';
      });
  });

  input.addEventListener('keydown', function(e) { if (e.key === 'Enter') submit.click(); });
  closeBtn.addEventListener('click', function() { panel.style.display = 'none'; stopRefresh(); });
})();
</script>

"""

# Insert the toolkit block right before </body>
if "</body>" in src:
    src = src.replace("</body>", TOOLKIT_BLOCK + "</body>", 1)
    print("OK: toolkit block inserted before </body>")
else:
    print("WARN: </body> not found")

with open(IDX, "w", encoding="utf-8") as f:
    f.write(src)

# ─── (3) Bump SW version + cache-bust ────────────────────────────────────
SW = "/tmp/my-project/insight-analytics/service-worker.js"
with open(SW, "r", encoding="utf-8") as f:
    sw = f.read()
sw_new = re.sub(
    r"const VERSION = 'v\d+\.\d+\.\d+-[^']+';",
    "const VERSION = 'v4.82.0-20261008-main-site-signal-toolkit';",
    sw, count=1,
)
sw_new = re.sub(r"\?v=\d+\.\d+\.\d+", "?v=4.82.0", sw_new)
if sw_new != sw:
    with open(SW, "w", encoding="utf-8") as f:
        f.write(sw_new)
    print("OK: SW VERSION → v4.82.0, all ?v= → 4.82.0")
