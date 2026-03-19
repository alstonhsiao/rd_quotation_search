# Scripts 資料夾

本資料夾存放 rd_quotation_search 專案的所有實用腳本工具。

---

## 📂 腳本列表

### 1. test_line_bot.sh
**用途**：LINE bot webhook 自動化測試腳本

**功能**：
- 測試 3 種搜尋類型（品名、廠商、加工類型）
- 使用 curl 模擬 LINE webhook 請求
- 快速驗證 n8n workflow 是否正常運作

**使用方式**：
```bash
cd /Users/alston/Documents/AntiGravity/rd_quotation_search
./scripts/test_line_bot.sh
```

**預期輸出**：
- 正常：`{"message":"Workflow was started"}` (HTTP 200)
- 錯誤：`{"code":404,"message":"The requested webhook..."}` → 需要手動修復 webhook

**適用場景**：
- 每次修改 workflow 後驗證
- 檢查 webhook 是否已正確註冊
- 快速測試不需要開啟 LINE app

---

### 2. debug_exec.py
**用途**：n8n 執行記錄分析工具

**功能**：
- 解析 n8n execution JSON 檔案
- 顯示執行狀態、錯誤訊息、節點執行情況
- 幫助快速定位 workflow 問題

**使用方式**：
```bash
# 1. 先下載執行記錄
curl -s "$N8N_HOST/api/v1/executions/33951" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  > /tmp/exec_33951.json

# 2. 分析執行記錄
python3 scripts/debug_exec.py 33951
```

**輸出範例**：
```
=== 執行記錄 33951 ===
狀態: error
Workflow: WUI9OBlNcbvalbs8
開始: 2026-03-19T06:40:46.746Z
結束: 2026-03-19T06:40:46.826Z

📋 節點執行狀況:
  ✅ LINE Webhook (0.04s)
  ❌ Parse & Route: ReferenceError: body is not defined
```

**適用場景**：
- workflow 執行失敗時追蹤原因
- 檢查哪個節點出錯
- 分析執行時間瓶頸

---

### 3. sync_sheets_manual.py
**用途**：CSV 到 JSON 資料轉換工具

**功能**：
- 將 Google Sheets 匯出的 CSV 轉換為 `quotations.json`
- 自動計算總筆數和更新時間
- 保持 n8n workflow 所需的 JSON 格式

**使用方式**：
```bash
# 1. 從 Google Sheets 下載 CSV 檔案
#    (手動操作：檔案 > 下載 > 逗號分隔值 (.csv))

# 2. 執行轉換（預設讀取 data.csv）
python3 scripts/sync_sheets_manual.py

# 3. 推送到 GitHub
git add quotations.json
git commit -m "data: update quotations (新增 X 筆)"
git push
```

**輸出範例**：
```
✅ 成功轉換 490 筆資料
📁 已儲存至: quotations.json
```

**適用場景**：
- Google Sheets 有新報價資料時更新
- 手動資料同步（推薦方式，因無 Service Account）
- 驗證資料格式是否正確

**注意事項**：
- CSV 檔案必須使用 UTF-8 編碼
- 欄位順序必須與試算表一致（時間戳記、加工類型、廠商...）
- 轉換後記得 git push，n8n workflow 才會讀到新資料

---

### 4. test_json.py
**用途**：JSON 格式驗證工具

**功能**：
- 檢查 `quotations.json` 格式是否正確
- 驗證必要欄位（lastUpdated, totalRecords, data）
- 顯示資料統計和範例

**使用方式**：
```bash
python3 scripts/test_json.py
```

**輸出範例**：
```
✅ JSON 格式正確
📊 總筆數: 490
🕒 更新時間: 2026-03-19T06:33:08
📝 第一筆資料:
  - 品名: 起子手柄
  - 廠商: 新三和
  - 加工類型: 塑膠射出
```

**適用場景**：
- 執行 sync_sheets_manual.py 後驗證
- 檢查 JSON 結構是否符合 n8n workflow 需求
- 快速查看資料內容

---

### 5. sync_local.sh
**用途**：自動化本機同步腳本（未來擴充用）

**功能**：
- 檢查是否有新的 CSV 檔案（latest.csv）
- 自動執行轉換並推送到 GitHub
- 可設定 crontab 定時執行

**使用方式**：
```bash
# 手動執行
./scripts/sync_local.sh

# 設定自動化（crontab）
crontab -e
# 加入：09:00 和 21:00 自動執行
0 9 * * * cd /path/to/repo && ./scripts/sync_local.sh
0 21 * * * cd /path/to/repo && ./scripts/sync_local.sh
```

**注意事項**：
- 目前需要手動從 Google Sheets 下載 CSV 並重新命名為 latest.csv
- 未來可考慮整合 Google Sheets API（需要 Service Account）

