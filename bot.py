import os, threading, asyncio, requests, json
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h", "4h", "1d"]

SUBS_FILE = "subs.json"
subscribers = set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, 'r') as f: subscribers = set(json.load(f))
except: pass
def save_subs():
    try:
        with open(SUBS_FILE, 'w') as f: json.dump(list(subscribers), f)
    except: pass

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return f"BOT MA20 + VOLUME + ACCUMULATION - {len(subscribers)} users - OK"

def get_klines_full(symbol, interval, limit=50):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        if isinstance(r, dict): return None
        return {
            "closes": [float(x[4]) for x in r],
            "highs": [float(x[2]) for x in r],
            "lows": [float(x[3]) for x in r],
            "vols": [float(x[5]) for x in r]
        }
    except: return None

def calc_ma(data, period):
    res=[]
    for i in range(len(data)):
        if i+1>=period: res.append(sum(data[i+1-period:i+1])/period)
        else: res.append(None)
    return res

def analyze(symbol, interval):
    d = get_klines_full(symbol, interval, 50)
    if not d: return None
    closes, highs, lows, vols = d["closes"], d["highs"], d["lows"], d["vols"]
    if len(closes)<35: return None

    # MA 14x34
    ma14 = calc_ma(closes, 14)
    ma34 = calc_ma(closes, 34)
    cross = None
    if ma14[-2] < ma34[-2] and ma14[-1] > ma34[-1]: cross="GOLDEN"
    elif ma14[-2] > ma34[-2] and ma14[-1] < ma34[-1]: cross="DEATH"

    # VOLUME SPIKE
    cur_vol = vols[-1]
    avg20 = sum(vols[-21:-1])/20
    ratio = cur_vol/avg20 if avg20>0 else 0
    spike = None
    if ratio>=3: spike="X3"
    elif ratio>=2: spike="X2"
    elif ratio>=1.5: spike="X1.5"

    # ACCUMULATION
    last10_high = max(highs[-10:])
    last10_low = min(lows[-10:])
    range_pct = (last10_high - last10_low)/last10_low*100 if last10_low>0 else 99
    avg5 = sum(vols[-5:])/5
    avg_prev5 = sum(vols[-10:-5])/5
    vol_trend = avg5/avg_prev5 if avg_prev5>0 else 1
    score=0
    if range_pct < 8: score+=1
    if vol_trend > 1.2: score+=1
    if ratio > 1.3: score+=1
    price_pos = (closes[-1]-last10_low)/(last10_high-last10_low)*100 if last10_high!=last10_low else 50
    if 35 < price_pos < 75: score+=1
    is_accum = score>=3

    return {
        "symbol":symbol, "interval":interval, "price":closes[-1],
        "ma14":ma14[-1], "ma34":ma34[-1], "cross":cross, "diff":ma14[-1]-ma34[-1],
        "ratio":ratio, "spike":spike, "range_pct":range_pct, "vol_trend":vol_trend,
        "is_accum":is_accum, "score":score
    }

# ===== COMMANDS =====
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT MA20 FIX - SIGNAL GOM HANG + VOLUME\n\n"
        "/scan - Quet MA 1H\n/scan_d - Quet MA 1D\n"
        "/vol - Quet Volume Spike x2 x3 (1H)\n/vol 4h /vol 1d\n"
        "/acc - Quet con dang GOM HANG\n/acc 4h /acc 1d\n"
        "/check - Check tat ca tin hieu hot\n"
        "/auto_on - BAT BAO CA NHAN (MA + VOL X2/X3 + GOM)\n"
        "/auto_off - Tat bao"
    )

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    itv = "1d" if context.args and context.args[0]=="d" else "1h"
    await update.message.reply_text(f"⏳ Quet MA 14x34 {itv}...")
    lines=[]
    for sym in COINS:
        r = await asyncio.to_thread(analyze, sym, itv)
        if r: lines.append(f"{'🟢' if r['diff']>0 else '🔴'} {sym}: ${r['price']:.2f}")
    await update.message.reply_text(f"SCAN MA {itv}:\n" + "\n".join(lines))

async def vol_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    itv = context.args[0] if context.args and context.args[0] in INTERVALS else "1h"
    await update.message.reply_text(f"⏳ Quet Volume Spike {itv}...")
    found=[]
    for sym in COINS:
        r = await asyncio.to_thread(analyze, sym, itv)
        if r and r['spike']:
            found.append(f"{'💥 X3' if r['spike']=='X3' else '🔥 X2' if r['spike']=='X2' else '⚡ X1.5'} {sym} x{r['ratio']:.2f} ${r['price']:.3f}")
    if not found: await update.message.reply_text(f"Khong co con nao x1.5+ o khung {itv}")
    else: await update.message.reply_text(f"📊 VOLUME SPIKE {itv}:\n" + "\n".join(found))

