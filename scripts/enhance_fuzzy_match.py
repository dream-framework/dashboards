#!/usr/bin/env python3
"""
Enhance the fuzzy address matching demo:
1. Better address normalization — strip unit numbers, ordinals, directions, postal codes
2. Map modal — tiny icon next to each geocoded address opens OpenStreetMap embed
"""
import re

PATH = '/home/z/insight-analytics/js/blog-fuzzy-match.js'
src = open(PATH).read()

# ─── 1. Enhanced normalizeAddress ─────────────────────────────────────────
OLD_NORM = r"""  function normalizeAddress(addr) {
    if (!addr) return { base: '', unit: '' };
    var s = String(addr).toLowerCase().trim();
    // Replace punctuation with spaces (period, comma, hash).
    s = s.replace(/[.,#]/g, ' ');
    var tokens = s.split(/\s+/).filter(Boolean);
    // Expand common abbreviations — but only when the token is exactly the
    // abbreviation AND not followed by a number ("St 4" stays as "St").
    var expanded = tokens.map(function (tok, i) {
      var nextIsDigit = i + 1 < tokens.length && /^\d/.test(tokens[i + 1]);
      if (tok === 'st'  && !nextIsDigit) return 'street';
      if (tok === 'str')                 return 'street';
      if (tok === 'ave' || tok === 'av') return 'avenue';
      if (tok === 'rd')                  return 'road';
      if (tok === 'blvd'|| tok === 'blv')return 'boulevard';
      if (tok === 'dr')                  return 'drive';
      if (tok === 'ln')                  return 'lane';
      if (tok === 'ct')                  return 'court';
      if (tok === 'cir')                 return 'circle';
      if (tok === 'cres')                return 'crescent';
      if (tok === 'pl')                  return 'place';
      if (tok === 'apt')                 return 'apartment';
      if (tok === 'ste')                 return 'suite';
      if (tok === 'bldg')                return 'building';
      return tok;
    });
    // Split out unit suffixes — anything after "unit"/"apartment"/"suite"/
    // "building" goes into the unit field (kept for geocoding, not used in the
    // Jaro-Winkler comparison).
    var baseTokens = [];
    var unitTokens = [];
    var inUnit = false;
    for (var i = 0; i < expanded.length; i++) {
      var t = expanded[i];
      if (t === 'unit' || t === 'apartment' || t === 'suite' || t === 'building') {
        inUnit = true;
        continue;
      }
      if (inUnit) unitTokens.push(t);
      else baseTokens.push(t);
    }
    return {
      base: baseTokens.join(' ').replace(/\s+/g, ' ').trim(),
      unit: unitTokens.join(' ').replace(/\s+/g, ' ').trim()
    };
  }"""

