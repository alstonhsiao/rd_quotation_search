#!/usr/bin/env python3
"""
產生 n8n workflow JSON（LINE 報價搜尋系統 v2）
使用方式：python3 scripts/build_workflow.py
輸出：n8n_workflow.json
"""
import json

LINE_TOKEN = "Bearer 0O5969QUfQUA0k01anwNsrSw55ENuAZ/Gcb8QVe0LGtMDHovXEJYo6Gmo/p/Fhyqy0QpFKBkz6uXInrhbf9bHi8CXkMeOsizpmMerMj3cVfKIO8cReXFHM15mxAgKtd9s8gexKlgaaiO96eIfsb9egdB04t89/1O/w1cDnyilFU="

# ─── Node 2: Parse & Route ───
parse_route_js = """\
// 解析 LINE 訊息並判斷路由
const input = $input.first().json;
const body = input.body || input;
const event = body.events?.[0];

if (!event || event.type !== 'message' || event.message.type !== 'text') {
  return [];
}

const replyToken = event.replyToken;
const userId = event.source?.userId;
const text = event.message.text.trim();

// 按鈕點選：模式選擇
if (text === '搜尋加工類型' || text === '搜尋廠商') {
  const modeMap = { '搜尋加工類型': '加工類型', '搜尋廠商': '廠商' };
  return [{
    json: {
      action: 'prompt',
      replyToken,
      searchMode: modeMap[text]
    }
  }];
}

// 搜尋指令（格式：加工類型:關鍵字 或 廠商:關鍵字）
const match = text.match(/^(加工類型|廠商)[:：\\s]+(.+)$/);
if (match) {
  return [{
    json: {
      action: 'search',
      replyToken,
      userId,
      searchMode: match[1],
      keyword: match[2].trim()
    }
  }];
}

// 預設：顯示主目錄
return [{
  json: {
    action: 'menu',
    replyToken
  }
}];"""

# ─── Node 4: Reply Menu jsonBody ───
reply_menu_body = """={{ { replyToken: $json.replyToken, messages: [{ type: 'flex', altText: '首君報價查詢系統', contents: { type: 'bubble', size: 'mega', header: { type: 'box', layout: 'vertical', contents: [{ type: 'text', text: '📋 首君報價查詢系統', weight: 'bold', size: 'xl', color: '#ffffff', align: 'center' }], backgroundColor: '#1DB446', paddingAll: '20px' }, body: { type: 'box', layout: 'vertical', contents: [{ type: 'text', text: '請選擇查詢方式', size: 'md', align: 'center', color: '#666666' }], paddingAll: '20px' }, footer: { type: 'box', layout: 'vertical', spacing: 'md', contents: [{ type: 'button', style: 'primary', height: 'md', action: { type: 'message', label: '🔍 搜尋加工類型', text: '搜尋加工類型' }, color: '#1DB446' }, { type: 'button', style: 'primary', height: 'md', action: { type: 'message', label: '🏭 搜尋廠商', text: '搜尋廠商' }, color: '#1976D2' }], paddingAll: '20px' } } }] } }}"""

# ─── Node 5: Reply Prompt jsonBody ───
reply_prompt_body = """={{ { replyToken: $json.replyToken, messages: [{ type: 'text', text: '請輸入' + $json.searchMode + '關鍵字\\n\\n格式：' + $json.searchMode + ':關鍵字\\n範例：' + ($json.searchMode === '加工類型' ? '加工類型:表面處理' : '廠商:新三和') }] } }}"""

