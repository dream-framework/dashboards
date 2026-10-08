#!/usr/bin/env python3
"""
Reword AI chat fallback messages on both the main site and dashboards site.

Old tone: blunt "AI is offline / I'm offline / couldn't reach the AI service"
New tone: warm, acknowledges the issue, stresses we're already on it.

Scope: AI CHAT surfaces only (per user request). Status pill text like
"Groq · offline" is intentionally NOT touched — that's a technical status
indicator, not a chat reply.

Files edited:
  /tmp/my-project/insight-analytics/js/assistant.js                       (3 msgs)
  /tmp/my-project/insight-analytics/js/blog-markets-dashboard.js          (1 msg)
  /tmp/my-project/insight-analytics/dashboards-preview/js/visual-chat.js  (1 msg)
  /tmp/my-project/insight-analytics/dashboards-preview/js/contact-chat.js (1 msg)
  /tmp/my-project/insight-analytics/dashboards-preview/js/exec-ai-brief.js(1 msg)
  /home/z/my-project/js/visual-chat.js                                    (1 msg)
  /home/z/my-project/js/contact-chat.js                                  (1 msg)
  /home/z/my-project/js/exec-ai-brief.js                                  (1 msg)
  /home/z/my-project/dashboards/js/visual-chat.js                         (1 msg, dup)
  /home/z/my-project/dashboards/js/contact-chat.js                        (1 msg, dup)
  /home/z/my-project/dashboards/js/exec-ai-brief.js                       (1 msg, dup)
"""
import os
import sys

