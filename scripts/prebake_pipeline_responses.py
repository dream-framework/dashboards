#!/usr/bin/env python3
"""
Pre-bake real Groq responses for the pipeline-builder demo's 3 sample templates.

Background: the deployed Netlify Groq proxy at dashboards-groq-proxy.netlify.app
has a stale ALLOWED_ORIGINS list — it doesn't include https://insight-analytics.ca
so the browser blocks the demo's POST requests with a CORS mismatch. We can't
redeploy the proxy from this environment (no NETLIFY_TOKEN).

Workaround: this script calls the Groq proxy directly (server-side, no CORS)
to capture REAL AI responses for the 3 sample templates' auto-analysis + a
pipeline spec for each suggested action. The captured JSON gets inlined into
blog-pipeline-builder.js as a fallback when the live Groq call fails.

This way the demo works for sample-template users even when the proxy is
stale — and the responses are actual Groq outputs, not hand-written mocks.

Outputs:
  /home/z/my-project/scripts/pipeline-builder-prebaked.json  (raw captures)
"""
import json
import random
import sys
import urllib.request
import urllib.error

GROQ_PROXY = 'https://dashboards-groq-proxy.netlify.app/groq-proxy'
GROQ_MODEL = 'qwen/qwen3.8-27b'

# ─── Sample data generators (mirror the JS in blog-pipeline-builder.js) ─────

def pick(lst, rng=None):
    rng = rng or random
    return rng.choice(lst)

def rand_int(lo, hi, rng=None):
    rng = rng or random
    return rng.randint(lo, hi)

def synth_name(rng=None):
    rng = rng or random
    first = ['Alex','Sam','Jordan','Taylor','Morgan','Casey','Riley','Quinn','Avery','Drew','Skyler','Cameron','Reese','Jamie','Dana','Sage']
    last = ['Carter','Brooks','Reyes','Patel','Nguyen','Okafor','Singh','Walsh','Lim','Hassan','Park','Costa','Klein','Rossi','Adams','Becker']
    return pick(first, rng) + ' ' + pick(last, rng)

def synth_company(rng=None):
    rng = rng or random
    p1 = ['Blue','Summit','Apex','Vertex','North','Pioneer','Cobalt','Meridian','Quill','Iron','Stellar','Granite']
    p2 = ['Logistics','Systems','Capital','Materials','Dynamics','Foods','Health','Energy','Robotics','Media','Furniture','Chemicals']
    return pick(p1, rng) + ' ' + pick(p2, rng) + ' ' + pick(['Inc.','Ltd.','Co.','LLC','Corp.'], rng)

def gen_regional_sales(seed=None):
    rng = random.Random(seed) if seed is not None else random
    rows = []
    regions = ['Ontario','Quebec','BC','Alberta','Nova Scotia']
    products = [
        {'name': 'Widget A', 'price': 25},
        {'name': 'Widget B', 'price': 45},
        {'name': 'Widget C', 'price': 12},
        {'name': 'Widget D', 'price': 85},
        {'name': 'Widget E', 'price': 120}
    ]
    channels = ['Online','Retail','Partner']
    for i in range(50):
        dt = f"2026-{7 + rand_int(0, 2, rng):02d}-{rand_int(1, 28, rng):02d}"
        region = pick(regions, rng)
        prod = pick(products, rng)
        qty = rand_int(10, 200, rng)
        if region in ('Ontario', 'Quebec'):
            qty = round(qty * 1.35)
        if prod['name'] in ('Widget D', 'Widget E') and int(dt.split('-')[1]) >= 8:
            qty = round(qty * 1.4)
        rows.append({
            'date': dt, 'region': region, 'product': prod['name'],
            'qty': qty, 'revenue': qty * prod['price'], 'channel': pick(channels, rng)
        })
    return rows

def gen_hr_headcount(seed=None):
    rng = random.Random(seed) if seed is not None else random
    rows = []
    depts = ['Engineering','Sales','Operations','Finance','HR']
    roles = {
        'Engineering': ['Software Engineer','DevOps Engineer','QA Engineer','Engineering Manager'],
        'Sales':        ['Account Executive','SDR','Sales Manager','Customer Success'],
        'Operations':   ['Operations Analyst','Logistics Coordinator','Ops Manager'],
        'Finance':      ['Financial Analyst','Accountant','Controller'],
        'HR':           ['HR Generalist','Recruiter','HR Manager']
    }
    for i in range(30):
        dept = pick(depts, rng)
        level = pick(['Junior','Mid','Senior'], rng)
        role = pick(roles[dept], rng)
        base = (rand_int(55000, 72000, rng) if level == 'Junior'
                else rand_int(75000, 98000, rng) if level == 'Mid'
                else rand_int(105000, 145000, rng))
        hire_year = rand_int(2018, 2026, rng)
        hire_date = f"{hire_year}-{rand_int(1, 12, rng):02d}-{rand_int(1, 28, rng):02d}"
        r = rng.random()
        status = 'Active' if r < 0.8 else ('On-Leave' if r < 0.92 else 'Terminated')
        rows.append({
            'employee_id': f'EMP-{i+1:03d}', 'name': synth_name(rng),
            'department': dept, 'title': level + ' ' + role,
            'hire_date': hire_date, 'salary': base, 'status': status
        })
    return rows

