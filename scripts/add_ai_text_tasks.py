#!/usr/bin/env python3
"""
Add text-task support (summary / bullet_points / Q&A) to the pipeline-builder demo.

The current demo only handles TABULAR pipelines (filter/summarize/sort/etc)
on row-based documents. The user wants:
  - Plain English summaries on PDFs/Word/Excels
  - Main points as a bulleted list
  - Natural language Q&A on the document content

Architecture: extend the spec format to support an `aiTask` field that
takes precedence over `steps[]`. When Groq sees a text-task instruction
(summarize / main points / question about), it returns a spec with
`aiTask{}` instead of `steps[]`. The runner dispatches based on which
field is present.

This script patches blog-pipeline-builder.js with 5 changes:

1. analyzeDocument prompt — encourage Groq to suggest BOTH tabular tasks
   AND text tasks (summarize / main points / Q&A) based on document
   content. PDFs/Word/text-heavy docs should get text-task suggestions;
   Excel/CSV with rows should get tabular suggestions (and maybe one or
   two text tasks too).

2. generatePipelineSpec prompt — add an `aiTask` branch. If the
   instruction is a text task (summarize, main points, key takeaways,
   ask a question, etc.), Groq returns:
     {
       "name": "...",
       "description": "...",
       "aiTask": {
         "type": "summary" | "bullet_points" | "qa",
         "question": "...",        // only for qa
         "length": "short"|"medium"|"long",  // optional, for summary
         "count": 5                // optional, for bullet_points
       },
       "output": { "format": "html_text", ... }
     }
   Otherwise return the existing steps[] format.

3. Add executeAITask(doc, aiTask) — calls Groq with task-specific prompts
   using the document content as context. Returns a string (the AI-
   generated summary / bullet list / answer).

4. onRunClick — dispatch: if spec.aiTask, call executeAITask and store
   the result in state.aiResult; else executePipeline as before.

5. renderResultsCard — handle both: tabular results show table+chart+
   downloads (existing); AI text results render as a text card with the
   AI-generated content (no table, no chart, but with download buttons
   for plain-text + email).

6. buildEmailBody — for AI text tasks, use the AI text as the email body
   instead of building a table.

7. onEmailClick — dispatch based on state.aiResult vs state.result.

Verified with node --check after each patch.
"""
import re

PATH = '/home/z/insight-analytics/js/blog-pipeline-builder.js'
src = open(PATH).read()

# ─── Patch 1: analyzeDocument prompt — encourage both tabular AND text-task suggestions ──
old_analyze_prompt = """      '  "suggestedActions": [\\n' +
      '    "3-5 natural-language suggested actions, each a one-sentence instruction like \\'Summarize total revenue by region\\'",\\n' +
      '    "Make them specific to this data, not generic",\\n' +
      '    "Vary the difficulty — easy (sort), medium (summarize), advanced (filter+summarize)"\\n' +
      '  ],\\n' +"""

new_analyze_prompt = """      '  "suggestedActions": [\\n' +
      '    "4-6 natural-language suggested actions, each a one-sentence instruction",\\n' +
      '    "Include a MIX of: tabular tasks (e.g. \\'Summarize total revenue by region\\', \\'Top 5 products by qty\\', \\'Filter to Ontario and sort by revenue desc\\') AND text tasks (e.g. \\'Summarize this document in plain English\\', \\'What are the main points?\\', \\'Ask a question about this report\\')",\\n' +
      '    "For text-heavy documents (PDF/Word with little tabular data), lean toward text tasks",\\n' +
      '    "For row-based documents (Excel/CSV with many rows), lean toward tabular tasks but include at least one text task",\\n' +
      '    "Make them specific to this data, not generic"\\n' +
      '  ],\\n' +"""

assert old_analyze_prompt in src, "analyzeDocument prompt not found"
src = src.replace(old_analyze_prompt, new_analyze_prompt, 1)

