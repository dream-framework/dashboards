#!/usr/bin/env python3
"""
Add text-task support (summary / bullet_points / Q&A) to the pipeline-builder demo.
v2 — uses raw strings + simpler concatenation to avoid triple-quote issues.
"""
import re

PATH = '/home/z/insight-analytics/js/blog-pipeline-builder.js'
src = open(PATH).read()

# ─── Patch 1: analyzeDocument prompt ───────────────────────────────────────
OLD_1 = r"""      '  "suggestedActions": [\n' +
      '    "3-5 natural-language suggested actions, each a one-sentence instruction like \'Summarize total revenue by region\'",\n' +
      '    "Make them specific to this data, not generic",\n' +
      '    "Vary the difficulty — easy (sort), medium (summarize), advanced (filter+summarize)"\n' +
      '  ],\n' +"""

NEW_1 = r"""      '  "suggestedActions": [\n' +
      '    "4-6 natural-language suggested actions, each a one-sentence instruction",\n' +
      '    "Include a MIX of: tabular tasks (e.g. \'Summarize total revenue by region\', \'Top 5 products by qty\', \'Filter to Ontario and sort by revenue desc\') AND text tasks (e.g. \'Summarize this document in plain English\', \'What are the main points?\', \'Ask a question about this report\')",\n' +
      '    "For text-heavy documents (PDF/Word with little tabular data), lean toward text tasks",\n' +
      '    "For row-based documents (Excel/CSV with many rows), lean toward tabular tasks but include at least one text task",\n' +
      '    "Make them specific to this data, not generic"\n' +
      '  ],\n' +"""

assert OLD_1 in src, "patch 1 (analyzeDocument prompt) old_str not found"
src = src.replace(OLD_1, NEW_1, 1)
print("  [1] analyzeDocument prompt updated")

# ─── Patch 2: generatePipelineSpec prompt tail ──────────────────────────────
OLD_2 = r"""      '  "output": { "format": "html_table"|"csv"|"excel"|"pdf", "emailSubject": "subject line", "emailBodyIntro": "one-sentence intro" }\n' +
      '}';"""

NEW_2 = r"""      '  "output": { "format": "html_table"|"csv"|"excel"|"pdf"|"html_text", "emailSubject": "subject line", "emailBodyIntro": "one-sentence intro" }\n' +
      '}\n\n' +
      'CRITICAL DISPATCH RULE:\n' +
      '  - If the instruction is a TABULAR operation (filter, summarize, aggregate, sort, count, group, top N, etc.) -> return spec with "steps[]"\n' +
      '  - If the instruction is a TEXT TASK (summarize the document, main points, key takeaways, what does this report say, ask a question, explain, describe) -> return spec with "aiTask{}" instead of "steps[]"\n' +
      '  - DO NOT include both. Pick one based on the instruction wording.\n\n' +
      'aiTask shape (only when the instruction is a text task):\n' +
      '  "aiTask": {\n' +
      '    "type": "summary" | "bullet_points" | "qa",\n' +
      '    "question": "...",          // ONLY for type="qa" — restate the user\'s question\n' +
      '    "length": "short" | "medium" | "long",   // optional, only for type="summary"\n' +
      '    "count": 5                  // optional, only for type="bullet_points" — how many points to extract\n' +
      '  }\n' +
      '  output.format for aiTask = "html_text"\n' +
      '  Leave "steps" OUT of the JSON entirely when aiTask is present.';"""

assert OLD_2 in src, "patch 2 (spec prompt tail) old_str not found"
src = src.replace(OLD_2, NEW_2, 1)
print("  [2] generatePipelineSpec prompt tail updated (added aiTask branch)")

# ─── Patch 3: spec validation ──────────────────────────────────────────────
OLD_3 = r"""    ).then(function (content) {
      var spec = extractJson(content);
      if (!spec.steps || !Array.isArray(spec.steps) || !spec.steps.length) {
        throw new Error('The AI didn\u2019t produce any pipeline steps. Try rephrasing your instruction.');
      }
      // Light validation — strip obviously bad step types so the executor doesn't choke.
      spec.steps = spec.steps.filter(function (s) { return s && typeof s.type === 'string'; });
      if (!spec.steps.length) {
        throw new Error('The AI returned an unexpected response. Try rephrasing your instruction.');
      }
      if (!spec.output || typeof spec.output !== 'object') spec.output = { format: 'html_table' };
      return spec;
    });"""

