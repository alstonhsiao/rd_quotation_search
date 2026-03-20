#!/usr/bin/env python3
"""
Fix access control issues in the n8n workflow:
1. Parse & Route: add userId to ALL return paths (menu, prompt, search)
2. Connections: move Access Check Not Active from main[1] to main[0]
   so both access checks receive data from the single Code node output
3. Deploy updated workflow to n8n via API
"""
import json, os, sys, time, uuid, urllib.request, urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
WORKFLOW_FILE = os.path.join(ROOT_DIR, 'n8n_workflow.json')

def load_env():
    env = {}
    env_path = os.path.join(ROOT_DIR, '.env.local')
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k] = v
    return env

# The fixed Parse & Route JS code with userId in ALL return paths
FIXED_JSCODE = r"""// 解析 LINE 訊息並判斷路由
const input = $input.first().json;
const body = input.body || input;
const event = body.events?.[0];

if (!event || event.type !== 'message' || event.message.type !== 'text') {
  return [];
}

const replyToken = event.replyToken;
const userId = event.source?.userId;
const text = (event.message.text || '').trim();
const MODE_TTL_MS = 30 * 60 * 1000;
const staticData = $getWorkflowStaticData('global');
staticData.modeByUser = staticData.modeByUser || {};
const modeByUser = staticData.modeByUser;
const now = Date.now();

for (const [uid, state] of Object.entries(modeByUser)) {
  if (!state || !state.mode || !state.updatedAt || now - state.updatedAt > MODE_TTL_MS) {
    delete modeByUser[uid];
  }
}

// 返回主畫面
if (text === '回到主畫面') {
  if (userId) {
    delete modeByUser[userId];
  }
  return [{
    json: {
      action: 'menu',
      replyToken,
      userId
    }
  }];
}

// 按鈕點選：模式選擇
if (text === '搜尋加工類型' || text === '搜尋廠商') {
  const modeMap = { '搜尋加工類型': '加工類型', '搜尋廠商': '廠商' };
  if (userId) {
    modeByUser[userId] = { mode: modeMap[text], updatedAt: now };
  }
  return [{
    json: {
      action: 'prompt',
      replyToken,
      userId,
      searchMode: modeMap[text]
    }
  }];
}

// 搜尋指令（格式：加工類型:關鍵字 / 廠商:關鍵字 / 品名:關鍵字）
// 支援分頁尾碼：第2頁 或 2頁
const match = text.match(/^(加工類型|廠商|品名)[:：\s]+(.+)$/);
if (match) {
  let keyword = match[2].trim();
  let page = 1;
  const pageMatch = keyword.match(/(?:^|\s)(?:第)?(\d{1,3})頁?$/);
  if (pageMatch) {
    page = Math.max(1, Number(pageMatch[1]) || 1);
    keyword = keyword.slice(0, pageMatch.index).trim();
  }

  if (!keyword) {
    return [{
      json: {
        action: 'prompt',
        replyToken,
        userId,
        searchMode: match[1]
      }
    }];
  }

  return [{
    json: {
      action: 'search',
      replyToken,
      userId,
      searchMode: match[1],
      keyword,
      page
    }
  }];
}

// 只有關鍵字：根據最近一次按鈕模式自動搜尋
if (userId && modeByUser[userId]?.mode) {
  let keyword = text;
  let page = 1;
  const pageMatch = keyword.match(/(?:^|\s)(?:第)?(\d{1,3})頁?$/);
  if (pageMatch) {
    page = Math.max(1, Number(pageMatch[1]) || 1);
    keyword = keyword.slice(0, pageMatch.index).trim();
  }

  if (keyword) {
    return [{
      json: {
        action: 'search',
        replyToken,
        userId,
        searchMode: modeByUser[userId].mode,
        keyword,
        page
      }
    }];
  }

  return [{
    json: {
      action: 'prompt',
      replyToken,
      userId,
      searchMode: modeByUser[userId].mode
    }
  }];
}

// 預設：顯示主目錄
return [{
  json: {
    action: 'menu',
    replyToken,
    userId
  }
}];"""


