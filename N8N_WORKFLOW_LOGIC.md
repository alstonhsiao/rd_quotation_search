# n8n Workflow 流程邏輯分析

## 架構概覽

```
LINE Webhook (接收) 
  ↓
Parse & Route (解析判斷)
  ↓
Switch Action (三路分支)
  ├→ [提示路徑] Reply Prompt → (直接回覆 LINE)
  ├→ [搜尋路徑] Read Quotations JSON → Search & Build Flex → Reply Result → (回覆 LINE)
  └→ [說明路徑] Reply Help → (直接回覆 LINE)
```

---

## 詳細節點流程

### 🟢 Node 1: LINE Webhook
**類型**: `n8n-nodes-base.webhook`

**設定**:
```json
{
  "httpMethod": "POST",
  "path": "line-quotation",
  "responseMode": "onReceived"  // 立即回應 200 OK
}
```

**功能**:
- 接收 LINE Messaging API 的 POST 請求
- webhook URL: `https://alstonn8n2026.zeabur.app/webhook/line-quotation`
- `responseMode: onReceived` → 立即回傳 200 OK 給 LINE，避免 timeout

**輸入資料結構** (LINE webhook payload):
```json
{
  "events": [
    {
      "type": "message",
      "message": {
        "type": "text",
        "text": "品名:棘輪"
      },
      "replyToken": "xxxxx",
      "source": {
        "userId": "Uxxxx"
      }
    }
  ]
}
```

**n8n 內部處理**:
- n8n 會將 POST body 包裝為 `$input.first().json.body`
- 但 API 測試時可能直接是 `$input.first().json`
- 因此 Parse & Route 做了相容處理：`const body = input.body || input;`

**輸出 → Parse & Route**

---

### 🔵 Node 2: Parse & Route
**類型**: `n8n-nodes-base.code` (JavaScript)

**功能**: 解析使用者訊息，判斷是「按鈕點選」、「搜尋指令」或「需要說明」

**核心邏輯**:
```javascript
// 取得輸入（相容 LINE webhook 和 API 測試）
const input = $input.first().json;
const body = input.body || input;  // ← 關鍵：相容性處理
const event = body.events?.[0];

// 驗證訊息類型
if (!event || event.type !== 'message' || event.message.type !== 'text') {
  return [];  // 不是文字訊息，忽略
}

const text = event.message.text.trim();
```

**路由判斷邏輯** (3 種情況):

#### 情況 1: 按鈕點選（模式選擇）
```javascript
const modeButtons = ['品名搜尋', '廠商搜尋', '加工類型搜尋'];

if (modeButtons.includes(text)) {
  // 使用者點選 Quick Reply 按鈕
  const modeMap = { 
    '品名搜尋': '品名', 
    '廠商搜尋': '廠商', 
    '加工類型搜尋': '加工類型' 
  };
  
  return [{
    json: {
      action: 'prompt',         // ← 路由到「提示」
      replyToken,
      searchMode: modeMap[text]
    }
  }];
}
```

#### 情況 2: 搜尋指令（格式：`模式:關鍵字`）
```javascript
// 正則表達式：支援全形冒號、空格分隔
const match = text.match(/^(品名|廠商|加工類型)[:：\s]+(.+)$/i);

if (match) {
  return [{
    json: {
      action: 'search',          // ← 路由到「搜尋」
      replyToken,
      userId,
      searchMode: match[1],      // 品名/廠商/加工類型
      keyword: match[2].trim()   // 關鍵字
    }
  }];
}
```

#### 情況 3: 其他情況（顯示說明）
```javascript
// 預設：不符合以上兩種格式
return [{
  json: {
    action: 'help',              // ← 路由到「說明」
    replyToken
  }
}];
```

**輸出格式**:
```json
// 提示路徑
{ "action": "prompt", "replyToken": "...", "searchMode": "品名" }

// 搜尋路徑
{ "action": "search", "replyToken": "...", "searchMode": "品名", "keyword": "棘輪", "userId": "..." }

// 說明路徑
{ "action": "help", "replyToken": "..." }
```

**輸出 → Switch Action**

---

### 🟡 Node 3: Switch Action
**類型**: `n8n-nodes-base.switch`

**功能**: 根據 `action` 欄位路由到不同節點

**條件規則**:
```json
{
  "rules": {
    "values": [
      {
        "conditions": { "string": [{ "value1": "={{ $json.action }}", "value2": "prompt" }] },
        "outputKey": "提示"
      },
      {
        "conditions": { "string": [{ "value1": "={{ $json.action }}", "value2": "search" }] },
        "outputKey": "搜尋"
      },
      {
        "conditions": { "string": [{ "value1": "={{ $json.action }}", "value2": "help" }] },
        "outputKey": "說明"
      }
    ]
  }
}
```

