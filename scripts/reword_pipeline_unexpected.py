#!/usr/bin/env python3
"""
Second pass: catch the remaining 'unexpected response' / 'didn't produce'
messages in the pipeline builder (malformed-reply cases). These aren't
network failures but the tone was still blunt — softened for consistency
with the warm-recovery tone.

Lines 247, 266, 865, 871 in blog-pipeline-builder.js.
"""
import os

EDITS = [
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "    if (!content) throw new Error('AI returned an empty response. Try rephrasing your instruction.');",
        "new": "    if (!content) throw new Error('AI returned an empty response — we\\'re looking into it. Try rephrasing your instruction in a moment.');",
    },
    # Lines 266 and 871 share the same text — replace_all
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "      throw new Error('The AI returned an unexpected response. Try rephrasing your instruction.');",
        "new": "      throw new Error('The AI returned an unexpected response — we\\'re looking into it. Try rephrasing your instruction in a moment.');",
        "replace_all": True,
    },
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-pipeline-builder.js",
        "old": "        throw new Error('The AI didn\\u2019t produce a pipeline or an AI task. Try rephrasing your instruction.');",
        "new": "        throw new Error('The AI didn\\u2019t produce a pipeline or an AI task — we\\'re looking into it. Try rephrasing your instruction in a moment.');",
    },
]


def apply_edits():
    changed = []
    skipped = []
    for i, e in enumerate(EDITS, 1):
        path = e["file"]
        old = e["old"]
        new = e["new"]
        replace_all = e.get("replace_all", False)
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
        if not replace_all and src.count(old) > 1:
            skipped.append(f"  [{i}] SKIP — {src.count(old)} matches in {path} (need unique anchor or replace_all)")
            continue
        src = src.replace(old, new) if replace_all else src.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        n = "all" if replace_all else 1
        changed.append(f"  [{i}] OK ({n}): {os.path.basename(path)}")

    print("=== CHANGED ===")
    print("\n".join(changed) if changed else "  (none)")
    print("\n=== SKIPPED ===")
    print("\n".join(skipped) if skipped else "  (none)")


if __name__ == "__main__":
    apply_edits()
