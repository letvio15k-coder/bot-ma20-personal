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
def home(): return f"SUPER BOT FINAL VOL MUA BAN - {len(subscribers)} users OK"

def calc_ma(data,p):
    return sum(data[-p:])/p if len(data)>=p else None

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
        opens=[float(x[1]) for x in r]
        highs=[float(x[2]) for x in r]
        lows=[float(x[3]) for x in r]
        vols=[float(x[5]) for x in r]
        quote_vols=[float(x[7]) for x in r]
        taker_buy_quote=[float(x[10]) for x in r] # QUAN TRỌNG: Vol mua

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

        # VOLUME MUA / BÁN
        cur_vol=vols[-1]
        cur_taker_buy=taker_buy_quote[-1]
        cur_quote_vol=quote_vols[-1]
        avg20=sum(vols[-21:-1])/20 if len(vols)>21 else sum(vols[:-1])/20
        ratio=cur_vol/avg20 if avg20>0 else 0
        buy_ratio=(cur_taker_buy/cur_quote_vol*100) if cur_quote_vol>0 else 50
        is_green=closes[-1]>opens[-1]
        body=abs(closes[-1]-opens[-1])
        upper_wick=highs[-1]-max(closes[-1],opens[-1])
        lower_wick=min(closes[-1],opens[-1])-lows[-1]

        spike="X3" if ratio>=3 else "X2" if ratio>=2 else "X1.5" if ratio>=1.5 else None
        vol_type=None
        if spike:
            if buy_ratio>=60 and is_green: vol_type=f"🟢 MUA MANH {spike}"
            elif buy_ratio<=40 and not is_green: vol_type=f"🔴 BAN MANH {spike}"
            elif buy_ratio>=60 and lower_wick>body: vol_type=f"🟢 MUA BAT DAY {spike}"
            elif buy_ratio<=40 and upper_wick>body: vol_type=f"🔴 BAN CHOT LOI {spike}"
            else: vol_type=f"🟡 TRUNG TINH {spike} Mua {buy_ratio:.0f}%"

        # ACCUMULATION
        last10_high=max(highs[-10:])
        last10_low=min(lows[-10:])
        range_pct=(last10_high-last10_low)/last10_low*100 if last10_low>0 else 99
        avg5=sum(vols[-5:])/5
        avg_prev5=sum(vols[-10:-5])/5
        vtrend=avg5/avg_prev5 if avg_prev5>0 else 1
        score=0
        if range_pct<8: score+=1
        if vtrend>1.2: score+=1
        if ratio>1.3: score+=1
        pos=(closes[-1]-last10_low)/(last10_high-last10_low)*100 if last10_high!=last10_low else 50
        if 35<pos<75: score+=1
        is_accum=score>=3

        # SQUEEZE
        bws=[]
        for i in range(20,35):
            sub=closes[-i:-i+20] if len(closes)>=i else closes[-20:]
            if len(sub)==20:
                m=sum(sub)/20
                v=sum((x-m)**2 for x in sub)/20
                s=math.sqrt(v)
                bws.append((m+2*s-(m-2*s))/m*100)
        avg_bw=sum(bws)/len(bws) if bws else (bb["bw"] if bb else 0)
        is_squeeze=bb and bb["bw"]<4 and bb["bw"]<avg_bw*0.6
        is_breakout=bb and bb["bw"]>avg_bw*1.4 and bws and bws[-1]<5
        is_super=is_accum and is_squeeze and ratio>=2 and buy_ratio>=55

        return {
            "symbol":symbol,"interval":interval,"price":closes[-1],
            "ma14":ma14,"ma34":ma34,"cross":cross,"diff":diff,
            "bb":bb,"ratio":ratio,"spike":spike,"vol_type":vol_type,"buy_ratio":buy_ratio,"is_green":is_green,
            "range":range_pct,"vtrend":vtrend,"score":score,"is_accum":is_accum,
            "is_squeeze":is_squeeze,"is_breakout":is_breakout,"avg_bw":avg_bw,"is_super":is_super
        }
    except Exception as e:
        print(f"err {symbol} {e}")
        return None

# COMMANDS
async def start_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        "💎 SUPER BOT FINAL - VOL MUA BAN\n\n"
        "/super - Sieu tin hieu GOM+SQUEEZE+VOL MUA X2\n"
        "/vol - Quet Volume X3 phan biet MUA/BAN\n/vol 4h /vol 1d\n"
        "/bb - Quet Bollinger\n/acc - Quet Gom Hang\n/check - Quet tat ca\n"
        "/auto_on - Bat bao tu dong\n/auto_off - Tat"
    )

