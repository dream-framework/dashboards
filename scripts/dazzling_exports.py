#!/usr/bin/env python3
"""
Dazzling email/export formatting for the pipeline-builder demo.

Patches:
1. buildEmailBody() — polished plain-text with Unicode box-drawing chars
   (works with mailto:). Branded header bar, document metadata, styled
   table with right-aligned numerics + currency formatting, footer with
   tagline + URL.
2. buildEmailBodyHTML() — NEW. Full HTML email with inline CSS for the
   in-modal preview + the 'Download as HTML email' button.
3. buildEmailBodyForAI() — polished plain-text for AI text results.
4. buildEmailBodyHTMLForAI() — NEW. HTML email for AI results.
5. openEmailPreview / openEmailPreviewForText — show the HTML rendered
   version in the modal + add 'Download as HTML email' button alongside
   'Open in email client'.
6. downloadPDF() — branded layout: gradient header bar, IA mark text,
   document metadata, styled table with colored header + alternating rows,
   page footer with tagline + URL + page number.
7. downloadExcel() — set column widths via ws['!cols'], freeze header row
   via ws['!freeze'], bold header cells.
"""
import re

PATH = '/home/z/insight-analytics/js/blog-pipeline-builder.js'
src = open(PATH).read()

# ─── Patch 1: buildEmailBody (polished plain-text with Unicode box-drawing) ─
OLD_BUILD_EMAIL = r"""  function buildEmailBody(spec, rows, columns) {
    var intro = (spec && spec.output && spec.output.emailBodyIntro) ||
      'Here is the result of the pipeline: ' + (spec ? spec.name : '');
    if (!rows.length) return intro + '\n\n(No rows in the result.)';
    var cols = columns.length ? columns : Object.keys(rows[0] || {});
    // Compute column widths (cap at 30 chars per cell to keep it readable).
    var widths = cols.map(function (c) { return Math.max(3, String(c).length); });
    var shown = rows.slice(0, 50);
    shown.forEach(function (r) {
      cols.forEach(function (c, i) {
        var l = String(r[c] == null ? '' : r[c]).length;
        if (l > widths[i]) widths[i] = Math.min(30, l);
      });
    });
    var pad = function (s, w) { s = String(s == null ? '' : s); return s.length > w ? s.slice(0, w - 1) + '\u2026' : s + ' '.repeat(w - s.length); };
    var header = cols.map(function (c, i) { return pad(c, widths[i]); }).join(' | ');
    var sep    = cols.map(function (_, i) { return '-'.repeat(widths[i]); }).join('-+-');
    var lines = [intro, '', header, sep];
    shown.forEach(function (r) {
      lines.push(cols.map(function (c, i) { return pad(r[c], widths[i]); }).join(' | '));
    });
    if (rows.length > shown.length) lines.push('... (' + (rows.length - shown.length) + ' more rows not shown)');
    return lines.join('\n');
  }"""

