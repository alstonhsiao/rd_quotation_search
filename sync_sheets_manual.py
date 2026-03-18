#!/usr/bin/env python3
"""
手動同步方式：從匯出的 CSV 轉換為 JSON
使用方式：
1. 從 Google Sheets 下載 CSV（檔案 → 下載 → CSV）
2. 執行：python sync_sheets_manual.py input.csv
"""

import csv
import json
import sys
from datetime import datetime

def csv_to_json(csv_file, output_file="quotations.json"):
    """將 CSV 轉換為 JSON"""
    
    try:
        data = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        
        # 建立輸出結構
        output = {
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "totalRecords": len(data),
            "data": data
        }
        
        # 寫入 JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 成功轉換 {len(data)} 筆資料")
        print(f"📄 輸出檔案: {output_file}")
        print(f"📅 更新時間: {output['lastUpdated']}")
        
    except FileNotFoundError:
        print(f"❌ 找不到檔案: {csv_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 轉換失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方式: python sync_sheets_manual.py <csv檔案>")
        print("範例: python sync_sheets_manual.py 表單回應1.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    csv_to_json(csv_file)