async def acc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    itv = context.args[0] if context.args and context.args[0] in INTERVALS else "4h"
    await update.message.reply_text(f"⏳ Quet Gom Hang {itv}...")
    found=[]
    for sym in COINS:
        r = await asyncio.to_thread(analyze, sym, itv)
        if r and r['is_accum']:
            found.append(f"🟩 GOM {sym} ({r['score']}/4) Range {r['range_pct']:.1f}% Vol x{r['vol_trend']:.2f} Gia ${r['price']:.3f}")
    if not found: await update.message.reply_text(f"Khong co con nao dang gom o khung {itv}")
    else: await update.message.reply_text(f"📦 DANG GOM HANG {itv}:\n" + "\n".join(found))

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Dang check tat ca tin hieu hot 1H+4H+1D...")
    msgs=[]
    for itv in INTERVALS:
        for sym in COINS:
            r = await asyncio.to_thread(analyze, sym, itv)
            if not r: continue
            if r['cross']: msgs.append(f"{'🚀 GOLDEN' if r['cross']=='GOLDEN' else '💀 DEATH'} {sym} {itv}")
            if r['spike'] in ['X2','X3']: msgs.append(f"{'💥 VOL X3' if r['spike']=='X3' else '🔥 VOL X2'} {sym} {itv} x{r['ratio']:.2f}")
            if r['is_accum'] and r['score']==4: msgs.append(f"🟩 GOM MANH {sym} {itv}")
    if not msgs: await update.message.reply_text("⚪️ Chua co tin hieu hot")
    else: await update.message.reply_text("🔔 TIN HIEU HOT:\n" + "\n".join(msgs[:30]))

# JOB BAO CA NHAN - FIX LOI TIMEDOUT
async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers: return
    for itv in INTERVALS:
        for sym in COINS:
            try:
                r = await asyncio.to_thread(analyze, sym, itv)
                if not r: continue
                msg=None
                if r['cross']: msg = f"{'🚀 GOLDEN CROSS' if r['cross']=='GOLDEN' else '💀 DEATH CROSS'} {r['symbol']} {itv}\nGia ${r['price']:.4f}"
                elif r['spike']=='X3': msg = f"💥 VOLUME SIÊU SPIKE X3 {r['symbol']} {itv}\nVol x{r['ratio']:.2f} Gia ${r['price']:.4f}\nCo bien lon sap xay ra!"
                elif r['spike']=='X2': msg = f"🔥 VOLUME SPIKE X2 {r['symbol']} {itv}\nVol x{r['ratio']:.2f} Gia ${r['price']:.4f}"
                elif r['is_accum'] and r['score']>=4 and itv in ['4h','1d']: msg = f"🟩 GOM HANG MANH {r['symbol']} {itv}\nScore {r['score']}/4 Range {r['range_pct']:.1f}% VolTrend x{r['vol_trend']:.2f}\nGia dang di ngang - Ca map dang gom!"

                if msg:
                    for cid in list(subscribers):
                        try: await context.bot.send_message(chat_id=cid, text=msg)
                        except: pass
            except Exception as e:
                print(f"Job err {sym} {itv}: {e}")
                continue

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_chat.id); save_subs()
    if not context.job_queue.get_jobs_by_name("ma_personal"):
        context.job_queue.run_repeating(check_job, interval=1800, first=15, name="ma_personal") # 30p check 1 lan
    await update.message.reply_text("✅ DA BAT BAO CA NHAN!\nBao khi:\n- MA 14 cat 34 (1H/4H/1D)\n- Volume Spike X2/X3\n- Gom hang manh 4H/1D")

async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.discard(update.effective_chat.id); save_subs()
    await update.message.reply_text("🛑 Da tat bao.")

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__ == '__main__':
    try: asyncio.set_event_loop(asyncio.new_event_loop())
    except: pass
    threading.Thread(target=run_flask, daemon=True).start()
    # FIX LOI TIMEDOUT 10:37 AM
    app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).pool_timeout(30).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", lambda u,c: scan_cmd(u, type('o',((),{'args':['1h']}))())))
    app.add_handler(CommandHandler("scan_d", lambda u,c: scan_cmd(u, type('o',((),{'args':['d']}))())))
    app.add_handler(CommandHandler("vol", vol_cmd))
    app.add_handler(CommandHandler("acc", acc_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("auto_on", auto_on))
    app.add_handler(CommandHandler("auto_off", auto_off))
    app.add_handler(CommandHandler("ma", scan_cmd)) # giu lenh cu
    app.job_queue.run_repeating(check_job, interval=1800, first=20, name="ma_personal")
    print("BOT MA + VOL + ACCUMULATION RUNNING")
    app.run_polling()
