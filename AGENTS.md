# AGENTS.md — rd_quotation_search

本文件供 AI 代理人（GitHub Copilot、Claude 等）使用，說明此專案的背景、架構、程式碼慣例與所有 n8n Node 的完整設定細節。

---

## 專案背景

- **目的**：讓公司成員透過 LINE 搜尋「首君供應商報價管理表單」，快速找到歷史報價資料
- **部署環境**：n8n self-hosted (`https://alstonn8n2026.zeabur.app`)
- **資料來源**：GitHub 託管 JSON 資料庫（`quotations.json`，由同步流程定時更新）
- **資料筆數**：490 筆（最後更新：2026-03-19）
- **Workflow ID**：`Hr7UCyvl4DLJrQnc`（需手動在 UI 啟用 webhook）
- **前端**：LINE Messaging API（主目錄 Flex Message + 指令搜尋）
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

## n8n Workflow 架構（v2）

此 workflow 採用 **stateless 設計**，使用者輸入任意文字顯示主目錄，透過按鈕選擇搜尋模式後輸入關鍵字。

### 流程圖

```
LINE User Message
  ↓
[1] LINE Webhook (接收訊息)
  ↓
[2] Parse & Route (判斷：主目錄/提示/搜尋)
  ↓
[3] Switch (3-way routing)
  ├→ 主目錄：[4] Reply Menu (Flex Message，兩個按鈕)
  ├→ 提示：  [5] Reply Prompt (告知輸入格式)
  └→ 搜尋：  [6] Read Quotations JSON → [7] Search & Build Flex → [8] Reply Result
```

### 使用者互動流程

```
使用者輸入任意文字 → 主目錄 Flex（兩按鈕：搜尋加工類型 / 搜尋廠商）
  → 點選「搜尋加工類型」→ 提示「請輸入加工類型:關鍵字」
    → 輸入「加工類型:表面處理」→ 搜尋結果 Flex Carousel
  → 點選「搜尋廠商」→ 提示「請輸入廠商:關鍵字」
    → 輸入「廠商:新三和」→ 搜尋結果 Flex Carousel
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

解析 LINE 訊息，判斷為「模式選擇按鈕」、「搜尋指令」或「其他（顯示主目錄）」。

```javascript
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
    json: { action: 'prompt', replyToken, searchMode: modeMap[text] }
  }];
}

// 搜尋指令（格式：加工類型:關鍵字 或 廠商:關鍵字）
const match = text.match(/^(加工類型|廠商)[:：\s]+(.+)$/);
if (match) {
  return [{
    json: { action: 'search', replyToken, userId, searchMode: match[1], keyword: match[2].trim() }
  }];
}

// 預設：顯示主目錄
return [{ json: { action: 'menu', replyToken } }];
```

**Outputs**:
- `action === 'menu'` → Node 4 (Reply Menu)
- `action === 'prompt'` → Node 5 (Reply Prompt)
- `action === 'search'` → Node 6 (Read Quotations JSON)

---

### Node 3 | Switch Action

- **類型**: `n8n-nodes-base.switch`
- **條件**:
  1. `{{ $json.action }} === 'menu'` → 主目錄
  2. `{{ $json.action }} === 'prompt'` → 提示
  3. `{{ $json.action }} === 'search'` → 搜尋

---

### Node 4 | Reply Menu (HTTP Request)

回傳主目錄 Flex Message，含兩個按鈕。

- **Method**: POST
- **URL**: `https://api.line.me/v2/bot/message/reply`
- **Body**: Flex Message bubble，包含：
  - Header：`📋 首君報價查詢系統`（綠色背景）
  - Body：`請選擇查詢方式`
  - Footer：兩個按鈕
    - `🔍 搜尋加工類型`（綠色，送出 `搜尋加工類型`）
    - `🏭 搜尋廠商`（藍色，送出 `搜尋廠商`）

---

### Node 5 | Reply Prompt (HTTP Request)

提示使用者輸入搜尋關鍵字。

- **Method**: POST
- **URL**: `https://api.line.me/v2/bot/message/reply`
- **Body**: 動態文字訊息
  - 加工類型模式：`請輸入加工類型關鍵字\n\n格式：加工類型:關鍵字\n範例：加工類型:表面處理`
  - 廠商模式：`請輸入廠商關鍵字\n\n格式：廠商:關鍵字\n範例：廠商:新三和`

---

### Node 6 | Read Quotations JSON (HTTP Request)

讀取 GitHub Raw 的 `quotations.json`（無需認證）。

- **Method**: GET
- **URL**: `https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json`

---

### Node 7 | Search & Build Flex (Code JS)

搜尋資料並建立 Flex Message Carousel。

- **搜尋欄位**：`加工類型` 或 `廠商`（由 searchMode 決定）
- **搜尋方式**：`toLowerCase().includes()` 模糊比對
- **排序**：依時間戳記由新到舊
- **限制**：最多顯示 10 筆
- **無結果**：回傳文字訊息提示重新輸入
- **每張卡片**：品名、加工類型、廠商、填表人、日期、備註、報價單連結按鈕

---

### Node 8 | Reply Result (HTTP Request)

回傳搜尋結果（Flex Message Carousel 或 Text）。

- **Method**: POST
- **URL**: `https://api.line.me/v2/bot/message/reply`
- **Body**: 動態判斷 messageType（flex 或 text）

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
- **指令格式**：`加工類型:關鍵字` / `廠商:關鍵字`（支援全形冒號 `：` 及空格分隔）
- **設計特色**：Stateless（無 session 管理），任意文字顯示主目錄

---

## 已知限制

- Google Drive 連結部分為 `open?id=` 格式，直接以 URI Action 開啟，無法在 LINE 內預覽圖片
- 若欄 F 有多個 Drive 連結（逗號分隔），目前只取第一個
- JSON 資料更新頻率取決於同步排程；非即時讀取試算表
- Stateless 設計：每次請求獨立執行，無法記憶使用者上次搜尋內容
