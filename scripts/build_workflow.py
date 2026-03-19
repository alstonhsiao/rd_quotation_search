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
      replyToken
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
      searchMode: modeMap[text]
    }
  }];
}

// 搜尋指令（格式：加工類型:關鍵字 / 廠商:關鍵字 / 品名:關鍵字）
// 支援分頁尾碼：第2頁 或 2頁
const match = text.match(/^(加工類型|廠商|品名)[:：\\s]+(.+)$/);
if (match) {
  let keyword = match[2].trim();
  let page = 1;
  const pageMatch = keyword.match(/(?:^|\\s)(?:第)?(\\d{1,3})頁?$/);
  if (pageMatch) {
    page = Math.max(1, Number(pageMatch[1]) || 1);
    keyword = keyword.slice(0, pageMatch.index).trim();
  }

  if (!keyword) {
    return [{
      json: {
        action: 'prompt',
        replyToken,
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
  const pageMatch = keyword.match(/(?:^|\\s)(?:第)?(\\d{1,3})頁?$/);
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
      searchMode: modeByUser[userId].mode
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
reply_prompt_body = """={{ { replyToken: $json.replyToken, messages: [{ type: 'text', text: '請直接輸入關鍵字\\n\\n範例：' + ($json.searchMode === '加工類型' ? '表面處理' : '新三和') + '\\n分頁：關鍵字 第2頁\\n\\n（也支援舊格式：' + $json.searchMode + ':關鍵字）' }] } }}"""

# ─── Node 7: Search & Build Flex ───
search_build_js = """\
// 搜尋資料並建立 Flex Message
const routeInput = $('Switch Action').first().json || {};
const { searchMode, keyword, replyToken } = routeInput;
const requestedPage = Math.max(1, Number(routeInput.page) || 1);
const rawResponse = $input.first().json || {};
const PAGE_SIZE = 8;
const MAX_RESULT_CAP = 100;
const VIEW_HOST = 'https://alstonn8n2026.zeabur.app';
const VIEW_PATH = '/webhook/quotation-view';
const VIEW_TTL_MS = 15 * 60 * 1000;

function parseTimestamp(raw) {
  const str = String(raw || '').trim();
  if (!str) return 0;

  const tw = str.match(/^(\\d{4})\\/(\\d{1,2})\\/(\\d{1,2})\\s*(上午|下午)?\\s*(\\d{1,2}):(\\d{2})(?::(\\d{2}))?$/);
  if (tw) {
    let hour = Number(tw[5]);
    const minute = Number(tw[6]);
    const second = Number(tw[7] || 0);
    const meridiem = tw[4];
    if (meridiem === '下午' && hour < 12) hour += 12;
    if (meridiem === '上午' && hour === 12) hour = 0;
    return new Date(Number(tw[1]), Number(tw[2]) - 1, Number(tw[3]), hour, minute, second).getTime();
  }

  const fallback = Date.parse(str);
  return Number.isNaN(fallback) ? 0 : fallback;
}

function formatDate(raw) {
  const str = String(raw || '').trim();
  const m = str.match(/^(\\d{4})\\/(\\d{1,2})\\/(\\d{1,2})/);
  if (!m) return str;
  return m[1] + '/' + m[2].padStart(2, '0') + '/' + m[3].padStart(2, '0');
}

function buildDriveLinks(raw) {
  const original = String(raw || '').split(',')[0].trim();
  if (!original || !original.startsWith('http')) {
    return { previewUrl: '', openUrl: '' };
  }

  const idMatch = original.match(/[?&]id=([^&]+)/) || original.match(/\\/file\\/d\\/([^/?]+)/) || original.match(/\\/d\\/([^/?]+)/);
  if (!idMatch) {
    return { previewUrl: original, openUrl: original };
  }

  const fileId = encodeURIComponent(idMatch[1]);
  return {
    previewUrl: 'https://drive.google.com/thumbnail?id=' + fileId + '&sz=w1000',
    openUrl: 'https://drive.google.com/file/d/' + fileId + '/view'
  };
}

let dbPayload = rawResponse;
if (typeof rawResponse.data === 'string') {
  try {
    dbPayload = JSON.parse(rawResponse.data);
  } catch (error) {
    return [{
      json: {
        replyToken,
        messageType: 'text',
        text: '資料格式異常，請稍後再試。'
      }
    }];
  }
} else if (rawResponse.data && typeof rawResponse.data === 'object') {
  dbPayload = rawResponse.data;
}

const rows = Array.isArray(dbPayload.data) ? dbPayload.data : [];

if (!searchMode || !keyword) {
  return [{
    json: {
      replyToken,
      messageType: 'text',
      text: '請先選擇查詢模式後再輸入關鍵字\\n\\n格式：加工類型:關鍵字 或 廠商:關鍵字'
    }
  }];
}

const globalState = $getWorkflowStaticData('global');
globalState.viewerTokens = globalState.viewerTokens || {};
const viewerTokens = globalState.viewerTokens;
const nowMs = Date.now();
for (const [token, data] of Object.entries(viewerTokens)) {
  if (!data || !data.expiresAt || data.expiresAt <= nowMs) {
    delete viewerTokens[token];
  }
}

const viewerToken = (nowMs.toString(36) + Math.random().toString(36).slice(2, 10));
viewerTokens[viewerToken] = {
  mode: searchMode,
  keyword,
  expiresAt: nowMs + VIEW_TTL_MS
};
const viewerUrl = VIEW_HOST + VIEW_PATH + '?t=' + encodeURIComponent(viewerToken);

const field = searchMode;
const keyLower = String(keyword).toLowerCase();

const matched = rows.filter(row => {
  const value = row[field];
  return value && String(value).toLowerCase().includes(keyLower);
});
const sorted = matched.sort((a, b) => parseTimestamp(b['時間戳記']) - parseTimestamp(a['時間戳記']));
const totalMatched = sorted.length;
const capped = sorted.slice(0, MAX_RESULT_CAP);
const totalPages = Math.max(1, Math.ceil(capped.length / PAGE_SIZE));
const page = Math.min(requestedPage, totalPages);
const start = (page - 1) * PAGE_SIZE;
const end = start + PAGE_SIZE;
const results = capped.slice(start, end);

if (!results.length) {
  return [{
    json: {
      replyToken,
      messageType: 'text',
      text: '查無「' + keyword + '」相關報價資料\\n\\n請改用其他關鍵字重試，或輸入「回到主畫面」。'
    }
  }];
}

const bubbles = results.map(row => {
  const drive = buildDriveLinks(row['拍照報價單']);
  const dateStr = formatDate(row['時間戳記']);
  const hasNote = row['備註'] && row['備註'].trim();
  const hasDrive = !!drive.openUrl;

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

  const footerContents = [{
    type: 'button',
    style: 'primary',
    color: '#1976D2',
    height: 'sm',
    action: { type: 'uri', label: '網頁瀏覽全部報價(15分)', uri: viewerUrl }
  }];

  if (hasDrive) {
    footerContents.push({
      type: 'button',
      style: 'primary',
      color: '#1DB446',
      height: 'sm',
      action: { type: 'uri', label: '查看原圖', uri: drive.openUrl }
    });
  } else {
    footerContents.push({
      type: 'button',
      style: 'primary',
      color: '#FF9800',
      height: 'sm',
      action: { type: 'uri', label: '查看原始資料', uri: viewerUrl }
    });
  }

  footerContents.push({
    type: 'button',
    style: 'primary',
    color: '#6C757D',
    height: 'sm',
    action: { type: 'message', label: '回到主畫面', text: '回到主畫面' }
  });

  const bubble = {
    type: 'bubble', size: 'kilo',
    header: {
      type: 'box', layout: 'vertical', backgroundColor: '#1DB446', paddingAll: 'sm',
      contents: [{ type: 'text', text: searchMode + '：' + keyword, color: '#ffffff', size: 'xs' }]
    },
    body: { type: 'box', layout: 'vertical', contents: bodyContents },
    footer: { type: 'box', layout: 'vertical', spacing: 'md', contents: footerContents }
  };

  if (drive.previewUrl) {
    bubble.hero = {
      type: 'image',
      url: drive.previewUrl,
      size: 'full',
      aspectRatio: '20:13',
      aspectMode: 'cover',
      action: { type: 'uri', uri: drive.openUrl || drive.previewUrl }
    };
  }

  return bubble;
});

const summaryLines = [
  '第 ' + page + '/' + totalPages + ' 頁',
  '目前顯示第 ' + (start + 1) + '-' + (start + results.length) + ' 筆',
  '符合條件：' + totalMatched + ' 筆'
];

if (totalMatched > MAX_RESULT_CAP) {
  summaryLines.push('超過 ' + MAX_RESULT_CAP + ' 筆，僅顯示前 ' + MAX_RESULT_CAP + ' 筆');
}

const navButtons = [];
if (page > 1) {
  navButtons.push({
    type: 'button',
    style: 'secondary',
    height: 'sm',
    action: { type: 'message', label: '上一頁', text: searchMode + ':' + keyword + ' 第' + (page - 1) + '頁' }
  });
}
if (page < totalPages) {
  navButtons.push({
    type: 'button',
    style: 'primary',
    height: 'sm',
    action: { type: 'message', label: '下一頁', text: searchMode + ':' + keyword + ' 第' + (page + 1) + '頁' }
  });
}

const summaryBubble = {
  type: 'bubble',
  size: 'kilo',
  body: {
    type: 'box',
    layout: 'vertical',
    spacing: 'sm',
    contents: [{
      type: 'text',
      text: summaryLines.join('\\n'),
      wrap: true,
      size: 'sm',
      color: '#555555'
    }]
  },
  footer: {
    type: 'box',
    layout: 'vertical',
    spacing: 'sm',
    contents: navButtons.length ? navButtons : [{
      type: 'text',
      text: '已是最後一頁',
      align: 'center',
      size: 'xs',
      color: '#888888'
    }]
  }
};

bubbles.push(summaryBubble);

return [{
  json: {
    replyToken,
    messageType: 'flex',
    flexContents: { type: 'carousel', contents: bubbles },
    altText: '「' + keyword + '」共 ' + totalMatched + ' 筆（第 ' + page + '/' + totalPages + ' 頁）'
  }
}];"""

viewer_build_html_js = """\
const request = $('Viewer Webhook').first().json || {};
const rawToken = String(request.query?.t || request.t || '').trim();
const globalState = $getWorkflowStaticData('global');
globalState.viewerTokens = globalState.viewerTokens || {};
const viewerTokens = globalState.viewerTokens;
const nowMs = Date.now();

for (const [token, data] of Object.entries(viewerTokens)) {
  if (!data || !data.expiresAt || data.expiresAt <= nowMs) {
    delete viewerTokens[token];
  }
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('\"', '&quot;')
    .replaceAll(\"'\", '&#39;');
}

function pageTemplate(title, desc, body = '') {
  return '<!doctype html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">'
    + '<title>' + escapeHtml(title) + '</title>'
    + '<style>body{margin:0;font-family:Arial,\"Noto Sans TC\",sans-serif;background:#f2f6f2;color:#213021}'
    + '.wrap{max-width:980px;margin:0 auto;padding:16px}.card{background:#fff;border:1px solid #dce6dc;border-radius:12px;padding:14px;margin-bottom:12px}'
    + '.muted{color:#586758;font-size:13px}.ttl{font-size:22px;font-weight:700;margin:0 0 6px}.grid{display:grid;gap:12px}'
    + '.img{width:100%;height:180px;object-fit:cover;border-radius:8px;background:#eef4ee}.btn{display:inline-block;margin-top:8px;padding:8px 10px;border-radius:8px;background:#1db446;color:#fff;text-decoration:none;font-size:13px}'
    + '</style></head><body><div class=\"wrap\"><div class=\"card\"><h1 class=\"ttl\">' + escapeHtml(title) + '</h1><div class=\"muted\">' + escapeHtml(desc) + '</div></div>'
    + body + '</div></body></html>';
}

if (!rawToken) {
  return [{ json: { html: pageTemplate('連結無效', '缺少存取憑證，請回 LINE 重新點選。') } }];
}

const payload = viewerTokens[rawToken];
if (!payload || payload.expiresAt <= nowMs) {
  delete viewerTokens[rawToken];
  return [{ json: { html: pageTemplate('連結已過期', '此連結僅有效 15 分鐘，請回 LINE 重新點選「網頁瀏覽全部報價」。') } }];
}

const rawResponse = $input.first().json || {};
let dbPayload = rawResponse;
if (typeof rawResponse.data === 'string') {
  try {
    dbPayload = JSON.parse(rawResponse.data);
  } catch (error) {
    return [{ json: { html: pageTemplate('資料格式錯誤', '無法解析資料內容，請稍後重試。') } }];
  }
} else if (rawResponse.data && typeof rawResponse.data === 'object') {
  dbPayload = rawResponse.data;
}

const rows = Array.isArray(dbPayload.data) ? dbPayload.data : [];
const mode = payload.mode;
const keyword = payload.keyword;
const keyLower = String(keyword || '').toLowerCase();

function parseTs(raw) {
  const s = String(raw || '').trim();
  const m = s.match(/^(\\d{4})\\/(\\d{1,2})\\/(\\d{1,2})\\s*(上午|下午)?\\s*(\\d{1,2}):(\\d{2})(?::(\\d{2}))?$/);
  if (!m) {
    const n = Date.parse(s);
    return Number.isNaN(n) ? 0 : n;
  }
  let h = Number(m[5]);
  if (m[4] === '下午' && h < 12) h += 12;
  if (m[4] === '上午' && h === 12) h = 0;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), h, Number(m[6]), Number(m[7] || 0)).getTime();
}

function driveLinks(raw) {
  const original = String(raw || '').split(',')[0].trim();
  if (!original || !original.startsWith('http')) return { preview: '', open: '' };
  const idMatch = original.match(/[?&]id=([^&]+)/) || original.match(/\\/file\\/d\\/([^/?]+)/) || original.match(/\\/d\\/([^/?]+)/);
  if (!idMatch) return { preview: original, open: original };
  const id = encodeURIComponent(idMatch[1]);
  return {
    preview: 'https://drive.google.com/thumbnail?id=' + id + '&sz=w1000',
    open: 'https://drive.google.com/file/d/' + id + '/view'
  };
}

const matched = rows
  .filter((row) => row[mode] && String(row[mode]).toLowerCase().includes(keyLower))
  .sort((a, b) => parseTs(b['時間戳記']) - parseTs(a['時間戳記']))
  .slice(0, 100);

if (!matched.length) {
  return [{ json: { html: pageTemplate('查無資料', '條件：' + mode + ' = ' + keyword + '。請回 LINE 換關鍵字。') } }];
}

const remainMin = Math.max(0, Math.ceil((payload.expiresAt - nowMs) / 60000));
const cards = matched.map((row) => {
  const d = driveLinks(row['拍照報價單']);
  const img = d.preview ? '<a href=\"' + escapeHtml(d.open || d.preview) + '\" target=\"_blank\" rel=\"noopener\"><img class=\"img\" src=\"' + escapeHtml(d.preview) + '\" alt=\"quote\"></a>' : '';
  const note = row['備註'] ? '<div class=\"muted\">備註：' + escapeHtml(row['備註']) + '</div>' : '';
  const btn = d.open ? '<a class=\"btn\" href=\"' + escapeHtml(d.open) + '\" target=\"_blank\" rel=\"noopener\">查看原圖</a>' : '';
  return '<article class=\"card\">' + img
    + '<h2 style=\"margin:8px 0 6px;font-size:18px\">' + escapeHtml(row['品名'] || '(無品名)') + '</h2>'
    + '<div class=\"muted\">日期：' + escapeHtml(row['時間戳記'] || '-') + '</div>'
    + '<div class=\"muted\">加工：' + escapeHtml(row['加工類型'] || '-') + '</div>'
    + '<div class=\"muted\">廠商：' + escapeHtml(row['廠商'] || '-') + '</div>'
    + '<div class=\"muted\">填表人：' + escapeHtml(row['填表人'] || '-') + '</div>'
    + note + btn + '</article>';
}).join('');

const desc = '條件：' + mode + ' = ' + keyword + '，共 ' + matched.length + ' 筆（最多 100 筆）。連結剩餘約 ' + remainMin + ' 分鐘。';
return [{ json: { html: pageTemplate('報價快速瀏覽', desc, '<section class=\"grid\">' + cards + '</section>') } }];
"""

# ─── Node 8: Reply Result jsonBody ───
reply_result_body = """={{ { replyToken: $json.replyToken, messages: [($json.messageType === 'flex' ? { type: 'flex', altText: $json.altText, contents: $json.flexContents } : { type: 'text', text: $json.text })] } }}"""

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
            "id": "webhook-trigger-v2",
            "name": "LINE Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
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
                "rules": {
                    "values": [
                        {
                            "conditions": {
                                "options": {
                                    "caseSensitive": True,
                                    "leftValue": "",
                                    "typeValidation": "strict",
                                    "version": 2
                                },
                                "conditions": [{
                                    "id": "0f2284b0-31dd-4c53-9ef0-35a4f97fcb64",
                                    "leftValue": "={{ $json.action }}",
                                    "rightValue": "menu",
                                    "operator": {
                                        "type": "string",
                                        "operation": "equals"
                                    }
                                }],
                                "combinator": "and"
                            },
                            "renameOutput": True,
                            "outputKey": "主目錄"
                        },
                        {
                            "conditions": {
                                "options": {
                                    "caseSensitive": True,
                                    "leftValue": "",
                                    "typeValidation": "strict",
                                    "version": 2
                                },
                                "conditions": [{
                                    "id": "8a57934c-a2af-4cc4-a83b-2ef7ab0e34ce",
                                    "leftValue": "={{ $json.action }}",
                                    "rightValue": "prompt",
                                    "operator": {
                                        "type": "string",
                                        "operation": "equals"
                                    }
                                }],
                                "combinator": "and"
                            },
                            "renameOutput": True,
                            "outputKey": "提示"
                        },
                        {
                            "conditions": {
                                "options": {
                                    "caseSensitive": True,
                                    "leftValue": "",
                                    "typeValidation": "strict",
                                    "version": 2
                                },
                                "conditions": [{
                                    "id": "f4e9b8d6-f208-4f7d-8754-3cbab6b2d592",
                                    "leftValue": "={{ $json.action }}",
                                    "rightValue": "search",
                                    "operator": {
                                        "type": "string",
                                        "operation": "equals"
                                    }
                                }],
                                "combinator": "and"
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
            "typeVersion": 3.2,
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
        # Node 9: Viewer Webhook (HTML)
        {
            "parameters": {
                "httpMethod": "GET",
                "path": "quotation-view",
                "options": {},
                "responseMode": "responseNode"
            },
            "id": "webhook-viewer-v2",
            "name": "Viewer Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [240, 760]
        },
        # Node 10: Read Quotations JSON (Viewer)
        {
            "parameters": {
                "url": "=https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json",
                "options": {}
            },
            "id": "http-read-json-viewer",
            "name": "Read Quotations JSON (Viewer)",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [440, 760]
        },
        # Node 11: Build Viewer HTML
        {
            "parameters": {
                "jsCode": viewer_build_html_js
            },
            "id": "code-viewer-html",
            "name": "Build Viewer HTML",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [640, 760]
        },
        # Node 12: Respond Viewer HTML
        {
            "parameters": {
                "respondWith": "text",
                "responseBody": "={{ $json.html }}",
                "options": {
                    "responseCode": 200,
                    "responseHeaders": {
                        "entries": [
                            {
                                "name": "Content-Type",
                                "value": "text/html; charset=utf-8"
                            },
                            {
                                "name": "Cache-Control",
                                "value": "no-store"
                            }
                        ]
                    }
                }
            },
            "id": "respond-viewer",
            "name": "Respond Viewer",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [840, 760]
        },
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
        },
        "Viewer Webhook": {
            "main": [[{"node": "Read Quotations JSON (Viewer)", "type": "main", "index": 0}]]
        },
        "Read Quotations JSON (Viewer)": {
            "main": [[{"node": "Build Viewer HTML", "type": "main", "index": 0}]]
        },
        "Build Viewer HTML": {
            "main": [[{"node": "Respond Viewer", "type": "main", "index": 0}]]
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