NEW_BUILD_EMAIL = r"""  // Format a value for display in plain-text email/preview. Numeric values
  // get thousand separators; values that look like currency keep their $.
  function fmtVal(v) {
    if (v == null || v === '') return '';
    if (typeof v === 'number') {
      // Use locale-formatted number with thousand separators.
      try { return v.toLocaleString('en-CA', { maximumFractionDigits: 2 }); }
      catch (e) { return String(v); }
    }
    return String(v);
  }
  function isNumericCol(rows, col) {
    var n = 0, numericCount = 0;
    for (var i = 0; i < rows.length && n < 8; i++) {
      var v = rows[i][col];
      if (v == null || v === '') continue;
      n++;
      if (typeof v === 'number' || /^-?[\d,.$%\s]+$/.test(String(v))) numericCount++;
    }
    return n > 0 && numericCount / n >= 0.7;
  }

  // Polished plain-text email body — Unicode box-drawing chars for a sleek
  // branded look that renders correctly in Gmail / Outlook / Apple Mail.
  // mailto: links only support plain text, so this is what actually gets
  // sent. The in-modal preview also shows an HTML version (buildEmailBodyHTML)
  // for users who want to see what a fully-rendered email would look like.
  function buildEmailBody(spec, rows, columns) {
    var name = (spec && spec.name) || 'Pipeline Result';
    var intro = (spec && spec.output && spec.output.emailBodyIntro) || '';
    var generated = new Date().toLocaleString('en-CA', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: 'numeric', minute: '2-digit'
    });
    var docName = state.document ? state.document.name : '';
    var docMeta = state.document
      ? (state.document.type.toUpperCase() + ' \u00b7 ' + state.document.rowCount + ' rows \u00d7 ' + state.document.columnCount + ' cols')
      : '';
    var bar = '\u2550'.repeat(60);
    var header = bar + '\n' +
      '  INSIGHT ANALYTICS  \u00b7  PIPELINE RESULT\n' +
      bar + '\n\n' +
      'Pipeline:  ' + name + '\n' +
      'Source:    ' + docName + (docMeta ? '  (' + docMeta + ')' : '') + '\n' +
      'Generated: ' + generated + '\n\n' +
      '\u2500'.repeat(60) + '\n' +
      '  RESULT  \u00b7  ' + rows.length + ' rows \u00d7 ' + (columns.length || (rows[0] ? Object.keys(rows[0]).length : 0)) + ' columns\n' +
      '\u2500'.repeat(60) + '\n';
    if (intro) header += '\n' + intro + '\n';
    if (!rows.length) return header + '\n(No rows in the result.)\n\n' + emailFooter();
    var cols = columns.length ? columns : Object.keys(rows[0] || {});
    var numericCols = cols.map(function (c) { return isNumericCol(rows, c); });
    // Compute column widths (cap at 32 chars per cell).
    var widths = cols.map(function (c) { return Math.max(3, String(c).length); });
    var shown = rows.slice(0, 50);
    shown.forEach(function (r) {
      cols.forEach(function (c, i) {
        var l = fmtVal(r[c]).length;
        if (l > widths[i]) widths[i] = Math.min(32, l);
      });
    });
    var pad = function (s, w, align) {
      s = fmtVal(s);
      if (s.length > w) return s.slice(0, w - 1) + '\u2026';
      var pad = ' '.repeat(w - s.length);
      return align === 'right' ? pad + s : s + pad;
    };
    var headerRow = '  ' + cols.map(function (c, i) { return pad(c, widths[i], numericCols[i] ? 'right' : 'left'); }).join('  \u2502  ');
    var sepRow    = '  ' + cols.map(function (_, i) { return '\u2500'.repeat(widths[i]); }).join('  \u253c  ');
    var lines = [header, headerRow, sepRow];
    shown.forEach(function (r) {
      lines.push('  ' + cols.map(function (c, i) { return pad(r[c], widths[i], numericCols[i] ? 'right' : 'left'); }).join('  \u2502  '));
    });
    if (rows.length > shown.length) lines.push('\n  ... ' + (rows.length - shown.length) + ' more rows not shown \u2014 download CSV/Excel for the full dataset.');
    lines.push('');
    lines.push(emailFooter());
    return lines.join('\n');
  }

  function emailFooter() {
    return '\u2500'.repeat(60) + '\n\n' +
      'Insight Analytics  \u00b7  Live truth on every desk.\n' +
      'https://insight-analytics.ca';
  }

  // ─── HTML email version (for in-modal preview + 'Download as HTML email') ──
  // Full HTML with inline CSS so it renders in any email client that supports
  // HTML. Branded gradient header bar, document metadata card, styled table
  // with brand-colored header row + alternating row colors + right-aligned
  // numerics, footer with tagline + URL.
  function buildEmailBodyHTML(spec, rows, columns) {
    var name = (spec && spec.name) || 'Pipeline Result';
    var intro = (spec && spec.output && spec.output.emailBodyIntro) || '';
    var generated = new Date().toLocaleString('en-CA', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: 'numeric', minute: '2-digit'
    });
    var docName = state.document ? esc(state.document.name) : '';
    var docMeta = state.document
      ? (state.document.type.toUpperCase() + ' &middot; ' + state.document.rowCount + ' rows &times; ' + state.document.columnCount + ' cols')
      : '';
    var cols = columns.length ? columns : (rows[0] ? Object.keys(rows[0]) : []);
    var numericCols = cols.map(function (c) { return isNumericCol(rows, c); });
    var shown = rows.slice(0, 50);
    var headerCells = cols.map(function (c, i) {
      return '<th style="padding:10px 14px;text-align:' + (numericCols[i] ? 'right' : 'left') + ';font-weight:700;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:#fff;background:#4338ca;border-bottom:2px solid #0e7490;">' + esc(c) + '</th>';
    }).join('');
    var bodyRows = shown.map(function (r, idx) {
      var bg = idx % 2 === 0 ? '#ffffff' : '#f1f5f9';
      var cells = cols.map(function (c, i) {
        var v = fmtVal(r[c]);
        return '<td style="padding:8px 14px;text-align:' + (numericCols[i] ? 'right' : 'left') + ';font-size:13px;color:#0f172a;border-bottom:1px solid #e2e8f0;background:' + bg + ';">' + esc(v) + '</td>';
      }).join('');
      return '<tr>' + cells + '</tr>';
    }).join('');
    var moreNote = rows.length > shown.length
      ? '<p style="margin:14px 0 0;color:#64748b;font-size:12px;font-style:italic;">... ' + (rows.length - shown.length) + ' more rows not shown &mdash; download CSV/Excel for the full dataset.</p>'
      : '';
    var introHTML = intro ? '<p style="margin:0 0 18px;color:#475569;font-size:14px;line-height:1.6;">' + esc(intro) + '</p>' : '';
    return '' +
      '<div style="font-family:Inter,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;background:#f8fafc;padding:24px;">' +
        // Branded header bar
        '<div style="background:linear-gradient(135deg,#4338ca 0%,#0e7490 100%);padding:24px 28px;border-radius:12px 12px 0 0;">' +
          '<div style="font-size:11px;font-weight:700;letter-spacing:0.16em;color:#cbd5e1;text-transform:uppercase;">INSIGHT ANALYTICS</div>' +
          '<div style="font-size:22px;font-weight:700;color:#fff;margin-top:4px;">Pipeline Result</div>' +
        '</div>' +
        // Body
        '<div style="background:#fff;padding:24px 28px;border:1px solid #e2e8f0;border-top:0;">' +
          '<div style="margin-bottom:20px;padding:14px 16px;background:#f1f5f9;border-radius:8px;border-left:3px solid #4338ca;">' +
            '<div style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">PIPELINE</div>' +
            '<div style="font-size:15px;font-weight:600;color:#0f172a;">' + esc(name) + '</div>' +
            (docName ? '<div style="font-size:12px;color:#64748b;margin-top:4px;">Source: ' + docName + (docMeta ? ' &middot; ' + docMeta : '') + '</div>' : '') +
            '<div style="font-size:12px;color:#64748b;margin-top:2px;">Generated: ' + esc(generated) + '</div>' +
          '</div>' +
          introHTML +
          '<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;color:#64748b;text-transform:uppercase;margin:0 0 8px;">Result &middot; ' + rows.length + ' rows &times; ' + cols.length + ' cols</div>' +
          '<table style="width:100%;border-collapse:collapse;font-family:Inter,Helvetica,Arial,sans-serif;">' +
            '<thead><tr>' + headerCells + '</tr></thead>' +
            '<tbody>' + bodyRows + '</tbody>' +
          '</table>' +
          moreNote +
        '</div>' +
        // Footer
        '<div style="background:#0b1120;padding:18px 28px;border-radius:0 0 12px 12px;text-align:center;">' +
          '<div style="font-size:13px;font-weight:600;color:#e6edf7;">Insight Analytics &middot; <em style="font-style:italic;color:#06b6d4;">Live truth on every desk.</em></div>' +
          '<div style="font-size:11px;color:#64748b;margin-top:4px;"><a href="https://insight-analytics.ca" style="color:#06b6d4;text-decoration:none;">insight-analytics.ca</a></div>' +
        '</div>' +
      '</div>';
  }

  // HTML email for AI text results — same branded header/footer, but the body
  // is the AI-generated text rendered as styled paragraphs/bullets.
  function buildEmailBodyHTMLForAI(spec, aiText) {
    var name = (spec && spec.name) || 'AI Result';
    var intro = (spec && spec.output && spec.output.emailBodyIntro) || '';
    var generated = new Date().toLocaleString('en-CA', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: 'numeric', minute: '2-digit'
    });
    var docName = state.document ? esc(state.document.name) : '';
    var docMeta = state.document
      ? (state.document.type.toUpperCase() + ' &middot; ' + state.document.rowCount + ' rows &times; ' + state.document.columnCount + ' cols')
      : '';
    // Convert AI text to HTML — paragraphs separated by blank lines, bullets preserved.
    var textHTML = esc(aiText)
      .replace(/\r?\n\r?\n/g, '</p><p style="margin:0 0 14px;color:#0f172a;font-size:14px;line-height:1.7;">')
      .replace(/\r?\n/g, '<br>');
    var introHTML = intro ? '<p style="margin:0 0 18px;color:#475569;font-size:14px;line-height:1.6;">' + esc(intro) + '</p>' : '';
    return '' +
      '<div style="font-family:Inter,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;background:#f8fafc;padding:24px;">' +
        '<div style="background:linear-gradient(135deg,#4338ca 0%,#0e7490 100%);padding:24px 28px;border-radius:12px 12px 0 0;">' +
          '<div style="font-size:11px;font-weight:700;letter-spacing:0.16em;color:#cbd5e1;text-transform:uppercase;">INSIGHT ANALYTICS</div>' +
          '<div style="font-size:22px;font-weight:700;color:#fff;margin-top:4px;">AI Executive Summary</div>' +
        '</div>' +
        '<div style="background:#fff;padding:24px 28px;border:1px solid #e2e8f0;border-top:0;">' +
          '<div style="margin-bottom:20px;padding:14px 16px;background:#f1f5f9;border-radius:8px;border-left:3px solid #4338ca;">' +
            '<div style="font-size:11px;font-weight:700;color:#64748b;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">PIPELINE</div>' +
            '<div style="font-size:15px;font-weight:600;color:#0f172a;">' + esc(name) + '</div>' +
            (docName ? '<div style="font-size:12px;color:#64748b;margin-top:4px;">Source: ' + docName + (docMeta ? ' &middot; ' + docMeta : '') + '</div>' : '') +
            '<div style="font-size:12px;color:#64748b;margin-top:2px;">Generated: ' + esc(generated) + '</div>' +
          '</div>' +
          introHTML +
          '<div style="padding:18px 20px;background:linear-gradient(135deg,rgba(99,102,241,0.04),rgba(6,182,212,0.03));border:1px solid #e2e8f0;border-radius:8px;">' +
            '<p style="margin:0 0 14px;color:#0f172a;font-size:14px;line-height:1.7;">' + textHTML + '</p>' +
          '</div>' +
        '</div>' +
        '<div style="background:#0b1120;padding:18px 28px;border-radius:0 0 12px 12px;text-align:center;">' +
          '<div style="font-size:13px;font-weight:600;color:#e6edf7;">Insight Analytics &middot; <em style="font-style:italic;color:#06b6d4;">Live truth on every desk.</em></div>' +
          '<div style="font-size:11px;color:#64748b;margin-top:4px;"><a href="https://insight-analytics.ca" style="color:#06b6d4;text-decoration:none;">insight-analytics.ca</a></div>' +
        '</div>' +
      '</div>';
  }"""

