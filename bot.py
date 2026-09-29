import os, threading, asyncio, requests, json
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
INTERVAL = "1h"
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]

SUBS_FILE = "subs.json"
subscribers = set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, 'r') as f:
            subscribers = set(json.load(f))
except: pass

def save_subs():
    try:
        with open(SUBS_FILE, 'w') as f:
            json.dump(list(subscribers), f)
    except: pass

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return f"MA 20 COINS PERSONAL BOT - {len(subscribers)} users"

def get_klines(symbol, limit=100):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={INTERVAL}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        if isinstance(r, dict) and 'code' in r: return []
        return [float(x[4]) for x in r]
    except: return []

def calc_ma_series(data, period):
    s=[]
    for i in range(len(data)):
        if i+1 >= period: s.append(sum(data[i+1-period:i+1])/period)
        else: s.append(None)
    return s

def check_coin(symbol):
    closes = get_klines(symbol, 100)
    if len(closes) < 35: return None
    ma14 = calc_ma_series(closes, 14)
    ma34 = calc_ma_series(closes, 34)
    return {
        "symbol": symbol, "price": closes[-1], "ma14": ma14[-1], "ma34": ma34[-1],
        "cross": "GOLDEN" if ma14[-2] < ma34[-2] and ma14[-1] > ma34[-1] else "DEATH" if ma14[-2] > ma34[-2] and ma14[-1] < ma34[-1] else None,
        "diff": ma14[-1]-ma34[-1]
    }

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 BOT MA 14x34 CÁ NHÂN - 20 COINS\nKhung: {INTERVAL}\nList: {', '.join(COINS)}\n\n/ma WLD - Xem MA 1 con\n/scan - Quét nhanh cả 20 con\n/check - Con nào vừa cắt nến 1H\n/auto_on - BẬT báo riêng cho bạn mỗi giờ\n/auto_off - Tắt báo\n\nBot báo thẳng vào đây, không cần Channel!")

async def ma_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await update.message.reply_text("Dùng: /ma WLD"); return
    sym = context.args[0].upper()
    d = check_coin(sym)
    if not d: await update.message.reply_text(f"Không lấy được {sym}"); return
    status = "🟢 TĂNG" if d['diff']>0 else "🔴 GIẢM"
    await update.message.reply_text(f"📊 {sym} {INTERVAL}\nGiá: ${d['price']:.4f}\nMA14: ${d['ma14']:.4f}\nMA34: ${d['ma34']:.4f}\n{status}")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"⏳ Đang quét 20 con...")
    lines=[]
    for sym in COINS:
        d = check_coin(sym)
        if d:
            icon = "🟢" if d['diff']>0 else "🔴"
            lines.append(f"{icon} {sym}: ${d['price']:.2f}")
    await update.message.reply_text("📈 SCAN MA 14x34 1H:\n\n" + "\n".join(lines))

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    found=[]
    for sym in COINS:
        d = check_coin(sym)
        if d and d['cross']: found.append(d)
    if not found: await update.message.reply_text(f"⚪️ 1H vừa rồi: 20 con chưa cắt"); return
    txt=""
    for d in found:
        txt+=f"{'🚀 GOLDEN CROSS' if d['cross']=='GOLDEN' else '💀 DEATH CROSS'} {d['symbol']}\nGiá ${d['price']:.4f}\n\n"
    await update.message.reply_text(txt)

async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers: return
    for sym in COINS:
        d = check_coin(sym)
        if d and d['cross']:
            msg = f"{'🚀 GOLDEN CROSS' if d['cross']=='GOLDEN' else '💀 DEATH CROSS'} {d['symbol']} {INTERVAL}!\nGiá: ${d['price']:.4f}\nMA14: ${d['ma14']:.4f}\nMA34: ${d['ma34']:.4f}"
            for chat_id in list(subscribers):
                try: await context.bot.send_message(chat_id=chat_id, text=msg)
                except: pass

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id); save_subs()
    if not context.job_queue.get_jobs_by_name("ma_personal"):
        context.job_queue.run_repeating(check_job, interval=3600, first=15, name="ma_personal")
    await update.message.reply_text(f"✅ Đã BẬT báo cá nhân! Mỗi giờ bot sẽ quét 20 con, con nào cắt MA 14x34 sẽ nhắn RIÊNG cho bạn ở đây!")

async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers: subscribers.remove(chat_id); save_subs()
    await update.message.reply_text("🛑 Đã TẮT báo cá nhân.")

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    try: asyncio.set_event_loop(asyncio.new_event_loop())
    except: pass
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ma", ma_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.job_queue.run_repeating(check_job, interval=3600, first=20, name="ma_personal")
    print("PERSONAL BOT RUNNING")
    app.run_polling()