NEW_3 = r"""    ).then(function (content) {
      var spec = extractJson(content);
      // Accept EITHER steps[] (tabular) OR aiTask{} (text task).
      // Groq decides which path based on the instruction wording.
      var hasAiTask = spec.aiTask && typeof spec.aiTask === 'object' && typeof spec.aiTask.type === 'string';
      var hasSteps = spec.steps && Array.isArray(spec.steps) && spec.steps.length;
      if (!hasAiTask && !hasSteps) {
        throw new Error('The AI didn\u2019t produce a pipeline or an AI task. Try rephrasing your instruction.');
      }
      if (hasSteps && !hasAiTask) {
        // Tabular path — strip obviously bad step types so the executor doesn't choke.
        spec.steps = spec.steps.filter(function (s) { return s && typeof s.type === 'string'; });
        if (!spec.steps.length) {
          throw new Error('The AI returned an unexpected response. Try rephrasing your instruction.');
        }
      }
      if (!spec.output || typeof spec.output !== 'object') {
        spec.output = { format: hasAiTask ? 'html_text' : 'html_table' };
      }
      return spec;
    });"""

assert OLD_3 in src, "patch 3 (spec validation) old_str not found"
src = src.replace(OLD_3, NEW_3, 1)
print("  [3] spec validation accepts EITHER steps OR aiTask")

# ─── Patch 4: Add executeAITask function ───────────────────────────────────
# Insert right before "// ─── Pipeline executor"
EXEC_HEADER = "  // ─── Pipeline executor"

AI_TASK_FN = r"""  // ─── AI text-task executor (summary / bullet_points / Q&A) ────────────────
  // Used when the spec has `aiTask` instead of `steps[]`. Calls Groq with a
  // task-specific prompt, using the document content as context. Returns a
  // string (the AI-generated summary / bulleted list / answer).
  //
  // Document content passed to Groq:
  //   - For row-based docs (Excel/CSV): first 30 rows as JSON
  //   - For text docs (PDF/Word): first 4000 chars of rawText
  //   - For PDFs with detected tables: both the raw text AND the first 30 rows
  function executeAITask(doc, aiTask) {
    var docContent;
    if (doc.rows && doc.rows.length) {
      docContent = 'First 30 rows of the document (JSON):\n' +
        JSON.stringify(doc.rows.slice(0, 30));
      if (doc.rawText && doc.rawText.length > 10) {
        docContent += '\n\nAdditional document text (first 2000 chars):\n' +
          doc.rawText.slice(0, 2000);
      }
    } else if (doc.rawText) {
      docContent = 'Document text (first 4000 chars):\n' + doc.rawText.slice(0, 4000);
    } else {
      docContent = '(empty document — no extractable content)';
    }

    var taskType = aiTask.type || 'summary';
    var systemPrompt, userPrompt;

    if (taskType === 'qa') {
      var question = aiTask.question || 'What is this document about?';
      systemPrompt = 'You are an analyst answering questions about a document. ' +
        'Answer using only information from the document. Be specific. ' +
        'If the document does not contain the answer, say so honestly. ' +
        '2-4 sentences, plain text, no markdown, no headers.';
      userPrompt = 'Document: ' + doc.name + ' (' + doc.type + ')\n\n' +
        docContent + '\n\n' +
        'Question: ' + question + '\n\n' +
        'Answer:';
    } else if (taskType === 'bullet_points') {
      var count = aiTask.count || 6;
      systemPrompt = 'You are an analyst extracting main points from a document. ' +
        'List ' + count + ' main points as a bulleted list. ' +
        'Each point: one sentence, a specific fact / trend / insight from the document. ' +
        'Output: one bullet per line, each starting with \u2022 (a bullet character). ' +
        'No markdown headers, no intro paragraph, just the bulleted list.';
      userPrompt = 'Document: ' + doc.name + ' (' + doc.type + ')\n\n' +
        docContent + '\n\n' +
        'List ' + count + ' main points:';
    } else {
      // summary (default)
      var lengthHint = aiTask.length === 'short' ? '1 paragraph (3-4 sentences)' :
                       aiTask.length === 'long' ? '3-4 paragraphs' :
                       '2 paragraphs (4-6 sentences total)';
      systemPrompt = 'You are an analyst writing a plain-English summary of a document. ' +
        'Capture the document\'s purpose, key data points, notable patterns, and any anomalies. ' +
        'Write ' + lengthHint + '. ' +
        'Plain text, no markdown, no headers, just paragraphs.';
      userPrompt = 'Document: ' + doc.name + ' (' + doc.type + ')\n\n' +
        docContent + '\n\n' +
        'Summary:';
    }

    return callGroq(
      [{ role: 'system', content: systemPrompt },
       { role: 'user', content: userPrompt }],
      { temperature: 0.3, max_tokens: 800 }
    ).then(function (content) {
      return (content || '').trim();
    });
  }

"""

