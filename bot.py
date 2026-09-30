import os, threading, asyncio, requests, json, math
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h","4h","1d"]

SUBS_FILE = "subs.json"
subscribers=set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE,'r') as f: subscribers=set(json.load(f))
except: pass
def save_subs():
    try:
        with open(SUBS_FILE,'w') as f: json.dump(list(subscribers), f)
    except: pass

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return f"BOLLINGER BOT - {len(subscribers)} users OK"

def get_klines(symbol, interval, limit=50):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        if isinstance(r, dict): return None
        return [float(x[4]) for x in r]
    except: return None

def bollinger(closes, period=20, std=2):
    if len(closes) < period: return None
    ma = sum(closes[-period:])/period
    variance = sum((x-ma)**2 for x in closes[-period:])/period
    stdev = math.sqrt(variance)
    upper = ma + std*stdev
    lower = ma - std*stdev
    bandwidth = (upper - lower)/ma * 100
    # %B
    percent_b = (closes[-1] - lower) / (upper - lower) if upper!=lower else 0.5
    return {"ma":ma, "upper":upper, "lower":lower, "bandwidth":bandwidth, "percent_b":percent_b, "price":closes[-1]}

def analyze_bb(symbol, interval):
    closes = get_klines(symbol, interval, 50)
    if not closes: return None
    bb = bollinger(closes, 20, 2)
    if not bb: return None

    # Check Squeeze - 20 nến trước bandwidth trung bình
    prev_bandwidths=[]
    for i in range(20, 40):
        if len(closes) >= i:
            sub = closes[-i:-i+20] if i>20 else closes[-20:]
            if len(sub)==20:
                ma=sum(sub)/20
                var=sum((x-ma)**2 for x in sub)/20
                sd=math.sqrt(var)
                bw=(ma+2*sd - (ma-2*sd))/ma*100
                prev_bandwidths.append(bw)
    avg_bw = sum(prev_bandwidths)/len(prev_bandwidths) if prev_bandwidths else bb["bandwidth"]

    signal=None
    if bb["percent_b"] <= 0.05: signal="CHAM BAND DUOI"
    elif bb["percent_b"] >= 0.95: signal="CHAM BAND TREN"
    elif bb["bandwidth"] < 4 and bb["bandwidth"] < avg_bw*0.6: signal="SQUEEZE"
    elif bb["bandwidth"] > avg_bw*1.5 and prev_bandwidths and prev_bandwidths[-1] < 5: signal="BREAKOUT"

    return {**bb, "symbol":symbol, "interval":interval, "signal":signal, "avg_bw":avg_bw}

# COMMANDS
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 BOLLINGER BAND BOT\n\n"
        "/bb - Quet BB 1H\n/bb 4h - Quet BB 4H\n/bb 1d - Quet BB 1D\n"
        "/bbsq - Chi quet SQUEEZE (thắt nút) sap no\n"
        "/bblow - Chi quet con cham band duoi (sắp bay)\n"
        "/check - Quet tat ca tin hieu hot\n"
        "/auto_on - Bat bao tu dong\n/auto_off - Tat"
    )

async def bb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    itv = context.args[0] if context.args and context.args[0] in INTERVALS else "1h"
    await update.message.reply_text(f"⏳ Quet Bollinger {itv}...")
    lines=[]
    for sym in COINS:
        r = await asyncio.to_thread(analyze_bb, sym, itv)
        if not r: continue
        icon = "🔵"
        if r["signal"]=="CHAM BAND DUOI": icon="🟢 CHAM DUOI"
        elif r["signal"]=="CHAM BAND TREN": icon="🔴 CHAM TREN"
        elif r["signal"]=="SQUEEZE": icon="🟡 SQUEEZE"
        elif r["signal"]=="BREAKOUT": icon="💥 BREAKOUT"
        lines.append(f"{icon} {sym}: ${r['price']:.3f} | %B {r['percent_b']:.2f} | BW {r['bandwidth']:.1f}%")
    await update.message.reply_text(f"📈 BB {itv.upper()}:\n" + "\n".join(lines[:25]))

