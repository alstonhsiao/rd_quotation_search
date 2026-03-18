# AGENTS.md — rd_quotation_search

本文件供 AI 代理人（GitHub Copilot、Claude 等）使用，說明此專案的背景、架構、程式碼慣例與所有 n8n Node 的完整設定細節。

---

## 專案背景

- **目的**：讓公司成員透過 LINE 搜尋「首君供應商報價管理表單」，快速找到歷史報價資料
- **部署環境**：n8n self-hosted (`https://alstonn8n2026.zeabur.app`)
- **資料來源**：GitHub 託管 JSON 資料庫（`quotations.json`，由同步流程定時更新）
- **前端**：LINE Messaging API（指令格式 + Flex Message）
- **設計特色**：Stateless（無 session 管理）

---

## 試算表結構

**Spreadsheet ID**: `1WZ_sZvfBjUiIPHrY6WkdR1yBXLHdYB_Fb8T3VTYQ0GI`

### 分頁 `表單回應 1`（主資料，約 491 筆，2022–2026）

| 欄 | 欄位 | 資料範例 |
|---|---|---|
| A | 時間戳記 | `2026/3/17 下午 5:03:36` |
| B | 加工類型 | `表面處理` / `車床/模具` / `沖壓/模具` / `原物料` ... |
| C | 廠商 | `新三和` / `亮新` / `炎助` ... |
| D | 填表人 | `林啟生` / `紀淑美` / `王俊偉` / `白仁豪` ... |
| E | 品名 | `起子手柄` / `棘輪板手` ... |
| F | 拍照報價單 | `https://drive.google.com/open?id=...` (可能多個，逗號分隔) |
| G | 備註 | 單價、模具費、其他說明 |

### 讀取方式

- **JSON 端點**：`https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json`
- **無需認證**：GitHub Raw 公開讀取
- **資料格式**：`{ lastUpdated, totalRecords, data[] }`，其中 `data[]` 內欄位使用中文欄位名

---

## n8n Workflow 架構

此 workflow 採用 **stateless 設計**，完全透過指令格式（如 `品名:棘輪`）進行搜尋，無需 Google 寫入權限。

### 流程圖

```
LINE User Message
  ↓
[1] LINE Webhook (接收訊息)
  ↓
[2] Parse & Route (判斷指令類型)
  ↓
[3] Switch (3-way routing)
  ├→ 提示：[4] Reply Prompt (教學如何使用)
  ├→ 搜尋：[6] Read Quotations JSON → [7] Search & Build Flex → [8] Reply Result
  └→ 說明：[5] Reply Help (Quick Reply buttons)
```

---

## n8n Node 完整設定

### Node 1 | LINE Webhook
- **類型**: `n8n-nodes-base.webhook`
- **Path**: `line-quotation`
- **HTTP Method**: POST
- **Response Mode**: `onReceived` (立即回 200 OK)

---

### Node 2 | Parse & Route (Code JS)

解析 LINE 訊息，判斷為「按鈕選擇」、「指令搜尋」或「需要說明」。

```javascript
// 解析 LINE Event 並判斷是「選模式」還是「直接搜尋」
const body = $input.first().json.body;
const event = body.events?.[0];

if (!event || event.type !== 'message' || event.message.type !== 'text') {
  return [];
}

const userId = event.source.userId;
const replyToken = event.replyToken;
const text = event.message.text.trim();

// 判斷是「模式選擇」或「直接搜尋」
const modeButtons = ['品名搜尋', '廠商搜尋', '加工類型搜尋'];

if (modeButtons.includes(text)) {
  // 回覆提示
  const modeMap = { '品名搜尋': '品名', '廠商搜尋': '廠商', '加工類型搜尋': '加工類型' };
  return [{
    json: {
      action: 'prompt',
      replyToken,
      searchMode: modeMap[text]
    }
  }];
}

// 檢查是否為「模式:關鍵字」格式
const match = text.match(/^(品名|廠商|加工類型)[:：\s]+(.+)$/i);
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

// 預設顯示說明
return [{
  json: {
    action: 'help',
    replyToken
  }
}];
```

**Outputs**:
- `action === 'prompt'` → Node 4 (Reply Prompt)
- `action === 'search'` → Node 6 (Read Quotations JSON)
- `action === 'help'` → Node 5 (Reply Help)

---

### Node 3 | Switch Action

- **類型**: `n8n-nodes-base.switch`
- **條件**:
  1. `{{ $json.action }} === 'prompt'` → 提示
  2. `{{ $json.action }} === 'search'` → 搜尋
  3. `{{ $json.action }} === 'help'` → 說明

---

### Node 4 | Reply Prompt (HTTP Request)

教學使用者如何輸入指令格式。

- **Method**: POST
- **URL**: `https://api.line.me/v2/bot/message/reply`
- **Headers**:
  - `Authorization`: `Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}`
- **Body** (JSON):
```json
{
  "replyToken": "{{ $json.replyToken }}",
  "messages": [{
    "type": "text",
    "text": "請輸入格式：{{ $json.searchMode }}:關鍵字\n\n範例：\n品名:棘輪\n廠商:亮新\n加工類型:表面處理"
  }]
}
```

---

### Node 5 | Reply Help (HTTP Request)

顯示使用說明 + Quick Reply 按鈕。

