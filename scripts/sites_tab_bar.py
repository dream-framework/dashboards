#!/usr/bin/env python3
"""
Add a site-selector tab bar to both sites' activity panels + thread the
selected site through the fetch URLs.

UI: 3-tab bar at the top of the panel (below the header):
  [ Combined ] [ Main ] [ Dashboards ]
Active tab gets the gradient background; inactive tabs are subtle.
Default = Combined (preserves existing behavior).

JS state: `currentSite` ('combined' | 'main' | 'dashboards').
- fetchState / fetchVisits adds &site= to the URL when currentSite !== 'combined'
- Tab click handler updates currentSite, re-renders the active tab styling,
  and immediately re-fetches.

Files patched:
  /tmp/my-project/insight-analytics/index.html           (main site)
  /home/z/my-project/index.html                          (dashboards site)
"""
import os

# ─── MAIN SITE PATCH ──────────────────────────────────────────────────────
MAIN_PATH = "/tmp/my-project/insight-analytics/index.html"
with open(MAIN_PATH, "r", encoding="utf-8") as f:
    main_src = f.read()

# (1) Add the tab bar HTML right after the summary cards section in cfgPanel.
# Find the line that opens the summary cards grid and inject the tabs above it.
MAIN_OLD_HEADER = """    <style>@keyframes cfgPulse{0%,100%{opacity:0.7;transform:scale(1)}50%{opacity:1;transform:scale(1.3)}}</style>

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;">"""

MAIN_NEW_HEADER = """    <style>@keyframes cfgPulse{0%,100%{opacity:0.7;transform:scale(1)}50%{opacity:1;transform:scale(1.3)}}</style>

    <!-- Site selector tab bar — filter the activity panel by site -->
    <div id="cfgTabs" style="display:flex;gap:4px;margin-bottom:16px;border-bottom:1px solid var(--card-border,rgba(0,0,0,0.08));padding-bottom:8px;">
      <button data-site="combined" class="cfg-tab" style="padding:6px 14px;border:0;border-radius:8px;background:linear-gradient(135deg,var(--primary,#6366f1),var(--accent,#06b6d4));color:#fff;font-size:11px;font-weight:600;cursor:pointer;">Combined</button>
      <button data-site="main" class="cfg-tab" style="padding:6px 14px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;background:transparent;color:var(--text-soft,#64748b);font-size:11px;font-weight:600;cursor:pointer;">Main</button>
      <button data-site="dashboards" class="cfg-tab" style="padding:6px 14px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;background:transparent;color:var(--text-soft,#64748b);font-size:11px;font-weight:600;cursor:pointer;">Dashboards</button>
    </div>

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;">"""

if MAIN_OLD_HEADER in main_src:
    main_src = main_src.replace(MAIN_OLD_HEADER, MAIN_NEW_HEADER)
    print("OK: main site — tab bar inserted")
else:
    print("WARN: main site header pattern not found")

# (2) Add currentSite state var + tab click handler + thread &site= through
# the fetchState function. Find the existing var declarations block.
MAIN_OLD_VARS = "  var timer = null;\n  var key = null;"
MAIN_NEW_VARS = """  var timer = null;
  var key = null;
  var currentSite = 'combined';  // 'combined' | 'main' | 'dashboards'"""

if MAIN_OLD_VARS in main_src:
    main_src = main_src.replace(MAIN_OLD_VARS, MAIN_NEW_VARS)
    print("OK: main site — currentSite state var added")
else:
    print("WARN: main site vars pattern not found")

# (3) Modify fetchState() to add &site= when currentSite !== 'combined'
MAIN_OLD_FETCH = """  function fetchState() {
    var url = EP + '?op=visits&password=' + encodeURIComponent(key);
    fetch(url, { headers: { 'Origin': ORIGIN } })
      .then(function(r) { return r.status === 403 ? null : r.json(); })
      .then(function(data) {
        if (!data) { stopRefresh(); panel.style.display = 'none'; return; }
        renderState(data);
      })
      .catch(function() {});
    var devUrl = EP + '?op=devices&password=' + encodeURIComponent(key);"""

MAIN_NEW_FETCH = """  function fetchState() {
    var siteQs = currentSite !== 'combined' ? '&site=' + currentSite : '';
    var url = EP + '?op=visits&password=' + encodeURIComponent(key) + siteQs;
    fetch(url, { headers: { 'Origin': ORIGIN } })
      .then(function(r) { return r.status === 403 ? null : r.json(); })
      .then(function(data) {
        if (!data) { stopRefresh(); panel.style.display = 'none'; return; }
        renderState(data);
      })
      .catch(function() {});
    var devUrl = EP + '?op=devices&password=' + encodeURIComponent(key) + siteQs;"""