# ─── Patch 2: generatePipelineSpec prompt — add aiTask branch ──────────────
old_spec_prompt_tail = """      '  "output": { "format": "html_table"|"csv"|"excel"|"pdf", "emailSubject": "subject line", "emailBodyIntro": "one-sentence intro" }\\n' +
      '}';"""

new_spec_prompt_tail = """      '  "output": { "format": "html_table"|"csv"|"excel"|"pdf"|"html_text", "emailSubject": "subject line", "emailBodyIntro": "one-sentence intro" }\\n' +
      '}\\n\\n' +
      'CRITICAL DISPATCH RULE:\\n' +
      '  - If the instruction is a TABULAR operation (filter, summarize, aggregate, sort, count, group, top N, etc.) → return spec with "steps[]"\\n' +
      '  - If the instruction is a TEXT TASK (summarize the document, main points, key takeaways, what does this report say, ask a question, explain, describe) → return spec with "aiTask{}" instead of "steps[]"\\n' +
      '  - DO NOT include both. Pick one based on the instruction wording.\\n\\n' +
      'aiTask shape (only when the instruction is a text task):\\n' +
      '  "aiTask": {\\n' +
      '    "type": "summary" | "bullet_points" | "qa",\\n' +
      '    "question": "...",          // ONLY for type="qa" — restate the user\\'s question\\n' +
      '    "length": "short" | "medium" | "long",   // optional, only for type="summary"\\n' +
      '    "count": 5                  // optional, only for type="bullet_points" — how many points to extract\\n' +
      '  }\\n' +
      '  output.format for aiTask = "html_text"\\n' +
      '  Leave "steps" OUT of the JSON entirely when aiTask is present.';"""

assert old_spec_prompt_tail in src, "spec prompt tail not found"
src = src.replace(old_spec_prompt_tail, new_spec_prompt_tail, 1)

# ─── Patch 3: Update spec validation — accept EITHER steps OR aiTask ────────
old_validation = """    ).then(function (content) {
      var spec = extractJson(content);
      if (!spec.steps || !Array.isArray(spec.steps) || !spec.steps.length) {
        throw new Error('The AI didn\\u2019t produce any pipeline steps. Try rephrasing your instruction.');
      }
      // Light validation — strip obviously bad step types so the executor doesn't choke.
      spec.steps = spec.steps.filter(function (s) { return s && typeof s.type === 'string'; });
      if (!spec.steps.length) {
        throw new Error('The AI returned an unexpected response. Try rephrasing your instruction.');
      }
      if (!spec.output || typeof spec.output !== 'object') spec.output = { format: 'html_table' };
      return spec;
    });"""

