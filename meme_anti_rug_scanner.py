import requests
import time
from datetime import datetime

# ==================== تنظیمات ====================
CHAIN = "solana"
MIN_LIQUIDITY = 10000
MAX_MC = 300000
MIN_5M_BUYS = 25
MIN_VOLUME_1H = 20000
MAX_AGE_MIN = 120
CHECK_INTERVAL = 40

# تلگرام
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

def send_telegram(message):
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ تلگرام تنظیم نشده")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def rug_check(token_address):
    try:
        url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            mint_revoked = data.get("mintAuthority", {}).get("revoked", False)
            freeze_revoked = data.get("freezeAuthority", {}).get("revoked", False)
            lp_locked = data.get("liquidity", {}).get("locked", False) or data.get("lpBurned", False)
            score = data.get("riskScore", 0)
            return {
                "safe": mint_revoked and freeze_revoked and lp_locked and score > 70,
                "details": f"MintRev:{mint_revoked} | FreezeRev:{freeze_revoked} | LPLocked:{lp_locked} | Score:{score}"
            }
    except:
        pass
    return {"safe": False, "details": "چک دستی لازم"}

def fetch_new_pairs():
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q=&chain={CHAIN}"
        resp = requests.get(url, timeout=15)
        return resp.json().get("pairs", []) if resp.status_code == 200 else []
    except:
        return []

def analyze_pair(pair):
    try:
        base = pair.get("baseToken", {})
        txns = pair.get("txns", {}).get("m5", {})
        volume = pair.get("volume", {}).get("h1", 0)
        mc = pair.get("fdv") or pair.get("marketCap", 0)
        liq = pair.get("liquidity", {}).get("usd", 0)
        age_ms = pair.get("pairCreatedAt")
        age = (time.time() * 1000 - age_ms) / (1000 * 60) if age_ms else 999

        buys_5m = txns.get("buys", 0)

        score = 0
        reasons = []

        if liq >= MIN_LIQUIDITY:
            score += 2
            reasons.append(f"Liq OK")
        if 20000 <= mc <= MAX_MC:
            score += 3
            reasons.append(f"MC مناسب")
        if buys_5m >= MIN_5M_BUYS:
            score += 3
            reasons.append(f"Buys قوی")
        if volume >= MIN_VOLUME_1H:
            score += 2
            reasons.append(f"Volume رو به رشد")
        if age < MAX_AGE_MIN:
            score += 2
            reasons.append(f"جدید")

        token_addr = base.get("address")
        rug_info = rug_check(token_addr)
        if rug_info["safe"]:
            score += 5
            reasons.append("✅ Anti-Rug قوی")
        else:
            reasons.append("⚠️ " + rug_info["details"])

        if score >= 12:
            return {
                "name": f"{base.get('name')} ({base.get('symbol')})",
                "address": token_addr,
                "url": pair.get("url"),
                "mc": mc,
                "liq": liq,
                "score": score,
                "reasons": reasons,
                "age": age,
                "rug_details": rug_info["details"]
            }
        return None
    except:
        return None

def main():
    print("🛡️ Anti-Rug Meme Scanner شروع شد (سخت‌گیرانه)")
    send_telegram("🛡️ <b>Anti-Rug Scanner فعال شد!</b>\nفقط کوین‌های امن و با پتانسیل.")
    
    seen = set()
    while True:
        pairs = fetch_new_pairs()
        candidates = []
        
        for p in pairs[:150]:
            analysis = analyze_pair(p)
            if analysis and analysis["address"] not in seen:
                candidates.append(analysis)
                seen.add(analysis["address"])
        
        if candidates:
            candidates.sort(key=lambda x: x["score"], reverse=True)
            for c in candidates[:3]:
                msg = f"""🚀 <b>کاندید امن!</b>

{c['name']}
MC: ${{c['mc']/1000:.1f}}k | Liq: ${{c['liq']/1000:.1f}}k
Score: {c['score']} | Age: {c['age']:.0f} دقیقه

دلایل: {', '.join(c['reasons'])}

Rug: {c['rug_details']}

🔗 {c['url']}"""
                print(msg)
                send_telegram(msg)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()