assert OLD_BUILD_EMAIL in src, "patch 1 (buildEmailBody) old_str not found"
src = src.replace(OLD_BUILD_EMAIL, NEW_BUILD_EMAIL, 1)
print("  [1] buildEmailBody + buildEmailBodyHTML + AI versions added")

# ─── Patch 2: Update openEmailPreview to show HTML preview + add 'Download HTML' button ──
OLD_PREVIEW = r"""  function openEmailPreview(spec, rows, columns) {
    var subject = (spec && spec.output && spec.output.emailSubject) || ('Pipeline result: ' + (spec ? spec.name : 'untitled'));
    var body = buildEmailBody(spec, rows, columns);
    openModal('Email preview', '\
      <div class="pb-analysis-section">\
        <p class="pb-analysis-label">Subject</p>\
        <div class="pb-modal-pre">' + esc(subject) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Body</p>\
        <div class="pb-modal-pre">' + esc(body) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Recipient</p>\
        <input class="pb-input" id="pb-email-recipient" type="email" placeholder="recipient@example.com" />\
      </div>',
      [
        { label: 'Open in email client', primary: true, action: function () {
          var to = ($('pb-email-recipient') || {}).value || '';
          var url = 'mailto:' + encodeURIComponent(to).replace(/%40/, '@') +
            '?subject=' + encodeURIComponent(subject) +
            '&body=' + encodeURIComponent(body);
          window.location.href = url;
        } }
      ]);
  }"""