NEW_NORM = r"""  function normalizeAddress(addr) {
    if (!addr) return { base: '', unit: '' };
    var s = String(addr).toLowerCase().trim();
    // Replace punctuation with spaces (period, comma, hash, parentheses).
    s = s.replace(/[.,#()]/g, ' ');
    // Strip Canadian postal codes (e.g., "m5h 2c2" or "M5H2C2")
    s = s.replace(/\b[a-z]\d[a-z]\s?\d[a-z]\d\b/g, ' ');
    // Strip US ZIP codes (e.g., "10001" or "10001-1234")
    s = s.replace(/\b\d{5}(-\d{4})?\b/g, ' ');
    // Strip ordinal suffixes: "1st" → "1", "2nd" → "2", "3rd" → "3", "4th" → "4"
    s = s.replace(/(\d+)(st|nd|rd|th)\b/g, '$1');
    // Expand cardinal direction abbreviations
    s = s.replace(/\bn\b(?=\s+\w)/g, 'north');
    s = s.replace(/\bs\b(?=\s+\w)/g, 'south');
    s = s.replace(/\be\b(?=\s+\w)/g, 'east');
    s = s.replace(/\bw\b(?=\s+\w)/g, 'west');
    s = s.replace(/\bnw\b/g, 'northwest');
    s = s.replace(/\bne\b/g, 'northeast');
    s = s.replace(/\bsw\b/g, 'southwest');
    s = s.replace(/\bse\b/g, 'southeast');
    var tokens = s.split(/\s+/).filter(Boolean);
    // Expand common abbreviations — but only when the token is exactly the
    // abbreviation AND not followed by a number ("St 4" stays as "St").
    var expanded = tokens.map(function (tok, i) {
      var nextIsDigit = i + 1 < tokens.length && /^\d/.test(tokens[i + 1]);
      if (tok === 'st'  && !nextIsDigit) return 'street';
      if (tok === 'str')                 return 'street';
      if (tok === 'ave' || tok === 'av') return 'avenue';
      if (tok === 'rd')                  return 'road';
      if (tok === 'blvd'|| tok === 'blv')return 'boulevard';
      if (tok === 'dr')                  return 'drive';
      if (tok === 'ln')                  return 'lane';
      if (tok === 'ct')                  return 'court';
      if (tok === 'cir')                 return 'circle';
      if (tok === 'cres')                return 'crescent';
      if (tok === 'pl')                  return 'place';
      if (tok === 'apt')                 return 'apartment';
      if (tok === 'ste')                 return 'suite';
      if (tok === 'bldg')                return 'building';
      if (tok === 'fl' || tok === 'flr') return 'floor';
      if (tok === 'dept')               return 'department';
      if (tok === 'hwy')                return 'highway';
      if (tok === 'ex' || tok === 'expy')return 'expressway';
      if (tok === 'pkwy')               return 'parkway';
      if (tok === 'ter' || tok === 'terr')return 'terrace';
      if (tok === 'sq')                 return 'square';
      if (tok === 'trl')                return 'trail';
      if (tok === 'wy')                 return 'way';
      return tok;
    });
    // Split out unit suffixes — anything after "unit"/"apartment"/"suite"/
    // "building"/"floor"/"department"/"dept" goes into the unit field (kept
    // for geocoding, NOT used in the Jaro-Winkler comparison — units are noisy
    // and the same physical address can have many different unit formats).
    // Also strip a leading "#" that was already converted to a space.
    var baseTokens = [];
    var unitTokens = [];
    var inUnit = false;
    for (var i = 0; i < expanded.length; i++) {
      var t = expanded[i];
      if (t === 'unit' || t === 'apartment' || t === 'suite' || t === 'building'
          || t === 'floor' || t === 'department') {
        inUnit = true;
        continue;
      }
      // Also treat a bare number after the street name (no unit prefix) as a
      // unit IF it appears after at least 3 tokens (e.g., "123 main street 4"
      // → base="123 main street", unit="4"). This catches "#4" → "4" cases
      // where the # was stripped to a space and the number is left dangling.
      if (inUnit) unitTokens.push(t);
      else baseTokens.push(t);
    }
    // If the last base token is a bare number AND we already have ≥3 base tokens,
    // it's likely a unit number that was written without a prefix (e.g., "123
    // main street 4" — the "4" is a unit). Move it to the unit field.
    if (baseTokens.length >= 3 && /^\d+$/.test(baseTokens[baseTokens.length - 1])
        && !inUnit) {
      unitTokens.unshift(baseTokens.pop());
    }
    return {
      base: baseTokens.join(' ').replace(/\s+/g, ' ').trim(),
      unit: unitTokens.join(' ').replace(/\s+/g, ' ').trim()
    };
  }"""

assert OLD_NORM in src, "normalizeAddress not found"
src = src.replace(OLD_NORM, NEW_NORM, 1)
print("  [1] Enhanced normalizeAddress: strip postal codes, ordinals, directions, more abbreviations, bare-number unit detection")

# ─── 2. Add map icon next to geocoded addresses + map modal ───────────────
# Modify the geocoding results table to add a map icon next to the matched address
OLD_GEO_ROW = r"""        return '<tr>' +
          '<td style="max-width:200px;white-space:normal;">' + esc(gc.originalAddress) + '</td>' +
          '<td style="max-width:280px;white-space:normal;">' + (gc.ok ? esc(gc.matchedAddress) : '<span style="color:var(--text-soft);font-style:italic;">' + esc(gc.error || '') + '</span>') + '</td>' +
          '<td class="fm-coords">' + latlon + '</td>' +
          '<td class="num">' + (gc.ok ? fmtNumber(gc.importance) : '\u2014') + '</td>' +
          '<td>' + statusPill + '</td>' +
        '</tr>';"""

NEW_GEO_ROW = r"""        var mapIcon = gc.ok
          ? ' <button class="fm-map-btn" data-fm-map="' + idx + '" type="button" title="View on map" aria-label="View on map"><i class="fas fa-map-pin"></i></button>'
          : '';
        return '<tr>' +
          '<td style="max-width:200px;white-space:normal;">' + esc(gc.originalAddress) + '</td>' +
          '<td style="max-width:280px;white-space:normal;">' + (gc.ok ? esc(gc.matchedAddress) + mapIcon : '<span style="color:var(--text-soft);font-style:italic;">' + esc(gc.error || '') + '</span>') + '</td>' +
          '<td class="fm-coords">' + latlon + '</td>' +
          '<td class="num">' + (gc.ok ? fmtNumber(gc.importance) : '\u2014') + '</td>' +
          '<td>' + statusPill + '</td>' +
        '</tr>';"""

# The old code uses `var geoRows = state.geocodes.map(function (gc) {` — need to
# change to include `idx` parameter for the map button's data attribute
OLD_MAP_FUNC = r"""      var geoRows = state.geocodes.map(function (gc) {
        var a = gc.address || {};
        var latlon = gc.ok ? esc(gc.lat) + ', ' + esc(gc.lon) : '\u2014';
        var statusPill = gc.ok
          ? '<span class="fm-status-pill matched">OK</span>'
          : '<span class="fm-status-pill unmatched">Failed</span>';
        return '<tr>' +"""

