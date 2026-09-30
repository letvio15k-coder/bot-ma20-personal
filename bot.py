import os, threading, asyncio, requests, json, math
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h","4h","1d"]

SUBS_FILE="subs.json"
subscribers=set()
try:
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE,'r') as f: subscribers=set(json.load(f))
except: pass
def save_subs():
    try:
        with open(SUBS_FILE,'w') as f: json.dump(list(subscribers),f)
    except: pass

app_flask=Flask(__name__)
@app_flask.route('/')
def home(): return f"SUPER BOT MA+BB+VOL+ACC - {len(subscribers)} users OK"

def calc_ma(data,p): return sum(data[-p:])/p if len(data)>=p else None

def bollinger(closes,p=20,std=2):
    if len(closes)<p: return None
    ma=sum(closes[-p:])/p
    var=sum((x-ma)**2 for x in closes[-p:])/p
    sd=math.sqrt(var)
    upper=ma+std*sd
    lower=ma-std*sd
    bw=(upper-lower)/ma*100 if ma!=0 else 0
    pb=(closes[-1]-lower)/(upper-lower) if upper!=lower else 0.5
    return {"ma":ma,"upper":upper,"lower":lower,"bw":bw,"pb":pb}

def analyze(symbol, interval):
    try:
        url=f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit=50"
        r=requests.get(url,timeout=10).json()
        if isinstance(r,dict): return None
        closes=[float(x[4]) for x in r]
        highs=[float(x[2]) for x in r]
        lows=[float(x[3]) for x in r]
        vols=[float(x[5]) for x in r]
        if len(closes)<35: return None

        # MA 14x34
        ma14=calc_ma(closes,14)
        ma34=calc_ma(closes,34)
        ma14_prev=calc_ma(closes[:-1],14)
        ma34_prev=calc_ma(closes[:-1],34)
        cross=None
        if ma14_prev and ma34_prev:
            if ma14_prev<ma34_prev and ma14>ma34: cross="GOLDEN"
            elif ma14_prev>ma34_prev and ma14<ma34: cross="DEATH"
        diff=ma14-ma34 if ma14 and ma34 else 0

        # BB
        bb=bollinger(closes,20,2)
        # Vol
        cur_vol=vols[-1]
        avg20=sum(vols[-21:-1])/20
        ratio=cur_vol/avg20 if avg20>0 else 0
        spike="X3" if ratio>=3 else "X2" if ratio>=2 else "X1.5" if ratio>=1.5 else None

        # Accumulation
        last10_high=max(highs[-10:])
        last10_low=min(lows[-10:])
        range_pct=(last10_high-last10_low)/last10_low*100 if last10_low>0 else 99
        avg5=sum(vols[-5:])/5
        avg_prev5=sum(vols[-10:-5])/5
        vol_trend=avg5/avg_prev5 if avg_prev5>0 else 1
        score=0
        if range_pct<8: score+=1
        if vol_trend>1.2: score+=1
        if ratio>1.3: score+=1
        pos=(closes[-1]-last10_low)/(last10_high-last10_low)*100 if last10_high!=last10_low else 50
        if 35<pos<75: score+=1
        is_accum=score>=3

        # SQUEEZE check
        bws=[]
        for i in range(20,35):
            sub=closes[-i:-i+20] if len(closes)>=i+20 else closes[-20:]
            if len(sub)==20:
                m=sum(sub)/20
                v=sum((x-m)**2 for x in sub)/20
                s=math.sqrt(v)
                bws.append((m+2*s-(m-2*s))/m*100)
        avg_bw=sum(bws)/len(bws) if bws else bb["bw"] if bb else 0
        is_squeeze = bb and bb["bw"]<4 and bb["bw"]<avg_bw*0.6
        is_breakout = bb and bb["bw"]>avg_bw*1.4 and bws and bws[-1]<5

        # SUPER SIGNAL = GOM + SQUEEZE + VOL X2
        is_super = is_accum and is_squeeze and ratio>=2

        return {
            "symbol":symbol,"interval":interval,"price":closes[-1],
            "ma14":ma14,"ma34":ma34,"cross":cross,"diff":diff,
            "bb":bb,"ratio":ratio,"spike":spike,"range":range_pct,"vtrend":vol_trend,"score":score,"is_accum":is_accum,
            "is_squeeze":is_squeeze,"is_breakout":is_breakout,"avg_bw":avg_bw,"is_super":is_super
        }
    except Exception as e:
        print(f"analyze err {symbol}: {e}")
        return None