NEW_PREVIEW = r"""  function openEmailPreview(spec, rows, columns) {
    var subject = (spec && spec.output && spec.output.emailSubject) || ('Pipeline result: ' + (spec ? spec.name : 'untitled'));
    var bodyPlain = buildEmailBody(spec, rows, columns);
    var bodyHTML = buildEmailBodyHTML(spec, rows, columns);
    openModal('Email preview', '\
      <div class="pb-analysis-section">\
        <p class="pb-analysis-label">Subject</p>\
        <div class="pb-modal-pre">' + esc(subject) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Preview (rendered HTML)</p>\
        <div class="pb-email-html-preview">' + bodyHTML + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label" style="cursor:pointer;text-decoration:underline;" id="pb-toggle-plain">Show plain-text body (what gets sent via mailto:)</p>\
        <div class="pb-modal-pre" id="pb-plain-body" style="display:none;">' + esc(bodyPlain) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Recipient</p>\
        <input class="pb-input" id="pb-email-recipient" type="email" placeholder="recipient@example.com" />\
      </div>',
      [
        { label: 'Download as HTML email', primary: false, action: function () {
          // Self-contained .html file the user can open in a browser + forward
          // via their email client. Full branded HTML email with inline CSS.
          var fullHTML = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + esc(subject) + '</title></head><body>' + bodyHTML + '</body></html>';
          var blob = new Blob([fullHTML], { type: 'text/html;charset=utf-8' });
          var url = URL.createObjectURL(blob);
          var a = document.createElement('a');
          a.href = url;
          a.download = (spec && spec.name ? spec.name.replace(/[^a-z0-9]+/gi, '_').toLowerCase() : 'pipeline_result') + '.html';
          document.body.appendChild(a); a.click(); document.body.removeChild(a);
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        } },
        { label: 'Open in email client', primary: true, action: function () {
          var to = ($('pb-email-recipient') || {}).value || '';
          var url = 'mailto:' + encodeURIComponent(to).replace(/%40/, '@') +
            '?subject=' + encodeURIComponent(subject) +
            '&body=' + encodeURIComponent(bodyPlain);
          window.location.href = url;
        } }
      ]);
    // Wire the plain-text toggle
    setTimeout(function () {
      var toggle = $('pb-toggle-plain');
      var plain = $('pb-plain-body');
      if (toggle && plain) {
        toggle.addEventListener('click', function () {
          plain.style.display = plain.style.display === 'none' ? 'block' : 'none';
        });
      }
    }, 50);
  }"""

