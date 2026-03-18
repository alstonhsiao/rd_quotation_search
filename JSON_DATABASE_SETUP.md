# JSON 資料庫部署指南

## 📋 架構說明

```
Google Sheets (私有)
    ↓
本機/GitHub Actions 同步腳本
    ↓
quotations.json (GitHub Repository)
    ↓
GitHub Pages / Raw URL (公開訪問)
    ↓
n8n Workflow 讀取並搜尋
    ↓
LINE Bot 回傳結果
```

---

## 🚀 部署步驟

### 步驟 1：初始化 Git Repository

```bash
cd /Users/alston/Documents/AntiGravity/rd_quotation_search

# 初始化 Git（如果尚未初始化）
git init
git add .
git commit -m "Initial commit: LINE quotation search system"

# 推送到 GitHub
gh repo create rd_quotation_search --public --source=. --push
# 或使用：
# git remote add origin https://github.com/YOUR_USERNAME/rd_quotation_search.git
# git push -u origin main
```

### 步驟 2：首次同步資料

#### 方法 A：手動匯出（推薦，因為沒有 Service Account）

1. 開啟 Google Sheets：
   https://docs.google.com/spreadsheets/d/1WZ_sZvfBjUiIPHrY6WkdR1yBXLHdYB_Fb8T3VTYQ0GI

2. 點選「檔案」→「下載」→「逗號分隔值 (.csv)」

3. 將下載的檔案重新命名為 `latest.csv` 並放在專案根目錄

4. 執行同步腳本：
   ```bash
   python3 sync_sheets_manual.py latest.csv
   ```

5. 推送到 GitHub：
   ```bash
   git add quotations.json
   git commit -m "🔄 Initial sync: quotations data"
   git push
   ```

#### 方法 B：使用 Service Account（如果有的話）

1. 取得 Google Service Account JSON 金鑰
2. 將 JSON 內容存為 `service_account.json`
3. 執行：
   ```bash
   pip install gspread oauth2client
   python3 sync_sheets_to_json.py
   git add quotations.json
   git commit -m "🔄 Initial sync: quotations data"
   git push
   ```

---

### 步驟 3：設定自動同步

#### 選項 A：本機 Cron（macOS/Linux）

1. 編輯 `sync_local.sh`，確認路徑正確

2. 設定 crontab：
   ```bash
   crontab -e
   ```

3. 加入以下兩行（每天 09:00 和 21:00 執行）：
   ```cron
   0 9 * * * /Users/alston/Documents/AntiGravity/rd_quotation_search/sync_local.sh >> /tmp/sync_sheets.log 2>&1
   0 21 * * * /Users/alston/Documents/AntiGravity/rd_quotation_search/sync_local.sh >> /tmp/sync_sheets.log 2>&1
   ```

4. **注意**：本機 cron 需要：
   - 手動將最新 CSV 下載並命名為 `latest.csv`
   - 或修改腳本自動從 Google Drive 下載（需要額外設定）

#### 選項 B：GitHub Actions（需要 Service Account）

1. 前往 GitHub Repository → Settings → Secrets and variables → Actions

2. 新增 Secret：
   - Name: `GOOGLE_SERVICE_ACCOUNT_JSON`
   - Value: 貼上完整的 Service Account JSON 內容

3. GitHub Actions 會自動執行 `.github/workflows/sync-sheets.yml`

4. 每天 09:00 和 21:00 UTC 自動執行

---

### 步驟 4：更新 n8n Workflow

1. 編輯 `n8n_workflow.json`，找到 `Read Quotations JSON` node

2. 將 URL 更新為您的 GitHub Repository：
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/rd_quotation_search/main/quotations.json
   ```
   **替換 `YOUR_USERNAME` 為您的 GitHub 使用者名稱**

3. 重新生成硬編碼版本：
   ```bash
   sed 's/Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}/Bearer YOUR_LINE_TOKEN/g' \
       n8n_workflow.json > n8n_workflow_deploy.json
   ```

4. 刪除舊 workflow 並上傳新版本：
   ```bash
   # 刪除舊的
   curl -X DELETE "https://alstonn8n2026.zeabur.app/api/v1/workflows/Vq6I9dhPOOWJ63Py" \
     -H "X-N8N-API-KEY: YOUR_N8N_API_KEY"
   
   # 上傳新的
   curl -X POST https://alstonn8n2026.zeabur.app/api/v1/workflows \
     -H "X-N8N-API-KEY: YOUR_N8N_API_KEY" \
     -H "Content-Type: application/json" \
     -d @n8n_workflow_deploy.json
   
   # 激活
   curl -X POST "https://alstonn8n2026.zeabur.app/api/v1/workflows/NEW_WORKFLOW_ID/activate" \
     -H "X-N8N-API-KEY: YOUR_N8N_API_KEY"
   ```

---

### 步驟 5：測試

1. 確認 JSON 可訪問：
   ```bash
   curl https://raw.githubusercontent.com/YOUR_USERNAME/rd_quotation_search/main/quotations.json
   ```

2. 測試 LINE Bot：
   - 發送：`品名:棘輪`
   - 應該回傳搜尋結果

---

## 🔄 日常維護

### 手動觸發同步

```bash
# 本機執行
./sync_local.sh

# 或使用 GitHub Actions
# 前往 Repository → Actions → 同步 Google Sheets 到 JSON → Run workflow
```

### 更新資料

當試算表有新資料時：
1. 下載最新 CSV（如果使用手動方式）
2. 執行同步腳本
3. Git commit & push

---

## ⚠️ 注意事項

- **quotations.json** 將被公開在 GitHub，確保不含敏感資訊
- 如果試算表有隱私資料，請先過濾後再匯出
- 建議定期備份試算表資料
- GitHub Actions 有每月執行時間限制（免費版 2000 分鐘）

---

## 🆘 疑難排解

### 問題：quotations.json 沒有更新

**檢查**：
```bash
# 查看 Git log
git log --oneline -5

# 查看 GitHub Actions 執行狀態
gh run list --limit 5
```

### 問題：LINE Bot 查無資料

**檢查**：
1. JSON 檔案格式是否正確
2. n8n workflow URL 是否正確
3. workflow 是否已激活

---

## 📚 相關檔案

- `sync_sheets_to_json.py` - Service Account 版同步腳本
- `sync_sheets_manual.py` - 手動 CSV 轉 JSON 腳本  
- `sync_local.sh` - 本機 cron 執行腳本
- `.github/workflows/sync-sheets.yml` - GitHub Actions 設定
- `quotations.json` - JSON 資料庫
