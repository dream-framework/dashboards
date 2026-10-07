#!/usr/bin/env python3
"""
Replace the fabricated '10 MW per degree' rule-of-thumb framing with the
real concept: temperature sensitivity in MW/°C is a real, system-dependent
parameter (ranges from <1 MW/°C for small systems to 50+ MW/°C for large
regional grids). There is no universal '10 MW per degree' rule of thumb.

Updates 5 references across:
  /tmp/my-project/insight-analytics/blog/weather-load-forecast.html (4 refs)
  /tmp/my-project/insight-analytics/js/blog-load-forecast.js       (1 ref)
"""
import os

EDITS = [
    # ─── (1) Meta description (line 11) ─────────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/blog/weather-load-forecast.html",
        "old": "  <meta name=\"description\" content=\"Real weather data from your location, realistic load patterns, interpretable statistical model that learns the actual temperature-load relationship (not '10 MW per degree'). 14-day forecast with operational recommendations and AI explanations.\" />",
        "new": "  <meta name=\"description\" content=\"Real weather data from your location, realistic load patterns, interpretable statistical model that learns the actual temperature-load relationship (not the single-number MW/°C shorthand). 14-day forecast with operational recommendations and AI explanations.\" />",
    },
    # ─── (2) The offending paragraph (line 160) ──────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/blog/weather-load-forecast.html",
        "old": "    <p>Every utility forecast team knows the rule of thumb: <em>\"10 MW per degree.\"</em> It's in the planning spreadsheet. It's in the operator's head. It's wrong — or at least, it's a single number standing in for a relationship that changes by season, by hour, by humidity, by wind. The real temperature-load relationship has a change-point (the balance point where heating gives way to cooling), different slopes above and below that point, and interactions with humidity, wind, and solar radiation that the rule of thumb can't capture.</p>",
        "new": "    <p>Every utility forecast team uses a temperature-sensitivity number — <em>megawatts per degree Celsius (MW/°C)</em> — as the planning shorthand. It's in the spreadsheet. It's in the operator's head. And it's the wrong framing: a single number standing in for a relationship that changes by season, by hour, by humidity, by wind. The actual sensitivity varies from under 1 MW/°C for a small municipal system to 50 MW/°C or more for a large regional grid — there is no universal number. The real temperature-load relationship has a change-point (the balance point where heating gives way to cooling), different slopes above and below that point, and interactions with humidity, wind, and solar radiation that the single-number shorthand can't capture.</p>",
    },
    # ─── (3) Trained model bullet (line 174) ─────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/blog/weather-load-forecast.html",
        "old": "The model learned the actual slopes — not \"10 MW per degree\".</li>",
        "new": "The model learned the actual slopes — not a single MW/°C shorthand.</li>",
    },
    # ─── (4) Comparison table row (line 185) ──────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/blog/weather-load-forecast.html",
        "old": "        <tr><td>\"10 MW per degree\" — one number for all seasons, all hours</td><td>Model learns separate heating and cooling slopes + the change-point where they meet</td></tr>",
        "new": "        <tr><td>Single MW/°C number — same for all seasons, all hours</td><td>Model learns separate heating and cooling slopes + the change-point where they meet</td></tr>",
    },
    # ─── (5) JS comment (line 1310) ───────────────────────────────────────────
    {
        "file": "/tmp/my-project/insight-analytics/js/blog-load-forecast.js",
        "old": "  // differentiator from \"10 MW per degree\" — the model LEARNS the change-",
        "new": "  // differentiator from the single-number MW/°C shorthand — the model LEARNS the change-",
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

    print("=== CHANGED ===")
    print("\n".join(changed) if changed else "  (none)")
    print("\n=== SKIPPED ===")
    print("\n".join(skipped) if skipped else "  (none)")


if __name__ == "__main__":
    apply_edits()
