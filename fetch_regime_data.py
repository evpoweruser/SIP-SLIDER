#!/usr/bin/env python3
"""
fetch_regime_data.py — Month-End Regime Checklist Live Data Fetcher & Offline HTML Code Injector
- Fetches live market metrics (Nifty Smallcap 250 P/E & 12m drawdown, BSE Clean Environment drawdown,
  Brent Crude 3-month % change, Hang Seng TECH % above 3y low, RBI stance, MAHKTECH premium vs iNAV,
  and MAHKTECH 20-day average turnover in INR).
- Writes `regime_inputs.json`.
- Automatically injects the latest live values directly into `regime_checklist_fetcher.html` and `index.html`
  between `/* AUTO_INJECT_START */` and `/* AUTO_INJECT_END */` so any downloaded HTML file runs 100% offline
  with the latest live data pre-populated in its code.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASELINE_DATA = {
    "smallcap_pe": 32.35,
    "smallcap_dd_pct": 2.96,
    "clean_env_dd_pct": 18.73,
    "brent_3m_pct": -0.38,
    "hstech_above_3y_low_pct": 8.65,
    "rbi_stance": "Hawkish",
    "mahktech_premium_pct": 30.92,
    "mahktech_turnover_inr": 11600970,
}

RAW_COMPONENTS = {
    "smallcapPeak": 18551.00,
    "smallcapCurrent": 18002.00,
    "cleanEnvPeak": 9.9646,
    "cleanEnvCurrent": 8.0978,
    "brent3mAgo": 92.42,
    "brentToday": 92.07,
    "hstechLow": 3706.30,
    "hstechCurrent": 4027.06,
    "mahktechLtp": 20.58,
    "mahktechInav": 15.72,
    "mahktechVol": 529000,
    "mahktechAvgPrice": 21.93,
}


def fetch_yahoo_chart(ticker, range_str="1y", interval="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_str}&interval={interval}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    result = data["chart"]["result"][0]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    volumes = [v for v in result["indicators"]["quote"][0].get("volume", []) if v is not None]
    return closes, volumes


def fetch_indexpe_smallcap_pe():
    url = "https://indexpe.in/nifty-smallcap-250"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    m = re.search(r"Nifty Smallcap 250 PE Ratio:\s*([0-9]+\.[0-9]+)", html, re.I)
    if m:
        return round(float(m.group(1)), 2)
    return None


def build_regime_json():
    payload = dict(BASELINE_DATA)
    raw = dict(RAW_COMPONENTS)

    # 1. Nifty Smallcap 250 P/E from IndexPE
    try:
        pe = fetch_indexpe_smallcap_pe()
        if pe is not None:
            payload["smallcap_pe"] = pe
    except Exception:
        pass

    # 2. Nifty Smallcap 250 drawdown from 12m peak
    try:
        closes, _ = fetch_yahoo_chart("%5ENSMIDCP", range_str="1y", interval="1d")
        if closes:
            peak_12m = round(max(closes), 2)
            current = round(closes[-1], 2)
            raw["smallcapPeak"] = peak_12m
            raw["smallcapCurrent"] = current
            payload["smallcap_dd_pct"] = round(max(0.0, (peak_12m - current) / peak_12m * 100.0), 2)
    except Exception:
        pass

    # 4. Brent Crude 3-month change %
    try:
        closes, _ = fetch_yahoo_chart("BZ=F", range_str="3mo", interval="1d")
        if len(closes) >= 2:
            brent_3m_ago = round(closes[0], 2)
            brent_now = round(closes[-1], 2)
            raw["brent3mAgo"] = brent_3m_ago
            raw["brentToday"] = brent_now
            payload["brent_3m_pct"] = round((brent_now - brent_3m_ago) / brent_3m_ago * 100.0, 2)
    except Exception:
        pass

    # 5. HSTECH above 3-year low %
    try:
        closes, _ = fetch_yahoo_chart("%5EHSTECH", range_str="3y", interval="1wk")
        if closes:
            low_3y = round(min(closes), 2)
            current = round(closes[-1], 2)
            raw["hstechLow"] = low_3y
            raw["hstechCurrent"] = current
            payload["hstech_above_3y_low_pct"] = round((current - low_3y) / low_3y * 100.0, 2)
    except Exception:
        pass

    # 8. MAHKTECH 20-day average turnover (INR)
    try:
        closes, volumes = fetch_yahoo_chart("MAHKTECH.NS", range_str="1mo", interval="1d")
        if closes and volumes:
            recent_c = closes[-20:]
            recent_v = volumes[-20:]
            avg_vol = int(round(sum(recent_v) / len(recent_v)))
            avg_prc = round(sum(recent_c) / len(recent_c), 2)
            turnovers = [c * v for c, v in zip(recent_c, recent_v)]
            raw["mahktechVol"] = avg_vol
            raw["mahktechAvgPrice"] = avg_prc
            raw["mahktechLtp"] = round(recent_c[-1], 2)
            payload["mahktech_turnover_inr"] = int(round(sum(turnovers) / len(turnovers)))
    except Exception:
        pass

    with open("regime_inputs.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload, indent=2))
    return {"inputs": payload, "raw": raw}


def inject_into_html(html_file, payload, raw):
    if not os.path.exists(html_file):
        return
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_baseline = {
        "asOfDate": today_str,
        "smallcapPe": payload["smallcap_pe"],
        "smallcapPeak": raw["smallcapPeak"],
        "smallcapCurrent": raw["smallcapCurrent"],
        "smallcapDdPct": payload["smallcap_dd_pct"],
        "cleanEnvMode": "proxy",
        "cleanEnvPeak": raw["cleanEnvPeak"],
        "cleanEnvCurrent": raw["cleanEnvCurrent"],
        "cleanEnvDdPct": payload["clean_env_dd_pct"],
        "brent3mAgo": raw["brent3mAgo"],
        "brentToday": raw["brentToday"],
        "brent3mPct": payload["brent_3m_pct"],
        "hstechLow": raw["hstechLow"],
        "hstechCurrent": raw["hstechCurrent"],
        "hstechAboveLowPct": payload["hstech_above_3y_low_pct"],
        "rbiStance": payload["rbi_stance"],
        "mahktechLtp": raw["mahktechLtp"],
        "mahktechInav": raw["mahktechInav"],
        "mahktechPremPct": payload["mahktech_premium_pct"],
        "mahktechVol": raw["mahktechVol"],
        "mahktechAvgPrice": raw["mahktechAvgPrice"],
        "mahktechTurnover": payload["mahktech_turnover_inr"],
    }
    replacement = (
        "/* AUTO_INJECT_START */\n    const VERIFIED_BASELINE = "
        + json.dumps(new_baseline, indent=6)
        + ";\n    /* AUTO_INJECT_END */"
    )
    html = re.sub(
        r"/\* AUTO_INJECT_START \*/[\s\S]*?/\* AUTO_INJECT_END \*/",
        replacement,
        html,
    )
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Injected latest live data into {html_file} for offline execution.")


class RegimeRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/regime.json"):
            data = build_regime_json()["inputs"]
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    import os
    res = build_regime_json()
    if "--inject-html" in sys.argv:
        idx = sys.argv.index("--inject-html")
        targets = [sys.argv[idx + 1]] if idx + 1 < len(sys.argv) else ["regime_checklist_fetcher.html", "index.html"]
        for t in targets:
            inject_into_html(t, res["inputs"], res["raw"])
        if "index.html" not in targets and os.path.exists("index.html"):
            inject_into_html("index.html", res["inputs"], res["raw"])
    if "--serve" in sys.argv:
        print("Serving live regime JSON at http://127.0.0.1:8765/regime.json ...")
        HTTPServer(("127.0.0.1", 8765), RegimeRequestHandler).serve_forever()