async def bbsq_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Dang tim con SQUEEZE (thắt nút) - tín hiệu sắp nổ to...")
    found=[]
    for itv in ["1h","4h","1d"]:
        for sym in COINS:
            r = await asyncio.to_thread(analyze_bb, sym, itv)
            if r and r["signal"] in ["SQUEEZE","BREAKOUT"]:
                found.append(f"{'🟡 SQUEEZE' if r['signal']=='SQUEEZE' else '💥 BREAKOUT'} {sym} {itv} BW {r['bandwidth']:.1f}% (TB {r['avg_bw']:.1f}%)")
    if not found: await update.message.reply_text("Hien tai chua co con nao SQUEEZE, thi truong dang di ngang rong")
    else: await update.message.reply_text("💣 SQUEEZE - SAP NO:\n" + "\n".join(found))

async def bblow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Tim con cham BAND DUOI (quá bán)...")
    found=[]
    for itv in INTERVALS:
        for sym in COINS:
            r = await asyncio.to_thread(analyze_bb, sym, itv)
            if r and r["signal"]=="CHAM BAND DUOI":
                found.append(f"🟢 {sym} {itv} Gia ${r['price']:.3f} chạm dưới ${r['lower']:.3f} %B {r['percent_b']:.2f}")
    if not found: await update.message.reply_text("Khong co con nao cham band duoi")
    else: await update.message.reply_text("🟢 CHAM BAND DUOI - CO HOI MUA:\n" + "\n".join(found))

async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers: return
    for itv in INTERVALS:
        for sym in COINS:
            try:
                r = await asyncio.to_thread(analyze_bb, sym, itv)
                if not r or not r["signal"]: continue
                msg=None
                if r["signal"]=="SQUEEZE": msg=f"🟡 SQUEEZE THẮT NÚT {sym} {itv}\nBandwidth {r['bandwidth']:.2f}% rất nhỏ (TB {r['avg_bw']:.1f}%)\nChuẩn bị có biến lớn! Canh breakout!"
                elif r["signal"]=="BREAKOUT": msg=f"💥 BREAKOUT BOLLINGER {sym} {itv}\nVừa thoát Squeeze! Gia ${r['price']:.3f}\nBand tren ${r['upper']:.3f} - Duoi ${r['lower']:.3f}"
                elif r["signal"]=="CHAM BAND DUOI" and itv in ["4h","1d"]: msg=f"🟢 CHẠM BAND DƯỚI {sym} {itv}\nGia ${r['price']:.3f} cham band duoi ${r['lower']:.3f}\n%B={r['percent_b']:.2f} - Qua ban, co hoi hoi len"

                if msg:
                    for cid in list(subscribers):
                        try: await context.bot.send_message(chat_id=cid, text=msg)
                        except: pass
            except: continue

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_chat.id); save_subs()
    if not context.job_queue.get_jobs_by_name("bb_job"):
        context.job_queue.run_repeating(check_job, interval=1800, first=15, name="bb_job")
    await update.message.reply_text("✅ Da bat bao BOLLINGER!\n- Bao khi SQUEEZE / BREAKOUT\n- Bao khi cham band duoi 4H/1D")
async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.discard(update.effective_chat.id); save_subs()
    await update.message.reply_text("🛑 Da tat")

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__ == '__main__':
    try: asyncio.set_event_loop(asyncio.new_event_loop())
    except: pass
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).pool_timeout(30).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("bb", bb_cmd))
    app.add_handler(CommandHandler("bbsq", bbsq_cmd))
    app.add_handler(CommandHandler("bblow", bblow_cmd))
    app.add_handler(CommandHandler("check", bbsq_cmd))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.job_queue.run_repeating(check_job, interval=1800, first=20, name="bb_job")
    print("BOLLINGER BOT RUNNING")
    app.run_polling()
