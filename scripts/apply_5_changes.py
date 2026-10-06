#!/usr/bin/env python3
"""
Apply 5 user-requested changes:
1. Add 'Generate executive summary' chip to each demo (always visible alongside
   Groq's suggested actions, triggers aiTask{type:'summary',length:'medium'})
2. (separate script for blog index re-order)
3. (separate edits for main page hero)
4. Footer tagline: 'Live truth on every desk, leadership included.' → 'Live truth on every desk.'
5. Hide force refresh button initially; show only when an SW update is pending
"""
import re

# ─── Change 1: Add 'Generate executive summary' chip to each demo ──────────
PATH_JS = '/home/z/insight-analytics/js/blog-pipeline-builder.js'
src = open(PATH_JS).read()

# Insert a hardcoded "Generate executive summary" chip BEFORE the Groq-generated
# chips. This chip uses a special data-pb-suggest="exec" attribute that the click
# handler recognizes as a built-in executive-summary action (not a Groq-suggested
# one indexed by number).
OLD_CHIPS_RENDER = """      var chips = (a.suggestedActions || []).map(function (s, i) {
        return '<button class="pb-chip" data-pb-suggest="' + i + '" type="button">' + esc(s) + '</button>';
      }).join('');"""

NEW_CHIPS_RENDER = """      // Built-in 'Generate executive summary' chip — always shown regardless of
      // what Groq suggests. Triggers aiTask{type:'summary', length:'medium'} on
      // the current document via a special 'exec' marker (the click handler
      // recognizes this and bypasses the Groq-indexed suggestion lookup).
      var execChip = '<button class="pb-chip pb-chip-exec" data-pb-suggest="exec" type="button">' +
        '<i class="fas fa-file-signature" style="font-size:0.78rem;margin-right:4px;"></i>Generate executive summary</button>';
      var chips = (a.suggestedActions || []).map(function (s, i) {
        return '<button class="pb-chip" data-pb-suggest="' + i + '" type="button">' + esc(s) + '</button>';
      }).join('');"""

assert OLD_CHIPS_RENDER in src, "chips render block not found"
src = src.replace(OLD_CHIPS_RENDER, NEW_CHIPS_RENDER, 1)

# Update the chips container to include the exec chip first
OLD_CHIPS_CONTAINER = "' + (chips ? '<div class=\"pb-analysis-section\"><p class=\"pb-analysis-label\">Suggested actions \\u2014 click to prefill</p><div class=\"pb-chips\">' + chips + '</div></div>' : '') + '\\"
NEW_CHIPS_CONTAINER = "' + (chips ? '<div class=\"pb-analysis-section\"><p class=\"pb-analysis-label\">Suggested actions \\u2014 click to prefill</p><div class=\"pb-chips\">' + execChip + chips + '</div></div>' : '') + '\\"
assert OLD_CHIPS_CONTAINER in src, "chips container not found"
src = src.replace(OLD_CHIPS_CONTAINER, NEW_CHIPS_CONTAINER, 1)

# Update the click handler to recognize 'exec' marker
OLD_CHIP_CLICK = """      var chip = t.closest('[data-pb-suggest]');
      if (chip && state.analysis) {
        var idx = parseInt(chip.getAttribute('data-pb-suggest'), 10);
        state.instruction = state.analysis.suggestedActions[idx] || '';"""

NEW_CHIP_CLICK = """      var chip = t.closest('[data-pb-suggest]');
      if (chip && state.analysis) {
        var marker = chip.getAttribute('data-pb-suggest');
        if (marker === 'exec') {
          // Built-in executive-summary chip — bypass the Groq suggestion index
          // and set a fixed instruction that Groq's spec generator will
          // recognize as a text task (returns aiTask{type:'summary', length:'medium'}).
          state.instruction = 'Generate an executive summary of this document';
        } else {
          var idx = parseInt(marker, 10);
          state.instruction = state.analysis.suggestedActions[idx] || '';
        }"""

assert OLD_CHIP_CLICK in src, "chip click handler not found"
src = src.replace(OLD_CHIP_CLICK, NEW_CHIP_CLICK, 1)

# Add CSS for .pb-chip-exec (slightly different styling — gradient bg to make
# it stand out as the primary action among the suggestions)
OLD_CHIP_CSS = ".pb-chip {"
NEW_CHIP_CSS = ".pb-chip-exec { background: linear-gradient(135deg, #4338ca, #0e7490); color: #fff; border-color: transparent; box-shadow: 0 4px 12px -4px rgba(67,56,202,0.45); }\\\n.pb-chip-exec:hover { transform: translateY(-1px); box-shadow: 0 6px 16px -6px rgba(67,56,202,0.6); }\\\n.pb-chip {"
assert OLD_CHIP_CSS in src, ".pb-chip CSS not found"
src = src.replace(OLD_CHIP_CSS, NEW_CHIP_CSS, 1)

open(PATH_JS, 'w').write(src)
print(f"  [1] 'Generate executive summary' chip added to /js/blog-pipeline-builder.js")