NEW_MAP_FUNC = r"""      var geoRows = state.geocodes.map(function (gc, idx) {
        var a = gc.address || {};
        var latlon = gc.ok ? esc(gc.lat) + ', ' + esc(gc.lon) : '\u2014';
        var statusPill = gc.ok
          ? '<span class="fm-status-pill matched">OK</span>'
          : '<span class="fm-status-pill unmatched">Failed</span>';
        var mapIcon = gc.ok
          ? ' <button class="fm-map-btn" data-fm-map="' + idx + '" type="button" title="View on map" aria-label="View on map"><i class="fas fa-map-pin"></i></button>'
          : '';
        return '<tr>' +
          '<td style="max-width:200px;white-space:normal;">' + esc(gc.originalAddress) + '</td>' +
          '<td style="max-width:280px;white-space:normal;">' + (gc.ok ? esc(gc.matchedAddress) + mapIcon : '<span style="color:var(--text-soft);font-style:italic;">' + esc(gc.error || '') + '</span>') + '</td>' +
          '<td class="fm-coords">' + latlon + '</td>' +
          '<td class="num">' + (gc.ok ? fmtNumber(gc.importance) : '\u2014') + '</td>' +
          '<td>' + statusPill + '</td>' +
        '</tr>';"""

assert OLD_MAP_FUNC in src, "geocoding map function not found"
src = src.replace(OLD_MAP_FUNC, NEW_MAP_FUNC, 1)
print("  [2] Added map icon next to each geocoded address")

# ─── 3. Add click handler for map button + map modal ─────────────────────
# Find the event delegation section and add the map button handler
OLD_CLICK_HANDLER = r"""      if (t.closest('#fm-generate-brief')) { onGenerateBriefClick(); return; }"""

NEW_CLICK_HANDLER = r"""      if (t.closest('#fm-generate-brief')) { onGenerateBriefClick(); return; }
      // Map pin button — opens an OpenStreetMap embed in a modal
      var mapBtn = t.closest('[data-fm-map]');
      if (mapBtn) {
        var geoIdx = parseInt(mapBtn.getAttribute('data-fm-map'), 10);
        var gc = state.geocodes[geoIdx];
        if (gc && gc.ok && gc.lat && gc.lon) {
          var lat = gc.lat, lon = gc.lon;
          var delta = 0.005;
          var bbox = (parseFloat(lon) - delta) + ',' + (parseFloat(lat) - delta) + ',' + (parseFloat(lon) + delta) + ',' + (parseFloat(lat) + delta);
          var mapSrc = 'https://www.openstreetmap.org/export/embed.html?bbox=' + bbox + '&layer=mapnik&marker=' + lat + ',' + lon;
          openModal('Location: ' + (gc.matchedAddress || '').slice(0, 60) + (gc.matchedAddress.length > 60 ? '\u2026' : ''),
            '<div style="margin-bottom:10px;color:var(--text-muted);font-size:0.88rem;line-height:1.6;">' +
              '<strong style="color:var(--text);">Real address:</strong> ' + esc(gc.matchedAddress) + '<br>' +
              '<strong style="color:var(--text);">Original:</strong> ' + esc(gc.originalAddress) + '<br>' +
              '<strong style="color:var(--text);">Coordinates:</strong> ' + esc(lat) + ', ' + esc(lon) + ' · <strong style="color:var(--text);">Importance:</strong> ' + fmtNumber(gc.importance) +
            '</div>' +
            '<iframe src="' + mapSrc + '" style="width:100%;height:400px;border:0;border-radius:10px;" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>',
            [{ label: 'Close', primary: true, action: function () { closeModal(); } }]);
        }
        return;
      }"""

assert OLD_CLICK_HANDLER in src, "click handler not found"
src = src.replace(OLD_CLICK_HANDLER, NEW_CLICK_HANDLER, 1)
print("  [3] Added map modal click handler (OpenStreetMap embed iframe)")

# ─── 4. Add CSS for .fm-map-btn ──────────────────────────────────────────
OLD_CSS_MARKER = ".fm-status-pill.matched {"
NEW_CSS = """.fm-map-btn { display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--accent);cursor:pointer;font-size:0.7rem;padding:0;margin:0 0 0 4px;vertical-align:middle;transition:all 180ms ease; }
.fm-map-btn:hover { background:var(--accent);color:#fff;border-color:var(--accent);transform:scale(1.1); }
[data-theme="dark"] .fm-map-btn { background:rgba(255,255,255,0.06);color:var(--accent); }
[data-theme="dark"] .fm-map-btn:hover { background:var(--accent);color:#fff; }
.fm-status-pill.matched {"""

assert OLD_CSS_MARKER in src, "fm-status-pill CSS marker not found"
src = src.replace(OLD_CSS_MARKER, NEW_CSS, 1)
print("  [4] Added CSS for .fm-map-btn")

# ─── Write back ────────────────────────────────────────────────────────────
open(PATH, 'w').write(src)
print(f"\nDone. Wrote {PATH}")