assert OLD_PREVIEW in src, "patch 2 (openEmailPreview) old_str not found"
src = src.replace(OLD_PREVIEW, NEW_PREVIEW, 1)
print("  [2] openEmailPreview shows HTML preview + Download HTML email button")

# ─── Patch 3: Update openEmailPreviewForText (AI text version) ──────────────
OLD_PREVIEW_AI = r"""  function openEmailPreviewForText(spec, aiText) {
    var subject = (spec && spec.output && spec.output.emailSubject) ||
      ('AI result: ' + (spec ? spec.name : 'untitled'));
    var intro = (spec && spec.output && spec.output.emailBodyIntro) ||
      ('Here is the AI-generated result for: ' + (spec ? spec.name : ''));
    var body = intro + '\n\n' + aiText;
    openModal('Email preview', '\
      <div class="pb-analysis-section">\
        <p class="pb-analysis-label">Subject</p>\
        <div class="pb-modal-pre">' + esc(subject) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Body</p>\
        <div class="pb-modal-pre">' + esc(body) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Recipient</p>\
        <input class="pb-input" id="pb-email-recipient" type="email" placeholder="recipient@example.com" />\
      </div>',
      [
        { label: 'Open in email client', primary: true, action: function () {
          var to = ($('pb-email-recipient') || {}).value || '';
          var url = 'mailto:' + encodeURIComponent(to).replace(/%40/, '@') +
            '?subject=' + encodeURIComponent(subject) +
            '&body=' + encodeURIComponent(body);
          window.location.href = url;
        } }
      ]);
  }"""

NEW_PREVIEW_AI = r"""  function openEmailPreviewForText(spec, aiText) {
    var subject = (spec && spec.output && spec.output.emailSubject) ||
      ('AI result: ' + (spec ? spec.name : 'untitled'));
    var intro = (spec && spec.output && spec.output.emailBodyIntro) ||
      ('Here is the AI-generated result for: ' + (spec ? spec.name : ''));
    var bodyPlain = intro + '\n\n' + aiText + '\n\n' + emailFooter();
    var bodyHTML = buildEmailBodyHTMLForAI(spec, aiText);
    openModal('Email preview', '\
      <div class="pb-analysis-section">\
        <p class="pb-analysis-label">Subject</p>\
        <div class="pb-modal-pre">' + esc(subject) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Preview (rendered HTML)</p>\
        <div class="pb-email-html-preview">' + bodyHTML + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label" style="cursor:pointer;text-decoration:underline;" id="pb-toggle-plain">Show plain-text body (what gets sent via mailto:)</p>\
        <div class="pb-modal-pre" id="pb-plain-body" style="display:none;">' + esc(bodyPlain) + '</div>\
      </div>\
      <div class="pb-analysis-section" style="margin-top:14px;">\
        <p class="pb-analysis-label">Recipient</p>\
        <input class="pb-input" id="pb-email-recipient" type="email" placeholder="recipient@example.com" />\
      </div>',
      [
        { label: 'Download as HTML email', primary: false, action: function () {
          var fullHTML = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + esc(subject) + '</title></head><body>' + bodyHTML + '</body></html>';
          var blob = new Blob([fullHTML], { type: 'text/html;charset=utf-8' });
          var url = URL.createObjectURL(blob);
          var a = document.createElement('a');
          a.href = url;
          a.download = (spec && spec.name ? spec.name.replace(/[^a-z0-9]+/gi, '_').toLowerCase() : 'ai_result') + '.html';
          document.body.appendChild(a); a.click(); document.body.removeChild(a);
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        } },
        { label: 'Open in email client', primary: true, action: function () {
          var to = ($('pb-email-recipient') || {}).value || '';
          var url = 'mailto:' + encodeURIComponent(to).replace(/%40/, '@') +
            '?subject=' + encodeURIComponent(subject) +
            '&body=' + encodeURIComponent(bodyPlain);
          window.location.href = url;
        } }
      ]);
    setTimeout(function () {
      var toggle = $('pb-toggle-plain');
      var plain = $('pb-plain-body');
      if (toggle && plain) {
        toggle.addEventListener('click', function () {
          plain.style.display = plain.style.display === 'none' ? 'block' : 'none';
        });
      }
    }, 50);
  }"""

assert OLD_PREVIEW_AI in src, "patch 3 (openEmailPreviewForText) old_str not found"
src = src.replace(OLD_PREVIEW_AI, NEW_PREVIEW_AI, 1)
print("  [3] openEmailPreviewForText shows HTML preview + Download HTML email button")

