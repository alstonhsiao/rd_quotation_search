#!/usr/bin/env python3
"""
測試 quotations.json 格式
"""

import json
import sys

def test_json_format(json_file="quotations.json"):
    """驗證 JSON 檔案格式"""
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 檢查必要欄位
        required_fields = ["lastUpdated", "totalRecords", "data"]
        for field in required_fields:
            if field not in data:
                print(f"❌ 缺少必要欄位: {field}")
                return False
        
        # 檢查資料格式
        if not isinstance(data["data"], list):
            print("❌ data 欄位必須是陣列")
            return False
        
        # 檢查第一筆資料的欄位
        if len(data["data"]) > 0:
            first_row = data["data"][0]
            expected_fields = ["時間戳記", "加工類型", "廠商", "填表人", "品名", "拍照報價單", "備註"]
            
            print(f"✅ 總筆數: {data['totalRecords']}")
            print(f"✅ 實際筆數: {len(data['data'])}")
            print(f"✅ 最後更新: {data['lastUpdated']}")
            print(f"\n📋 第一筆資料欄位:")
            
            for field in expected_fields:
                if field in first_row:
                    value = str(first_row[field])[:50]
                    print(f"  ✓ {field}: {value}...")
                else:
                    print(f"  ⚠️  {field}: (缺少)")
        
        print(f"\n✅ JSON 格式正確")
        return True
        
    except FileNotFoundError:
        print(f"❌ 找不到檔案: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "quotations.json"
    success = test_json_format(json_file)
    sys.exit(0 if success else 1)