- **Method**: POST
- **URL**: `https://api.line.me/v2/bot/message/reply`
- **Headers**:
  - `Authorization`: `Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}`
- **Body** (JSON):
```json
{
  "replyToken": "{{ $json.replyToken }}",
  "messages": [{
    "type": "text",
    "text": "👋 首君報價查詢系統\n\n請點選搜尋方式，或直接輸入：\n品名:關鍵字\n廠商:關鍵字\n加工類型:關鍵字",
    "quickReply": {
      "items": [
        { "type": "action", "action": { "type": "message", "label": "🔍 品名搜尋", "text": "品名搜尋" }},
        { "type": "action", "action": { "type": "message", "label": "🏭 廠商搜尋", "text": "廠商搜尋" }},
        { "type": "action", "action": { "type": "message", "label": "⚙️ 加工類型搜尋", "text": "加工類型搜尋" }}
      ]
    }
  }]
}
```

---

### Node 6 | Read Quotations JSON (HTTP Request)

讀取 GitHub Raw 的 `quotations.json`（無需認證）。

- **Method**: GET
- **URL**: `https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json`

**Output**: JSON 物件（含 `lastUpdated`, `totalRecords`, `data`）

---

### Node 7 | Search & Build Flex (Code JS)

解析 JSON、執行搜尋、建立 Flex Message Carousel。

```javascript
// 搜尋與建立 Flex Message
const { searchMode, keyword, replyToken } = $input.first().json;
const jsonResponse = $('Read Quotations JSON').first().json;

// 取得資料陣列
const rows = jsonResponse.data || [];

// 搜尋邏輯
const fieldMap = { '品名': '品名', '廠商': '廠商', '加工類型': '加工類型' };
const field = fieldMap[searchMode] || '品名';
const keyLower = keyword.toLowerCase();

const results = rows
  .filter(row => row[field] && row[field].toLowerCase().includes(keyLower))
  .sort((a, b) => new Date(b['時間戳記']) - new Date(a['時間戳記']))
  .slice(0, 10);

const total = rows.filter(row => row[field] && row[field].toLowerCase().includes(keyLower)).length;

if (!results.length) {
  return [{
    json: {
      replyToken,
      messageType: 'text',
      text: `「${keyword}」查無相關報價資料 😕\n\n請重新搜尋或點選按鈕：`,
      hasQuickReply: true
    }
  }];
}

// 建立 Flex Message Bubbles
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
    action: { type: 'uri', label: '查看報價單 →', uri: driveUrl }
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
        type: 'text', text: `共 ${total} 筆結果\n顯示最新 10 筆`,
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
    altText: `「${keyword}」共 ${total} 筆報價資料`,
    hasQuickReply: true
  }
}];
```

---

### Node 8 | Reply Result (HTTP Request)

回傳搜尋結果（Flex Message 或 Text）+ Quick Reply。

- **Method**: POST
- **URL**: `https://api.line.me/v2/bot/message/reply`
- **Headers**:
  - `Authorization`: `Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}`
- **Body** (JS Expression):
```javascript
{{ 
  const msg = $json.messageType === 'flex' 
    ? { type: 'flex', altText: $json.altText, contents: $json.flexContents }
    : { type: 'text', text: $json.text };
    
  const quickReply = $json.hasQuickReply ? {
    items: [
      { type: 'action', action: { type: 'message', label: '🔍 品名搜尋', text: '品名搜尋' }},
      { type: 'action', action: { type: 'message', label: '🏭 廠商搜尋', text: '廠商搜尋' }},
      { type: 'action', action: { type: 'message', label: '⚙️ 加工類型搜尋', text: '加工類型搜尋' }}
    ]
  } : undefined;
  
  if (quickReply) msg.quickReply = quickReply;
  
  return JSON.stringify({
    replyToken: $json.replyToken,
    messages: [msg]
  });
}}
```

---

## 環境變數對應表

| 變數名 | 用於 Node | 說明 |
|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | 4, 5, 8 | Bearer Token 認證 |
| `N8N_HOST` | 文件說明 | `https://alstonn8n2026.zeabur.app` |
| `N8N_WEBHOOK_PATH` | 文件說明 | `/webhook/line-quotation` |
| `JSON_DB_URL` | 6 | `quotations.json` 公開網址（可選，若不寫死 URL） |

---

## 程式碼慣例

- 所有 Code node 使用 **ES2020 JavaScript**（n8n 內建 V8）
- 欄位名稱沿用原 Google Sheets header row 的**中文欄位名稱**（`品名`, `廠商`, `加工類型`...）
- 搜尋比對統一轉 `toLowerCase()` 後做 `includes()`
- Flex Message 遵循 [LINE Flex Message Simulator](https://developers.line.biz/flex-simulator/) 規範
- **指令格式**：`品名:關鍵字` / `廠商:關鍵字` / `加工類型:關鍵字`（支援全形冒號 `：` 及空格分隔）

---

## 已知限制

- Google Drive 連結部分為 `open?id=` 格式，直接以 URI Action 開啟，無法在 LINE 內預覽圖片
- 若欄 F 有多個 Drive 連結（逗號分隔），目前只取第一個
- JSON 資料更新頻率取決於同步排程；非即時讀取試算表
- Stateless 設計：每次請求獨立執行，無法記憶使用者上次搜尋內容