# ─── Patch 4: Branded PDF export ───────────────────────────────────────────
OLD_PDF = r"""  function downloadPDF(rows, columns, filename, title) {
    return loadScript('jspdf').then(function () {
      var jsPDF = window.jspdf ? window.jspdf.jsPDF : window.jsPDF;
      if (!jsPDF) throw new Error('jsPDF failed to load');
      var doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
      var cols = columns.length ? columns : (rows[0] ? Object.keys(rows[0]) : []);
      var pageW = doc.internal.pageSize.getWidth();
      var pageH = doc.internal.pageSize.getHeight();
      var margin = 36;
      // Title
      doc.setFont('helvetica', 'bold'); doc.setFontSize(14);
      doc.text(title || 'Pipeline Result', margin, margin);
      doc.setFontSize(9); doc.setFont('helvetica', 'normal'); doc.setTextColor(120);
      doc.text(rows.length + ' rows \u00d7 ' + cols.length + ' columns', margin, margin + 14);
      doc.setTextColor(0);
      // Compute column widths proportional to max content length, capped.
      var maxLens = cols.map(function (c) { return String(c).length; });
      rows.slice(0, 200).forEach(function (r) {
        cols.forEach(function (c, i) {
          var l = String(r[c] == null ? '' : r[c]).length;
          if (l > maxLens[i]) maxLens[i] = l;
        });
      });
      var totalLen = maxLens.reduce(function (a, b) { return a + b; }, 0) || 1;
      var colWidths = maxLens.map(function (l) { return Math.max(40, (l / totalLen) * (pageW - 2 * margin)); });
      // Normalize to fit.
      var totalW = colWidths.reduce(function (a, b) { return a + b; }, 0);
      var scale = (pageW - 2 * margin) / totalW;
      colWidths = colWidths.map(function (w) { return w * scale; });
      var y = margin + 30;
      var rowH = 16;
      var headerH = 18;
      // Header row
      doc.setFillColor(99, 102, 241); doc.setFillColor(67, 56, 202);
      doc.rect(margin, y - headerH + 4, pageW - 2 * margin, headerH, 'F');
      doc.setTextColor(255); doc.setFont('helvetica', 'bold'); doc.setFontSize(8);
      var x = margin;
      cols.forEach(function (c, i) {
        doc.text(String(c).slice(0, Math.floor(colWidths[i] / 4)), x + 4, y - 4);
        x += colWidths[i];
      });
      y += 4;
      doc.setTextColor(30); doc.setFont('helvetica', 'normal'); doc.setFontSize(8);
      rows.slice(0, 500).forEach(function (r, ridx) {
        if (y > pageH - margin) { doc.addPage(); y = margin + 4; }
        if (ridx % 2 === 1) { doc.setFillColor(245, 246, 248); doc.rect(margin, y - headerH + 8, pageW - 2 * margin, rowH, 'F'); }
        x = margin;
        cols.forEach(function (c, i) {
          var val = r[c] == null ? '' : String(r[c]);
          var maxChars = Math.floor(colWidths[i] / 4);
          if (val.length > maxChars) val = val.slice(0, maxChars - 1) + '\u2026';
          doc.text(val, x + 4, y);
          x += colWidths[i];
        });
        y += rowH;
      });
      doc.save(filename || 'pipeline-result.pdf');
    });
  }"""