assert EXEC_HEADER in src, "patch 4 (exec header) needle not found"
src = src.replace(EXEC_HEADER, AI_TASK_FN + EXEC_HEADER, 1)
print("  [4] executeAITask(doc, aiTask) added before executePipeline")

# ─── Patch 5: onRunClick dispatch ──────────────────────────────────────────
OLD_5 = r"""  function onRunClick() {
    if (!state.document || !state.pipeline) return;
    try {
      var res = executePipeline(state.document, state.pipeline);
      state.result = res; state.resultError = null;
      state.visibleRows = 25;
      renderSlot('results');
    } catch (e) {
      state.result = null; state.resultError = e.message || 'Pipeline execution failed.';
      renderSlot('results');
    }
  }"""

NEW_5 = r"""  function onRunClick() {
    if (!state.document || !state.pipeline) return;
    var spec = state.pipeline;
    // Dispatch: AI text task vs tabular pipeline. Groq picked which path
    // based on the instruction wording — we just route.
    if (spec.aiTask) {
      state.aiLoading = true; state.aiResult = null; state.resultError = null;
      state.result = null;  // clear any prior tabular result
      renderSlot('results');
      executeAITask(state.document, spec.aiTask).then(function (text) {
        state.aiLoading = false;
        state.aiResult = text;
        renderSlot('results');
      }).catch(function (e) {
        state.aiLoading = false;
        state.aiResult = null;
        state.resultError = e.message || 'AI task failed.';
        renderSlot('results');
      });
    } else {
      try {
        var res = executePipeline(state.document, spec);
        state.result = res; state.resultError = null;
        state.aiResult = null;  // clear any prior AI result
        state.visibleRows = 25;
        renderSlot('results');
      } catch (e) {
        state.result = null; state.resultError = e.message || 'Pipeline execution failed.';
        renderSlot('results');
      }
    }
  }"""

assert OLD_5 in src, "patch 5 (onRunClick) old_str not found"
src = src.replace(OLD_5, NEW_5, 1)
print("  [5] onRunClick dispatches aiTask vs steps")

# ─── Patch 6: renderResultsCard ────────────────────────────────────────────
OLD_6 = r"""  function renderResultsCard() {
    var slot = $('pb-results-slot');
    if (!slot) return;
    if (!state.result && !state.resultError) { slot.innerHTML = ''; return; }
    var err = state.resultError
      ? '<div class="pb-error"><i class="fas fa-triangle-exclamation"></i> ' + esc(state.resultError) + '</div>'
      : '';
    var body = '';
    if (state.result) {
      var r = state.result;
      body = '\
        <p class="pb-result-summary">' + r.rows.length + ' rows \u00d7 ' + r.columns.length + ' columns</p>\
        ' + renderTableHTML(r.rows, r.columns, state.visibleRows) + '\
        <div class="pb-chart-card">\
          <p class="pb-chart-title"><i class="fas fa-chart-bar"></i> Auto-chart</p>\
          <div class="pb-chart-body"></div>\
        </div>\
        <div class="pb-download-row">\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="csv" type="button"><i class="fas fa-file-csv"></i> CSV</button>\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="excel" type="button"><i class="fas fa-file-excel"></i> Excel</button>\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="pdf" type="button"><i class="fas fa-file-pdf"></i> PDF</button>\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="json" type="button"><i class="fas fa-file-code"></i> JSON</button>\
          <div class="pb-spacer"></div>\
          <button class="btn btn-ghost pb-btn-sm" id="pb-save-pipeline" type="button"><i class="fas fa-bookmark"></i> Save pipeline</button>\
          <button class="btn btn-primary pb-btn-sm" id="pb-email-results" type="button"><i class="fas fa-envelope"></i> Email results</button>\
        </div>';
    }
    slot.innerHTML = '\
      <div class="pb-card">\
        <div class="pb-card-step">Step 4</div>\
        <h3 class="pb-card-title">Results</h3>\
        ' + err + '\
        ' + body + '\
      </div>';
    if (state.result) renderChart(slot);
  }"""