def gen_invoice_aging(seed=None):
    rng = random.Random(seed) if seed is not None else random
    rows = []
    import datetime
    today = datetime.date.today()
    for i in range(40):
        issue = today - datetime.timedelta(days=rand_int(1, 120, rng))
        due = issue + datetime.timedelta(days=30)
        days = (today - issue).days
        bucket = ('Current' if days < 30 else '30-60' if days < 60 else '60-90' if days < 90 else '90+')
        rows.append({
            'invoice_id': f'INV-{1001+i}', 'customer': synth_company(rng),
            'issue_date': issue.isoformat(), 'due_date': due.isoformat(),
            'amount': rand_int(1000, 25000, rng), 'days_outstanding': days,
            'status': bucket
        })
    return rows

SAMPLE_TEMPLATES = [
    {'key': 'sales',    'name': 'Regional Sales Q3',       'columns': ['date','region','product','qty','revenue','channel'],                  'generate': gen_regional_sales},
    {'key': 'hr',       'name': 'HR Headcount Snapshot',  'columns': ['employee_id','name','department','title','hire_date','salary','status'], 'generate': gen_hr_headcount},
    {'key': 'invoices', 'name': 'Invoice Aging',          'columns': ['invoice_id','customer','issue_date','due_date','amount','days_outstanding','status'], 'generate': gen_invoice_aging},
]

# ─── Groq call (server-side — bypasses CORS) ─────────────────────────────────

import time