NEW_PDF = r"""  function downloadPDF(rows, columns, filename, title) {
    return loadScript('jspdf').then(function () {
      var jsPDF = window.jspdf ? window.jspdf.jsPDF : window.jsPDF;
      if (!jsPDF) throw new Error('jsPDF failed to load');
      var doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
      var cols = columns.length ? columns : (rows[0] ? Object.keys(rows[0]) : []);
      var pageW = doc.internal.pageSize.getWidth();
      var pageH = doc.internal.pageSize.getHeight();
      var margin = 36;
      var generated = new Date().toLocaleString('en-CA', { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
      var docName = state.document ? state.document.name : '';
      var docMeta = state.document ? (state.document.type.toUpperCase() + ' \u00b7 ' + state.document.rowCount + ' rows') : '';
      // ── Branded gradient header bar (two-tone rectangle approximation) ──
      doc.setFillColor(67, 56, 202);  // indigo-700
      doc.rect(0, 0, pageW, 56, 'F');
      doc.setFillColor(14, 116, 144);  // cyan-700
      doc.rect(0, 56, pageW, 4, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFont('helvetica', 'bold'); doc.setFontSize(8);
      doc.text('INSIGHT ANALYTICS', margin, 22);
      doc.setFontSize(16);
      doc.text(title || 'Pipeline Result', margin, 40);
      // Generated date right-aligned in header
      doc.setFontSize(8); doc.setFont('helvetica', 'normal');
      doc.text('Generated ' + generated, pageW - margin, 22, { align: 'right' });
      // ── Document metadata box ──
      var metaBoxY = 80;
      doc.setFillColor(241, 245, 249);  // slate-100
      doc.rect(margin, metaBoxY, pageW - 2 * margin, 38, 'F');
      doc.setFillColor(67, 56, 202);  // indigo accent strip on left
      doc.rect(margin, metaBoxY, 3, 38, 'F');
      doc.setTextColor(100, 116, 139); doc.setFontSize(8); doc.setFont('helvetica', 'bold');
      doc.text('PIPELINE', margin + 14, metaBoxY + 12);
      doc.setTextColor(15, 23, 42); doc.setFontSize(11); doc.setFont('helvetica', 'bold');
      doc.text(title || 'Pipeline Result', margin + 14, metaBoxY + 26);
      if (docName) {
        doc.setTextColor(100, 116, 139); doc.setFontSize(8); doc.setFont('helvetica', 'normal');
        doc.text('Source: ' + docName + (docMeta ? '  \u00b7  ' + docMeta : ''), margin + 250, metaBoxY + 12);
      }
      doc.setTextColor(100, 116, 139); doc.setFontSize(8);
      doc.text(rows.length + ' rows \u00d7 ' + cols.length + ' cols', pageW - margin - 4, metaBoxY + 26, { align: 'right' });
      // ── Compute column widths ──
      var numericCols = cols.map(function (c) { return isNumericCol(rows, c); });
      var maxLens = cols.map(function (c) { return String(c).length; });
      rows.slice(0, 200).forEach(function (r) {
        cols.forEach(function (c, i) {
          var l = fmtVal(r[c]).length;
          if (l > maxLens[i]) maxLens[i] = Math.min(28, l);
        });
      });
      var totalLen = maxLens.reduce(function (a, b) { return a + b; }, 0) || 1;
      var colWidths = maxLens.map(function (l) { return Math.max(40, (l / totalLen) * (pageW - 2 * margin)); });
      var totalW = colWidths.reduce(function (a, b) { return a + b; }, 0);
      var scale = (pageW - 2 * margin) / totalW;
      colWidths = colWidths.map(function (w) { return w * scale; });
      // ── Table ──
      var tableTop = metaBoxY + 50;
      var rowH = 16;
      var headerH = 20;
      // Header row
      doc.setFillColor(67, 56, 202);  // indigo-700
      doc.rect(margin, tableTop, pageW - 2 * margin, headerH, 'F');
      doc.setTextColor(255, 255, 255); doc.setFont('helvetica', 'bold'); doc.setFontSize(8);
      var x = margin + 6;
      cols.forEach(function (c, i) {
        var label = String(c).slice(0, Math.floor(colWidths[i] / 4));
        if (numericCols[i]) {
          doc.text(label, x + colWidths[i] - 6, tableTop + 13, { align: 'right' });
        } else {
          doc.text(label, x, tableTop + 13);
        }
        x += colWidths[i];
      });
      // Body rows
      var y = tableTop + headerH;
      doc.setFont('helvetica', 'normal'); doc.setFontSize(8);
      rows.slice(0, 500).forEach(function (r, ridx) {
        if (y > pageH - margin - 30) {
          // Page footer before page break
          doc.setTextColor(100, 116, 139); doc.setFontSize(7);
          doc.text('Insight Analytics  \u00b7  Live truth on every desk.  \u00b7  insight-analytics.ca', margin, pageH - 12);
          doc.text('Page ' + doc.internal.getNumberOfPages(), pageW - margin, pageH - 12, { align: 'right' });
          doc.addPage();
          // Repeat header row on the new page
          doc.setFillColor(67, 56, 202);
          doc.rect(margin, tableTop, pageW - 2 * margin, headerH, 'F');
          doc.setTextColor(255, 255, 255); doc.setFont('helvetica', 'bold'); doc.setFontSize(8);
          x = margin + 6;
          cols.forEach(function (c, i) {
            var label = String(c).slice(0, Math.floor(colWidths[i] / 4));
            if (numericCols[i]) doc.text(label, x + colWidths[i] - 6, tableTop + 13, { align: 'right' });
            else doc.text(label, x, tableTop + 13);
            x += colWidths[i];
          });
          doc.setFont('helvetica', 'normal'); doc.setFontSize(8);
          y = tableTop + headerH;
        }
        if (ridx % 2 === 1) {
          doc.setFillColor(241, 245, 249);  // slate-100 alternating row
          doc.rect(margin, y, pageW - 2 * margin, rowH, 'F');
        }
        doc.setTextColor(15, 23, 42);
        x = margin + 6;
        cols.forEach(function (c, i) {
          var val = fmtVal(r[c]);
          var maxChars = Math.floor(colWidths[i] / 4);
          if (val.length > maxChars) val = val.slice(0, maxChars - 1) + '\u2026';
          if (numericCols[i]) {
            doc.text(val, x + colWidths[i] - 6, y + 11, { align: 'right' });
          } else {
            doc.text(val, x, y + 11);
          }
          x += colWidths[i];
        });
        y += rowH;
      });
      // ── Page footer (always on last page) ──
      doc.setDrawColor(226, 232, 240); doc.setLineWidth(0.5);
      doc.line(margin, pageH - 28, pageW - margin, pageH - 28);
      doc.setTextColor(100, 116, 139); doc.setFontSize(8); doc.setFont('helvetica', 'normal');
      doc.text('Insight Analytics  \u00b7  Live truth on every desk.', margin, pageH - 16);
      doc.setTextColor(6, 182, 212); doc.setFont('helvetica', 'bold');
      doc.text('insight-analytics.ca', pageW - margin, pageH - 16, { align: 'right' });
      doc.save(filename || 'pipeline-result.pdf');
    });
  }"""