NEW_6 = r"""  function renderResultsCard() {
    var slot = $('pb-results-slot');
    if (!slot) return;
    // Three render branches: AI text result (state.aiResult), tabular result
    // (state.result), or loading/error state.
    var hasAi = !!state.aiResult;
    var hasTab = !!state.result;
    var loading = !!state.aiLoading;
    if (!hasAi && !hasTab && !state.resultError && !loading) { slot.innerHTML = ''; return; }
    var err = state.resultError
      ? '<div class="pb-error"><i class="fas fa-triangle-exclamation"></i> ' + esc(state.resultError) + '</div>'
      : '';
    var body = '';
    if (loading) {
      body = '<div class="pb-loading-block"><div class="pb-spinner"></div><div>AI is generating the response\u2026</div><div class="pb-loading-sub">This may take a few seconds for long documents.</div></div>';
    } else if (hasAi) {
      // AI text result — render as a styled text card. Convert newlines to <br>,
      // preserve bullet characters, escape HTML.
      var textHTML = esc(state.aiResult).replace(/\r?\n/g, '<br>');
      body = '\
        <div class="pb-ai-result-card">\
          <div class="pb-ai-result-text">' + textHTML + '</div>\
        </div>\
        <div class="pb-download-row">\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="txt" type="button"><i class="fas fa-file-lines"></i> Download as text</button>\
          <div class="pb-spacer"></div>\
          <button class="btn btn-ghost pb-btn-sm" id="pb-save-pipeline" type="button"><i class="fas fa-bookmark"></i> Save pipeline</button>\
          <button class="btn btn-primary pb-btn-sm" id="pb-email-results" type="button"><i class="fas fa-envelope"></i> Email results</button>\
        </div>';
    } else if (hasTab) {
      var r = state.result;
      body = '\
        <p class="pb-result-summary">' + r.rows.length + ' rows \u00d7 ' + r.columns.length + ' columns</p>\
        ' + renderTableHTML(r.rows, r.columns, state.visibleRows) + '\
        <div class="pb-chart-card">\
          <p class="pb-chart-title"><i class="fas fa-chart-bar"></i> Auto-chart</p>\
          <div class="pb-chart-body"></div>\
        </div>\
        <div class="pb-download-row">\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="csv" type="button"><i class="fas fa-file-csv"></i> CSV</button>\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="excel" type="button"><i class="fas fa-file-excel"></i> Excel</button>\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="pdf" type="button"><i class="fas fa-file-pdf"></i> PDF</button>\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="json" type="button"><i class="fas fa-file-code"></i> JSON</button>\
          <div class="pb-spacer"></div>\
          <button class="btn btn-ghost pb-btn-sm" id="pb-save-pipeline" type="button"><i class="fas fa-bookmark"></i> Save pipeline</button>\
          <button class="btn btn-primary pb-btn-sm" id="pb-email-results" type="button"><i class="fas fa-envelope"></i> Email results</button>\
        </div>';
    }
    slot.innerHTML = '\
      <div class="pb-card">\
        <div class="pb-card-step">Step 4</div>\
        <h3 class="pb-card-title">Results</h3>\
        ' + err + '\
        ' + body + '\
      </div>';
    if (hasTab) renderChart(slot);
  }"""

