#!/usr/bin/env python3
"""
Second pass: trim the verbose paragraph on line 160 of weather-load-forecast.html
back to the punchy rhythm of the original, and fix the remaining '10 MW per
degree' reference in blog/index.html line 121. No fabricated specific values.

Keeps the blog's original tone: short, declarative, punchy. Just swaps the
made-up rule of thumb for the real concept (MW/°C is a system-dependent
parameter, not a universal number).
"""
import os

EDITS = [
    # ─── Line 160: trim the verbose paragraph back to a punchy rhythm ───────
    {
        "file": "/tmp/my-project/insight-analytics/blog/weather-load-forecast.html",
        "old": "    <p>Every utility forecast team uses a temperature-sensitivity number — <em>megawatts per degree Celsius (MW/°C)</em> — as the planning shorthand. It's in the spreadsheet. It's in the operator's head. And it's the wrong framing: a single number standing in for a relationship that changes by season, by hour, by humidity, by wind. The actual sensitivity varies from under 1 MW/°C for a small municipal system to 50 MW/°C or more for a large regional grid — there is no universal number. The real temperature-load relationship has a change-point (the balance point where heating gives way to cooling), different slopes above and below that point, and interactions with humidity, wind, and solar radiation that the single-number shorthand can't capture.</p>",
        "new": "    <p>Every utility forecast team uses a temperature-sensitivity number — <em>megawatts per degree Celsius (MW/°C)</em> — as the planning shorthand. It's in the spreadsheet. It's in the operator's head. It's wrong — or at least, it's a single number standing in for a relationship that changes by season, by hour, by humidity, by wind, and by the size and climate of the system it's measured on. There is no universal number. The real temperature-load relationship has a change-point (the balance point where heating gives way to cooling), different slopes above and below that point, and interactions with humidity, wind, and solar radiation that the single-number shorthand can't capture.</p>",
    },
    # ─── blog/index.html line 121: fix the remaining '10 MW per degree' ─────
    {
        "file": "/tmp/my-project/insight-analytics/blog/index.html",
        "old": "      <p>Real weather from your location, realistic load patterns, interpretable OLS model that learns the actual temperature-load relationship (not \"10 MW per degree\"). 14-day forecast with operational recommendations + AI explanations. Try the live demo.</p>",
        "new": "      <p>Real weather from your location, realistic load patterns, interpretable OLS model that learns the actual temperature-load relationship (not a single MW/°C shorthand). 14-day forecast with operational recommendations + AI explanations. Try the live demo.</p>",
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
        src = src.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        changed.append(f"  [{i}] OK: {os.path.basename(path)}")

    print("=== CHANGED ===")
    print("\n".join(changed) if changed else "  (none)")
    print("\n=== SKIPPED ===")
    print("\n".join(skipped) if skipped else "  (none)")


if __name__ == "__main__":
    apply_edits()