**3 個輸出分支**:
- **[提示]** → Reply Prompt
- **[搜尋]** → Read Quotations JSON
- **[說明]** → Reply Help

---

## 🔀 路徑 A: 提示路徑 (Prompt Path)

### 🟢 Node 4: Reply Prompt
**類型**: `n8n-nodes-base.httpRequest`

**功能**: 回覆使用者如何輸入搜尋指令

**HTTP 請求設定**:
```json
{
  "method": "POST",
  "url": "https://api.line.me/v2/bot/message/reply",
  "headers": {
    "Authorization": "Bearer [LINE_CHANNEL_ACCESS_TOKEN]"
  }
}
```

**Body 內容** (動態):
```json
{
  "replyToken": "{{ $json.replyToken }}",
  "messages": [{
    "type": "text",
    "text": "請輸入格式：{{ $json.searchMode }}:關鍵字\n\n範例：\n品名:棘輪\n廠商:亮新\n加工類型:表面處理"
  }]
}
```

**使用者看到**:
```
請輸入格式：品名:關鍵字

範例：
品名:棘輪
廠商:亮新
加工類型:表面處理
```

**流程結束** (此路徑不繼續往下)

---

## 🔍 路徑 B: 搜尋路徑 (Search Path) ← 核心功能

### 🟢 Node 6: Read Quotations JSON
**類型**: `n8n-nodes-base.httpRequest`

**功能**: 從 GitHub 讀取 JSON 資料庫

**HTTP 請求設定**:
```json
{
  "method": "GET",
  "url": "https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json"
}
```

**回應資料結構**:
```json
{
  "lastUpdated": "2026-03-19T06:33:08",
  "totalRecords": 490,
  "data": [
    {
      "時間戳記": "2026/3/17 下午 5:03:36",
      "加工類型": "表面處理",
      "廠商": "新三和",
      "填表人": "林啟生",
      "品名": "起子手柄",
      "拍照報價單": "https://drive.google.com/open?id=...",
      "備註": "單價 $35/件"
    },
    // ...489 筆資料
  ]
}
```

**輸出 → Search & Build Flex**

---

### 🔵 Node 7: Search & Build Flex
**類型**: `n8n-nodes-base.code` (JavaScript)

**功能**: 搜尋資料 + 建立 Flex Message Carousel

**核心邏輯** (分 4 步驟):

#### 步驟 1: 取得輸入資料
```javascript
const { searchMode, keyword, replyToken } = $input.first().json;
const jsonResponse = $('Read Quotations JSON').first().json;
const rows = jsonResponse.data || [];
```

#### 步驟 2: 搜尋邏輯
```javascript
// 欄位對應
const fieldMap = { '品名': '品名', '廠商': '廠商', '加工類型': '加工類型' };
const field = fieldMap[searchMode] || '品名';
const keyLower = keyword.toLowerCase();

// 篩選 + 排序 + 取前 10 筆
const results = rows
  .filter(row => row[field] && row[field].toLowerCase().includes(keyLower))
  .sort((a, b) => new Date(b['時間戳記']) - new Date(a['時間戳記']))
  .slice(0, 10);

const total = rows.filter(row => row[field] && row[field].toLowerCase().includes(keyLower)).length;
```

**搜尋特性**:
- **不區分大小寫**: `keyword.toLowerCase()`
- **模糊搜尋**: `includes()` 而非精確比對
- **排序**: 依時間戳記由新到舊
- **限制筆數**: 最多顯示 10 筆

#### 步驟 3: 無結果處理
```javascript
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
```

#### 步驟 4: 建立 Flex Message
```javascript
const bubbles = results.map(row => {
  const driveUrl = (row['拍照報價單'] || '').split(',')[0].trim();
  const dateStr = (row['時間戳記'] || '').substring(0, 10);
  const hasNote = row['備註'] && row['備註'].trim();
  const hasDrive = driveUrl.startsWith('http');

  // Body 內容
  const bodyContents = [
    { type: 'text', text: row['品名'] || '(無品名)', weight: 'bold', size: 'md', wrap: true },
    { type: 'separator', margin: 'sm' },
    {
      type: 'box', layout: 'vertical', spacing: 'xs', margin: 'sm',
      contents: [
        // 加工類型
        {
          type: 'box', layout: 'baseline',
          contents: [
            { type: 'text', text: '加工', size: 'sm', color: '#888888', flex: 2 },
            { type: 'text', text: row['加工類型'] || '-', size: 'sm', flex: 5, wrap: true }
          ]
        },
        // 廠商
        { type: 'box', layout: 'baseline', contents: [...] },
        // 填表人
        { type: 'box', layout: 'baseline', contents: [...] },
        // 日期
        { type: 'box', layout: 'baseline', contents: [...] }
      ]
    }
  ];

  // 備註（如果有）
  if (hasNote) {
    const noteText = row['備註'].length > 60 ? row['備註'].substring(0, 60) + '…' : row['備註'];
    bodyContents.push({ type: 'separator', margin: 'sm' });
    bodyContents.push({ type: 'text', text: noteText, size: 'xs', color: '#666666', wrap: true, margin: 'sm' });
  }

  // Footer：報價單按鈕或提示
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

// 如果超過 10 筆，加上提示卡片
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
```