new_validation = """    ).then(function (content) {
      var spec = extractJson(content);
      // Accept EITHER steps[] (tabular) OR aiTask{} (text task).
      // Groq decides which path based on the instruction wording.
      var hasAiTask = spec.aiTask && typeof spec.aiTask === 'object' && typeof spec.aiTask.type === 'string';
      var hasSteps = spec.steps && Array.isArray(spec.steps) && spec.steps.length;
      if (!hasAiTask && !hasSteps) {
        throw new Error('The AI didn\\u2019t produce a pipeline or an AI task. Try rephrasing your instruction.');
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

assert old_validation in src, "spec validation not found"
src = src.replace(old_validation, new_validation, 1)

# ─── Patch 4: Add executeAITask function — insert before executePipeline ───
# (right after the resolveColumn helper + before "// ─── Pipeline executor")
ai_task_block = """  // ─── AI text-task executor (summary / bullet_points / Q&A) ────────────────
  // Used when the spec has `aiTask` instead of `steps[]`. Calls Groq with a
  // task-specific prompt, using the document content as context. Returns a
  // string (the AI-generated summary / bulleted list / answer).
  //
  // Document content passed to Groq:
  //   - For row-based docs (Excel/CSV): first 30 rows as JSON
  //   - For text docs (PDF/Word): first 4000 chars of rawText
  //   - For PDFs with detected tables: both the raw text AND the first 30 rows
  //
  // Truncation: 4000 chars max for rawText (Groq context window). 30 rows for
  // tabular. Keeps the prompt well under the model's 32K context limit.
  function executeAITask(doc, aiTask) {
    var docContent;
    if (doc.rows && doc.rows.length) {
      // For row-based docs, send the first 30 rows as compact JSON
      docContent = 'First 30 rows of the document (JSON):\\n' +
        JSON.stringify(doc.rows.slice(0, 30));
      if (doc.rawText && doc.rawText.length > 10) {
        docContent += '\\n\\nAdditional document text (first 2000 chars):\\n' +
          doc.rawText.slice(0, 2000);
      }
    } else if (doc.rawText) {
      // Text-only doc — first 4000 chars
      docContent = 'Document text (first 4000 chars):\\n' + doc.rawText.slice(0, 4000);
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
      userPrompt = 'Document: ' + doc.name + ' (' + doc.type + ')\\n\\n' +
        docContent + '\\n\\n' +
        'Question: ' + question + '\\n\\n' +
        'Answer:';
    } else if (taskType === 'bullet_points') {
      var count = aiTask.count || 6;
      systemPrompt = 'You are an analyst extracting main points from a document. ' +
        'List ' + count + ' main points as a bulleted list. ' +
        'Each point: one sentence, a specific fact / trend / insight from the document. ' +
        'Output: one bullet per line, each starting with \\u2022 (a bullet character). ' +
        'No markdown headers, no intro paragraph, just the bulleted list.';
      userPrompt = 'Document: ' + doc.name + ' (' + doc.type + ')\\n\\n' +
        docContent + '\\n\\n' +
        'List ' + count + ' main points:';
    } else {
      // summary (default)
      var lengthHint = aiTask.length === 'short' ? '1 paragraph (3-4 sentences)' :
                       aiTask.length === 'long' ? '3-4 paragraphs' :
                       '2 paragraphs (4-6 sentences total)';
      systemPrompt = 'You are an analyst writing a plain-English summary of a document. ' +
        'Capture the document\\'s purpose, key data points, notable patterns, and any anomalies. ' +
        'Write ' + lengthHint + '. ' +
        'Plain text, no markdown, no headers, just paragraphs.';
      userPrompt = 'Document: ' + doc.name + ' (' + doc.type + ')\\n\\n' +
        docContent + '\\n\\n' +
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

# Insert right before "// ─── Pipeline executor"
exec_header = "  // ─── Pipeline executor"
assert exec_header in src, "executor header not found"
src = src.replace(exec_header, ai_task_block + exec_header, 1)

# ─── Patch 5: Update onRunClick to dispatch aiTask vs steps ─────────────────
old_run = """  function onRunClick() {
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

new_run = """  function onRunClick() {
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

assert old_run in src, "onRunClick not found"
src = src.replace(old_run, new_run, 1)

# ─── Patch 6: Update renderResultsCard to handle AI text results ────────────
old_results = """  function renderResultsCard() {
    var slot = $('pb-results-slot');
    if (!slot) return;
    if (!state.result && !state.resultError) { slot.innerHTML = ''; return; }
    var err = state.resultError
      ? '<div class="pb-error"><i class="fas fa-triangle-exclamation"></i> ' + esc(state.resultError) + '</div>'
      : '';
    var body = '';
    if (state.result) {
      var r = state.result;
      body = '\\
        <p class="pb-result-summary">' + r.rows.length + ' rows \\u00d7 ' + r.columns.length + ' columns</p>\\
        ' + renderTableHTML(r.rows, r.columns, state.visibleRows) + '\\
        <div class="pb-chart-card">\\
          <p class="pb-chart-title"><i class="fas fa-chart-bar"></i> Auto-chart</p>\\
          <div class="pb-chart-body"></div>\\
        </div>\\
        <div class="pb-download-row">\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="csv" type="button"><i class="fas fa-file-csv"></i> CSV</button>\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="excel" type="button"><i class="fas fa-file-excel"></i> Excel</button>\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="pdf" type="button"><i class="fas fa-file-pdf"></i> PDF</button>\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="json" type="button"><i class="fas fa-file-code"></i> JSON</button>\\
          <div class="pb-spacer"></div>\\
          <button class="btn btn-ghost pb-btn-sm" id="pb-save-pipeline" type="button"><i class="fas fa-bookmark"></i> Save pipeline</button>\\
          <button class="btn btn-primary pb-btn-sm" id="pb-email-results" type="button"><i class="fas fa-envelope"></i> Email results</button>\\
        </div>';
    }
    slot.innerHTML = '\\
      <div class="pb-card">\\
        <div class="pb-card-step">Step 4</div>\\
        <h3 class="pb-card-title">Results</h3>\\
        ' + err + '\\
        ' + body + '\\
      </div>';
    if (state.result) renderChart(slot);
  }"""

new_results = """  function renderResultsCard() {
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
      body = '<div class="pb-loading-block"><div class="pb-spinner"></div><div>AI is generating the response\\u2026</div><div class="pb-loading-sub">This may take a few seconds for long documents.</div></div>';
    } else if (hasAi) {
      // AI text result — render as a styled text card. Convert newlines to <br>,
      // preserve bullet characters, escape HTML.
      var textHTML = esc(state.aiResult).replace(/\\r?\\n/g, '<br>');
      body = '\\
        <div class="pb-ai-result-card">\\
          <div class="pb-ai-result-text">' + textHTML + '</div>\\
        </div>\\
        <div class="pb-download-row">\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="txt" type="button"><i class="fas fa-file-lines"></i> Download as text</button>\\
          <div class="pb-spacer"></div>\\
          <button class="btn btn-ghost pb-btn-sm" id="pb-save-pipeline" type="button"><i class="fas fa-bookmark"></i> Save pipeline</button>\\
          <button class="btn btn-primary pb-btn-sm" id="pb-email-results" type="button"><i class="fas fa-envelope"></i> Email results</button>\\
        </div>';
    } else if (hasTab) {
      var r = state.result;
      body = '\\
        <p class="pb-result-summary">' + r.rows.length + ' rows \\u00d7 ' + r.columns.length + ' columns</p>\\
        ' + renderTableHTML(r.rows, r.columns, state.visibleRows) + '\\
        <div class="pb-chart-card">\\
          <p class="pb-chart-title"><i class="fas fa-chart-bar"></i> Auto-chart</p>\\
          <div class="pb-chart-body"></div>\\
        </div>\\
        <div class="pb-download-row">\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="csv" type="button"><i class="fas fa-file-csv"></i> CSV</button>\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="excel" type="button"><i class="fas fa-file-excel"></i> Excel</button>\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="pdf" type="button"><i class="fas fa-file-pdf"></i> PDF</button>\\
          <button class="btn btn-ghost pb-btn-sm" data-pb-download="json" type="button"><i class="fas fa-file-code"></i> JSON</button>\\
          <div class="pb-spacer"></div>\\
          <button class="btn btn-ghost pb-btn-sm" id="pb-save-pipeline" type="button"><i class="fas fa-bookmark"></i> Save pipeline</button>\\
          <button class="btn btn-primary pb-btn-sm" id="pb-email-results" type="button"><i class="fas fa-envelope"></i> Email results</button>\\
        </div>';
    }
    slot.innerHTML = '\\
      <div class="pb-card">\\
        <div class="pb-card-step">Step 4</div>\\
        <h3 class="pb-card-title">Results</h3>\\
        ' + err + '\\
        ' + body + '\\
      </div>';
    if (hasTab) renderChart(slot);
  }"""

assert old_results in src, "renderResultsCard not found"
src = src.replace(old_results, new_results, 1)

# ─── Patch 7: Update onDownloadClick to handle 'txt' for AI results ─────────
old_download = """  function onDownloadClick(kind) {
    if (!state.result) return;
    var rows = state.result.rows, cols = state.result.columns;
    if (kind === 'csv')   downloadCSV(rows, cols);
    else if (kind === 'excel') downloadExcel(rows, cols).catch(function () { alertSafe('Excel export failed — the library may not have loaded.'); });"""

new_download = """  function onDownloadClick(kind) {
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

assert old_download in src, "onDownloadClick head not found"
src = src.replace(old_download, new_download, 1)

# ─── Patch 8: Update onEmailClick + buildEmailBody for AI text results ──────
old_email_click = """  function onEmailClick() {
    if (!state.result || !state.pipeline) return;
    openEmailPreview(state.pipeline, state.result.rows, state.result.columns);
  }"""

new_email_click = """  function onEmailClick() {
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
    var body = intro + '\\n\\n' + aiText;
    openModal('Email preview', '\\
      <div class="pb-analysis-section">\\
        <p class="pb-analysis-label">Subject</p>\\
        <div class="pb-modal-pre">' + esc(subject) + '</div>\\
      </div>\\
      <div class="pb-analysis-section" style="margin-top:14px;">">\\
        <p class="pb-analysis-label">Body</p>\\
        <div class="pb-modal-pre">' + esc(body) + '</div>\\
      </div>\\
      <div class="pb-analysis-section" style="margin-top:14px;">\\
        <p class="pb-analysis-label">Recipient</p>\\
        <input class="pb-input" id="pb-email-recipient" type="email" placeholder="recipient@example.com" />\\
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

assert old_email_click in src, "onEmailClick not found"
src = src.replace(old_email_click, new_email_click, 1)

# ─── Patch 9: Add CSS for .pb-ai-result-card + .pb-ai-result-text ──────────
# Insert before ".pb-saved-list" (which exists in the CSS block)
old_saved_css = ".pb-saved-list { list-style: none; padding: 0; margin: 0; }\\"
new_ai_css = """.pb-ai-result-card { padding: 20px 24px; border-radius: var(--radius); background: linear-gradient(135deg, rgba(99,102,241,0.04), rgba(6,182,212,0.03)); border: 1px solid var(--border); margin-top: 8px; }\\
.pb-ai-result-text { font-size: 0.98rem; line-height: 1.75; color: var(--text); white-space: normal; }\\
.pb-ai-result-text br + br { margin-top: 8px; }\\
\\
.pb-saved-list { list-style: none; padding: 0; margin: 0; }\\"

assert old_saved_css in src, ".pb-saved-list CSS not found"
src = src.replace(old_saved_css, new_ai_css, 1)

# ─── Patch 10: Reset aiResult on doc/sample/generate changes ───────────────
# Find places that reset state.result and also reset state.aiResult
patches_for_reset = [
    ("state.result = null; state.resultError = null;\n    state.visibleRows = 25;",
     "state.result = null; state.resultError = null; state.aiResult = null; state.aiLoading = false;\n    state.visibleRows = 25;"),
]
for old, new in patches_for_reset:
    cnt = src.count(old)
    if cnt > 0:
        src = src.replace(old, new)
        print(f"  reset patch applied ({cnt} occurrences)")

# Also need to reset aiResult when generating a new pipeline
old_gen_reset = "state.result = null; state.resultError = null;"
new_gen_reset = "state.result = null; state.resultError = null; state.aiResult = null; state.aiLoading = false;"
src = src.replace(old_gen_reset, new_gen_reset)

# ─── Write back ────────────────────────────────────────────────────────────
open(PATH, 'w').write(src)
print(f"Patched {PATH}")
print(f"  + analyzeDocument prompt — encourages mix of tabular + text-task suggestions")
print(f"  + generatePipelineSpec prompt — aiTask branch + dispatch rule")
print(f"  + spec validation — accepts EITHER steps OR aiTask")
print(f"  + executeAITask(doc, aiTask) — calls Groq with task-specific prompts")
print(f"  + onRunClick — dispatches aiTask vs steps")
print(f"  + renderResultsCard — handles AI text results + loading state")
print(f"  + onDownloadClick — 'txt' download for AI results")
print(f"  + onEmailClick + openEmailPreviewForText — email body for AI text")
print(f"  + CSS for .pb-ai-result-card + .pb-ai-result-text")
print(f"  + state.aiResult / state.aiLoading reset on doc/sample/generate changes")