# COMMANDS
async def start_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        "💎 SUPER BOT 3 TRONG 1\nMA 14x34 + BB + VOL + ACC\n\n"
        "/check - Quet tin hieu HOT (1H/4H/1D)\n"
        "/super - Chi quet SUPER SIGNAL GOM+SQUEEZE+VOL X2\n"
        "/vol - Quet Volume X2 X3\n/bb - Quet Bollinger\n/acc - Quet Gom Hang\n"
        "/ma - Quet MA 14x34\n"
        "/auto_on - BAT BAO TU DONG\n/auto_off - Tat"
    )

async def check_all(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("⏳ Dang quet SUPER SCAN 20 coin x 3 khung...")
    msgs=[]
    for itv in INTERVALS:
        for sym in COINS:
            r=await asyncio.to_thread(analyze,sym,itv)
            if not r: continue
            if r["is_super"]:
                msgs.append(f"💎💎💎 SUPER SIGNAL {sym} {itv} | Gom {r['score']}/4 Squeeze BW {r['bb']['bw']:.1f}% Vol x{r['ratio']:.1f} Gia ${r['price']:.3f}")
            elif r["cross"]:
                msgs.append(f"{'🚀 GOLDEN' if r['cross']=='GOLDEN' else '💀 DEATH'} {sym} {itv}")
            elif r["spike"]=="X3":
                msgs.append(f"💥 VOL X3 {sym} {itv} x{r['ratio']:.1f}")
            elif r["is_breakout"]:
                msgs.append(f"💥 BREAKOUT BB {sym} {itv} BW {r['bb']['bw']:.1f}%")
    if not msgs: await u.message.reply_text("⚪️ Chua co tin hieu hot")
    else: await u.message.reply_text("🔔 TIN HIEU HOT:\n" + "\n".join(msgs[:35]))

async def super_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("⏳ Dang san SUPER SIGNAL (GOM + SQUEEZE + VOL X2)...")
    found=[]
    for itv in ["4h","1d","1h"]:
        for sym in COINS:
            r=await asyncio.to_thread(analyze,sym,itv)
            if r and r["is_super"]:
                found.append(f"💎 SUPER {sym} {itv}\nGom {r['score']}/4 Range {r['range']:.1f}% Squeeze {r['bb']['bw']:.1f}% Vol x{r['ratio']:.1f} Gia ${r['price']:.4f} BB %B {r['bb']['pb']:.2f}")
    if not found: await u.message.reply_text("Chua co SUPER SIGNAL, nhung co the co SQUEEZE + GOM yeu, go /check de xem")
    else: await u.message.reply_text("💎💎💎 SUPER SIGNAL - KEO X10 TIEM NANG:\n\n" + "\n\n".join(found))

async def vol_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    itv=c.args[0] if c.args and c.args[0] in INTERVALS else "1h"
    await u.message.reply_text(f"⏳ Quet Volume {itv}...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,itv)
        if r and r["spike"]: lines.append(f"{'💥 X3' if r['spike']=='X3' else '🔥 X2' if r['spike']=='X2' else '⚡ X1.5'} {sym} x{r['ratio']:.2f} ${r['price']:.3f}")
    await u.message.reply_text("\n".join(lines) if lines else f"Khong co Vol spike {itv}")

async def bb_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    itv=c.args[0] if c.args and c.args[0] in INTERVALS else "4h"
    await u.message.reply_text(f"⏳ Quet Bollinger {itv}...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,itv)
        if not r or not r["bb"]: continue
        if r["is_squeeze"]: lines.append(f"🟡 SQUEEZE {sym} BW {r['bb']['bw']:.1f}%")
        elif r["is_breakout"]: lines.append(f"💥 BREAKOUT {sym} BW {r['bb']['bw']:.1f}%")
        elif r["bb"]["pb"]<=0.1: lines.append(f"🟢 CHAM DUOI {sym} %B {r['bb']['pb']:.2f}")
    await u.message.reply_text("\n".join(lines) if lines else f"Khong co tin hieu BB dac biet {itv}")

async def acc_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    itv=c.args[0] if c.args and c.args[0] in INTERVALS else "4h"
    await u.message.reply_text(f"⏳ Quet Gom Hang {itv}...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,itv)
        if r and r["is_accum"]: lines.append(f"🟩 GOM {sym} {r['score']}/4 Range {r['range']:.1f}% VolTrend x{r['vtrend']:.2f}")
    await u.message.reply_text("\n".join(lines) if lines else f"Khong co gom hang {itv}")

async def ma_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("⏳ Quet MA 14x34...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,"1h")
        if r: lines.append(f"{'🟢' if r['diff']>0 else '🔴'} {sym} MA14 {r['ma14']:.2f} MA34 {r['ma34']:.2f}")
    await u.message.reply_text("\n".join(lines[:20]))

async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers: return
    for itv in INTERVALS:
        for sym in COINS:
            try:
                r=await asyncio.to_thread(analyze,sym,itv)
                if not r: continue
                msg=None
                if r["is_super"]:
                    msg=f"💎💎💎 SUPER SIGNAL {sym} {itv}\n🟩 Gom hang {r['score']}/4\n🟡 Squeeze BW {r['bb']['bw']:.1f}% (TB {r['avg_bw']:.1f}%)\n🔥 Vol x{r['ratio']:.2f}\nGia ${r['price']:.4f}\n=> KEO X10 TIEM NANG!"
                elif r["cross"]:
                    msg=f"{'🚀 GOLDEN CROSS' if r['cross']=='GOLDEN' else '💀 DEATH CROSS'} {sym} {itv} Gia ${r['price']:.4f}"
                elif r["spike"]=="X3":
                    msg=f"💥 VOL X3 {sym} {itv} x{r['ratio']:.2f} Gia ${r['price']:.4f}"
                elif r["is_breakout"]:
                    msg=f"💥 BREAKOUT BOLLINGER {sym} {itv} BW {r['bb']['bw']:.1f}% Gia ${r['price']:.4f}"

                if msg:
                    for cid in list(subscribers):
                        try: await context.bot.send_message(chat_id=cid,text=msg)
                        except: pass
            except: continue

async def auto_on(u:Update,c:ContextTypes.DEFAULT_TYPE):
    subscribers.add(u.effective_chat.id); save_subs()
    if not c.job_queue.get_jobs_by_name("super_job"):
        c.job_queue.run_repeating(check_job,interval=1800,first=10,name="super_job")
    await u.message.reply_text("✅ DA BAT BAO SUPER!\n- SUPER SIGNAL Gom+Squeeze+Vol X2\n- MA Cross\n- Vol X3\n- Breakout BB\n30 phut check 1 lan")

async def auto_off(u:Update,c:ContextTypes.DEFAULT_TYPE):
    subscribers.discard(u.effective_chat.id); save_subs()
    await u.message.reply_text("🛑 Da tat")

def run_flask(): app_flask.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))

if __name__=='__main__':
    try: asyncio.set_event_loop(asyncio.new_event_loop())
    except: pass
    threading.Thread(target=run_flask,daemon=True).start()
    app=Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).pool_timeout(30).build()
    app.add_handler(CommandHandler("start",start_cmd))
    app.add_handler(CommandHandler("check",check_all))
    app.add_handler(CommandHandler("super",super_cmd))
    app.add_handler(CommandHandler("vol",vol_cmd))
    app.add_handler(CommandHandler("bb",bb_cmd))
    app.add_handler(CommandHandler("acc",acc_cmd))
    app.add_handler(CommandHandler("ma",ma_cmd))
    app.add_handler(CommandHandler("scan",ma_cmd))
    app.add_handler(CommandHandler("auto_on",auto_on))
    app.add_handler(CommandHandler("auto_off",auto_off))
    app.job_queue.run_repeating(check_job,interval=1800,first=20,name="super_job")
    print("SUPER BOT RUNNING")
    app.run_polling()