assert OLD_6 in src, "patch 6 (renderResultsCard) old_str not found"
src = src.replace(OLD_6, NEW_6, 1)
print("  [6] renderResultsCard handles AI text results + loading state")

# ─── Patch 7: onDownloadClick — handle 'txt' for AI results ────────────────
OLD_7 = r"""  function onDownloadClick(kind) {
    if (!state.result) return;
    var rows = state.result.rows, cols = state.result.columns;
    if (kind === 'csv')   downloadCSV(rows, cols);
    else if (kind === 'excel') downloadExcel(rows, cols).catch(function () { alertSafe('Excel export failed — the library may not have loaded.'); });"""

NEW_7 = r"""  function onDownloadClick(kind) {
    // 'txt' is for AI text-task results — download the AI output as a plain-text file.
    if (kind === 'txt' && state.aiResult != null) {
      var blob = new Blob([state.aiResult], { type: 'text/plain;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = (state.pipeline && state.pipeline.name ? state.pipeline.name.replace(/[^a-z0-9]+/gi, '_').toLowerCase() : 'ai_result') + '.txt';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      return;
    }
    if (!state.result) return;
    var rows = state.result.rows, cols = state.result.columns;
    if (kind === 'csv')   downloadCSV(rows, cols);
    else if (kind === 'excel') downloadExcel(rows, cols).catch(function () { alertSafe('Excel export failed — the library may not have loaded.'); });"""

assert OLD_7 in src, "patch 7 (onDownloadClick) old_str not found"
src = src.replace(OLD_7, NEW_7, 1)
print("  [7] onDownloadClick handles 'txt' for AI results")

# ─── Patch 8: onEmailClick + openEmailPreviewForText ───────────────────────
OLD_8 = r"""  function onEmailClick() {
    if (!state.result || !state.pipeline) return;
    openEmailPreview(state.pipeline, state.result.rows, state.result.columns);
  }"""

NEW_8 = r"""  function onEmailClick() {
    if (!state.pipeline) return;
    // For AI text results, the email body is the AI output directly (no table).
    // For tabular results, build the table-formatted body.
    if (state.aiResult != null) {
      openEmailPreviewForText(state.pipeline, state.aiResult);
    } else if (state.result) {
      openEmailPreview(state.pipeline, state.result.rows, state.result.columns);
    }
  }

  function openEmailPreviewForText(spec, aiText) {
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

assert OLD_8 in src, "patch 8 (onEmailClick) old_str not found"
src = src.replace(OLD_8, NEW_8, 1)
print("  [8] onEmailClick + openEmailPreviewForText handle AI text results")

# ─── Patch 9: CSS for .pb-ai-result-card ───────────────────────────────────
OLD_9 = ".pb-saved-list { list-style: none; padding: 0; margin: 0; }\\"
NEW_9 = ".pb-ai-result-card { padding: 20px 24px; border-radius: var(--radius); background: linear-gradient(135deg, rgba(99,102,241,0.04), rgba(6,182,212,0.03)); border: 1px solid var(--border); margin-top: 8px; }\\\n.pb-ai-result-text { font-size: 0.98rem; line-height: 1.75; color: var(--text); white-space: normal; }\\\n.pb-ai-result-text br + br { margin-top: 8px; }\\\n\\\n.pb-saved-list { list-style: none; padding: 0; margin: 0; }\\"

assert OLD_9 in src, "patch 9 (.pb-saved-list CSS) old_str not found"
src = src.replace(OLD_9, NEW_9, 1)
print("  [9] CSS for .pb-ai-result-card + .pb-ai-result-text added")

# ─── Patch 10: Reset aiResult/aiLoading on doc/sample/generate changes ─────
# Find all places that reset state.result = null and add aiResult reset.
cnt1 = src.count("state.result = null; state.resultError = null;")
src = src.replace(
    "state.result = null; state.resultError = null;",
    "state.result = null; state.resultError = null; state.aiResult = null; state.aiLoading = false;"
)
print(f"  [10] state.aiResult reset added to {cnt1} sites")

# ─── Write back ────────────────────────────────────────────────────────────
open(PATH, 'w').write(src)
print(f"\nDone. Wrote {PATH}")
