import os
import json
import requests
import yfinance as yf
from datetime import datetime

# 優先讀取環境變數，若無則使用你剛才提供的 Key
API_KEY = os.environ.get("FRED_API_KEY", "d7180845cdf189a918813171895e9aa8")

def fetch_reserve_data():
    """從 FRED API 抓取銀行準備金總額 (TOTRESNS)"""
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=WRESBAL&api_key={API_KEY}&file_type=json&sort_order=desc&limit=12"
    )
    # 修改為 30 秒或更長
    res = requests.get(url, timeout=30)
    res.raise_for_status()
    data = res.json()
    obs = data.get("observations", [])

    if len(obs) < 2:
        raise ValueError("FRED 回傳資料不足")

    # FRED TOTRESNS 單位為：Billions of Dollars (十億美元)
    # FRED WRESBAL 單位為：Millions of Dollars (百萬美元)
    valid_obs = [x for x in obs if x["value"] != "."]
    latest_val_m = float(valid_obs[0]["value"])
    prev_val_m = float(valid_obs[1]["value"])

    # 換算為兆美元 ($T) 需要除以一百萬
    latest_t = round(latest_val_m / 1000000, 3)     
    
    # 週變動換算為十億美元 ($B) 需要除以一千
    change_b = round((latest_val_m - prev_val_m) / 1000, 1)  

    return {
        "date": valid_obs[0]["date"],
        "current_t": latest_t,
        "current_b": latest_val_m / 1000,
        "change_b": change_b,
        "status": "消耗中" if change_b < 0 else "補水中"
    }

def fetch_market_data():
    """從 Yahoo Finance 抓取 VIX 與 S&P 500 (^GSPC)"""
    vix_ticker = yf.Ticker("^VIX")
    sp_ticker = yf.Ticker("^GSPC")

    vix_val = round(vix_ticker.history(period="5d")['Close'].iloc[-1], 1)
    sp_val = int(sp_ticker.history(period="5d")['Close'].iloc[-1])

    if vix_val < 18:
        vix_phase = "充盈期"
    elif vix_val <= 25:
        vix_phase = "摩擦期"
    else:
        vix_phase = "踩踏期"

    return {
        "vix": vix_val,
        "vix_phase": vix_phase,
        "sp500": sp_val
    }

def main():
    print("[1/2] 正在向 FRED 請求 TOTRESNS 數據...")
    # 把 reserve = () 改成下面這行
    reserve = fetch_reserve_data()

    print("[2/2] 正在抓取 VIX 與 S&P 500 數據...")
    market = fetch_market_data()

    # 組裝給前端使用的 JSON 結構
    output = {
        "updatedAt": reserve["date"],
        "totresns": {
            "current": reserve["current_t"],
            "rawBillions": reserve["current_b"],
            "weeklyChange": reserve["change_b"],
            "status": reserve["status"]
        },
        "vix": {
            "value": market["vix"],
            "phase": market["vix_phase"]
        },
        "sp500": market["sp500"]
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"成功更新 data.json！")
    print(f"基準日: {output['updatedAt']} | 準備金: ${output['totresns']['current']}T | VIX: {output['vix']['value']}")

if __name__ == "__main__":
    main()
