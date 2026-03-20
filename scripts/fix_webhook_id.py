#!/usr/bin/env python3
"""
Fix missing webhookId on n8n webhook nodes.

Root cause (n8n bug #21614, PR #27161):
When a workflow's webhook nodes lack a webhookId, getNodeWebhookPath()
constructs the wrong path, so webhook registration fails even though the
workflow is active. The n8n UI always assigns webhookId on save, but the
public API does not (yet).

This script:
1. GET the workflow via API
2. Add a UUID webhookId to each webhook node missing one
3. PUT the updated workflow back
4. Deactivate then reactivate to force webhook re-registration
5. Probe the webhook endpoint to verify
"""
import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error

def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k] = v
    return env

def api_request(host, api_key, path, method='GET', data=None, use_rest=False):
    """Make request to n8n. use_rest=True uses internal /rest/ API."""
    if use_rest:
        url = f'{host}/rest{path}'
    else:
        url = f'{host}/api/v1{path}'
    headers = {'X-N8N-API-KEY': api_key, 'Content-Type': 'application/json'}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.load(resp)
            # Internal REST API wraps result in {"data": ...}
            if use_rest and isinstance(result, dict) and 'data' in result:
                return result['data']
            return result
    except urllib.error.HTTPError as e:
        print(f'  HTTP {e.code}: {e.read().decode()[:300]}')
        return None

def main():
    env = load_env()
    host = env['N8N_HOST']
    api_key = env['N8N_API_KEY']
    wf_id = 'Hr7UCyvl4DLJrQnc'

    print(f'=== Fix webhookId for workflow {wf_id} ===')
    print(f'Host: {host}')

    # Step 1: GET workflow
    print('\n[1] GET workflow...')
    wf = api_request(host, api_key, f'/workflows/{wf_id}')
    if not wf:
        print('ERROR: Failed to get workflow')
        sys.exit(1)
    print(f'  Name: {wf["name"]}, Active: {wf["active"]}')

    # Step 2: Add webhookId where missing
    print('\n[2] Check webhook nodes...')
    changed = False
    for node in wf.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.webhook':
            existing = node.get('webhookId')
            if existing:
                print(f'  ✅ "{node["name"]}" already has webhookId={existing}')
            else:
                new_id = str(uuid.uuid4())
                node['webhookId'] = new_id
                print(f'  🔧 "{node["name"]}" → webhookId={new_id}')
                changed = True

    if not changed:
        print('  No changes needed.')
    else:
        # Step 3: Try internal REST API PATCH (what the UI uses)
        print('\n[3] PATCH workflow via internal REST API...')
        patch_payload = {
            'nodes': wf['nodes'],
            'connections': wf['connections'],
        }
        result = api_request(host, api_key, f'/workflows/{wf_id}', method='PATCH', data=patch_payload, use_rest=True)
        if result and result.get('name'):
            print(f'  ✅ PATCH result: name={result.get("name")}, active={result.get("active")}')
            for n in result.get('nodes', []):
                if n.get('type') == 'n8n-nodes-base.webhook':
                    print(f'    "{n["name"]}": webhookId={n.get("webhookId", "MISSING")}')
        else:
            # Fallback: try public API PUT with minimal settings
            print('  Internal REST PATCH failed, trying public API PUT with clean settings...')
            clean_settings = {}
            for k in ('executionOrder', 'saveManualExecutions', 'callerPolicy', 'errorWorkflow'):
                if k in wf.get('settings', {}):
                    clean_settings[k] = wf['settings'][k]
            payload = {
                'name': wf['name'],
                'nodes': wf['nodes'],
                'connections': wf['connections'],
                'settings': clean_settings,
            }
            result = api_request(host, api_key, f'/workflows/{wf_id}', method='PUT', data=payload)
            if result and result.get('name'):
                print(f'  ✅ PUT result: name={result.get("name")}, active={result.get("active")}')
            else:
                print('  ❌ Both approaches failed')

    # Step 4: Deactivate then activate
    print('\n[4] Deactivate workflow...')
    r = api_request(host, api_key, f'/workflows/{wf_id}/deactivate', method='POST')
    if r:
        print(f'  active={r.get("active")}')
    time.sleep(3)

    print('\n[5] Activate workflow...')
    r = api_request(host, api_key, f'/workflows/{wf_id}/activate', method='POST')
    if r:
        print(f'  active={r.get("active")}')
    time.sleep(5)

    # Step 5: Probe webhook
    print('\n[6] Probe webhook endpoint...')
    webhook_url = f'{host}/webhook/line-quotation'
    try:
        probe_data = json.dumps({"events": []}).encode()
        probe_req = urllib.request.Request(
            webhook_url,
            data=probe_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(probe_req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode()[:200]
            print(f'  ✅ HTTP {status}: {body}')
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode()[:200]
        if status == 404 and 'not registered' in body:
            print(f'  ❌ HTTP {status}: Webhook still not registered')
            print(f'     {body}')
        else:
            print(f'  ⚠️ HTTP {status}: {body}')
    except Exception as e:
        print(f'  ❌ Error: {e}')

    # Also probe GET webhook
    print('\n[7] Probe viewer webhook (GET)...')
    viewer_url = f'{host}/webhook/quotation-view'
    try:
        probe_req = urllib.request.Request(viewer_url, method='GET')
        with urllib.request.urlopen(probe_req, timeout=10) as resp:
            print(f'  ✅ HTTP {resp.status}')
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode()[:200]
        if status == 404 and 'not registered' in body:
            print(f'  ❌ HTTP {status}: Viewer webhook still not registered')
        else:
            print(f'  ⚠️ HTTP {status}: {body}')
    except Exception as e:
        print(f'  ❌ Error: {e}')

    print('\n=== Done ===')

if __name__ == '__main__':
    main()