if MAIN_OLD_FETCH in main_src:
    main_src = main_src.replace(MAIN_OLD_FETCH, MAIN_NEW_FETCH)
    print("OK: main site — fetchState now threads &site= through both fetches")
else:
    print("WARN: main site fetchState pattern not found")

# (4) Add tab click handler — wire up after the close button listener.
# Find the closeBtn listener and add the tab handler right after it.
MAIN_OLD_CLOSE = "  closeBtn.addEventListener('click', function() { panel.style.display = 'none'; stopRefresh(); });\n})();"

MAIN_NEW_CLOSE = """  closeBtn.addEventListener('click', function() { panel.style.display = 'none'; stopRefresh(); });

  // ─── Site tab bar: switch the active site filter + immediately re-fetch ─
  function setActiveTab(site) {
    currentSite = site;
    var tabs = document.querySelectorAll('.cfg-tab');
    tabs.forEach(function(t) {
      var isActive = t.getAttribute('data-site') === site;
      t.style.background = isActive ? 'linear-gradient(135deg,var(--primary,#6366f1),var(--accent,#06b6d4))' : 'transparent';
      t.style.color = isActive ? '#fff' : 'var(--text-soft,#64748b)';
      t.style.border = isActive ? '0' : '1px solid var(--card-border,rgba(0,0,0,0.15))';
    });
    if (key) fetchState();  // immediate refresh with the new filter
  }
  var tabContainer = document.getElementById('cfgTabs');
  if (tabContainer) {
    tabContainer.addEventListener('click', function(e) {
      var t = e.target.closest('.cfg-tab');
      if (!t) return;
      setActiveTab(t.getAttribute('data-site'));
    });
  }
})();"""

if MAIN_OLD_CLOSE in main_src:
    main_src = main_src.replace(MAIN_OLD_CLOSE, MAIN_NEW_CLOSE)
    print("OK: main site — tab click handler wired up")
else:
    print("WARN: main site close-btn pattern not found")

with open(MAIN_PATH, "w", encoding="utf-8") as f:
    f.write(main_src)


# ─── DASHBOARDS SITE PATCH ────────────────────────────────────────────────
DASH_PATH = "/home/z/my-project/index.html"
with open(DASH_PATH, "r", encoding="utf-8") as f:
    dash_src = f.read()

# (1) Add the tab bar HTML in adminVisitPanel after the style block
DASH_OLD_HEADER = """    <style>@keyframes adminPulse{0%,100%{opacity:0.7;transform:scale(1)}50%{opacity:1;transform:scale(1.3)}}</style>

    <!-- Summary cards -->"""

DASH_NEW_HEADER = """    <style>@keyframes adminPulse{0%,100%{opacity:0.7;transform:scale(1)}50%{opacity:1;transform:scale(1.3)}}</style>

    <!-- Site selector tab bar — filter the activity panel by site -->
    <div id="adminTabs" style="display:flex;gap:4px;margin-bottom:16px;border-bottom:1px solid var(--card-border,rgba(0,0,0,0.08));padding-bottom:8px;">
      <button data-site="combined" class="admin-tab" style="padding:6px 14px;border:0;border-radius:8px;background:linear-gradient(135deg,var(--primary,#6366f1),var(--accent,#06b6d4));color:#fff;font-size:11px;font-weight:600;cursor:pointer;">Combined</button>
      <button data-site="main" class="admin-tab" style="padding:6px 14px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;background:transparent;color:var(--text-soft,#64748b);font-size:11px;font-weight:600;cursor:pointer;">Main</button>
      <button data-site="dashboards" class="admin-tab" style="padding:6px 14px;border:1px solid var(--card-border,rgba(0,0,0,0.15));border-radius:8px;background:transparent;color:var(--text-soft,#64748b);font-size:11px;font-weight:600;cursor:pointer;">Dashboards</button>
    </div>

    <!-- Summary cards -->"""

if DASH_OLD_HEADER in dash_src:
    dash_src = dash_src.replace(DASH_OLD_HEADER, DASH_NEW_HEADER)
    print("OK: dashboards site — tab bar inserted")
else:
    print("WARN: dashboards site header pattern not found")