**輸出格式**:
```json
{
  "replyToken": "...",
  "messageType": "flex",
  "flexContents": {
    "type": "carousel",
    "contents": [
      { /* bubble 1 */ },
      { /* bubble 2 */ },
      // ...最多 11 個 bubbles (10 筆資料 + 1 個提示卡片)
    ]
  },
  "altText": "「棘輪」共 15 筆報價資料",
  "hasQuickReply": true
}
```

**輸出 → Reply Result**

---

### 🟢 Node 8: Reply Result
**類型**: `n8n-nodes-base.httpRequest`

**功能**: 回傳 Flex Message 或文字訊息到 LINE

**HTTP 請求設定**:
```json
{
  "method": "POST",
  "url": "https://api.line.me/v2/bot/message/reply",
  "headers": {
    "Authorization": "Bearer [LINE_CHANNEL_ACCESS_TOKEN]"
  }
}
```

**Body 內容** (動態生成):
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

**最終傳送到 LINE 的 JSON**:
```json
{
  "replyToken": "xxxxx",
  "messages": [
    {
      "type": "flex",
      "altText": "「棘輪」共 15 筆報價資料",
      "contents": { /* Flex Message Carousel */ },
      "quickReply": {
        "items": [
          { "type": "action", "action": { "type": "message", "label": "🔍 品名搜尋", "text": "品名搜尋" }},
          { "type": "action", "action": { "type": "message", "label": "🏭 廠商搜尋", "text": "廠商搜尋" }},
          { "type": "action", "action": { "type": "message", "label": "⚙️ 加工類型搜尋", "text": "加工類型搜尋" }}
        ]
      }
    }
  ]
}
```

**使用者在 LINE 看到**:
- Flex Message Carousel 卡片（可左右滑動）
- 每張卡片包含品名、加工類型、廠商、填表人、日期、備註、報價單按鈕
- 底部有 3 個 Quick Reply 按鈕

**流程結束**

---

## 📘 路徑 C: 說明路徑 (Help Path)

### 🟢 Node 5: Reply Help
**類型**: `n8n-nodes-base.httpRequest`

**功能**: 顯示使用說明 + Quick Reply 按鈕

**HTTP 請求設定**:
```json
{
  "method": "POST",
  "url": "https://api.line.me/v2/bot/message/reply",
  "headers": {
    "Authorization": "Bearer [LINE_CHANNEL_ACCESS_TOKEN]"
  }
}
```

**Body 內容**:
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

**使用者看到**:
```
👋 首君報價查詢系統

請點選搜尋方式，或直接輸入：
品名:關鍵字
廠商:關鍵字
加工類型:關鍵字

[🔍 品名搜尋] [🏭 廠商搜尋] [⚙️ 加工類型搜尋]
```

**流程結束**

---

## 🔄 完整執行流程圖（UML Sequence Diagram）

```
LINE User          LINE API          n8n Webhook          Parse & Route          Switch          [提示/搜尋/說明 路徑]          LINE API
   |                  |                    |                      |                   |                    |                      |
   |-- 品名:棘輪 ---->|                    |                      |                   |                    |                      |
   |                  |-- POST webhook --->|                      |                   |                    |                      |
   |                  |                    |-- 200 OK ----------->|                   |                    |                      |
   |                  |                    |                      |                   |                    |                      |
   |                  |                    |-- Parse input ------>|                   |                    |                      |
   |                  |                    |                      |-- Regex match --->|                   |                      |
   |                  |                    |                      |                   |-- action:search -->|                      |
   |                  |                    |                      |                   |                    |-- Read JSON -------->|
   |                  |                    |                      |                   |                    |<--- 490 records -----|
   |                  |                    |                      |                   |                    |                      |
   |                  |                    |                      |                   |                    |-- Filter & Sort ---->|
   |                  |                    |                      |                   |                    |-- Build Flex Msg --->|
   |                  |                    |                      |                   |                    |                      |
   |                  |                    |                      |                   |                    |-- POST reply ------->|
   |                  |<--------------------------- Flex Message Carousel -------------------------------|                      |
   |<-- Flex 卡片 ----|                    |                      |                   |                    |                      |
   |                  |                    |                      |                   |                    |                      |
```