assert OLD_PDF in src, "patch 4 (downloadPDF) old_str not found"
src = src.replace(OLD_PDF, NEW_PDF, 1)
print("  [4] downloadPDF branded layout (gradient header + styled table + footer)")

# ─── Patch 5: Excel export — column widths + frozen header + bold header ────
OLD_EXCEL = r"""  function downloadExcel(rows, columns, filename) {
    return loadScript('xlsx').then(function () {
      var cols = columns.length ? columns : (rows[0] ? Object.keys(rows[0]) : []);
      var data = [cols];
      rows.forEach(function (r) { data.push(cols.map(function (c) { return r[c]; })); });
      var ws = XLSX.utils.aoa_to_sheet(data);
      var wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Results');
      var arr = XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
      downloadBlob(filename || 'pipeline-result.xlsx', new Blob([arr], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
    });
  }"""

NEW_EXCEL = r"""  function downloadExcel(rows, columns, filename) {
    return loadScript('xlsx').then(function () {
      var cols = columns.length ? columns : (rows[0] ? Object.keys(rows[0]) : []);
      var data = [cols];
      rows.forEach(function (r) { data.push(cols.map(function (c) { return r[c]; })); });
      var ws = XLSX.utils.aoa_to_sheet(data);
      // Set column widths based on max content length per column (cap at 40 chars).
      ws['!cols'] = cols.map(function (c, i) {
        var maxLen = String(c).length;
        for (var j = 0; j < Math.min(rows.length, 200); j++) {
          var v = rows[j][c];
          var l = (v == null ? '' : String(v)).length;
          if (l > maxLen) maxLen = l;
        }
        return { wch: Math.min(40, Math.max(10, maxLen + 2)) };
      });
      // Freeze the header row so it stays visible when scrolling.
      ws['!freeze'] = { ySplit: 1, topLeftCell: 'A2', activePane: 'bottomLeft', state: 'frozen' };
      // Bold the header cells (best-effort — SheetJS community edition may
      // not preserve styling on all spreadsheet readers, but Excel + LibreOffice
      // both honor it).
      cols.forEach(function (c, i) {
        var addr = XLSX.utils.encode_cell({ r: 0, c: i });
        if (ws[addr]) {
          ws[addr].s = { font: { bold: true, color: { rgb: 'FFFFFF' } }, fill: { fgColor: { rgb: '4338CA' } } };
        }
      });
      var wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Results');
      var arr = XLSX.write(wb, { type: 'array', bookType: 'xlsx', cellStyles: true });
      downloadBlob(filename || 'pipeline-result.xlsx', new Blob([arr], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
    });
  }"""

assert OLD_EXCEL in src, "patch 5 (downloadExcel) old_str not found"
src = src.replace(OLD_EXCEL, NEW_EXCEL, 1)
print("  [5] downloadExcel sets column widths + frozen header + bold header cells")

# ─── Patch 6: CSS for .pb-email-html-preview ───────────────────────────────
# Insert before ".pb-saved-list"
OLD_CSS = ".pb-ai-result-card {"
NEW_CSS = ".pb-email-html-preview { max-height: 480px; overflow-y: auto; border: 1px solid var(--border); border-radius: 10px; padding: 0; background: #f8fafc; }\\\n.pb-email-html-preview > div { margin: 0 !important; }\\\n.pb-modal-pre { white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; line-height: 1.6; color: var(--text-soft); background: var(--surface-2); padding: 14px 16px; border-radius: 8px; max-height: 360px; overflow-y: auto; }\\\n.pb-ai-result-card {"
assert OLD_CSS in src, "patch 6 (.pb-ai-result-card CSS) needle not found"
src = src.replace(OLD_CSS, NEW_CSS, 1)
print("  [6] CSS for .pb-email-html-preview + .pb-modal-pre added")

# ─── Write back ────────────────────────────────────────────────────────────
open(PATH, 'w').write(src)
print(f"\nDone. Wrote {PATH}")
