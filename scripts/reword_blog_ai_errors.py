#!/usr/bin/env python3
"""
Two changes requested by the user:

1) Main site desktop nav + footer: 'Demos' → 'Live Demos'
   (mobile menu already says 'Live Demos'; desktop nav was missed)
   File: /tmp/my-project/insight-analytics/index.html — lines 139, 983

2) Propagate warm-recovery tone to the three blog demo JS files:
   - blog-pipeline-builder.js
   - blog-fuzzy-match.js
   - blog-load-forecast.js
   Each has 5-6 AI error messages that previously said things like
   'Couldn't reach the AI service. Please try again.' — reworded to
   stress active remediation.
"""
import os

# ─── (1) Desktop nav + footer: 'Demos' → 'Live Demos' ─────────────────────
IDX = "/tmp/my-project/insight-analytics/index.html"
with open(IDX, "r", encoding="utf-8") as f:
    src = f.read()

# Desktop nav link (line 139)
old_nav = '<a href="/blog/" class="nav-link" title="Demos — see it live. Production-ready pipelines.">Demos</a>'
new_nav = '<a href="/blog/" class="nav-link" title="Live Demos — see it live. Production-ready pipelines.">Live Demos</a>'
if old_nav in src:
    src = src.replace(old_nav, new_nav)
    print(f"OK: desktop nav link → 'Live Demos'")
else:
    print(f"WARN: desktop nav pattern not found (already fixed?)")

# Footer link (line 983)
old_footer = '<a href="/blog/" title="Demos — see it live. Production-ready pipelines.">Demos</a>'
new_footer = '<a href="/blog/" title="Live Demos — see it live. Production-ready pipelines.">Live Demos</a>'
if old_footer in src:
    src = src.replace(old_footer, new_footer)
    print(f"OK: footer link → 'Live Demos'")
else:
    print(f"WARN: footer pattern not found (already fixed?)")

with open(IDX, "w", encoding="utf-8") as f:
    f.write(src)


# ─── (2) Warm-recovery tone in blog demo JS files ─────────────────────────
# Same pattern across all three files: 5-6 AI error messages each.

EDITS = [
    # ─── blog-pipeline-builder.js ──────────────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "          throw new Error('AI service returned ' + r.status + '. Please try again.');",
        "new": "          throw new Error('AI service returned ' + r.status + '. We\\'re already on it — please try again in a moment.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "          throw new Error('AI returned an unexpected response. Try rephrasing your instruction.');",
        "new": "          throw new Error('AI returned an unexpected response — we\\'re looking into it. Try rephrasing your instruction in a moment.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "          throw new Error('The AI service took too long to respond. Please try again.');",
        "new": "          throw new Error('The AI service is taking longer than usual — we\\'re already on it. Please try again shortly.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "          throw new Error('Couldn\\u2019t reach the AI service (CORS or network error). ' +\n            'The Groq proxy may be cold-starting — please try again in a few seconds. ' +\n            'If the problem persists, please let us know via the Contact form.');",
        "new": "          throw new Error('Couldn\\u2019t reach the AI service (CORS or network error). ' +\n            'Our team is already on it and we should be back online shortly. ' +\n            'The Groq proxy may be cold-starting — please try again in a few seconds.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "        throw new Error('Couldn\\u2019t reach the AI service. Please try again — if the problem persists, the demo may be rate-limited.');",
        "new": "        throw new Error('Couldn\\u2019t reach the AI service at the moment — we\\'re already working to bring it back. Please try again shortly.');",
    },

    # ─── blog-fuzzy-match.js ───────────────────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-fuzzy-match.js",
        "old": "          throw new Error('AI service returned ' + r.status + '. Please try again.');",
        "new": "          throw new Error('AI service returned ' + r.status + '. We\\'re already on it — please try again in a moment.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-fuzzy-match.js",
        "old": "          throw new Error('AI returned an unexpected response. Please try again.');",
        "new": "          throw new Error('AI returned an unexpected response — we\\'re looking into it. Please try again in a moment.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-fuzzy-match.js",
        "old": "          throw new Error('The AI service took too long to respond. Please try again.');",
        "new": "          throw new Error('The AI service is taking longer than usual — we\\'re already on it. Please try again shortly.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-fuzzy-match.js",
        "old": "          throw new Error('Couldn\\u2019t reach the AI service (CORS or network error). ' +\n            'The Groq proxy may be cold-starting — please try again in a few seconds.');",
        "new": "          throw new Error('Couldn\\u2019t reach the AI service (CORS or network error). ' +\n            'Our team is already on it and we should be back online shortly. ' +\n            'The Groq proxy may be cold-starting — please try again in a few seconds.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-fuzzy-match.js",
        "old": "        throw new Error('Couldn\\u2019t reach the AI service. Please try again.');",
        "new": "        throw new Error('Couldn\\u2019t reach the AI service at the moment — we\\'re already working to bring it back. Please try again shortly.');",
    },

    # ─── blog-load-forecast.js ────────────────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "        if (!r.ok) throw new Error('AI service returned ' + r.status + '. Please try again.');",
        "new": "        if (!r.ok) throw new Error('AI service returned ' + r.status + '. We\\'re already on it — please try again in a moment.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "          throw new Error('AI returned an unexpected response. Try rephrasing your question.');",
        "new": "          throw new Error('AI returned an unexpected response — we\\'re looking into it. Try rephrasing your question in a moment.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "          throw new Error('The AI service took too long to respond. Please try again.');",
        "new": "          throw new Error('The AI service is taking longer than usual — we\\'re already on it. Please try again shortly.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "          throw new Error('Couldn\\u2019t reach the AI service (CORS or network error). ' +\n            'The Groq proxy may be cold-starting — please try again in a few seconds.');",
        "new": "          throw new Error('Couldn\\u2019t reach the AI service (CORS or network error). ' +\n            'Our team is already on it and we should be back online shortly. ' +\n            'The Groq proxy may be cold-starting — please try again in a few seconds.');",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "        throw new Error('Couldn\\u2019t reach the AI service. Please try again.');",
        "new": "        throw new Error('Couldn\\u2019t reach the AI service at the moment — we\\'re already working to bring it back. Please try again shortly.');",
    },
    # AI narration fallback (load forecast only)
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "      state.briefingsError = (e && e.message) || 'AI narration failed.';",
        "new": "      state.briefingsError = (e && e.message) || 'AI narration is temporarily unavailable — our team is already on it. The locally-computed briefing above is still fully available.';",
    },
]


def apply_edits():
    changed = []
    skipped = []
    for i, e in enumerate(EDITS, 1):
        path = e["file"]
        old = e["old"]
        new = e["new"]
        if not os.path.exists(path):
            skipped.append(f"  [{i}] MISSING FILE: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        if old not in src:
            if new in src:
                skipped.append(f"  [{i}] already applied: {path}")
            else:
                skipped.append(f"  [{i}] OLD STRING NOT FOUND in: {path}")
            continue
        count = src.count(old)
        if count > 1:
            skipped.append(f"  [{i}] SKIP — {count} matches in {path} (need unique anchor)")
            continue
        src = src.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        changed.append(f"  [{i}] OK: {os.path.basename(path)}")

    print("\n=== CHANGED ===")
    print("\n".join(changed) if changed else "  (none)")
    print("\n=== SKIPPED ===")
    print("\n".join(skipped) if skipped else "  (none)")


if __name__ == "__main__":
    apply_edits()
