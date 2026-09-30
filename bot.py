import os, threading, asyncio, requests, json
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h", "1d"]

SUBS_FILE = "subs.json"
subscribers = set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, 'r') as f:
            subscribers = set(json.load(f))
except:
    pass

def save_subs():
    try:
        with open(SUBS_FILE, 'w') as f:
            json.dump(list(subscribers), f)
    except:
        pass

app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return f"MA 20 COINS 1H+1D - {len(subscribers)} users"

def get_klines(symbol, interval, limit=100):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        if isinstance(r, dict) and 'code' in r:
            return []
        return [float(x[4]) for x in r]
    except:
        return []

def calc_ma(data, period):
    res = []
    for i in range(len(data)):
        if i + 1 >= period:
            res.append(sum(data[i+1-period:i+1]) / period)
        else:
            res.append(None)
    return res

def check_coin(symbol, interval):
    closes = get_klines(symbol, interval, 100)
    if len(closes) < 35:
        return None
    ma14 = calc_ma(closes, 14)
    ma34 = calc_ma(closes, 34)
    cross = None
    if ma14[-2] < ma34[-2] and ma14[-1] > ma34[-1]:
        cross = "GOLDEN"
    elif ma14[-2] > ma34[-2] and ma14[-1] < ma34[-1]:
        cross = "DEATH"
    return {
        "symbol": symbol,
        "interval": interval,
        "price": closes[-1],
        "ma14": ma14[-1],
        "ma34": ma34[-1],
        "cross": cross,
        "diff": ma14[-1] - ma34[-1]
    }

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 BOT MA 14x34 - 20 COINS - 2 KHUNG\n"
        f"/ma WLD - Xem ca 1H va 1D\n"
        f"/ma WLD 1d - Xem rieng khung 1 ngay\n"
        f"/scan - Quet 20 con khung 1H\n"
        f"/scan_d - Quet 20 con khung 1 NGAY\n"
        f"/check - Check con nao vua cat\n"
        f"/auto_on - BAT bao ca nhan 1H + 1D\n"
        f"/auto_off - Tat bao"
    )

async def ma_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Dung: /ma WLD")
        return
    sym = context.args[0].upper()
    req = context.args[1] if len(context.args) > 1 else None
    intervals = [req] if req in INTERVALS else INTERVALS
    txt = f"📊 {sym}:\n"
    for itv in intervals:
        d = check_coin(sym, itv)
        if not d:
            txt += f"\n{itv}: Khong lay duoc\n"
            continue
        status = "🟢 TANG" if d["diff"] > 0 else "🔴 GIAM"
        txt += f"\n--- {itv} ---\nGia: ${d['price']:.4f}\nMA14: ${d['ma14']:.4f}\nMA34: ${d['ma34']:.4f}\n{status}\n"
    await update.message.reply_text(txt)

async def scan_h_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Dang quet 20 con khung 1h...")
    lines = []
    for sym in COINS:
        d = check_coin(sym, "1h")
        if d:
            icon = "🟢" if d["diff"] > 0 else "🔴"
            lines.append(f"{icon} {sym}: ${d['price']:.2f}")
    await update.message.reply_text("📈 SCAN 1H:\n\n" + "\n".join(lines))

async def scan_d_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Dang quet 20 con khung 1d...")
    lines = []
    for sym in COINS:
        d = check_coin(sym, "1d")
        if d:
            icon = "🟢" if d["diff"] > 0 else "🔴"
            lines.append(f"{icon} {sym}: ${d['price']:.2f}")
    await update.message.reply_text("📈 SCAN 1D:\n\n" + "\n".join(lines))

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    found = []
    for itv in INTERVALS:
        for sym in COINS:
            d = check_coin(sym, itv)
            if d and d["cross"]:
                found.append(d)
    if not found:
        await update.message.reply_text("⚪️ Vua roi: 20 con chua co con nao cat o ca 1H va 1D")
        return
    txt = ""
    for d in found:
        txt += f"{'🚀 GOLDEN' if d['cross']=='GOLDEN' else '💀 DEATH'} {d['symbol']} {d['interval']} - ${d['price']:.4f}\n"
    await update.message.reply_text(txt)

async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers:
        return
    for itv in INTERVALS:
        for sym in COINS:
            d = check_coin(sym, itv)
            if d and d["cross"]:
                msg = f"{'🚀 GOLDEN CROSS' if d['cross']=='GOLDEN' else '💀 DEATH CROSS'} {d['symbol']} {itv}!\nGia: ${d['price']:.4f}\nMA14: ${d['ma14']:.4f}\nMA34: ${d['ma34']:.4f}"
                for chat_id in list(subscribers):
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=msg)
                    except:
                        pass

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    save_subs()
    if not context.job_queue.get_jobs_by_name("ma_personal"):
        context.job_queue.run_repeating(check_job, interval=3600, first=15, name="ma_personal")
    await update.message.reply_text("✅ Da BAT bao ca nhan 2 KHUNG 1H + 1D!")

async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subs()
    await update.message.reply_text("🛑 Da TAT bao ca nhan.")

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
    except:
        pass
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ma", ma_cmd))
    app.add_handler(CommandHandler("scan", scan_h_cmd))
    app.add_handler(CommandHandler("scan_d", scan_d_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.job_queue.run_repeating(check_job, interval=3600, first=20, name="ma_personal")
    print("PERSONAL BOT 1H+1D RUNNING")
    app.run_polling()