---

## 🧠 設計決策與理由

### 1. Stateless 設計
**為什麼不保存 session？**
- n8n 不適合做狀態管理（無內建 session 機制）
- 每次請求獨立執行，避免資料污染
- 簡化邏輯，降低錯誤率

**Trade-off**:
- ✅ 簡單、穩定、易維護
- ❌ 使用者需要記住指令格式（透過 Quick Reply 緩解）

### 2. JSON 資料庫 vs 即時讀取 Google Sheets
**為什麼使用 GitHub JSON？**
- Google Sheets 需要 Service Account 或 OAuth（複雜）
- n8n 到 Google API 可能有網路限制
- GitHub Raw 檔案無需認證，讀取速度快
- JSON 結構化資料，搜尋效率高

**Trade-off**:
- ✅ 簡單、快速、無認證問題
- ❌ 資料非即時（需手動同步）

### 3. Flex Message 而非純文字
**為什麼使用 Flex Message？**
- 視覺化呈現，資訊密度高
- 支援按鈕（報價單連結）
- Carousel 可滑動瀏覽多筆結果
- 專業感，提升使用體驗

**Trade-off**:
- ✅ 美觀、易讀、互動性強
- ❌ 程式碼較複雜、維護成本高

### 4. responseMode: onReceived
**為什麼立即回應 200 OK？**
- LINE Messaging API 有 3 秒 timeout 限制
- Read Quotations JSON + Search 可能超過 3 秒
- 先回應 200 OK，再非同步處理，避免 LINE 重送請求

**Trade-off**:
- ✅ 避免 timeout 錯誤
- ❌ 無法取得處理結果狀態碼（但 n8n 有執行記錄可查）

### 5. 正則表達式支援多種格式
```javascript
/^(品名|廠商|加工類型)[:：\s]+(.+)$/i
```
**為什麼支援全形冒號和空格？**
- 使用者可能用手機輸入（預設全形標點）
- 提升容錯性，減少輸入錯誤

**Trade-off**:
- ✅ 使用者體驗佳
- ❌ 正則表達式稍複雜

---

## 🐛 已知問題與限制

### 1. Webhook 註冊問題
**現象**: API activate 無法觸發 production webhook 註冊

**原因**: n8n Zeabur 平台限制

**解決方式**: 必須在 Web UI 手動開關 Active toggle

**影響**: 每次更新 workflow 都需要手動操作

---

### 2. 資料更新延遲
**現象**: Google Sheets 更新後，LINE bot 不會立即看到新資料

**原因**: 使用 GitHub JSON 資料庫（非即時）

**解決方式**: 手動執行 `python3 scripts/sync_sheets_manual.py` + `git push`

**影響**: 需要額外維護成本

---

### 3. Parse & Route 相容性
**現象**: LINE webhook 和 API 測試的輸入格式不同

**原因**: 
- LINE webhook: `$input.first().json.body.events`
- API 測試: `$input.first().json.events`

**解決方式**: `const body = input.body || input;`

**影響**: 程式碼需考慮相容性

---

### 4. 報價單連結無法預覽
**現象**: Google Drive 連結在 LINE 內無法顯示縮圖

**原因**: Drive 連結是 `open?id=` 格式，不是直接圖片 URL

**解決方式**: 無（需要使用者手動點擊開啟）

**影響**: 使用體驗較差

---

## 🚀 未來優化建議

### 1. 自動化資料同步
```bash
# 方案 A: Google Sheets API + Service Account
pip install gspread oauth2client
# 每小時自動讀取 Sheets → JSON → Git push

# 方案 B: Google Apps Script Webhook
# Sheets 更新時自動 POST 到 n8n webhook
# n8n 接收後更新 JSON 並推送到 GitHub
```

### 2. 圖片預覽優化
```javascript
// 方案：將 Drive 圖片轉為直接圖片 URL
// 在 Flex Message 中加入預覽圖
{
  "type": "image",
  "url": "https://drive.google.com/uc?id=FILE_ID",
  "size": "md",
  "aspectRatio": "4:3"
}
```

### 3. 模糊搜尋增強
```javascript
// 方案：使用 Fuse.js 或 Levenshtein distance
// 支援錯字容錯（例：「棘輪」誤打成「戟輪」）
const fuse = new Fuse(rows, { keys: ['品名'], threshold: 0.3 });
const results = fuse.search(keyword);
```

### 4. 搜尋歷史記錄
```javascript
// 方案：使用 n8n Database node 或外部 Redis
// 記錄每個使用者的搜尋歷史，提供「最近搜尋」按鈕
```

---

**建立時間**: 2026-03-19  
**最後更新**: 2026-03-19  
**文件版本**: v1.0