def call_groq(messages, temperature=0.3, max_tokens=800, retries=3):
    body = json.dumps({
        'model': GROQ_MODEL,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False
    }).encode()
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            GROQ_PROXY,
            data=body,
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
                return d['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                # Rate limit — wait 30s and retry
                wait = 30 * (attempt + 1)
                sys.stderr.write(f"  429 rate limit, waiting {wait}s (attempt {attempt+1}/{retries})\n")
                time.sleep(wait)
                continue
            elif e.code >= 500:
                # Server error — retry after short delay
                sys.stderr.write(f"  HTTP {e.code}, retrying (attempt {attempt+1}/{retries})\n")
                time.sleep(5 * (attempt + 1))
                continue
            else:
                # 4xx other than 429 — don't retry
                raise
        except Exception as e:
            last_err = e
            sys.stderr.write(f"  Network error: {e}, retrying (attempt {attempt+1}/{retries})\n")
            time.sleep(5 * (attempt + 1))
            continue
    raise last_err if last_err else Exception('Groq call failed after retries')

# Throttle: wait THROTTLE_MS between Groq calls to avoid 429s on the
# qwen3.8-27b model's 1000 OTPM (output tokens per minute) limit.
THROTTLE_MS = 4000  # 4s between calls = ~15 calls/min, well under OTPM limit

def call_groq_throttled(messages, **kwargs):
    """Wrap call_groq with a sleep before each call to respect rate limits."""
    time.sleep(THROTTLE_MS / 1000)
    return call_groq(messages, **kwargs)

def extract_json(text):
    """Strip markdown code fences and parse JSON."""
    s = text.strip()
    if s.startswith('```'):
        # Remove first line (```json or ```) and last ```
        lines = s.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        s = '\n'.join(lines)
    # Try to find the first { ... } block
    start = s.find('{')
    end = s.rfind('}')
    if start >= 0 and end > start:
        s = s[start:end+1]
    return json.loads(s)

# ─── Build prompts (mirror the JS) ──────────────────────────────────────────

def build_analysis_prompt(doc):
    sample = json.dumps(doc['rows'][:5], indent=2)
    return (
        f'You are analyzing a {doc["type"]} document titled "{doc["name"]}" with '
        f'{doc["rowCount"]} rows \u00d7 {doc["columnCount"]} columns.\n'
        f'Column headers: {", ".join(doc["columns"])}\n'
        f'First 5 rows (sample):\n{sample}\n\n'
        'Analyze this document and respond with a JSON object ONLY (no markdown, no explanation):\n'
        '{\n'
        '  "documentType": "what kind of data this is (e.g. \'regional sales\', \'invoice aging\', \'HR roster\')",\n'
        '  "summary": "one-sentence description of what\'s in the data",\n'
        '  "keyColumns": ["which columns look most important for analysis"],\n'
        '  "suggestedActions": [\n'
        '    "3-5 natural-language suggested actions, each a one-sentence instruction like \'Summarize total revenue by region\'",\n'
        '    "Make them specific to this data, not generic",\n'
        '    "Vary the difficulty — easy (sort), medium (summarize), advanced (filter+summarize)"\n'
        '  ],\n'
        '  "detectedFormulas": ["any formulas or derived columns you notice (e.g. \'revenue = qty \u00d7 price\')"],\n'
        '  "dataQualityNotes": ["any issues — missing values, outliers, etc."]\n'
        '}'
    )

def build_spec_prompt(doc, instruction):
    sample_row = json.dumps(doc['rows'][0]) if doc['rows'] else '(no rows)'
    return (
        'You are an AI pipeline constructor. Convert the user\'s natural language instruction into a JSON pipeline spec.\n\n'
        f'User\'s instruction: "{instruction}"\n\n'
        'Document context:\n'
        f'- Type: {doc["type"]}\n'
        f'- Name: {doc["name"]}\n'
        f'- Columns: {", ".join(doc["columns"])}\n'
        f'- Sample row: {sample_row}\n'
        f'- Row count: {doc["rowCount"]}\n\n'
        'Respond with a JSON object ONLY (no markdown, no explanation):\n'
        '{\n'
        '  "name": "short pipeline name",\n'
        '  "description": "one-sentence description of what the pipeline does",\n'
        '  "steps": [\n'
        '    { "type": "filter"|"summarize"|"sort"|"limit"|"select"|"transform", "description": "what this step does",\n'
        '      // filter:    { "column": "...", "operator": "=="|"!="|">"|"<"|">="|"<="|"contains", "value": ... }\n'
        '      // summarize: { "groupBy": ["col1", ...], "aggregation": "sum"|"count"|"avg"|"min"|"max", "valueColumn": "..." }\n'
        '      // sort:      { "column": "...", "order": "asc"|"desc" }\n'
        '      // limit:     { "count": 5 }\n'
        '      // select:    { "columns": ["col1", "col2"] }\n'
        '      // transform: { "newColumn": "...", "expression": "qty * price" } }\n'
        '    }\n'
        '  ],\n'
        '  "output": { "format": "html_table"|"csv"|"excel"|"pdf", "emailSubject": "subject line", "emailBodyIntro": "one-sentence intro" }\n'
        '}'
    )

# ─── Main: capture all responses ────────────────────────────────────────────

def main():
    out = {}
    for tpl in SAMPLE_TEMPLATES:
        # Use a fixed seed so the sample data is deterministic
        rows = tpl['generate'](seed=42)
        doc = {
            'type': 'excel',
            'name': tpl['name'] + ' (sample)',
            'columns': tpl['columns'][:],
            'rows': rows,
            'rowCount': len(rows),
            'columnCount': len(tpl['columns'])
        }
        print(f"\n=== {tpl['name']} ===")
        print(f"  rows: {len(rows)}, columns: {len(tpl['columns'])}")

        # 1. Auto-analysis
        print(f"  → analyzeDocument...")
        analysis_prompt = build_analysis_prompt(doc)
        analysis_content = call_groq(
            [{'role': 'system', 'content': 'You are a data analyst that outputs only raw JSON.'},
             {'role': 'user', 'content': analysis_prompt}],
            temperature=0.3, max_tokens=800
        )
        analysis = extract_json(analysis_content)
        print(f"    OK — documentType: {analysis.get('documentType')}, {len(analysis.get('suggestedActions', []))} suggested actions")

        # 2. Pipeline spec for each suggested action
        specs = {}
        for action in analysis.get('suggestedActions', []):
            print(f"  → generatePipelineSpec for: '{action[:60]}...'")
            spec_prompt = build_spec_prompt(doc, action)
            spec_content = call_groq(
                [{'role': 'system', 'content': 'You are a pipeline spec generator that outputs only raw JSON.'},
                 {'role': 'user', 'content': spec_prompt}],
                temperature=0.2, max_tokens=1000
            )
            try:
                spec = extract_json(spec_content)
                specs[action] = spec
                print(f"    OK — {len(spec.get('steps', []))} steps, format: {spec.get('output', {}).get('format')}")
            except Exception as e:
                print(f"    FAILED to parse spec: {e}")
                specs[action] = None

        out[tpl['key']] = {
            'templateName': tpl['name'],
            'analysis': analysis,
            'specs': specs,
            'rawAnalysisContent': analysis_content,
            'rawSpecContents': {k: v for k, v in zip(analysis.get('suggestedActions', []), [])}  # placeholder
        }

    # Write to file
    out_path = '/home/z/my-project/scripts/pipeline-builder-prebaked.json'
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n✓ Wrote prebaked responses to {out_path}")
    print(f"  Total: {sum(len(v['specs']) for v in out.values())} pipeline specs across {len(out)} templates")

if __name__ == '__main__':
    main()
