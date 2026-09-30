import os, threading, asyncio, requests, json
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h", "1d"] # Báo cả 2 khung

SUBS_FILE = "subs.json"
subscribers = set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, 'r') as f:
            subscribers = set(json.load(f))
except: pass

def save_subs():
    try:
        with open(SUBS_FILE, 'w') as f: json.dump(list(subscribers), f)
    except: pass

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return f"MA 20 COINS 1H+1D BOT - {len(subscribers)} users"

def get_klines(symbol, interval, limit=100):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
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

def check_coin(symbol, interval):
    closes = get_klines(symbol, interval, 100)
    if len(closes) < 35: return None
    ma14 = calc_ma_series(closes, 14)
    ma34 = calc_ma_series(closes, 34)
    return {
        "symbol": symbol, "interval": interval,
        "price": closes[-1], "ma14": ma14[-1], "ma34": ma34[-1],
        "cross": "GOLDEN" if ma14[-2] < ma34[-2] and ma14[-1] > ma34[-1] else "DEATH" if ma14[-2] > ma34[-2] and ma14[-1] < ma34[-1] else None,
        "diff": ma14[-1]-ma34[-1]
    }

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 BOT MA 14x34 - 20 COINS - 2 KHUNG\n"
        f"List: {', '.join(COINS)}\n\n"
        f"/ma WLD - Xem cả 1H và 1D\n"
        f"/ma WLD 1d - Xem riêng khung 1 ngày\n"
        f"/scan - Quét 20 con khung 1H\n"
        f"/scan_d - Quét 20 con khung 1 NGÀY\n"
        f"/check - Check con nào vừa cắt (cả 1H và 1D)\n"
        f"/auto_on - BẬT báo cá nhân 1H + 1D\n"
        f"/auto_off - Tắt báo"
    )

async def ma_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Dùng: /ma WLD hoặc /ma WLD 1d"); return
    sym = context.args[0].upper()
    interval_req = context.args[1] if len(context.args)>1 else None

    intervals_to_check = [interval_req] if interval_req in INTERVALS else INTERVALS

    txt = f"📊 {sym}:\n"
    for interval in intervals_to_check:
        d = check_coin(sym, interval)
        if not d: txt+= f"\n❌ {interval}: Không lấy được\n"; continue
        status = "🟢 TĂNG" if d['diff']>0 else "🔴 GIẢM"
        txt+= f"\n--- {interval} ---\nGiá: ${d['price']:.4f}\nMA14: ${d['ma14']:.4f}\nMA34: ${d['ma34']:.4f}\n{status}\n"
    await update.message.reply_text(txt)

async def scan_cmd(update: Updateimport os, threading, asyncio, requests, json
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h", "1d"] # Báo cả 2 khung

SUBS_FILE = "subs.json"
subscribers = set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, 'r') as f:
            subscribers = set(json.load(f))
except: pass

def save_subs():
    try:
        with open(SUBS_FILE, 'w') as f: json.dump(list(subscribers), f)
    except: pass

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return f"MA 20 COINS 1H+1D BOT - {len(subscribers)} users"

def get_klines(symbol, interval, limit=100):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
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

def check_coin(symbol, interval):
    closes = get_klines(symbol, interval, 100)
    if len(closes) < 35: return None
    ma14 = calc_ma_series(closes, 14)
    ma34 = calc_ma_series(closes, 34)
    return {
        "symbol": symbol, "interval": interval,
        "price": closes[-1], "ma14": ma14[-1], "ma34": ma34[-1],
        "cross": "GOLDEN" if ma14[-2] < ma34[-2] and ma14[-1] > ma34[-1] else "DEATH" if ma14[-2] > ma34[-2] and ma14[-1] < ma34[-1] else None,
        "diff": ma14[-1]-ma34[-1]
    }

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 BOT MA 14x34 - 20 COINS - 2 KHUNG\n"
        f"List: {', '.join(COINS)}\n\n"
        f"/ma WLD - Xem cả 1H và 1D\n"
        f"/ma WLD 1d - Xem riêng khung 1 ngày\n"
        f"/scan - Quét 20 con khung 1H\n"
        f"/scan_d - Quét 20 con khung 1 NGÀY\n"
        f"/check - Check con nào vừa cắt (cả 1H và 1D)\n"
        f"/auto_on - BẬT báo cá nhân 1H + 1D\n"
        f"/auto_off - Tắt báo"
    )

async def ma_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Dùng: /ma WLD hoặc /ma WLD 1d"); return
    sym = context.args[0].upper()
    interval_req = context.args[1] if len(context.args)>1 else None

    intervals_to_check = [interval_req] if interval_req in INTERVALS else INTERVALS

    txt = f"📊 {sym}:\n"
    for interval in intervals_to_check:
        d = check_coin(sym, interval)
        if not d: txt+= f"\n❌ {interval}: Không lấy được\n"; continue
        status = "🟢 TĂNG" if d['diff']>0 else "🔴 GIẢM"
        txt+= f"\n--- {interval} ---\nGiá: ${d['price']:.4f}\nMA14: ${d['ma14']:.4f}\nMA34: ${d['ma34']:.4f}\n{status}\n"
    await update.message.reply_text(txt)

async def scan_cmd(update: Update