# (2) Add currentSite state var
DASH_OLD_VARS = "  var pollTimer = null;\n  var adminPwd = null;"
DASH_NEW_VARS = """  var pollTimer = null;
  var adminPwd = null;
  var currentSite = 'combined';  // 'combined' | 'main' | 'dashboards'"""

if DASH_OLD_VARS in dash_src:
    dash_src = dash_src.replace(DASH_OLD_VARS, DASH_NEW_VARS)
    print("OK: dashboards site — currentSite state var added")
else:
    print("WARN: dashboards site vars pattern not found")

# (3) Modify fetchVisits() to thread &site= through both fetches
DASH_OLD_FETCH = """  function fetchVisits() {
    var url = PROXY + '?op=visits&password=' + encodeURIComponent(adminPwd);
    fetch(url, { headers: { 'Origin': 'https://insightanalyticsca.github.io' } })
      .then(function(r) { return r.status === 403 ? null : r.json(); })
      .then(function(data) {
        if (!data) { stopPolling(); visitPanel.style.display = 'none'; return; }
        renderVisits(data);
      })
      .catch(function() { /* silent retry on next poll */ });
    // Also fetch the full unique device/IP history from the NEW site
    // (which has the op=devices endpoint). The old site has 733 visits of
    // cumulative history but doesn't expose the detail endpoint.
    var devUrl = PROXY_DEVICES + '?op=devices&password=' + encodeURIComponent(adminPwd);"""

DASH_NEW_FETCH = """  function fetchVisits() {
    var siteQs = currentSite !== 'combined' ? '&site=' + currentSite : '';
    var url = PROXY + '?op=visits&password=' + encodeURIComponent(adminPwd) + siteQs;
    fetch(url, { headers: { 'Origin': 'https://insightanalyticsca.github.io' } })
      .then(function(r) { return r.status === 403 ? null : r.json(); })
      .then(function(data) {
        if (!data) { stopPolling(); visitPanel.style.display = 'none'; return; }
        renderVisits(data);
      })
      .catch(function() { /* silent retry on next poll */ });
    // Also fetch the full unique device/IP history, filtered by the same site
    var devUrl = PROXY_DEVICES + '?op=devices&password=' + encodeURIComponent(adminPwd) + siteQs;"""

if DASH_OLD_FETCH in dash_src:
    dash_src = dash_src.replace(DASH_OLD_FETCH, DASH_NEW_FETCH)
    print("OK: dashboards site — fetchVisits now threads &site= through both fetches")
else:
    print("WARN: dashboards site fetchVisits pattern not found")

# (4) Add tab click handler — wire up after the close button listener
DASH_OLD_CLOSE = """  pwdInput.addEventListener('keydown', function(e) { if (e.key === 'Enter') pwdSubmit.click(); });
  closeBtn.addEventListener('click', function() { visitPanel.style.display = 'none'; stopPolling(); });
})();"""

DASH_NEW_CLOSE = """  pwdInput.addEventListener('keydown', function(e) { if (e.key === 'Enter') pwdSubmit.click(); });
  closeBtn.addEventListener('click', function() { visitPanel.style.display = 'none'; stopPolling(); });

  // ─── Site tab bar: switch the active site filter + immediately re-fetch ─
  function setActiveTab(site) {
    currentSite = site;
    var tabs = document.querySelectorAll('.admin-tab');
    tabs.forEach(function(t) {
      var isActive = t.getAttribute('data-site') === site;
      t.style.background = isActive ? 'linear-gradient(135deg,var(--primary,#6366f1),var(--accent,#06b6d4))' : 'transparent';
      t.style.color = isActive ? '#fff' : 'var(--text-soft,#64748b)';
      t.style.border = isActive ? '0' : '1px solid var(--card-border,rgba(0,0,0,0.15))';
    });
    if (adminPwd) fetchVisits();  // immediate refresh with the new filter
  }
  var tabContainer = document.getElementById('adminTabs');
  if (tabContainer) {
    tabContainer.addEventListener('click', function(e) {
      var t = e.target.closest('.admin-tab');
      if (!t) return;
      setActiveTab(t.getAttribute('data-site'));
    });
  }
})();"""

if DASH_OLD_CLOSE in dash_src:
    dash_src = dash_src.replace(DASH_OLD_CLOSE, DASH_NEW_CLOSE)
    print("OK: dashboards site — tab click handler wired up")
else:
    print("WARN: dashboards site close-btn pattern not found")

with open(DASH_PATH, "w", encoding="utf-8") as f:
    f.write(dash_src)

print("\nBoth sites patched.")