**適用場景**：
- 需要定時自動同步資料
- 減少手動操作步驟
- 目前為可選腳本（手動執行 sync_sheets_manual.py 更直接）

---

## 🔧 環境變數設定

部分腳本需要環境變數（存放於 `.env.local`，不提交到 Git）：

```bash
# n8n API 設定
export N8N_HOST="https://alstonn8n2026.zeabur.app"
export N8N_API_KEY="eyJhbGci..."

# LINE Bot 設定
export LINE_CHANNEL_ACCESS_TOKEN="0O5969QUf..."
export LINE_CHANNEL_SECRET="7e1ad856..."
```

**載入方式**：
```bash
source .env.local
```

---

## 🗂️ 檔案關聯圖

```
專案根目錄
├── scripts/
│   ├── README.md (本文件)
│   ├── test_line_bot.sh         → 測試 n8n webhook
│   ├── debug_exec.py            → 分析 n8n 執行記錄
│   ├── sync_sheets_manual.py   → CSV → JSON 轉換
│   ├── test_json.py             → 驗證 JSON 格式
│   └── sync_local.sh            → 自動化同步（可選）
│
├── quotations.json              ← sync_sheets_manual.py 輸出
├── data.csv                     ← Google Sheets 匯出（手動下載）
├── n8n_workflow.json            ← workflow 定義檔
│
└── 文件
    ├── AGENTS.md                → AI Agent 完整說明
    ├── WEBHOOK_FIX_GUIDE.md     → webhook 手動修復指引
    └── TEST_AND_TEMPLATES.md    → 測試範本和疑難排解
```

---

## 🚀 常見工作流程

### 場景 1：更新報價資料

```bash
# 1. 從 Google Sheets 下載 CSV
#    (手動：檔案 > 下載 > 逗號分隔值)

# 2. 將檔案重新命名為 data.csv，放在專案根目錄

# 3. 執行轉換
python3 scripts/sync_sheets_manual.py

# 4. 驗證格式（可選）
python3 scripts/test_json.py

# 5. 推送到 GitHub
git add quotations.json
git commit -m "data: update quotations (新增 5 筆)"
git push

# LINE bot 會自動讀取更新後的 JSON（無需重新部署）
```

### 場景 2：修改 workflow 後測試

```bash
# 1. 在 n8n UI 中修改 workflow

# 2. 手動開關 Active toggle（確保 webhook 註冊）

# 3. 測試 webhook
./scripts/test_line_bot.sh

# 4. 如果測試失敗，檢查執行記錄
curl -s "$N8N_HOST/api/v1/executions?limit=1" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"

# 假設得到 exec ID: 34001
curl -s "$N8N_HOST/api/v1/executions/34001" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  > /tmp/exec_34001.json

python3 scripts/debug_exec.py 34001
```

### 場景 3：新環境設定

```bash
# 1. Clone 專案
git clone https://github.com/alstonhsiao/rd_quotation_search.git
cd rd_quotation_search

# 2. 建立環境變數檔案
cp .env.local.example .env.local
nano .env.local  # 填入實際的 token

# 3. 載入環境變數
source .env.local

# 4. 測試 webhook 連線
./scripts/test_line_bot.sh

# 5. 匯入 workflow 到 n8n
#    (在 n8n UI: Import from File → 選擇 n8n_workflow.json)

# 6. 手動開關 Active toggle 註冊 webhook
```

---

## 📋 維護檢查清單

定期檢查（每月一次）：

- [ ] 執行 `test_json.py` 確認資料格式正確
- [ ] 執行 `test_line_bot.sh` 確認 webhook 正常
- [ ] 檢查 n8n workflow 是否有 execution errors
- [ ] 確認 GitHub Actions 無錯誤（如有設定）
- [ ] 備份 `quotations.json` 到其他位置

---

## 🐛 疑難排解

### 問題：test_line_bot.sh 顯示 404 錯誤
**解決方式**：參考 [WEBHOOK_FIX_GUIDE.md](../WEBHOOK_FIX_GUIDE.md) 手動開關 Active toggle

### 問題：sync_sheets_manual.py 轉換失敗
**檢查項目**：
1. CSV 檔案編碼是否為 UTF-8
2. CSV 檔案是否存在且可讀取
3. 欄位數量是否正確（7 欄）

### 問題：debug_exec.py 找不到檔案
**解決方式**：
```bash
# 先下載執行記錄到 /tmp/
curl -s "$N8N_HOST/api/v1/executions/[EXEC_ID]" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  > /tmp/exec_[EXEC_ID].json
```

---

**最後更新**：2026-03-19  
**專案版本**：v1.0  
**維護者**：alston hsiao