# ─── Node 7: Search & Build Flex ───
search_build_js = """\
// 搜尋資料並建立 Flex Message
const { searchMode, keyword, replyToken } = $input.first().json;
const jsonResponse = $('Read Quotations JSON').first().json;
const rows = jsonResponse.data || [];

const field = searchMode;
const keyLower = keyword.toLowerCase();

const matched = rows.filter(row => row[field] && row[field].toLowerCase().includes(keyLower));
const total = matched.length;
const results = matched
  .sort((a, b) => new Date(b['時間戳記']) - new Date(a['時間戳記']))
  .slice(0, 10);

if (!results.length) {
  return [{
    json: {
      replyToken,
      messageType: 'text',
      text: '查無「' + keyword + '」相關報價資料\\n\\n請重新輸入：' + searchMode + ':關鍵字'
    }
  }];
}

const bubbles = results.map(row => {
  const driveUrl = (row['拍照報價單'] || '').split(',')[0].trim();
  const dateStr = (row['時間戳記'] || '').substring(0, 10);
  const hasNote = row['備註'] && row['備註'].trim();
  const hasDrive = driveUrl.startsWith('http');

  const bodyContents = [
    { type: 'text', text: row['品名'] || '(無品名)', weight: 'bold', size: 'md', wrap: true },
    { type: 'separator', margin: 'sm' },
    {
      type: 'box', layout: 'vertical', spacing: 'xs', margin: 'sm',
      contents: [
        {
          type: 'box', layout: 'baseline',
          contents: [
            { type: 'text', text: '加工', size: 'sm', color: '#888888', flex: 2 },
            { type: 'text', text: row['加工類型'] || '-', size: 'sm', flex: 5, wrap: true }
          ]
        },
        {
          type: 'box', layout: 'baseline',
          contents: [
            { type: 'text', text: '廠商', size: 'sm', color: '#888888', flex: 2 },
            { type: 'text', text: row['廠商'] || '-', size: 'sm', flex: 5, wrap: true }
          ]
        },
        {
          type: 'box', layout: 'baseline',
          contents: [
            { type: 'text', text: '填表人', size: 'sm', color: '#888888', flex: 2 },
            { type: 'text', text: row['填表人'] || '-', size: 'sm', flex: 5 }
          ]
        },
        {
          type: 'box', layout: 'baseline',
          contents: [
            { type: 'text', text: '日期', size: 'sm', color: '#888888', flex: 2 },
            { type: 'text', text: dateStr, size: 'sm', flex: 5 }
          ]
        }
      ]
    }
  ];

  if (hasNote) {
    const noteText = row['備註'].length > 60 ? row['備註'].substring(0, 60) + '…' : row['備註'];
    bodyContents.push({ type: 'separator', margin: 'sm' });
    bodyContents.push({ type: 'text', text: noteText, size: 'xs', color: '#666666', wrap: true, margin: 'sm' });
  }

  const footerContents = hasDrive ? [{
    type: 'button', style: 'primary', height: 'sm',
    action: { type: 'uri', label: '查看報價單', uri: driveUrl }
  }] : [{
    type: 'text', text: '（無報價單連結）', size: 'xs', color: '#aaaaaa', align: 'center'
  }];

  return {
    type: 'bubble', size: 'kilo',
    header: {
      type: 'box', layout: 'vertical', backgroundColor: '#1DB446', paddingAll: 'sm',
      contents: [{ type: 'text', text: searchMode + '：' + keyword, color: '#ffffff', size: 'xs' }]
    },
    body: { type: 'box', layout: 'vertical', contents: bodyContents },
    footer: { type: 'box', layout: 'vertical', contents: footerContents }
  };
});

if (total > 10) {
  bubbles.push({
    type: 'bubble', size: 'nano',
    body: {
      type: 'box', layout: 'vertical', justifyContent: 'center',
      contents: [{
        type: 'text', text: '共 ' + total + ' 筆結果\\n顯示最新 10 筆',
        align: 'center', size: 'sm', color: '#888888', wrap: true
      }]
    }
  });
}

return [{
  json: {
    replyToken,
    messageType: 'flex',
    flexContents: { type: 'carousel', contents: bubbles },
    altText: '「' + keyword + '」共 ' + total + ' 筆報價資料'
  }
}];"""

# ─── Node 8: Reply Result jsonBody ───
reply_result_body = """\
={{
  const msg = $json.messageType === 'flex'
    ? { type: 'flex', altText: $json.altText, contents: $json.flexContents }
    : { type: 'text', text: $json.text };

  return JSON.stringify({
    replyToken: $json.replyToken,
    messages: [msg]
  });
}}"""

