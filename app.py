"""ExpenseSort (FastAPI): paste/upload transactions -> ML categorizes them ->
dashboard with money in/out/net, a donut, category breakdown, a savings coach,
an editable table, and CSV export. Run: python app.py -> http://localhost:8001
"""
import os
import sys

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from categorizer import categorize
from parse import parse_transactions
from extract import extract_text

app = FastAPI(title="ExpenseSort", version="3.0")

EXAMPLE = ("Swiggy order 320\nUber ride 180\nAmazon purchase 1499\nElectricity bill 1200\n"
           "BigBasket groceries 850\nNetflix subscription 199\nApollo pharmacy 430\n"
           "Salary credited 60000\nOla cab 240\nJio recharge 299\nZomato dinner 540\n"
           "Flipkart order 2299\nSpotify premium 129\nPetrol pump 2000")


class Req(BaseModel):
    text: str = ""


@app.post("/categorize")
def categorize_endpoint(req: Req):
    return categorize(parse_transactions(req.text))


@app.post("/extract")
async def extract_endpoint(file: UploadFile = File(...)):
    data = await file.read()
    try:
        return {"text": extract_text(file.filename, data)}
    except Exception as e:
        return {"text": "", "error": f"Could not read {file.filename}: {e}"}


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.replace("%EX%", EXAMPLE.replace("\n", "\\n"))


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ExpenseSort — see where your money really goes</title>
<style>
  :root{
    --bg:#f2f6f5; --card:#ffffff; --ink:#0f2a27; --muted:#6b8079; --line:#e4ede9;
    --teal:#0f766e; --teal2:#12b3a6; --mint:#e7f7f1;
    --green:#12a150; --red:#e5484d; --amber:#d97706;
    --shadow:0 12px 34px rgba(6,78,72,.10); --shadow-sm:0 4px 14px rgba(6,78,72,.07);
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:"Inter","Segoe UI",system-ui,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5;}
  .hero{background:radial-gradient(120% 140% at 0% 0%,#14b8a6 0%,#0f766e 55%,#0b5c55 100%);color:#fff;
        padding:26px 24px 64px;position:relative;overflow:hidden;}
  .hero:after{content:"";position:absolute;right:-60px;top:-60px;width:240px;height:240px;border-radius:50%;
              background:rgba(255,255,255,.08);}
  .hero .in{max-width:1040px;margin:0 auto;position:relative;z-index:1;}
  .brand{display:flex;align-items:center;gap:11px;font-weight:800;font-size:23px;letter-spacing:.2px;}
  .logo{width:34px;height:34px;border-radius:10px;background:#fff;color:var(--teal);display:grid;place-items:center;font-weight:900;font-size:18px;box-shadow:0 4px 10px rgba(0,0,0,.15);}
  .hero p{opacity:.94;margin-top:10px;font-size:14.5px;max-width:600px;}
  .wrap{max-width:1040px;margin:-46px auto 48px;padding:0 18px;position:relative;z-index:2;}
  .panel{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);padding:22px;}
  .fld{display:block;font-size:13px;font-weight:700;color:var(--teal);margin-bottom:8px;}
  .uploadbar{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;}
  .filebtn{font-size:12.5px;font-weight:700;color:#fff;background:var(--teal);border-radius:10px;padding:8px 13px;cursor:pointer;box-shadow:var(--shadow-sm);}
  .filebtn:hover{background:var(--teal2);}
  .fname{font-size:12px;color:var(--muted);} input[type=file]{display:none;}
  textarea{width:100%;height:140px;padding:13px 15px;border:1.5px solid var(--line);border-radius:14px;font-size:13px;
           resize:vertical;font-family:ui-monospace,Consolas,monospace;color:var(--ink);background:#fbfefc;}
  textarea:focus{outline:none;border-color:var(--teal2);box-shadow:0 0 0 4px rgba(18,179,166,.15);}
  .row{display:flex;align-items:center;gap:14px;margin-top:14px;flex-wrap:wrap;}
  .primary{background:var(--teal);color:#fff;border:0;border-radius:13px;padding:13px 28px;font-size:15px;font-weight:800;cursor:pointer;box-shadow:0 8px 18px rgba(15,118,110,.32);}
  .primary:hover{background:var(--teal2);} .primary:disabled{opacity:.55;box-shadow:none;}
  .link{background:none;border:0;color:var(--teal);font-weight:700;cursor:pointer;font-size:13.5px;padding:6px;}
  .link:hover{text-decoration:underline;}
  #out{margin-top:6px;}

  .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:20px 0;}
  @media(max-width:640px){.kpis{grid-template-columns:1fr;}}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:var(--shadow-sm);
       display:flex;align-items:center;gap:14px;position:relative;overflow:hidden;}
  .kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;}
  .kpi.in:before{background:var(--green);} .kpi.out:before{background:var(--red);} .kpi.net:before{background:var(--teal);}
  .kpi .badge{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;font-size:22px;flex:none;}
  .kpi.in .badge{background:#e6f7ee;} .kpi.out .badge{background:#fdeaea;} .kpi.net .badge{background:var(--mint);}
  .kpi .lbl{font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-weight:700;}
  .kpi .val{font-size:25px;font-weight:800;margin-top:2px;}

  .dash{display:grid;grid-template-columns:300px 1fr;gap:18px;}
  @media(max-width:780px){.dash{grid-template-columns:1fr;}}
  .card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px 20px;box-shadow:var(--shadow-sm);}
  h3{font-size:12px;text-transform:uppercase;letter-spacing:.7px;margin:0 0 12px;color:var(--muted);font-weight:800;}
  .donutwrap{display:flex;flex-direction:column;align-items:center;}
  .legend{width:100%;margin-top:10px;}
  .lg{display:flex;align-items:center;gap:9px;font-size:12.5px;margin:6px 0;}
  .lg .em{font-size:14px;} .lg .amt{margin-left:auto;font-weight:700;font-variant-numeric:tabular-nums;}
  .catrow{display:grid;grid-template-columns:170px 1fr 92px;gap:12px;align-items:center;margin:11px 0;font-size:13px;}
  .cname{display:flex;align-items:center;gap:7px;font-weight:600;}
  .catbar{height:12px;border-radius:7px;background:#eef4f1;overflow:hidden;} .catbar>div{height:100%;border-radius:7px;}
  .amt{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;}
  .amt .pct{display:block;color:var(--muted);font-weight:500;font-size:11px;}
  .insights{margin-top:16px;} .insights ul{list-style:none;} .insights li{font-size:13.5px;margin:8px 0;padding-left:22px;position:relative;}
  .insights li:before{content:"•";position:absolute;left:6px;color:var(--teal2);font-weight:900;}

  .coach{margin-top:18px;border-radius:20px;padding:20px 22px;color:#fff;
         background:radial-gradient(120% 160% at 100% 0%,#16a34a 0%,#0f766e 70%);box-shadow:var(--shadow);}
  .coachhead{display:flex;align-items:center;gap:14px;margin-bottom:12px;}
  .coachicon{width:52px;height:52px;border-radius:14px;background:rgba(255,255,255,.2);display:grid;place-items:center;font-size:26px;flex:none;}
  .coachhead .ct{font-size:12.5px;opacity:.9;text-transform:uppercase;letter-spacing:.6px;font-weight:700;}
  .coachhead .camt{font-size:30px;font-weight:800;line-height:1.1;}
  .clist{list-style:none;} .clist li{display:flex;gap:10px;align-items:flex-start;font-size:13.5px;margin:9px 0;}
  .clist li .ci{flex:none;}
  .coachnote{font-size:12px;background:rgba(255,255,255,.16);border-radius:9px;padding:7px 11px;margin-top:12px;}

  .tblcard{margin-top:18px;}
  .tablehead{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
  .dl{background:var(--mint);color:var(--teal);border:0;border-radius:10px;padding:8px 13px;font-size:12.5px;font-weight:700;cursor:pointer;}
  .dl:hover{background:#d6f2e4;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);}
  tbody tr:hover{background:#f7fbf9;}
  td.r,th.r{text-align:right;font-variant-numeric:tabular-nums;}
  .tdot{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:7px;vertical-align:middle;}
  select{border:1px solid var(--line);border-radius:9px;padding:5px 7px;font-size:12.5px;background:#fff;color:var(--ink);}
  .foot{text-align:center;color:var(--muted);font-size:12.5px;margin-top:24px;}
  .hint{font-size:13px;color:var(--muted);margin-top:8px;}
</style></head>
<body>
  <div class="hero"><div class="in">
    <div class="brand"><span class="logo">₹</span> ExpenseSort</div>
    <p>Upload your bank statement (or paste transactions). See where your money really goes — income vs spending vs investments — and exactly where you can save.</p>
  </div></div>

  <div class="wrap">
    <div class="panel">
      <label class="fld">Upload your bank statement, or paste transactions (one per line, or CSV)</label>
      <div class="uploadbar">
        <label class="filebtn" for="file">&#8593; Upload statement PDF / CSV / TXT</label>
        <input id="file" type="file" accept=".pdf,.csv,.txt" onchange="upload()">
        <span class="fname" id="fname"></span>
      </div>
      <textarea id="tx" placeholder="Swiggy order 320&#10;Salary credited 60000&#10;Amazon purchase 1499"></textarea>
      <div class="row">
        <button class="primary" id="go" onclick="run()">Analyze my money</button>
        <button class="link" onclick="loadExample()">Try an example</button>
        <button class="link" onclick="clearAll()">Clear</button>
      </div>
    </div>
    <div id="out"></div>
    <div class="foot">Runs locally &middot; income vs spend from your balance &middot; edit any category and everything updates live</div>
  </div>

<script>
const EX="%EX%";
const COLORS={"Food & Dining":"#ef4444","Groceries":"#16a34a","Transport":"#3b82f6","Shopping":"#a855f7",
  "Bills & Utilities":"#f59e0b","Entertainment":"#ec4899","Health":"#06b6d4","Income":"#0d9488",
  "Transfers":"#64748b","Others":"#94a3b8","Investments":"#0ea5e9","Insurance":"#f97316",
  "Rent":"#84cc16","Bank Charges":"#78716c"};
const ICONS={"Food & Dining":"🍔","Groceries":"🛒","Transport":"🚗","Shopping":"🛍️","Bills & Utilities":"💡",
  "Entertainment":"🎬","Health":"🏥","Rent":"🏠","Insurance":"🛡️","Investments":"📈","Transfers":"🔁",
  "Bank Charges":"🏦","Income":"💰","Others":"📦"};
const NONSPEND=["Investments","Transfers","Bank Charges"];
const DISCRETIONARY=["Food & Dining","Shopping","Entertainment"];
const SUBS=["netflix","spotify","hotstar","prime","youtube","disney","apple","googleplay","gym"];
let STATE={rows:[],categories:[]};
function col(c){return COLORS[c]||"#94a3b8";}
function ico(c){return ICONS[c]||"📦";}
function esc(s){return (s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function inr(n){return '₹'+Math.round(Number(n)).toLocaleString('en-IN');}
function loadExample(){document.getElementById('tx').value=EX;run();}
function clearAll(){document.getElementById('tx').value='';document.getElementById('fname').textContent='';document.getElementById('out').innerHTML='';STATE={rows:[],categories:[]};}

async function upload(){
  const inp=document.getElementById('file'); if(!inp.files.length) return;
  const fd=new FormData(); fd.append('file',inp.files[0]);
  document.getElementById('fname').textContent='reading '+inp.files[0].name+'...';
  try{const r=await fetch('/extract',{method:'POST',body:fd});const d=await r.json();
    document.getElementById('tx').value=d.text||'';document.getElementById('fname').textContent=d.error?d.error:('loaded '+inp.files[0].name);
  }catch(e){document.getElementById('fname').textContent='could not read file';}
}
async function run(){
  const text=document.getElementById('tx').value.trim();const out=document.getElementById('out');
  if(!text){out.innerHTML='<p class="hint">Paste some transactions or click <b>Try an example</b>.</p>';return;}
  const b=document.getElementById('go');b.disabled=true;b.textContent='Analyzing...';
  try{const r=await fetch('/categorize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
    const d=await r.json(); STATE.rows=d.rows; STATE.categories=d.categories_list; render();
  }catch(e){out.innerHTML='<p class="hint">Error: '+esc(e)+'</p>';}
  b.disabled=false;b.textContent='Analyze my money';
}
function isIncome(r){return r.direction==='credit' || (!r.direction && r.category==='Income');}
function aggregate(){
  let income=0,expense=0,by={};
  STATE.rows.forEach(r=>{const a=Number(r.amount)||0;
    if(isIncome(r)){income+=a;}
    else{expense+=a;by[r.category]=(by[r.category]||0)+a;}});
  const cats=Object.entries(by).sort((x,y)=>y[1]-x[1]);
  return {income,expense,net:income-expense,cats};
}
function catSum(agg,name){return agg.cats.filter(([c])=>c===name).reduce((s,[,a])=>s+a,0);}
function donut(cats,expense){
  const R=68,C=2*Math.PI*R;let acc=0;
  const segs=cats.map(([c,a])=>{const seg=expense?a/expense*C:0;const s=`<circle cx="90" cy="90" r="${R}" fill="none" stroke="${col(c)}" stroke-width="24" stroke-dasharray="${seg} ${C-seg}" stroke-dashoffset="${-acc}" transform="rotate(-90 90 90)"/>`;acc+=seg;return s;}).join('');
  return `<svg width="180" height="180">${segs}<circle cx="90" cy="90" r="55" fill="#fff"/>
    <text x="90" y="82" text-anchor="middle" font-size="11" fill="#6b8079">Money out</text>
    <text x="90" y="106" text-anchor="middle" font-size="21" font-weight="800" fill="#0f766e">${inr(expense)}</text></svg>`;
}
function insights(agg){
  const t=[];
  const invest=catSum(agg,"Investments"),transfers=catSum(agg,"Transfers"),charges=catSum(agg,"Bank Charges");
  const spending=Math.max(0, agg.expense-invest-transfers-charges);
  if(invest+transfers+charges>0){let p=[];
    if(invest>0)p.push(`${inr(invest)} to investments`); if(transfers>0)p.push(`${inr(transfers)} to transfers`); if(charges>0)p.push(`${inr(charges)} to bank charges`);
    t.push(`Of ${inr(agg.expense)} that left your account, ${p.join(', ')} — your <b>actual spending was about ${inr(spending)}</b>.`);}
  const spendCats=agg.cats.filter(([c])=>!NONSPEND.includes(c));
  if(spendCats.length){const [c,a]=spendCats[0];const p=spending?Math.round(a/spending*100):0;t.push(`Your biggest actual spend is <b>${esc(c)}</b>: ${inr(a)} (${p}% of spending).`);}
  if(agg.income>0){const rate=Math.round(agg.net/agg.income*100);
    t.push(agg.net>=0?`Money in ${inr(agg.income)} vs out ${inr(agg.expense)} — net <b>${inr(agg.net)}</b> (${rate}% saved).`:`You spent ${inr(-agg.net)} more than came in this period.`);}
  const ex=STATE.rows.filter(r=>!isIncome(r));
  if(ex.length){const big=ex.reduce((m,r)=>Number(r.amount)>Number(m.amount)?r:m);t.push(`Largest single outflow: <b>${esc(big.description.slice(0,40))}</b> (${inr(big.amount)}).`);}
  return t;
}
function savingsAdvice(agg){
  const invest=catSum(agg,"Investments"),transfers=catSum(agg,"Transfers"),charges=catSum(agg,"Bank Charges");
  const spending=Math.max(0,agg.expense-invest-transfers-charges);
  const disc=agg.cats.filter(([c])=>DISCRETIONARY.includes(c)).reduce((s,[,a])=>s+a,0);
  let subTotal=0,subN=0;
  STATE.rows.forEach(r=>{const d=(r.description||'').toLowerCase().replace(/[^a-z0-9]/g,'');
    if(!isIncome(r)&&SUBS.some(s=>d.includes(s))){subTotal+=Number(r.amount)||0;subN++;}});
  const foodRows=STATE.rows.filter(r=>!isIncome(r)&&r.category==='Food & Dining');
  const foodSum=foodRows.reduce((s,r)=>s+(Number(r.amount)||0),0);
  const recs=[]; let potential=0;
  if(charges>0){recs.push(`Bank charges of <b>${inr(charges)}</b> are fully avoidable — keep the required minimum balance and this drops to zero.`);potential+=charges;}
  if(subTotal>0){const half=Math.round(subTotal*0.5);recs.push(`You pay <b>${inr(subTotal)}</b> across ${subN} subscription charge(s). Cancel the ones you rarely use — even half is ~${inr(half)} back.`);potential+=half;}
  if(foodRows.length>=4){const cut=Math.round(foodSum*0.3);recs.push(`You spent <b>${inr(foodSum)}</b> on ${foodRows.length} food/eating-out orders. Cooking a few more meals could save ~${inr(cut)}.`);potential+=cut;}
  else if(disc>0){const cut=Math.round(disc*0.2);recs.push(`Trim discretionary spend (${inr(disc)} on food/shopping/entertainment) by 20% to save ~${inr(cut)}.`);potential+=cut;}
  const spendCats=agg.cats.filter(([c])=>!NONSPEND.includes(c)&&c!=='Others');
  if(spendCats.length){const [c,a]=spendCats[0];if(spending&&a/spending>=0.3)recs.push(`<b>${esc(c)}</b> is your biggest real expense at ${Math.round(a/spending*100)}% of spending (${inr(a)}) — the first place to look at cutting.`);}
  if(agg.income>0){const rate=Math.round(agg.net/agg.income*100);
    recs.push(rate>=20?`Good news: your savings rate is <b>${rate}%</b> (healthy is 20%+).${invest>0?' And '+inr(invest)+' is going into investments — keep it up.':''}`
                      :`Your savings rate is <b>${rate}%</b>. Acting on the points above can push it past a healthy 20%.`);}
  return {potential:Math.round(potential),recs};
}
function render(){
  const agg=aggregate();const maxCat=Math.max(1,...agg.cats.map(c=>c[1]));
  const netColor=agg.net>=0?'var(--green)':'var(--red)';
  const adv=savingsAdvice(agg);
  const legend=agg.cats.map(([c,a])=>`<div class="lg"><span class="em">${ico(c)}</span>${esc(c)}<span class="amt" style="font-weight:700">${inr(a)}</span></div>`).join('');
  const breakdown=agg.cats.map(([c,a])=>{const p=agg.expense?Math.round(a/agg.expense*100):0;
    return `<div class="catrow"><span class="cname">${ico(c)} ${esc(c)}</span>
      <div class="catbar"><div style="width:${Math.round(a/maxCat*100)}%;background:${col(c)}"></div></div>
      <span class="amt">${inr(a)}<span class="pct">${p}%</span></span></div>`;}).join('');
  const opts=c=>STATE.categories.map(x=>`<option ${x===c?'selected':''}>${esc(x)}</option>`).join('');
  const rows=STATE.rows.map((r,i)=>`<tr><td>${esc(r.description)}</td>
     <td><span class="tdot" style="background:${col(r.category)}"></span><select onchange="recat(${i},this.value)">${opts(r.category)}</select></td>
     <td class="r">${inr(r.amount)}</td></tr>`).join('');
  const tips=insights(agg).map(t=>`<li>${t}</li>`).join('');
  const recs=adv.recs.map(r=>`<li><span class="ci">✅</span><span>${r}</span></li>`).join('');
  document.getElementById('out').innerHTML=`
    <div class="kpis">
      <div class="kpi in"><div class="badge">⬇️</div><div><div class="lbl">Money In</div><div class="val" style="color:var(--green)">${inr(agg.income)}</div></div></div>
      <div class="kpi out"><div class="badge">⬆️</div><div><div class="lbl">Money Out</div><div class="val" style="color:var(--red)">${inr(agg.expense)}</div></div></div>
      <div class="kpi net"><div class="badge">💼</div><div><div class="lbl">Net</div><div class="val" style="color:${netColor}">${inr(agg.net)}</div></div></div>
    </div>
    <div class="dash">
      <div class="card donutwrap"><h3>Where money went</h3>${donut(agg.cats,agg.expense)}<div class="legend">${legend}</div></div>
      <div class="card"><h3>Outflow by category</h3>${breakdown||'<span class="hint">No outflows found.</span>'}
        <div class="insights"><h3>Insights</h3><ul>${tips}</ul></div></div>
    </div>
    <div class="coach">
      <div class="coachhead"><span class="coachicon">💰</span><div><div class="ct">You could save about</div><div class="camt">${inr(adv.potential)}</div><div class="ct" style="opacity:.85">this period</div></div></div>
      <ul class="clist">${recs}</ul>
      <div class="coachnote">Estimates from your transactions. Cut the avoidable items first (charges, unused subscriptions), then trim discretionary spending.</div>
    </div>
    <div class="card tblcard">
      <div class="tablehead"><h3 style="margin:0">Transactions &nbsp;<span style="color:var(--muted);font-weight:500;text-transform:none;letter-spacing:0">(change a category if it's wrong)</span></h3>
        <button class="dl" onclick="downloadCSV()">&#8681; Download CSV</button></div>
      <table><thead><tr><th>Description</th><th>Category</th><th class="r">Amount</th></tr></thead><tbody>${rows}</tbody></table>
    </div>`;
}
function recat(i,val){STATE.rows[i].category=val;render();}
function downloadCSV(){
  const lines=[["description","category","amount"]].concat(STATE.rows.map(r=>[`"${(r.description||'').replace(/"/g,'""')}"`,r.category,r.amount]));
  const csv=lines.map(l=>l.join(",")).join("\\n");
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="expenses_categorized.csv";a.click();
}
window.addEventListener('load',loadExample);
</script>
</body></html>
"""


if __name__ == "__main__":
    import uvicorn
    print("ExpenseSort running at http://localhost:8001  (Ctrl+C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
