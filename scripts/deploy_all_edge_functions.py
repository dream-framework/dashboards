#!/usr/bin/env python3
"""
Deploy ALL edge functions (groq-proxy, markets-proxy, send-email) + netlify.toml
to the Netlify site startling-belekoy-b0ec70 (site ID 66437739-...).

The recent dashboards repo push triggered a Netlify auto-deploy that succeeded
but WITHOUT the edge functions — all three are now down. This script re-uploads
them via the Netlify API.
"""
import json, sys, time, urllib.request, urllib.error, hashlib, os
from pathlib import Path

TOKEN = 'nfp_4FQfq4gZLQqTm5TKHvepANqBAu8JQ1h20953'
SITE_ID = '66437739-8442-4dab-a739-a8c5abdef192'
API = 'https://api.netlify.com/api/v1'
REPO = Path('/home/z/my-project')

# Files to deploy — edge functions + netlify.toml
FILES = [
    ('netlify/edge-functions/groq-proxy.js',    REPO / 'netlify/edge-functions/groq-proxy.js'),
    ('netlify/edge-functions/markets-proxy.js',  REPO / 'netlify/edge-functions/markets-proxy.js'),
    ('netlify/edge-functions/send-email.js',     REPO / 'netlify/edge-functions/send-email.js'),
    ('netlify.toml',                             REPO / 'netlify.toml'),
]

def api(method, path, body=None, raw=False, content_type='application/json'):
    hdrs = {'Authorization': 'Bearer ' + TOKEN, 'User-Agent': 'edge-deploy/2.0'}
    data = None
    if body is not None:
        if raw:
            data = body
            hdrs['Content-Type'] = content_type
        else:
            data = json.dumps(body).encode()
            hdrs['Content-Type'] = 'application/json'
    req = urllib.request.Request(API + path, data=data, method=method, headers=hdrs)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, resp.read().decode(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500], dict(e.headers)
    except Exception as e:
        return 0, str(e)[:500], {}

# Step 1: Read all files + compute SHA1 hashes
print('=== Step 1: Read files + compute SHA1 ===')
file_data = []
for (rel_path, abs_path) in FILES:
    if not abs_path.exists():
        print(f'  SKIP (not found): {rel_path}')
        continue
    content = abs_path.read_bytes()
    sha1 = hashlib.sha1(content).hexdigest()
    file_data.append((rel_path, content, sha1))
    print(f'  {rel_path}: {len(content)} bytes, sha1={sha1[:12]}...')

# Step 2: Create a new deploy with file digests
print('\n=== Step 2: Create deploy ===')
digests = {fd[2]: fd[0] for fd in file_data}  # sha1 -> path
body = {'files': digests}
status, resp, _ = api('POST', f'/sites/{SITE_ID}/deploys', body=body)
if status not in (200, 201):
    print(f'  FAILED: HTTP {status}')
    print(f'  Body: {resp[:300]}')
    sys.exit(1)
deploy = json.loads(resp)
deploy_id = deploy['id']
print(f'  Deploy ID: {deploy_id}')
print(f'  Required files: {len(deploy.get("required", []))}')

# Step 3: Upload required files
print('\n=== Step 3: Upload files ===')
required = deploy.get('required', [])
sha_to_content = {fd[2]: fd[1] for fd in file_data}
sha_to_path = {fd[2]: fd[0] for fd in file_data}

for sha in required:
    if sha not in sha_to_content:
        print(f'  SKIP unknown sha: {sha[:12]}...')
        continue
    content = sha_to_content[sha]
    path = sha_to_path[sha]
    status, resp, headers = api('PUT', f'/deploys/{deploy_id}/files/{sha}',
                                body=content, raw=True,
                                content_type='application/octet-stream')
    print(f'  Upload {path}: HTTP {status}')
    if status not in (200, 201, 204):
        print(f'    Body: {resp[:300]}')
        sys.exit(1)

# Step 4: Wait for deploy to be ready
print('\n=== Step 4: Wait for deploy to be ready ===')
for attempt in range(30):
    time.sleep(3)
    status, resp, _ = api('GET', f'/deploys/{deploy_id}')
    if status == 200:
        d = json.loads(resp)
        state = d.get('state') or d.get('status')
        print(f'  [{attempt*3}s] state={state}')
        if state == 'ready':
            print('  ✓ Deploy ready!')
            break
        if state in ('error', 'rejected'):
            print(f'  FAILED: {state}')
            sys.exit(1)
else:
    print('  TIMEOUT waiting for deploy')
    sys.exit(1)

# Step 5: Verify edge functions
print('\n=== Step 5: Verify edge functions ===')
time.sleep(5)  # Give edge functions a moment to activate
for (name, url) in [
    ('groq-proxy', f'https://startling-belekoy-b0ec70.netlify.app/groq-proxy'),
    ('markets-proxy', f'https://startling-belekoy-b0ec70.netlify.app/markets-proxy?symbols=^GSPC'),
    ('send-email', f'https://startling-belekoy-b0ec70.netlify.app/send-email'),
]:
    try:
        req = urllib.request.Request(url, headers={'Origin': 'https://insight-analytics.ca'})
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read().decode()[:100]
        ct = resp.headers.get('content-type', '')
        if 'json' in ct or body.startswith('{') or body.startswith('['):
            print(f'  ✓ {name}: JSON response ({len(body)} chars)')
        else:
            print(f'  ? {name}: content-type={ct}, body={body[:60]}')
    except urllib.error.HTTPError as e:
        print(f'  ? {name}: HTTP {e.code} (might be expected for GET on POST-only endpoint)')
    except Exception as e:
        print(f'  ✗ {name}: {str(e)[:100]}')

print('\n=== Done ===')
print(f'Site: https://startling-belekoy-b0ec70.netlify.app')
print(f'Deploy ID: {deploy_id}')