EDITS = [
    # ─── Main site: assistant.js (3 chat fallback messages) ────────────────
    {
        "file": "/tmp/my-project/insight-analytics/js/assistant.js",
        "old": "      renderAssistantMessage(\"I'm offline right now — I can't reach the AI service. The fastest way to get a real answer is the Book a Working Session form on this page. I'll be back online shortly.\");",
        "new": "      renderAssistantMessage(\"I can't reach the AI service right now — our team is already on it and I should be back online shortly. The fastest way to get a real answer in the meantime is the Book a Working Session form on this page.\");",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/assistant.js",
        "old": "      renderAssistantMessage(\"I can't reach the AI service right now. The Book a Working Session form on this page goes straight to a human who can answer this.\");",
        "new": "      renderAssistantMessage(\"I can't reach the AI service at the moment — we're already working to bring it back online. The Book a Working Session form on this page goes straight to a human who can answer this right now.\");",
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/assistant.js",
        "old": "        streamEl.textContent = \"I couldn't reach the AI service for this question. The Book a Working Session form on this page goes straight to a human who can answer.\";",
        "new": "        streamEl.textContent = \"I couldn't reach the AI service for this one — we're already on it and should be back shortly. The Book a Working Session form on this page goes straight to a human who can answer.\";",
    },

    # ─── Main site: blog-markets-dashboard.js (AI narrative catch) ─────────
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-markets-dashboard.js",
        "old": "        if (el) { el.classList.remove('bmd-shimmer'); el.textContent = 'AI narrative unavailable — live data is still streaming in the dashboard above.'; }",
        "new": "        if (el) { el.classList.remove('bmd-shimmer'); el.textContent = 'AI narrative is temporarily unavailable — our team is already on it. Live data is still streaming in the dashboard above, so the numbers stay fresh while we restore the AI service.'; }",
    },

    # ─── Main site: dashboards-preview visual-chat.js ───────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/dashboards-preview/js/visual-chat.js",
        "old": "    var offlineMsg = 'AI is offline — Groq is not configured on this deployment.\\n\\n' +\n      'I can\\'t produce a live brief without the AI backend. ' +",
        "new": "    var offlineMsg = 'AI is temporarily unavailable — our team is already on it and we should be back online shortly.\\n\\n' +\n      'I can\\'t produce a live brief until the AI service is restored, but the dashboard above stays fully live. ' +",
    },

    # ─── Main site: dashboards-preview contact-chat.js ──────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/dashboards-preview/js/contact-chat.js",
        "old": "    var offlineMsg = 'AI is offline — Groq is not configured on this deployment.\\n\\n' +\n      'For a real answer, reach out directly:\\n' +",
        "new": "    var offlineMsg = 'AI is temporarily unavailable — our team is already on it and we should be back online shortly.\\n\\n' +\n      'For a real answer in the meantime, reach out directly:\\n' +",
    },

    # ─── Main site: dashboards-preview exec-ai-brief.js ─────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/dashboards-preview/js/exec-ai-brief.js",
        "old": "      var offlineMsg = 'AI is offline — refresh in a moment, or open Visual Chat below to ask directly.';",
        "new": "      var offlineMsg = 'AI is temporarily unavailable — our team is already on it. Try Visual Chat below to ask directly, or refresh in a moment.';",
    },

    # ─── Dashboards site: visual-chat.js (and dashboards/js/ duplicate) ───
    {
        "file": "/home/z/my-project/js/visual-chat.js",
        "old": "    var offlineMsg = 'AI is offline — Groq is not configured on this deployment.\\n\\n' +\n      'I can\\'t produce a live brief without the AI backend. ' +",
        "new": "    var offlineMsg = 'AI is temporarily unavailable — our team is already on it and we should be back online shortly.\\n\\n' +\n      'I can\\'t produce a live brief until the AI service is restored, but the dashboard above stays fully live. ' +",
    },
    {
        "file": "/home/z/my-project/dashboards/js/visual-chat.js",
        "old": "    var offlineMsg = 'AI is offline — Groq is not configured on this deployment.\\n\\n' +\n      'I can\\'t produce a live brief without the AI backend. ' +",
        "new": "    var offlineMsg = 'AI is temporarily unavailable — our team is already on it and we should be back online shortly.\\n\\n' +\n      'I can\\'t produce a live brief until the AI service is restored, but the dashboard above stays fully live. ' +",
    },

    # ─── Dashboards site: contact-chat.js (and duplicate) ───────────────────
    {
        "file": "/home/z/my-project/js/contact-chat.js",
        "old": "    var offlineMsg = 'AI is offline — Groq is not configured on this deployment.\\n\\n' +\n      'For a real answer, reach out directly:\\n' +",
        "new": "    var offlineMsg = 'AI is temporarily unavailable — our team is already on it and we should be back online shortly.\\n\\n' +\n      'For a real answer in the meantime, reach out directly:\\n' +",
    },
    {
        "file": "/home/z/my-project/dashboards/js/contact-chat.js",
        "old": "    var offlineMsg = 'AI is offline — Groq is not configured on this deployment.\\n\\n' +\n      'For a real answer, reach out directly:\\n' +",
        "new": "    var offlineMsg = 'AI is temporarily unavailable — our team is already on it and we should be back online shortly.\\n\\n' +\n      'For a real answer in the meantime, reach out directly:\\n' +",
    },

    # ─── Dashboards site: exec-ai-brief.js (and duplicate) ──────────────────
    {
        "file": "/home/z/my-project/js/exec-ai-brief.js",
        "old": "      var offlineMsg = 'AI is offline — refresh in a moment, or open Visual Chat below to ask directly.';",
        "new": "      var offlineMsg = 'AI is temporarily unavailable — our team is already on it. Try Visual Chat below to ask directly, or refresh in a moment.';",
    },
    {
        "file": "/home/z/my-project/dashboards/js/exec-ai-brief.js",
        "old": "      var offlineMsg = 'AI is offline — refresh in a moment, or open Visual Chat below to ask directly.';",
        "new": "      var offlineMsg = 'AI is temporarily unavailable — our team is already on it. Try Visual Chat below to ask directly, or refresh in a moment.';",
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
            # Try to detect if already applied (idempotent)
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
        changed.append(f"  [{i}] OK: {path}")

    print("=== CHANGED ===")
    print("\n".join(changed) if changed else "  (none)")
    print("\n=== SKIPPED ===")
    print("\n".join(skipped) if skipped else "  (none)")


if __name__ == "__main__":
    apply_edits()