def fix_local_workflow():
    """Fix the local n8n_workflow.json file."""
    with open(WORKFLOW_FILE) as f:
        wf = json.load(f)

    changes = []

    # Fix 1: Update Parse & Route jsCode to include userId in all paths
    for node in wf['nodes']:
        if node['name'] == 'Parse & Route':
            old_code = node['parameters']['jsCode']
            node['parameters']['jsCode'] = FIXED_JSCODE
            changes.append('Parse & Route: added userId to all return paths')
            break

    # Fix 2: Move Access Check Not Active from main[1] to main[0]
    pr_conns = wf['connections'].get('Parse & Route', {}).get('main', [])
    if len(pr_conns) >= 2:
        # main[0] currently has Access Check Active
        # main[1] currently has Access Check Not Active
        # Merge both into main[0]
        main0 = pr_conns[0]  # [{ node: "Access Check Active", ... }]
        main1 = pr_conns[1]  # [{ node: "Access Check Not Active", ... }]
        merged = main0 + main1
        wf['connections']['Parse & Route']['main'] = [merged]
        changes.append('Connections: merged Access Check Active & Not Active into main[0]')

    with open(WORKFLOW_FILE, 'w') as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)

    return wf, changes


def deploy_to_n8n(wf):
    """Deploy the fixed workflow to n8n via API."""
    env = load_env()
    host = env['N8N_HOST'].rstrip('/')
    api_key = env['N8N_API_KEY']
    workflow_id = wf.get('id', 'Hr7UCyvl4DLJrQnc')

    # Prepare PUT payload
    payload = {
        'name': wf.get('name', 'LINE 報價搜尋系統'),
        'nodes': wf['nodes'],
        'connections': wf['connections'],
        'settings': {
            'executionOrder': wf.get('settings', {}).get('executionOrder', 'v1')
        }
    }

    # PUT workflow
    url = f"{host}/api/v1/workflows/{workflow_id}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='PUT', headers={
        'X-N8N-API-KEY': api_key,
        'Content-Type': 'application/json'
    })

    print(f'PUT {url} ...')
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f'  Response: {resp.status} OK')

    # Deactivate
    print('Deactivating...')
    deact_url = f"{host}/api/v1/workflows/{workflow_id}/deactivate"
    req2 = urllib.request.Request(deact_url, data=b'', method='POST', headers={
        'X-N8N-API-KEY': api_key,
        'Content-Type': 'application/json'
    })
    with urllib.request.urlopen(req2) as resp:
        print(f'  Deactivated: {resp.status}')

    time.sleep(3)

    # Activate
    print('Activating...')
    act_url = f"{host}/api/v1/workflows/{workflow_id}/activate"
    req3 = urllib.request.Request(act_url, data=b'', method='POST', headers={
        'X-N8N-API-KEY': api_key,
        'Content-Type': 'application/json'
    })
    with urllib.request.urlopen(req3) as resp:
        print(f'  Activated: {resp.status}')

    time.sleep(3)

    # Verify webhooks
    print('\nVerifying webhooks...')
    for path, method in [('/webhook/line-quotation', 'POST'), ('/webhook/quotation-view', 'GET')]:
        probe_url = f"{host}{path}"
        try:
            if method == 'POST':
                probe_data = json.dumps({"events": []}).encode()
                probe_req = urllib.request.Request(probe_url, data=probe_data, headers={
                    'Content-Type': 'application/json'
                })
            else:
                probe_req = urllib.request.Request(probe_url)
            with urllib.request.urlopen(probe_req) as resp:
                print(f'  {method} {path} -> {resp.status} OK')
        except urllib.error.HTTPError as e:
            print(f'  {method} {path} -> {e.code} FAIL: {e.read().decode()[:200]}')


def main():
    print('=== Fixing Access Control Issues ===\n')

    wf, changes = fix_local_workflow()
    for c in changes:
        print(f'  [FIXED] {c}')

    print(f'\nLocal {WORKFLOW_FILE} updated.')
    print('\n=== Deploying to n8n ===\n')

    deploy_to_n8n(wf)
    print('\n=== Done ===')


if __name__ == '__main__':
    main()
