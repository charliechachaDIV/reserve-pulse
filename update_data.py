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
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()
    obs = data.get("observations", [])

    if len(obs) < 2:
        raise ValueError("FRED 回傳資料不足")

    # FRED TOTRESNS 單位為：Billions of Dollars (十億美元)
    # 取最新兩筆有效數值
    valid_obs = [x for x in obs if x["value"] != "."]
    latest_val_b = float(valid_obs[0]["value"])
    prev_val_b = float(valid_obs[1]["value"])

    latest_t = round(latest_val_b / 1000, 2)     # 換算為兆美元 ($T)
    change_b = round(latest_val_b - prev_val_b, 1)  # 週變動 (十億美元)

    return {
        "date": valid_obs[0]["date"],
        "current_t": latest_t,
        "current_b": latest_val_b,
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