# ─── Change 4: Footer tagline simplify ───────────────────────────────────
# Main site index.html
PATH_IDX = '/home/z/insight-analytics/index.html'
idx = open(PATH_IDX).read()
OLD_TAGLINE = 'Insight Analytics · <em>Live truth on every desk, leadership included.</em>'
NEW_TAGLINE = 'Insight Analytics · <em>Live truth on every desk.</em>'
assert OLD_TAGLINE in idx, "footer tagline not found in index.html"
idx = idx.replace(OLD_TAGLINE, NEW_TAGLINE)
open(PATH_IDX, 'w').write(idx)
print(f"  [4] Footer tagline simplified in index.html")

# Blog posts (universal-dashboard-builder.html, database-archaeology.html, etc.)
import os
for fn in os.listdir('/home/z/insight-analytics/blog/'):
    if not fn.endswith('.html'): continue
    p = f'/home/z/insight-analytics/blog/{fn}'
    s = open(p).read()
    if OLD_TAGLINE in s:
        s = s.replace(OLD_TAGLINE, NEW_TAGLINE)
        open(p, 'w').write(s)
        print(f"  [4] Footer tagline simplified in blog/{fn}")

# ─── Change 5: Hide force refresh button initially; show only on update ───
# In index.html, the script currently calls setTimeout(addForceRefreshButton, 800).
# Replace with: only call from the updatefound → state=installed → hasController flow.
OLD_FORCE_REFRESH_AUTOADD = "        // Add the force-refresh button once the DOM is ready.\n        // Use a small delay so it doesn't compete with initial paint.\n        setTimeout(addForceRefreshButton, 800);"
NEW_FORCE_REFRESH_AUTOADD = "        // Force-refresh button is HIDDEN on initial load — only shown when an\n        // actual SW update is pending (updatefound + state=installed + hasController).\n        // Showing it always made it look like permanent UI for no reason.\n        // addForceRefreshButton() is now called from the updatefound handler\n        // inside showUpdateToast() (replaces the toast with the button so the\n        // user has a clear, persistent 'click to refresh' affordance)."
assert OLD_FORCE_REFRESH_AUTOADD in idx, "force refresh autoadd not found"
idx = idx.replace(OLD_FORCE_REFRESH_AUTOADD, NEW_FORCE_REFRESH_AUTOADD)

# Replace showUpdateToast() with a function that ALSO adds the force-refresh
# button (so the user gets a persistent button when there's an update, not
# just a transient toast that auto-dismisses after 15s)
OLD_TOAST_FN = """        function showUpdateToast() {
          if (document.getElementById('sw-update-toast')) return;
          var toast = document.createElement('div');
          toast.id = 'sw-update-toast';
          toast.style.cssText = [
            'position:fixed','bottom:24px','left:50%','transform:translateX(-50%)',
            'background:linear-gradient(135deg,#4338ca,#0e7490)','color:#fff',
            'padding:12px 20px','border-radius:12px','box-shadow:0 12px 32px -8px rgba(67,56,202,0.55)',
            'font-family:Inter,system-ui,sans-serif','font-size:14px','font-weight:600',
            'z-index:99999','cursor:pointer','display:flex','align-items:center','gap:10px',
            'max-width:calc(100vw - 32px)'
          ].join(';');
          toast.innerHTML = '<span>\\u2728 Site updated — tap to reload</span>';
          toast.onclick = function () {
            navigator.serviceWorker.getRegistration().then(function (reg) {
              if (reg && reg.waiting) {
                reg.waiting.postMessage('skipWaiting');
              } else {
                window.location.reload();
              }
            });
          };
          document.body.appendChild(toast);
          setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
          }, 15000);
        }"""

NEW_TOAST_FN = """        function showUpdateToast() {
          // When a new SW has installed (updatefound + state=installed + hasController),
          // show BOTH:
          //   1. A persistent 'Force refresh' button (bottom-right) — the user can
          //      click it any time to wipe caches + unregister SW + hard reload.
          //   2. A transient toast (bottom-center, 15s) — same action via click.
          // The button stays until the user clicks it or the page reloads.
          addForceRefreshButton();
          if (document.getElementById('sw-update-toast')) return;
          var toast = document.createElement('div');
          toast.id = 'sw-update-toast';
          toast.style.cssText = [
            'position:fixed','bottom:24px','left:50%','transform:translateX(-50%)',
            'background:linear-gradient(135deg,#4338ca,#0e7490)','color:#fff',
            'padding:12px 20px','border-radius:12px','box-shadow:0 12px 32px -8px rgba(67,56,202,0.55)',
            'font-family:Inter,system-ui,sans-serif','font-size:14px','font-weight:600',
            'z-index:99999','cursor:pointer','display:flex','align-items:center','gap:10px',
            'max-width:calc(100vw - 32px)'
          ].join(';');
          toast.innerHTML = '<span>\\u2728 Site updated \\u2014 tap to reload</span>';
          toast.onclick = function () {
            navigator.serviceWorker.getRegistration().then(function (reg) {
              if (reg && reg.waiting) {
                reg.waiting.postMessage('skipWaiting');
              } else {
                forceRefresh();
              }
            });
          };
          document.body.appendChild(toast);
          setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
          }, 15000);
        }"""
assert OLD_TOAST_FN in idx, "showUpdateToast not found in index.html"
idx = idx.replace(OLD_TOAST_FN, NEW_TOAST_FN)
open(PATH_IDX, 'w').write(idx)
print(f"  [5] Force refresh button hidden initially; shown only when SW update is pending")

print("\nDone.")