async def super_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("⏳ San SUPER SIGNAL (GOM + SQUEEZE + VOL MUA X2)...")
    found=[]
    for itv in ["4h","1d","1h"]:
        for sym in COINS:
            r=await asyncio.to_thread(analyze,sym,itv)
            if r and r["is_super"]:
                found.append(f"💎 SUPER {sym} {itv} | {r['vol_type']} x{r['ratio']:.1f} Mua {r['buy_ratio']:.0f}%\nGom {r['score']}/4 Range {r['range']:.1f}% BW {r['bb']['bw']:.1f}% Gia ${r['price']:.4f}")
    await u.message.reply_text("\n\n".join(found) if found else "Chua co SUPER, go /check xem tin hieu le")

async def vol_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    itv=c.args[0] if c.args and c.args[0] in INTERVALS else "1h"
    await u.message.reply_text(f"⏳ Quet Volume MUA/BAN {itv}...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,itv)
        if r and r["spike"]:
            lines.append(f"{r['vol_type']} {sym} x{r['ratio']:.1f} Mua {r['buy_ratio']:.0f}% Gia ${r['price']:.3f} {'🟢' if r['is_green'] else '🔴'}")
    # Sort: Mua manh len dau
    lines_sorted=sorted(lines, key=lambda x: "🟢" in x, reverse=True)
    await u.message.reply_text(f"📊 VOL {itv.upper()} - PHAN BIET MUA BAN:\n" + "\n".join(lines_sorted) if lines_sorted else f"Khong co vol x1.5+ {itv}")

async def check_all(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("⏳ Quet tat ca tin hieu...")
    msgs=[]
    for itv in INTERVALS:
        for sym in COINS:
            r=await asyncio.to_thread(analyze,sym,itv)
            if not r: continue
            if r["is_super"]: msgs.append(f"💎 SUPER {sym} {itv} {r['vol_type']}")
            elif r["cross"]: msgs.append(f"{'🚀 GOLDEN' if r['cross']=='GOLDEN' else '💀 DEATH'} {sym} {itv}")
            elif r["spike"]=="X3": msgs.append(f"{r['vol_type']} {sym} {itv} x{r['ratio']:.1f}")
            elif r["is_breakout"]: msgs.append(f"💥 BREAKOUT {sym} {itv}")
    await u.message.reply_text("\n".join(msgs[:35]) if msgs else "⚪️ Chua co tin hieu hot")

async def bb_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    itv=c.args[0] if c.args and c.args[0] in INTERVALS else "4h"
    await u.message.reply_text(f"⏳ Quet BB {itv}...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,itv)
        if not r or not r["bb"]: continue
        if r["is_squeeze"]: lines.append(f"🟡 SQUEEZE {sym} BW {r['bb']['bw']:.1f}%")
        elif r["is_breakout"]: lines.append(f"💥 BREAKOUT {sym}")
        elif r["bb"]["pb"]<=0.1: lines.append(f"🟢 CHAM DUOI {sym}")
    await u.message.reply_text("\n".join(lines) if lines else f"Khong co BB dac biet {itv}")

async def acc_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    itv=c.args[0] if c.args and c.args[0] in INTERVALS else "4h"
    await u.message.reply_text(f"⏳ Quet Gom {itv}...")
    lines=[]
    for sym in COINS:
        r=await asyncio.to_thread(analyze,sym,itv)
        if r and r["is_accum"]: lines.append(f"🟩 GOM {sym} {r['score']}/4 Range {r['range']:.1f}%")
    await u.message.reply_text("\n".join(lines) if lines else f"Khong co gom {itv}")

async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers: return
    for itv in INTERVALS:
        for sym in COINS:
            try:
                r=await asyncio.to_thread(analyze,sym,itv)
                if not r: continue
                msg=None
                if r["is_super"]:
                    msg=f"💎💎💎 SUPER SIGNAL {sym} {itv}\n{r['vol_type']} x{r['ratio']:.1f} Mua {r['buy_ratio']:.0f}%\n🟩 Gom {r['score']}/4 🟡 Squeeze {r['bb']['bw']:.1f}%\nGia ${r['price']:.4f}\n=> KEO X10 TIEM NANG!"
                elif r["cross"]:
