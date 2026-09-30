import os, threading, asyncio, requests, json
from flask import Flask, render_template_string, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
COINS = ["UNI","TAO","FET","LINK","WLD","XLM","BNB","NEAR","ADA","SOL","SUI","BCH","XRP","POL","LTC","ZEC","FIL","HBAR","HYPE","OP"]
INTERVALS = ["1h", "1d"]

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

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Volume Spike x2 x3</title>
<style>
body{font-family:Arial;background:#0f1115;color:#fff;padding:12px}
h2{text-align:center;color:#00ff88;margin:5px}
.box{text-align:center;background:#1a1d24;padding:12px;border-radius:10px;margin:10px 0}
table{width:100%;border-collapse:collapse;margin-top:12px}
th,td{padding:9px;border:1px solid #333;text-align:center;font-size:13px}
th{background:#1a1d24}
.x15{background:#ffaa00;color:#000;font-weight:bold}
.x2{background:#ff4500;color:#fff;font-weight:bold;animation:blink 1s infinite}
.x3{background:#ff0040;color:#fff;font-weight:bold;animation:blink 0.5s infinite;font-size:15px}
@keyframes blink{50%{opacity:0.5}}
.ok{color:#666}
.btn{padding:7px 12px;background:#00ff88;color:#000;border:none;border-radius:6px;font-weight:bold;margin:3px}
select{padding:7px;border-radius:6px;background:#222;color:#fff;border:1px solid #444}
</style>
</head>
<body>
<h2>🔥 VOLUME SPIKE x1.5 x2 x3</h2>
<div class="box">
Khung: <select id="tf" onchange="update()"><option value="1h" {{sel1h}}>1H</option><option value="1d" {{sel1d}}>1D</option></select>
Mức lọc: <select id="lv" onchange="update()"><option value="1.5" {{f15}}>x1.5 trở lên</option><option value="2" {{f2}}>Chỉ x2 trở lên</option><option value="3" {{f3}}>Chỉ x3 siêu spike</option></select>
<button class="btn" onclick="location.reload()">🔄 Quét</button>
</div>
<table>
<tr><th>Coin</th><th>Giá</th><th>Vol hiện tại</th><th>TB 20 nến</th><th>Tỉ lệ</th><th>Trạng thái</th></tr>
{{rows}}
</table>
<div class="box" style="font-size:12px;color:#888">
🟨 x1.5 = Dòng tiền vào | 🟧 x2 = Cá mập gom | 🟥 x3 = Bùng nổ / xả mạnh<br>
Web tự refresh 60s - Bot MA 14x34 vẫn chạy nền
</div>
<script>
function update(){ var tf=document.getElementById('tf').value; var lv=document.getElementById('lv').value; window.location='/?interval='+tf+'&level='+lv; }
setTimeout(()=>location.reload(), 60000)
</script>
</body>
</html>
"""

def get_volume_data(symbol, interval):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit=21"
        r = requests.get(url, timeout=10).json()
        if isinstance(r, dict) and 'code' in r: return None
        vols = [float(x[5]) for x in r]
        closes = [float(x[4]) for x in r]
        cur, avg = vols[-1], sum(vols[:-1])/20
        ratio = cur/avg if avg>0 else 0
        return {"price":closes[-1],"cur":cur,"avg":avg,"ratio":ratio}
    except: return None

@app_flask.route('/')
def home():
    interval = request.args.get('interval','1h')
    level = float(request.args.get('level','1.5'))
    if interval not in ["1h","1d"]: interval="1h"

    rows_html = ""
    count_spike = 0
    for sym in COINS:
        d = get_volume_data(sym, interval)
        if not d: continue
        if d["ratio"] < level:
            if level==1.5: # vẫn hiện hết nếu chọn 1.5
                pass
            else:
                continue
        if d["ratio"] >= 3:
            status = f"<span class='x3'>💥 x3 SIÊU SPIKE x{d['ratio']:.2f}</span>"; count_spike+=1
        elif d["ratio"] >= 2:
            status = f"<span class='x2'>🔥 x2 SPIKE x{d['ratio']:.2f}</span>"; count_spike+=1
        elif d["ratio"] >= 1.5:
            status = f"<span class='x15'>⚡ x1.5 x{d['ratio']:.2f}</span>"; count_spike+=1
        else:
            status = f"<span class='ok'>Bình thường x{d['ratio']:.2f}</span>"

        # Nếu lọc x2, x3 thì chỉ hiện spike
        if level>1.5 and d["ratio"]<level: continue

        rows_html += f"<tr><td><b>{sym}</b></td><td>${d['price']:.3f}</td><td>{d['cur']:.0f}</td><td>{d['avg']:.0f}</td><td>x{d['ratio']:.2f}</td><td>{status}</td></tr>"

    if not rows_html:
        rows_html = f"<tr><td colspan=6>Không có con nào đạt x{level} ở khung {interval} - Thị trường đang yên ắng</td></tr>"

    sel1h = "selected" if interval=="1h" else ""
    sel1d = "selected" if interval=="1d" else ""
    f15 = "selected" if level==1.5 else ""
    f2 = "selected" if level==2 else ""
    f3 = "selected" if level==3 else ""
    return render_template_string(HTML_PAGE.replace("{{rows}}", rows_html).replace("{{sel1h}}", sel1h).replace("{{sel1d}}", sel1d).replace("{{f15}}", f15).replace("{{f2}}", f2).replace("{{f3}}", f3))

# ===== BOT TELEGRAM GIỮ NGUYÊN =====
def get_klines(symbol, interval, limit=100):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        if isinstance(r, dict) and 'code' in r: return []
        return [float(x[4]) for x in r]
    except: return []
def calc_ma(data, period):
    res=[]
    for i in range(len(data)):
        if i+1>=period: res.append(sum(data[i+1-period:i+1])/period)
        else: res.append(None)
    return res
def check_coin(symbol, interval):
    closes = get_klines(symbol, interval, 100)
    if len(closes)<35: return None
    ma14 = calc_ma(closes,14); ma34=calc_ma(closes,34)
    cross=None
    if ma14[-2]<ma34[-2] and ma14[-1]>ma34[-1]: cross="GOLDEN"
    elif ma14[-2]>ma34[-2] and ma14[-1]<ma34[-1]: cross="DEATH"
    return {"symbol":symbol,"interval":interval,"price":closes[-1],"ma14":ma14[-1],"ma34":ma34[-1],"cross":cross,"diff":ma14[-1]-ma34[-1]}

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME','your-app.onrender.com')}"
    await update.message.reply_text(f"🤖 BOT MA + WEB VOLUME x2 x3\n\n🌐 Web: {web_url}\n/?interval=1h&level=2 -> xem x2\n/?interval=1d&level=3 -> xem x3\n\n/ma WLD\n/scan /scan_d\n/auto_on")

async def ma_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    sym=context.args[0].upper(); req=context.args[1] if len(context.args)>1 else None
    intervals=[req] if req in INTERVALS else INTERVALS
    txt=f"📊 {sym}:\n"
    for itv in intervals:
        d=check_coin(sym,itv)
        if d: txt+=f"\n{itv}: ${d['price']:.4f} {'🟢' if d['diff']>0 else '🔴'}\n"
    await update.message.reply_text(txt)

async def scan_h_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines=[]
    for sym in COINS:
        d=check_coin(sym,"1h")
        if d: lines.append(f"{'🟢' if d['diff']>0 else '🔴'} {sym}")
    await update.message.reply_text("\n".join(lines))
async def scan_d_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines=[]
    for sym in COINS:
        d=check_coin(sym,"1d")
        if d: lines.append(f"{'🟢' if d['diff']>0 else '🔴'} {sym}")
    await update.message.reply_text("\n".join(lines))
async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    found=[]
    for itv in INTERVALS:
        for sym in COINS:
            d=check_coin(sym,itv)
            if d and d["cross"]: found.append(d)
    if not found: await update.message.reply_text("Chưa có cắt"); return
    await update.message.reply_text("".join([f"{'🚀' if d['cross']=='GOLDEN' else '💀'} {d['symbol']} {d['interval']}\n" for d in found]))

async def check_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers: return
    for itv in INTERVALS:
        for sym in COINS:
            d=check_coin(sym,itv)
            if d and d["cross"]:
                msg=f"{'🚀 GOLDEN' if d['cross']=='GOLDEN' else '💀 DEATH'} {d['symbol']} {itv} ${d['price']:.4f}"
                for cid in list(subscribers):
                    try: await context.bot.send_message(chat_id=cid,text=msg)
                    except: pass

async def auto_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_chat.id); save_subs()
    if not context.job_queue.get_jobs_by_name("ma_personal"):
        context.job_queue.run_repeating(check_job, interval=3600, first=15, name="ma_personal")
    await update.message.reply_text("✅ Đã BẬT!")
async def auto_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers.discard(update.effective_chat.id); save_subs()
    await update.message.reply_text("🛑 Đã TẮT.")

def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__ == '__main__':
    try: asyncio.set_event_loop(asyncio.new_event_loop())
    except: pass
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
    print("BOT + WEB X2 X3 RUNNING")
    app.run_polling()