# ─── 共用 HTTP Request 設定 ───
def line_reply_node(node_id, name, position, json_body):
    return {
        "parameters": {
            "method": "POST",
            "url": "https://api.line.me/v2/bot/message/reply",
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [{
                    "name": "Authorization",
                    "value": "=" + LINE_TOKEN
                }]
            },
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": json_body,
            "options": {}
        },
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": position
    }

# ─── 組合 Workflow ───
workflow = {
    "name": "LINE 報價搜尋系統",
    "nodes": [
        # Node 1: LINE Webhook（保留原設定）
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "line-quotation",
                "options": {},
                "responseMode": "onReceived"
            },
            "id": "webhook-trigger",
            "name": "LINE Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1.1,
            "position": [240, 380]
        },
        # Node 2: Parse & Route
        {
            "parameters": {
                "jsCode": parse_route_js
            },
            "id": "code-parse",
            "name": "Parse & Route",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [440, 380]
        },
        # Node 3: Switch Action
        {
            "parameters": {
                "mode": "rules",
                "rules": {
                    "values": [
                        {
                            "conditions": {
                                "string": [{
                                    "value1": "={{ $json.action }}",
                                    "value2": "menu"
                                }]
                            },
                            "renameOutput": True,
                            "outputKey": "主目錄"
                        },
                        {
                            "conditions": {
                                "string": [{
                                    "value1": "={{ $json.action }}",
                                    "value2": "prompt"
                                }]
                            },
                            "renameOutput": True,
                            "outputKey": "提示"
                        },
                        {
                            "conditions": {
                                "string": [{
                                    "value1": "={{ $json.action }}",
                                    "value2": "search"
                                }]
                            },
                            "renameOutput": True,
                            "outputKey": "搜尋"
                        }
                    ]
                },
                "options": {}
            },
            "id": "switch-action",
            "name": "Switch Action",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3,
            "position": [640, 380]
        },
        # Node 4: Reply Menu
        line_reply_node("http-reply-menu", "Reply Menu", [840, 200], reply_menu_body),
        # Node 5: Reply Prompt
        line_reply_node("http-reply-prompt", "Reply Prompt", [840, 380], reply_prompt_body),
        # Node 6: Read Quotations JSON
        {
            "parameters": {
                "url": "=https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json",
                "options": {}
            },
            "id": "http-read-json",
            "name": "Read Quotations JSON",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [840, 560]
        },
        # Node 7: Search & Build Flex
        {
            "parameters": {
                "jsCode": search_build_js
            },
            "id": "code-search",
            "name": "Search & Build Flex",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1040, 560]
        },
        # Node 8: Reply Result
        line_reply_node("http-reply-result", "Reply Result", [1240, 560], reply_result_body),
    ],
    "connections": {
        "LINE Webhook": {
            "main": [[{"node": "Parse & Route", "type": "main", "index": 0}]]
        },
        "Parse & Route": {
            "main": [[{"node": "Switch Action", "type": "main", "index": 0}]]
        },
        "Switch Action": {
            "main": [
                [{"node": "Reply Menu", "type": "main", "index": 0}],
                [{"node": "Reply Prompt", "type": "main", "index": 0}],
                [{"node": "Read Quotations JSON", "type": "main", "index": 0}]
            ]
        },
        "Read Quotations JSON": {
            "main": [[{"node": "Search & Build Flex", "type": "main", "index": 0}]]
        },
        "Search & Build Flex": {
            "main": [[{"node": "Reply Result", "type": "main", "index": 0}]]
        }
    },
    "settings": {
        "executionOrder": "v1"
    }
}

# ─── 輸出 ───
output_path = "n8n_workflow.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, ensure_ascii=False, indent=2)

print(f"✅ Workflow JSON 已產生: {output_path}")
print(f"   節點數: {len(workflow['nodes'])}")
print(f"   連線數: {sum(len(v['main']) for v in workflow['connections'].values())}")
