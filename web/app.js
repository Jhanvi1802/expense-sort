/* ExpenseSort SPA — Stitch-styled, fully wired to the FastAPI backend. */
let TOKEN=localStorage.getItem("es_token")||"";
let ME=null, TAB="dashboard";
let CATS=[], CATMETA={};   // filled from /api/categories
const NONSPEND=["Investments","Transfers","Bank Charges"];

const $=id=>document.getElementById(id);
const esc=s=>(s==null?"":String(s)).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const inr=n=>"₹"+Math.round(Number(n)||0).toLocaleString("en-IN");
const inr2=n=>"₹"+(Number(n)||0).toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2});
const kfmt=n=>{n=Number(n)||0;return n>=1e7?"₹"+(n/1e7).toFixed(1)+"Cr":n>=1e5?"₹"+(n/1e5).toFixed(1)+"L":n>=1e3?"₹"+(n/1e3).toFixed(0)+"k":"₹"+Math.round(n);};
const col=c=>(CATMETA[c]&&CATMETA[c].color)||"#94a3b8";
const ico=c=>(CATMETA[c]&&CATMETA[c].icon)||"📦";
const initials=n=>(n||"?").trim().split(/\s+/).slice(0,2).map(w=>w[0]).join("").toUpperCase();

async function api(path, method="GET", body){
  const opt={method, headers:{}};
  if(TOKEN) opt.headers["Authorization"]="Bearer "+TOKEN;
  if(body){opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(body);}
  const r=await fetch("/api"+path, opt);
  if(r.status===401 && ME){logout(); throw new Error("Session expired");}
  const d=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(d.detail||("Error "+r.status));
  return d;
}
function toast(m){const t=document.createElement("div");t.className="toast";t.textContent=m;document.body.appendChild(t);setTimeout(()=>t.remove(),2600);}
function closeModal(){$("modal").innerHTML="";}
function modal(html){$("modal").innerHTML=`<div class="modal" onclick="if(event.target===this)closeModal()"><div class="card">${html}</div></div>`;}
const EXAMPLE=["Salary credited 60000","Swiggy order 320","Uber ride 180","Amazon purchase 1499",
  "Electricity bill 1200","BigBasket groceries 850","Netflix subscription 199","Apollo pharmacy 430",
  "Jio recharge 299","Zomato dinner 540","LIC insurance premium 3500","Spotify premium 129",
  "Petrol pump 2000","AMB CHRG INCL GST 236"].join("\n");

/* donut svg from [{category,amount}] */
function donut(items, total, centerLabel, centerVal){
  const R=70,C=2*Math.PI*R;let acc=0;
  const segs=items.map(it=>{const seg=total?it.amount/total*C:0;
    const s=`<circle cx="90" cy="90" r="${R}" fill="none" stroke="${col(it.category)}" stroke-width="26" stroke-linecap="butt" stroke-dasharray="${seg} ${C-seg}" stroke-dashoffset="${-acc}" transform="rotate(-90 90 90)"/>`;acc+=seg;return s;}).join("");
  return `<svg width="184" height="184" viewBox="0 0 180 180">${segs}
    <text x="90" y="84" text-anchor="middle" font-size="12" fill="#6c827b">${esc(centerLabel||"TOTAL")}</text>
    <text x="90" y="108" text-anchor="middle" font-size="22" font-weight="800" fill="#0f766e">${esc(centerVal)}</text></svg>`;
}

/* ---------------- AUTH ---------------- */
let authMode="register", pwShown=false;
function renderAuth(){
  $("auth").classList.remove("hidden");$("app").classList.add("hidden");$("onboard").classList.add("hidden");
  const reg=authMode==="register";
  $("auth").innerHTML=`<div class="authwrap">
    <div class="authhero">
      <div class="brand wh"><span class="logo">₹</span> ExpenseSort</div>
      <h1>Sort, split &amp; save — from the statement you already have</h1>
      <p>Financial clarity shouldn't be a chore. We turn your Indian bank statements into actionable insights, splits and budgets — without manual entry.</p>
      <div class="heros"><div><div class="n">10k+</div><div class="l">Active users</div></div>
        <div><div class="n">₹50Cr+</div><div class="l">Tracked monthly</div></div></div>
    </div>
    <div class="authform"><div class="authcard">
      <h2 class="page">${reg?"Create your account":"Welcome back"}</h2>
      <p class="sub">${reg?"Join the modern community of Indians managing money better.":"Log in to your ExpenseSort dashboard."}</p>
      <div id="af"></div>
      <label style="display:${reg?'flex':'none'};gap:8px;font-size:12.5px;margin-top:14px;align-items:flex-start">
        <input type="checkbox" id="i_terms" style="width:auto;margin-top:3px"> <span>I agree to the <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>.</span></label>
      <div class="err" id="aerr"></div>
      <button class="btn" style="width:100%;margin-top:10px" onclick="submitAuth()">${reg?"Create Account →":"Log In →"}</button>
      <div class="divider">OR CONTINUE WITH</div>
      <div class="oauth"><button onclick="toast('Social login is a demo stub')"><b>G</b> Google</button>
        <button onclick="toast('Social login is a demo stub')"><b>⌥</b> GitHub</button></div>
      <p class="sub" style="text-align:center;margin-top:20px">${reg?"Already have an account?":"New here?"}
        <button class="link" onclick="setAuth('${reg?'login':'register'}')">${reg?"Log In":"Sign Up"}</button></p>
    </div></div>
  </div>`;
  $("af").innerHTML=(reg?`<label class="fld">FULL NAME</label><input id="i_name" placeholder="Arjun Sharma">`:``)
    +`<label class="fld">EMAIL ADDRESS</label><input id="i_email" type="email" placeholder="arjun@company.in">
      <label class="fld">PASSWORD</label><div style="position:relative"><input id="i_pw" type="password" placeholder="••••••••">
      <button class="eye" onclick="togglePw()">${pwShown?'🙈':'👁'}</button></div>`
    +(reg?`<label class="fld">UPI ID (OPTIONAL) <span class="pill g" style="float:right">FOR EASY SPLITS</span></label><input id="i_upi" placeholder="arjun@okaxis">`:``);
}
function setAuth(m){authMode=m;renderAuth();}
function togglePw(){pwShown=!pwShown;const i=$("i_pw");i.type=pwShown?"text":"password";renderAuthKeep(i.value);}
function renderAuthKeep(v){renderAuth();$("i_pw").value=v;$("i_pw").type=pwShown?"text":"password";}
async function submitAuth(){
  $("aerr").textContent="";
  try{
    const reg=authMode==="register";
    const email=$("i_email").value.trim(),pw=$("i_pw").value;
    if(!email||!pw){$("aerr").textContent="Email and password are required";return;}
    if(reg && !$("i_terms").checked){$("aerr").textContent="Please accept the Terms to continue";return;}
    const body=reg?{email,password:pw,name:$("i_name").value.trim()||email.split("@")[0],upi_id:$("i_upi").value.trim()}
                  :{email,password:pw};
    const d=await api("/"+(reg?"register":"login"),"POST",body);
    TOKEN=d.token;localStorage.setItem("es_token",TOKEN);boot();
  }catch(e){$("aerr").textContent=e.message;}
}
function logout(){TOKEN="";ME=null;localStorage.removeItem("es_token");renderAuth();}

/* ---------------- ONBOARDING ---------------- */
let obStep=1;const OB_TOTAL=4, obData={};
function startOnboard(){obStep=1;renderOb();}
function renderOb(){
  $("auth").classList.add("hidden");$("app").classList.add("hidden");$("onboard").classList.remove("hidden");
  const pct=Math.round(obStep/OB_TOTAL*100);
  let body="";
  if(obStep===1) body=`<div style="text-align:center">
     <div style="font-size:44px">👋</div><h2 style="font-size:24px;margin:12px 0">Welcome to ExpenseSort</h2>
     <p style="opacity:.9">Let's set up your money in about a minute.</p></div>`;
  else if(obStep===2) body=`<div style="text-align:center"><h2 style="font-size:24px">Your Profile</h2>
     <p style="opacity:.85;margin-bottom:6px">Personalize your financial identity.</p></div>
     <div class="obavatar">📷</div>
     <label class="fld" style="color:#fff">FULL NAME</label><input id="ob_name" value="${esc(ME.name||'')}" placeholder="Arjun Sharma">
     <label class="fld" style="color:#fff">PHONE NUMBER (OPTIONAL)</label><input id="ob_phone" placeholder="+91 98765 43210">
     <label class="fld" style="color:#fff">UPI ID</label><input id="ob_upi" value="${esc(ME.upi_id||'')}" placeholder="arjun@okaxis">
     <p style="font-size:12px;opacity:.8;margin-top:6px">ⓘ so friends can pay you back in one tap</p>`;
  else if(obStep===3) body=`<div style="text-align:center"><h2 style="font-size:24px">Your Income</h2>
     <p style="opacity:.85">Powers your cash-flow forecast. You can skip this.</p></div>
     <label class="fld" style="color:#fff;text-align:center">USUAL MONTHLY INCOME</label>
     <input id="ob_income" type="number" style="font-size:26px;text-align:center" placeholder="₹ 85,000">`;
  else body=`<div style="text-align:center"><h2 style="font-size:24px">Add your first data</h2>
     <p style="opacity:.85;margin-bottom:14px">Upload a statement or paste a few transactions.</p></div>
     <label class="btn mint" for="ob_file" style="width:100%">↑ Upload statement (PDF/CSV/TXT)</label>
     <input id="ob_file" type="file" accept=".pdf,.csv,.txt" style="display:none" onchange="obUpload()">
     <p id="ob_fname" style="font-size:12px;opacity:.85;text-align:center;margin:8px 0"></p>
     <textarea id="ob_tx" placeholder="Salary credited 60000&#10;Swiggy order 320" style="color:#fff;border-color:rgba(255,255,255,.3)"></textarea>
     <button class="link" style="color:var(--mint)" onclick="$('ob_tx').value=EXAMPLE">Use sample data</button>`;
  $("onboard").innerHTML=`<div class="obwrap"><div style="width:100%;max-width:440px">
    <div class="brand wh" style="justify-content:center;margin-bottom:18px"><span class="logo">₹</span> ExpenseSort</div>
    <div class="obcard">
      <div class="obtop"><span>Onboarding</span><span>Step ${obStep} of ${OB_TOTAL}</span></div>
      <div class="obprog"><div style="width:${pct}%"></div></div>
      ${body}
      <div class="rowb" style="margin-top:24px">
        ${obStep>1?`<button class="btn ghost" style="color:#fff;border-color:rgba(255,255,255,.4)" onclick="obPrev()">← Back</button>`:`<span></span>`}
        <div style="display:flex;gap:10px">
          ${(obStep===3||obStep===4)?`<button class="link" style="color:var(--mint)" onclick="obNext(true)">Skip</button>`:``}
          <button class="btn mint" onclick="obNext()">${obStep===OB_TOTAL?"Finish":"Continue →"}</button>
        </div>
      </div>
    </div></div></div>`;
}
function obPrev(){if(obStep>1)obStep--;renderOb();}
async function obUpload(){
  const inp=$("ob_file");if(!inp.files.length)return;
  $("ob_fname").textContent="reading "+inp.files[0].name+"...";
  const fd=new FormData();fd.append("file",inp.files[0]);
  const r=await fetch("/api/extract",{method:"POST",headers:{Authorization:"Bearer "+TOKEN},body:fd});
  const d=await r.json();obData.uploaded=r.ok;
  $("ob_fname").textContent=r.ok?`✓ added ${d.added} transactions`:`error: ${d.detail||''}`;
}
async function obNext(skip){
  try{
    if(obStep===2){await api("/me","POST",{name:$("ob_name").value.trim(),phone:$("ob_phone").value.trim(),upi_id:$("ob_upi").value.trim()});}
    if(obStep===3 && !skip){const v=parseFloat($("ob_income").value);if(v)await api("/me","POST",{monthly_income:v});}
    if(obStep===4){const t=($("ob_tx").value||"").trim();if(t)await api("/ingest","POST",{text:t});
      await api("/onboard","POST",{});await boot();return;}
    if(obStep<OB_TOTAL){obStep++;renderOb();}
  }catch(e){toast(e.message);}
}

/* ---------------- SHELL ---------------- */
const TABS=[["dashboard","Dashboard"],["transactions","Transactions"],["recurring","Recurring"],
  ["budgets","Budgets"],["trends","Trends"],["forecast","Forecast"],["tax","Tax"],["split","Split"]];
function renderNav(){
  $("nav").innerHTML=TABS.map(([k,l])=>`<button class="${TAB===k?'on':''}" onclick="go('${k}')">${l}</button>`).join("");
  const av=$("avatar");
  av.innerHTML=ME&&ME.photo?`<img src="${esc(ME.photo)}">`:initials(ME?ME.name:"");
}
async function go(tab){TAB=tab;renderNav();window.scrollTo(0,0);
  try{await VIEWS[tab]();}catch(e){$("view").innerHTML=`<div class="card">Error loading: ${esc(e.message)}</div>`;}}
async function boot(){
  ME=await api("/me").catch(()=>null);
  if(!ME)return logout();
  const c=await api("/categories");CATS=c.categories.map(x=>x.name);
  CATMETA={};c.categories.forEach(x=>CATMETA[x.name]={color:x.color,icon:x.icon});
  if(!ME.onboarded){$("auth").classList.add("hidden");startOnboard();return;}
  applyTheme();
  $("auth").classList.add("hidden");$("onboard").classList.add("hidden");$("app").classList.remove("hidden");
  renderNav();go("dashboard");
}
function applyTheme(){const t=(ME&&ME.prefs&&ME.prefs.theme)||"light";
  const dark=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme:dark)").matches);
  document.body.classList.toggle("dark",dark);}

const VIEWS={};
function fab(fn){return `<button class="fab" onclick="${fn}">+</button>`;}

/* ---------- DASHBOARD ---------- */
VIEWS.dashboard=async function(){
  const d=await api("/dashboard"), h=await api("/health").catch(()=>null);
  const spend=d.by_category.filter(c=>!NONSPEND.includes(c.category));
  const legend=d.by_category.slice(0,6).map(c=>{const p=d.expense?Math.round(c.amount/d.expense*100):0;
    return `<div class="listrow" style="padding:10px 0"><span class="micon" style="background:${col(c.category)}22;color:${col(c.category)}">${ico(c.category)}</span>
      <b>${esc(c.category)}</b><span style="margin-left:auto;text-align:right"><b>${inr(c.amount)}</b><div class="muted fs13">${p}% of total</div></span></div>`;}).join("");
  const recs=(d.coach.recs||[]).slice(0,3).map(r=>`<li><span class="check"></span><span>${r}</span></li>`).join("");
  const pcpct=Math.min(100,(ME.upi_id?25:0)+(ME.monthly_income?25:0)+(ME.phone?25:0)+25);
  $("view").innerHTML=`
    <div class="dropzone" id="dz" ondragover="event.preventDefault();this.classList.add('drag')" ondragleave="this.classList.remove('drag')" ondrop="dzDrop(event)">
      <div class="micon" style="margin:0 auto 10px;width:54px;height:54px;font-size:24px">📄</div>
      <div class="cardtitle">Upload or Paste Statement</div>
      <p class="muted mt" style="margin-top:6px">Drag &amp; drop your bank PDF/CSV here, or paste transactions to sort instantly.</p>
      <div class="rowb" style="justify-content:center;margin-top:14px">
        <label class="btn sm" for="dfile">Choose file</label><input id="dfile" type="file" accept=".pdf,.csv,.txt" style="display:none" onchange="dashUpload()">
        <button class="btn sm mint" onclick="pasteModal()">Paste text</button>
        <button class="link" onclick="tryExample()">Try an example</button>
      </div><p class="muted fs13" id="dz_msg" style="margin-top:8px"></p>
    </div>
    <div class="grid g3" style="margin:18px 0">
      <div class="kpi in"><div class="badge">📈</div><div><div class="lbl">Money In</div><div class="val">${inr(d.income)}</div></div></div>
      <div class="kpi out"><div class="badge">📉</div><div><div class="lbl">Money Out</div><div class="val">${inr(d.expense)}</div></div></div>
      <div class="kpi"><div class="badge">💼</div><div><div class="lbl">Net Savings</div><div class="val">${inr(d.net)}</div></div></div>
    </div>
    <div class="dash">
      <div class="card">
        <div class="rowb mb"><div class="cardtitle">Spending by Category</div></div>
        ${spend.length?`<div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center"><div class="donutwrap">${donut(spend,d.expense,"TOTAL",kfmt(d.expense))}</div>
          <div style="flex:1;min-width:220px">${legend}</div></div>`:'<p class="muted">No spending yet — add a statement above.</p>'}
      </div>
      <div>
        <div class="card mb"><h3>💡 Insights</h3>${(d.insights||[]).map(t=>`<p class="fs13" style="margin:9px 0">• ${t}</p>`).join("")||'<span class="muted">—</span>'}</div>
        <div class="gradcard mint">
          <div class="rowb"><div><div style="font-size:22px;font-weight:800">Savings Coach</div><div style="opacity:.85;font-size:12.5px">Personalized for you</div></div><div style="font-size:24px">🧠</div></div>
          <div style="margin:14px 0 4px;opacity:.9;font-size:13px">You could save</div>
          <div style="font-size:34px;font-weight:800">${inr(d.coach.potential)} <span style="font-size:14px;font-weight:600;opacity:.85">this period</span></div>
          <ul class="coachlist">${recs}</ul>
          <button class="btn dark" style="width:100%" onclick="go('budgets')">Set up budgets</button>
        </div>
        <div class="card mt"><div class="rowb"><b class="fs13">Profile Completion</b><b class="fs13">${pcpct}%</b></div>
          <div class="bar mt" style="margin-top:8px"><div style="width:${pcpct}%"></div></div></div>
      </div>
    </div>${fab("pasteModal()")}`;
};
function tryExample(){api("/ingest","POST",{text:EXAMPLE}).then(()=>{toast("Sample added");go("dashboard");});}
function pasteModal(){modal(`<div class="cardtitle mb">Paste transactions</div>
  <textarea id="p_tx" placeholder="Salary credited 60000&#10;Swiggy order 320"></textarea>
  <div class="rowb mt"><button class="link" onclick="$('p_tx').value=EXAMPLE">Example</button>
   <div><button class="link" onclick="closeModal()">Cancel</button> <button class="btn sm" onclick="pasteGo()">Add & analyze</button></div></div>`);}
async function pasteGo(){const t=$("p_tx").value.trim();if(!t)return;await api("/ingest","POST",{text:t});closeModal();toast("Added");go("dashboard");}
async function dashUpload(){await doUpload($("dfile"),$("dz_msg"));go("dashboard");}
async function dzDrop(e){e.preventDefault();e.currentTarget.classList.remove("drag");
  const f=e.dataTransfer.files[0];if(!f)return;const inp=$("dfile");const dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;await dashUpload();}
async function doUpload(inp,msgEl){
  if(!inp.files.length)return;if(msgEl)msgEl.textContent="reading "+inp.files[0].name+"...";
  const fd=new FormData();fd.append("file",inp.files[0]);
  const r=await fetch("/api/extract",{method:"POST",headers:{Authorization:"Bearer "+TOKEN},body:fd});
  const d=await r.json();if(msgEl)msgEl.textContent=r.ok?`✓ added ${d.added} transactions`:`error: ${d.detail||''}`;
}

/* ---------- TRANSACTIONS ---------- */
let txPage=1, txQuery="";
VIEWS.transactions=async function(){txPage=1;txQuery="";await renderTx();};
async function renderTx(){
  const d=await api(`/transactions?page=${txPage}&size=8${txQuery?`&q=${encodeURIComponent(txQuery)}`:''}`);
  const dash=await api("/dashboard");
  const goals=(await api("/goals")).goals;
  const g=goals[0];
  const opts=c=>CATS.map(x=>`<option ${x===c?'selected':''}>${esc(x)}</option>`).join("");
  const rows=d.rows.map(r=>`<tr>
    <td class="muted">${esc(r.txn_date||'—')}</td>
    <td><b>${esc(r.description)}</b> ${r.is_recurring?'<span class="pill rec">↻ RECURRING</span>':''}</td>
    <td><span class="pill g"><span class="tdot" style="background:${col(r.category)}"></span>
      <select onchange="recat(${r.id},this.value)" style="border:0;background:none;padding:0;width:auto;font-weight:700;color:var(--teal)">${opts(r.category)}</select></span></td>
    <td class="r" style="font-weight:700;color:${r.direction==='credit'?'var(--green)':'var(--ink)'}">${r.direction==='credit'?'+ ':'- '}${inr2(r.amount)}</td></tr>`).join("")
    ||`<tr><td colspan=4 class="muted" style="text-align:center;padding:30px">No transactions found.</td></tr>`;
  $("view").innerHTML=`
    <div class="grid" style="grid-template-columns:1.7fr 1fr;gap:18px;margin-bottom:18px">
      <div class="gradcard"><div class="lbl" style="opacity:.8;font-size:11px;letter-spacing:.5px">TOTAL BALANCE</div>
        <div style="font-size:40px;font-weight:800;margin:6px 0 18px">${inr2(dash.balance)}</div>
        <div class="rowb"><div style="display:flex;gap:26px">
          <div><div class="lbl" style="opacity:.75">Money In</div><div style="font-weight:700">${inr(dash.income)}</div></div>
          <div><div class="lbl" style="opacity:.75">Money Out</div><div style="font-weight:700">${inr(dash.expense)}</div></div></div>
          <button class="btn mint sm" onclick="go('trends')">View Analytics</button></div></div>
      <div class="card" style="text-align:center;display:flex;flex-direction:column;justify-content:center">
        ${g?`<div class="micon" style="margin:0 auto 8px;background:var(--mintbg);color:var(--teal);width:52px;height:52px;font-size:24px">🐷</div>
          <div class="cardtitle">${esc(g.name)}</div><div class="muted fs13">Saving Goal</div>
          <div class="bar" style="margin:14px 0 8px"><div style="width:${g.pct}%"></div></div>
          <b class="fs13" style="color:var(--teal)">${g.pct}% Achieved</b>`
          :`<div class="micon" style="margin:0 auto 8px;background:var(--mintbg);color:var(--teal);width:52px;height:52px;font-size:24px">🐷</div>
            <div class="cardtitle">No saving goal yet</div><button class="btn sm mt" onclick="goalModal()">Create a goal</button>`}
      </div>
    </div>
    <div class="card">
      <div class="rowb mb"><div><div class="cardtitle">Transactions</div><div class="muted fs13">Review and edit your recent activity</div></div>
        <div style="display:flex;gap:10px;align-items:center">
          <input class="box" style="width:220px" placeholder="🔍 Search transactions..." value="${esc(txQuery)}" onkeydown="if(event.key==='Enter'){txQuery=this.value;txPage=1;renderTx();}">
          <button class="btn sm" onclick="pasteModal()">+ Add New</button></div></div>
      <table><thead><tr><th>Date</th><th>Description</th><th>Category</th><th class="r">Amount</th></tr></thead><tbody>${rows}</tbody></table>
      <div class="rowb mt"><span class="muted fs13">Showing ${d.rows.length} of ${d.total} transactions</span>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="iconbtn" onclick="if(txPage>1){txPage--;renderTx();}">‹</button>
          <span class="fs13">Page ${d.page} of ${d.pages}</span>
          <button class="iconbtn" onclick="if(txPage<${d.pages}){txPage++;renderTx();}">›</button></div></div>
    </div>
    <div class="grid" style="grid-template-columns:1fr 2fr;gap:18px;margin-top:18px">
      <div class="card" style="background:var(--peach)"><div style="font-size:20px">✨</div>
        <div class="cardtitle mt" style="margin-top:8px">Smart Split</div><p class="fs13 muted">Automatically split shared expenses with your flatmates.</p>
        <button class="link" onclick="go('split')">SET UP NOW →</button></div>
      <div class="card" style="background:var(--bg)"><div class="rowb"><div><div class="cardtitle">Weekly Insights</div>
        <p class="fs13" style="max-width:520px">${esc((dash.insights&&dash.insights[0])||'Add more statements to unlock weekly insights.')}</p></div>
        <button class="btn outline sm" onclick="go('budgets')">View Budget Tips</button></div></div>
    </div>${fab("pasteModal()")}`;
}
async function recat(id,cat){await api("/transactions/recategorize","POST",{id,category:cat});toast("Category updated");}
function goalModal(){modal(`<div class="cardtitle mb">New saving goal</div>
  <label class="fld">GOAL NAME</label><input class="box" id="gl_name" placeholder="New Car Fund">
  <label class="fld">TARGET AMOUNT</label><input class="box" id="gl_target" type="number" placeholder="100000">
  <label class="fld">ALREADY SAVED</label><input class="box" id="gl_saved" type="number" placeholder="0">
  <div class="rowb mt"><button class="link" onclick="closeModal()">Cancel</button><button class="btn sm" onclick="goalGo()">Create</button></div>`);}
async function goalGo(){const n=$("gl_name").value.trim(),t=parseFloat($("gl_target").value);
  if(!n||!t){toast("Name and target needed");return;}
  await api("/goals","POST",{name:n,target:t,saved:parseFloat($("gl_saved").value)||0});closeModal();toast("Goal created");go("transactions");}

/* ---------- RECURRING ---------- */
VIEWS.recurring=async function(){
  const d=await api("/recurring");
  const projYear=Math.round(d.recurring_total*12);
  const list=d.series.map(s=>`<div class="listrow"><span class="micon" style="background:${s.is_subscription?'var(--mintbg)':'var(--peach)'}">${s.is_subscription?'▶':'☁'}</span>
    <div><b>${esc(s.label)}</b><div style="margin-top:3px">${s.is_subscription?'<span class="pill sub">SUBSCRIPTION</span>':'<span class="pill rec">RECURRING</span>'} <span class="muted fs13">${s.cadence} · seen ${s.count}×</span></div></div>
    <div style="margin-left:auto;text-align:right"><b>${inr2(s.avg_amount)}</b><div class="muted fs13">avg / charge</div></div></div>`).join("")
    ||`<p class="muted" style="padding:20px">Add 2+ statements (or repeated charges) to detect subscriptions.</p>`;
  $("view").innerHTML=`
    <div class="rowb mb"><div><h2 class="page">Recurring Payments</h2><div class="sub">Your fixed commitments and subscriptions.</div></div>
      <button class="btn" onclick="toast('Detected automatically from your statements')">+ Add Subscription</button></div>
    <div class="grid" style="grid-template-columns:1.7fr 1fr;gap:18px;margin-bottom:18px">
      <div class="gradcard"><div class="lbl" style="opacity:.8">MONTHLY COMMITMENT</div>
        <div style="font-size:38px;font-weight:800;margin:6px 0 16px">${inr(d.recurring_total)} <span style="font-size:15px;opacity:.8;font-weight:600">/ month</span></div>
        <div style="display:flex;gap:12px"><div class="chip" style="background:rgba(255,255,255,.15)"><div class="k" style="color:#cfe">Projected / year</div><div class="v" style="color:#fff">${inr(projYear)}</div></div>
          <div class="chip" style="background:rgba(255,255,255,.15)"><div class="k" style="color:#cfe">Subscriptions</div><div class="v" style="color:#fff">${d.subscription_count}</div></div></div></div>
      <div class="card" style="text-align:center;display:flex;flex-direction:column;justify-content:center">
        <div class="micon" style="margin:0 auto 8px;width:52px;height:52px;font-size:24px">📅</div>
        <div style="font-size:30px;font-weight:800">${d.series.length} Active</div><div class="muted">Recurring items</div></div>
    </div>
    <div class="card">${list}</div>
    ${d.subscription_count>1?`<div class="alert peach mt"><span style="font-size:20px">💡</span>
      <div><b>Optimization Alert</b><div class="fs13">You have ${d.subscription_count} subscriptions totalling ${inr(d.subscription_total)}/mo. Review overlaps to save up to ${inr(Math.round(d.subscription_total*0.5*12))}/year.</div></div>
      <button class="btn dark sm" style="margin-left:auto" onclick="go('trends')">Review Now</button></div>`:''}
    ${fab("pasteModal()")}`;
};

/* ---------- BUDGETS ---------- */
VIEWS.budgets=async function(){
  const d=await api("/budgets"), h=await api("/health").catch(()=>null), f=await api("/forecast").catch(()=>null);
  const totalBudget=d.budgets.reduce((s,b)=>s+b.limit,0), spent=d.budgets.reduce((s,b)=>s+b.spent,0);
  const remaining=totalBudget-spent, util=totalBudget?Math.round(spent/totalBudget*100):0;
  const rows=d.budgets.map(b=>{const c=b.state==='over'?'var(--red)':b.state==='warn'?'var(--amber)':'var(--green)';
    const label=b.state==='over'?`${b.pct}% OVER LIMIT`:b.state==='warn'?`${b.pct}% USED`:`${b.pct}% UTILIZED`;
    return `<div style="margin:16px 0"><div class="rowb"><div style="display:flex;gap:12px;align-items:center">
      <span class="micon" style="background:${col(b.category)}22;color:${col(b.category)};width:40px;height:40px">${ico(b.category)}</span>
      <div><b>${esc(b.category)}</b><div class="muted fs13">${inr(b.spent)} / ${inr(b.limit)}</div></div></div>
      <span class="pill ${b.state}">${label}</span></div>
      <div class="bar" style="margin-top:8px"><div style="width:${Math.min(100,b.pct)}%;background:${c}"></div></div>
      ${b.state==='over'?`<div class="fs13" style="color:var(--red);margin-top:5px">${inr(-b.remaining)} over budget. Adjust next month's goal. <button class="link" onclick="delBudget('${esc(b.category)}')">remove</button></div>`
        :`<div class="fs13 muted" style="margin-top:4px">${inr(b.remaining)} remaining <button class="link" onclick="delBudget('${esc(b.category)}')">remove</button></div>`}</div>`;}).join("")
    ||'<p class="muted">No budgets yet — add one below.</p>';
  $("view").innerHTML=`
    <div class="rowb mb"><div><div class="eyebrow">MONTHLY OVERVIEW</div><h2 class="page">Budget Management</h2></div>
      <div style="display:flex;gap:20px"><div class="chip" style="background:none"><div class="k">Total Budget</div><div class="v">${inr(totalBudget)}</div></div>
        <div class="chip" style="background:none"><div class="k">Remaining</div><div class="v" style="color:${remaining<0?'var(--red)':'var(--teal)'}">${inr(remaining)}</div></div></div></div>
    <div class="grid" style="grid-template-columns:1fr 1.8fr;gap:18px">
      <div class="gradcard"><div class="cardtitle" style="color:#fff">Overall Spend</div>
        <p style="opacity:.9;font-size:13.5px;margin-top:6px">You've used ${util}% of your monthly allocation.${util<80?" You're doing great!":""}</p>
        <div style="margin-top:auto;padding-top:40px"><div style="font-size:40px;font-weight:800">${inr(spent)}</div><div class="lbl" style="opacity:.8">SPENT THIS MONTH</div></div></div>
      <div class="card"><div class="cardtitle mb">Active Budgets</div>${rows}</div>
    </div>
    <div class="dropzone mt" style="text-align:left;padding:18px">
      <div class="rowb"><div style="display:flex;gap:12px;align-items:center"><span class="micon" style="background:var(--mintbg);color:var(--teal)">＋</span>
        <div><b>New Budget Category</b><div class="muted fs13">Planning a purchase or trip? Set a dedicated limit.</div></div></div>
        <div style="display:flex;gap:10px;align-items:center">
          <select class="box" id="b_cat" style="width:180px">${CATS.map(c=>`<option>${c}</option>`).join("")}</select>
          <input class="box" id="b_amt" type="number" placeholder="Amount ₹" style="width:130px">
          <button class="btn sm" onclick="saveBudget()">SET BUDGET</button></div></div></div>
    <div class="grid g3 mt">
      <div class="card"><div style="font-size:18px">📈</div><div class="cardtitle mt" style="margin-top:8px">Saving Forecast</div>
        <p class="fs13 muted">${f&&f.available?esc(f.message):"Add statements to forecast savings."}</p></div>
      <div class="card"><div style="font-size:18px">🔔</div><div class="cardtitle mt" style="margin-top:8px">Smart Alerts</div>
        <p class="fs13 muted">${d.budgets.filter(b=>b.state!=='ok').length} categories need attention this month.</p><button class="link" onclick="go('trends')">REVIEW NOW</button></div>
      <div class="card" style="text-align:center"><div class="micon" style="margin:0 auto;width:46px;height:46px">🏅</div>
        <div class="cardtitle mt" style="margin-top:8px">Financial Health</div>
        <div style="font-size:26px;font-weight:800;color:var(--teal)">${h?h.band:'—'}</div><div class="muted fs13">Score: ${h?h.score:'—'} / 900</div></div>
    </div>${fab("pasteModal()")}`;
};
async function saveBudget(){const c=$("b_cat").value,a=parseFloat($("b_amt").value);if(!a){toast("Enter an amount");return;}
  await api("/budgets","POST",{category:c,limit_amount:a});go("budgets");}
async function delBudget(c){await api("/budgets/"+encodeURIComponent(c),"DELETE");go("budgets");}

/* ---------- TRENDS ---------- */
VIEWS.trends=async function(){
  const d=await api("/trends"), dash=await api("/dashboard"), f=await api("/forecast").catch(()=>null), rec=await api("/recurring");
  const m=d.monthly, maxv=Math.max(1,...m.map(x=>Math.max(x.income,x.expense)));
  const avgSave=m.length?Math.round(m.reduce((s,x)=>s+x.net,0)/m.length):0;
  const bars=m.slice(-6).map(x=>`<div style="flex:1;text-align:center">
    <div style="display:flex;gap:4px;align-items:flex-end;height:150px;justify-content:center">
      <div title="in ${inr(x.income)}" style="width:16px;background:var(--teal);border-radius:4px 4px 0 0;height:${Math.round(x.income/maxv*148)||2}px"></div>
      <div title="out ${inr(x.expense)}" style="width:16px;background:var(--red);border-radius:4px 4px 0 0;height:${Math.round(x.expense/maxv*148)||2}px"></div></div>
    <div class="muted fs13" style="margin-top:6px">${esc((x.month||'').slice(5))}</div></div>`).join("");
  const brk=[...m].reverse().slice(0,6).map(x=>`<tr><td><b>${esc(x.month)}</b></td>
    <td class="r" style="color:var(--green)">${inr(x.income)}</td><td class="r" style="color:var(--red)">${inr(x.expense)}</td>
    <td class="r"><b>${inr(x.net)}</b></td><td class="r">${x.net>=0?'📈':'📉'}</td></tr>`).join("");
  const tm=dash.top_merchant;
  const subs=rec.series.slice(0,3).map(s=>`<div class="listrow" style="padding:9px 0"><span class="micon" style="width:34px;height:34px;font-size:15px">${s.is_subscription?'📺':'🔁'}</span>
    <div><b class="fs13">${esc(s.label)}</b><div class="muted" style="font-size:11px">${s.cadence}</div></div><b class="fs13" style="margin-left:auto">${inr(s.avg_amount)}</b></div>`).join("")||'<span class="muted fs13">None yet</span>';
  $("view").innerHTML=`
    ${d.anomalies.map(a=>`<div class="alert ${a.type==='duplicate'?'dup':''}"><span style="font-size:18px">${a.type==='price_hike'?'⚠️':'📄'}</span>
      <div><b>${a.type==='price_hike'?'Price hike detected:':'Possible duplicate:'}</b> ${esc(a.message)}</div>
      <button class="link" style="margin-left:auto" onclick="this.closest('.alert').remove()">Dismiss</button></div>`).join("")}
    <div class="grid" style="grid-template-columns:1.7fr 1fr;gap:18px;margin-bottom:18px">
      <div class="card"><div class="rowb mb"><div class="cardtitle">Income vs Expenses</div>
        <span class="fs13"><span style="color:var(--teal)">● Income</span> &nbsp; <span style="color:var(--red)">● Expense</span></span></div>
        ${m.length?`<div style="display:flex;gap:8px;align-items:flex-end">${bars}</div>`:'<p class="muted">Add statements across months to see trends.</p>'}</div>
      <div style="display:flex;flex-direction:column;gap:18px">
        <div class="gradcard"><div class="lbl" style="opacity:.8">AVG MONTHLY SAVINGS</div><div style="font-size:32px;font-weight:800;margin-top:6px">${inr(avgSave)}</div>
          <div class="fs13" style="opacity:.85;margin-top:6px">across ${m.length} month(s)</div></div>
        <div class="card"><h3>Burn Rate</h3><div style="font-size:24px;font-weight:800;color:var(--red)">${inr(f&&f.burn?f.burn.per_day:0)}<span class="fs13 muted" style="font-weight:600">/day</span></div>
          <div class="muted fs13">avg daily spend over ${f&&f.burn?f.burn.days:0} active days</div></div>
      </div>
    </div>
    <div class="grid g2 mb">
      <div class="card"><h3>Recurring Subs</h3>${subs}</div>
      <div class="card"><h3>Top Merchant</h3>${tm?`<div class="rowb"><div><b>${esc(tm.name)}</b><div class="muted fs13">${esc(tm.category)} · ${tm.count}×</div></div>
        <b>${inr(tm.spent)}</b></div>`:'<span class="muted fs13">No data</span>'}</div>
    </div>
    <div class="card"><div class="rowb mb"><div class="cardtitle">Trend Breakdown</div></div>
      <table><thead><tr><th>Month</th><th class="r">Income</th><th class="r">Expense</th><th class="r">Surplus</th><th class="r">Trend</th></tr></thead>
      <tbody>${brk||'<tr><td colspan=5 class="muted">No monthly data yet.</td></tr>'}</tbody></table></div>
    ${fab("pasteModal()")}`;
};

/* ---------- FORECAST ---------- */
VIEWS.forecast=async function(){
  const f=await api("/forecast");
  if(!f.available){$("view").innerHTML=`<h2 class="page">Cash-flow Forecast</h2><div class="card mt muted">${esc(f.message)}</div>${fab("pasteModal()")}`;return;}
  const reliability=Math.min(95,50+f.months*12);
  const up=f.upcoming.map(u=>`<div class="listrow" style="padding:12px 0"><span class="micon" style="width:40px;height:40px;background:${u.kind==='income'?'#e6f7ee':'var(--peach)'}">${u.kind==='income'?'💰':'🧾'}</span>
    <div><b class="fs13">${esc(u.label)}</b><div class="muted" style="font-size:11px">${u.cadence}</div></div>
    <b style="margin-left:auto;color:${u.kind==='income'?'var(--green)':'var(--red)'}">${u.kind==='income'?'+':'-'}${inr(u.amount)}</b></div>`).join("")||'<span class="muted fs13">No recurring items detected yet.</span>';
  $("view").innerHTML=`
    <div class="gradcard mb"><div class="rowb"><div>
      <div class="lbl" style="opacity:.8">NEXT 30 DAYS FORECAST</div>
      <div style="font-size:36px;font-weight:800;margin:6px 0">Projected ${f.projected_net>=0?'Surplus':'Shortfall'}: ${inr(Math.abs(f.projected_net))}</div>
      <p style="opacity:.9;max-width:520px">${esc(f.message)}</p>
      <div style="margin-top:16px;display:flex;gap:10px"><button class="btn mint" onclick="goalModal()">Move to a goal</button>
        <button class="btn ghost" style="color:#fff;border-color:rgba(255,255,255,.4)" onclick="go('trends')">View Details</button></div></div>
      <div class="card" style="background:rgba(255,255,255,.12);border:0;min-width:180px"><div class="fs13" style="color:#fff;opacity:.85">Committed recurring</div>
        <div style="font-size:24px;font-weight:800;color:#fff">${inr(f.committed_recurring)}</div><div class="fs13" style="color:#cfe">/ month</div></div></div>
    <div class="grid" style="grid-template-columns:1.6fr 1fr;gap:18px">
      <div class="card"><div class="rowb mb"><div class="cardtitle">Projection</div></div>
        <div class="grid g3"><div class="kpi in"><div class="badge">💰</div><div><div class="lbl">Income</div><div class="val" style="font-size:20px">${inr(f.projected_income)}</div></div></div>
          <div class="kpi out"><div class="badge">🧾</div><div><div class="lbl">Spend</div><div class="val" style="font-size:20px">${inr(f.projected_expense)}</div></div></div>
          <div class="kpi"><div class="badge">📊</div><div><div class="lbl">Burn / day</div><div class="val" style="font-size:20px">${inr(f.burn.per_day)}</div></div></div></div>
        <h3 class="mt" style="margin-top:20px">What-if simulation</h3>
        <div class="rowb"><input class="box" id="sim_amt" type="number" placeholder="Planned purchase ₹" style="max-width:220px" oninput="simCalc(${f.projected_net})">
          <div id="sim_out" class="fs13 muted">Enter an amount to see the impact.</div></div></div>
      <div class="card"><div class="cardtitle mb">Upcoming</div>${up}
        <div class="mt" style="margin-top:16px;text-align:center"><div style="font-size:22px;font-weight:800;color:var(--teal)">${reliability}%</div>
          <div class="muted fs13">Forecast reliability · based on ${f.months} month(s) of history</div></div></div>
    </div>${fab("pasteModal()")}`;
};
function simCalc(net){const v=parseFloat($("sim_amt").value)||0;const after=net-v;
  $("sim_out").innerHTML=v?`Your projected net becomes <b style="color:${after<0?'var(--red)':'var(--green)'}">${inr(after)}</b>. ${after<0?'Not recommended this month.':'Looks affordable.'}`:'Enter an amount to see the impact.';}

/* ---------- TAX ---------- */
VIEWS.tax=async function(){
  const d=await api("/tax");
  const util=Math.round(d.total_claimable/(150000+25000+50000)*100);
  const rows=d.sections.map(s=>`<tr><td><b style="color:${s.section.startsWith('80D')?'var(--red)':'var(--teal)'}">${esc(s.section)}</b></td>
    <td>${esc(s.label)}${s.entries.length?'<div class="muted fs13">'+s.entries.map(e=>esc(e.label)).join(', ')+'</div>':''}</td>
    <td class="r">${inr(s.claimed)}</td><td class="r">${inr(s.limit)}</td><td class="r">${inr(s.headroom)}</td>
    <td class="r">${s.claimed>=s.limit&&s.limit?'<span class="pill over">Maximised</span>':s.claimed>0?'<span class="pill sub">Tracked</span>':'<span class="pill g">Add entry</span>'}</td></tr>`).join("");
  const tips=d.sections.filter(s=>s.headroom>0&&s.limit).slice(0,2).map((s,i)=>`<div class="listrow" style="padding:10px 0;border:0">
    <span class="avatarsm" style="background:var(--mintbg);color:var(--teal)">${i+1}</span>
    <span class="fs13">You have <b>${inr(s.headroom)}</b> headroom in ${esc(s.section)}. Consider topping up before March 31st.</span></div>`).join("");
  $("view").innerHTML=`
    <div class="rowb mb"><div><div class="eyebrow">FINANCIAL YEAR 2025-26</div><h2 class="page">Tax Saver Planner</h2>
      <div class="sub">Track Section 80C / 80D / 80CCD investments in real time. Informational — not tax advice.</div></div>
      <div style="display:flex;gap:10px"><button class="btn ghost" onclick="toast('Report export is a demo stub')">Download Report</button>
        <button class="btn" onclick="taxModal()">Add Investment</button></div></div>
    <div class="grid g2 mb">
      <div class="card"><div class="eyebrow">PROJECTED TAX SAVINGS</div><div style="font-size:34px;font-weight:800;color:var(--teal);margin-top:4px">${inr(d.tax_saved)}</div>
        <div class="muted fs13">on ${inr(d.total_claimable)} of eligible deductions</div></div>
      <div class="gradcard"><div class="lbl" style="opacity:.8">CURRENT REGIME</div>
        <div style="font-size:26px;font-weight:800;text-transform:capitalize;margin:4px 0">${esc(d.regime)} Regime</div>
        <div class="seg" style="background:rgba(255,255,255,.15)"><button class="${d.regime==='old'?'on':''}" onclick="setRegime('old')">Old</button>
          <button class="${d.regime==='new'?'on':''}" onclick="setRegime('new')">New</button></div></div>
    </div>
    <div class="card"><div class="cardtitle mb">Deductions Breakdown</div>
      <table><thead><tr><th>Section</th><th>Investment Type</th><th class="r">Claimed</th><th class="r">Limit</th><th class="r">Headroom</th><th class="r">Status</th></tr></thead>
      <tbody>${rows}</tbody></table>
      <div class="rowb mt"><span class="eyebrow">OVERALL UTILISATION</span><b class="fs13" style="color:var(--teal)">${util}% of max deductions</b></div>
      <div class="bar" style="margin-top:6px"><div style="width:${Math.min(100,util)}%"></div></div></div>
    ${tips?`<div class="card mt"><h3>💡 Optimization Tips</h3>${tips}</div>`:''}
    ${fab("taxModal()")}`;
};
function taxModal(){modal(`<div class="cardtitle mb">Add investment</div>
  <label class="fld">SECTION</label><select class="box" id="tx_sec"><option>80C</option><option>80D</option><option>80CCD</option></select>
  <label class="fld">DESCRIPTION</label><input class="box" id="tx_lbl" placeholder="ELSS Mutual Fund">
  <label class="fld">AMOUNT</label><input class="box" id="tx_amt" type="number" placeholder="50000">
  <div class="rowb mt"><button class="link" onclick="closeModal()">Cancel</button><button class="btn sm" onclick="taxGo()">Add</button></div>`);}
async function taxGo(){const s=$("tx_sec").value,l=$("tx_lbl").value.trim(),a=parseFloat($("tx_amt").value);
  if(!l||!a){toast("Fill all fields");return;}await api("/tax/entry","POST",{section:s,label:l,amount:a});closeModal();toast("Added");go("tax");}
async function setRegime(r){await api("/tax/regime","POST",{regime:r});ME.tax_regime=r;go("tax");}

/* ---------- SPLIT ---------- */
let CURGROUP=null;
VIEWS.split=async function(){
  const {groups}=await api("/groups");
  if(groups.length && !CURGROUP) CURGROUP=groups[0].id;
  let rec=[];try{rec=(await api("/reconcile")).suggestions;}catch(e){}
  const gl=groups.map(g=>`<div class="grouprow ${g.id===CURGROUP?'on':''}" onclick="CURGROUP=${g.id};go('split')">
    <span class="micon" style="width:38px;height:38px;font-size:16px">${g.kind==='trip'?'✈️':g.kind==='flat'?'🏠':g.kind==='family'?'👪':'🎉'}</span>
    <div><b>${esc(g.name)}</b><div class="muted" style="font-size:11px;text-transform:uppercase">${esc(g.kind)}</div></div></div>`).join("")||'<p class="muted fs13">No groups yet.</p>';
  let center=`<div class="card" style="text-align:center;padding:50px"><div style="font-size:40px">👥</div>
    <div class="cardtitle mt">Create your first group</div><p class="muted">Split trips, rent and dinners with friends.</p>
    <button class="btn mt" onclick="groupModal()">+ New Group</button></div>`;
  let right="";
  if(CURGROUP){
    const g=await api("/groups/"+CURGROUP);
    const byId=Object.fromEntries(g.members.map(m=>[m.user_id,m.display_name]));
    const total=g.expenses.reduce((s,e)=>s+e.amount,0);
    const myShare=g.balances.find(b=>b.user_id===ME.id);
    const paidByMe=g.expenses.filter(e=>e.paid_by===ME.id).reduce((s,e)=>s+e.amount,0);
    const yourShare=paidByMe-(myShare?myShare.net:0);   // what you actually consumed
    const myOwed=g.simplified.filter(t=>t.from===ME.id).reduce((s,t)=>s+t.amount,0);
    const myGet=g.simplified.filter(t=>t.to===ME.id).reduce((s,t)=>s+t.amount,0);
    const gname=(groups.find(x=>x.id===CURGROUP)||{}).name||"Group";
    const avatars=g.members.slice(0,4).map(m=>`<span class="avatarsm">${initials(m.display_name)}</span>`).join("");
    const settle=g.simplified.map(t=>{const mine=t.from===ME.id||t.to===ME.id;
      const iOwe=t.from===ME.id;
      return `<div class="settlecard"><span class="avatarsm" style="width:38px;height:38px">${initials(iOwe?t.to_name:t.from_name)}</span>
        <div><b>${iOwe?'You owe '+esc(t.to_name):esc(t.from_name)+(t.to===ME.id?' owes you':' → '+esc(t.to_name))}</b>
          <div class="muted fs13">simplified settle-up</div></div>
        <b style="margin-left:auto;color:${iOwe?'var(--red)':'var(--green)'}">${inr2(t.amount)}</b>
        ${iOwe?`<button class="btn mint sm" onclick="upiLink(${CURGROUP},${t.to},${t.amount})">▦ UPI</button>
          <button class="btn ghost sm" onclick="settleUp(${CURGROUP},${t.from},${t.to},${t.amount})">Log cash</button>`
        :`<button class="btn ghost sm" onclick="toast('Reminder sent to '+'${esc(t.from_name)}')">Remind</button>`}</div>`;}).join("")||'<p class="muted" style="padding:16px">All settled up 🎉</p>';
    center=`<div class="card mb"><div class="rowb"><div><div style="font-size:24px;font-weight:800">${esc(gname)}</div>
        <div class="stack mt" style="margin-top:6px">${avatars}${g.members.length>4?`<span class="avatarsm" style="background:var(--muted)">+${g.members.length-4}</span>`:''}</div></div>
        <button class="btn" onclick="expenseModal()">+ Add Expense</button></div>
      <div class="grid g2 mt"><div class="chip"><div class="k">Total group spending</div><div class="v">${inr2(total)}</div></div>
        <div class="chip"><div class="k">Your share</div><div class="v">${inr2(yourShare)}</div></div></div></div>
      <div class="card"><div class="rowb mb"><div class="cardtitle">Settle Up</div></div>${settle}</div>
      <div class="card mt"><h3>Members</h3>${g.members.map(m=>`<div class="listrow" style="padding:8px 0"><span class="avatarsm">${initials(m.display_name)}</span><b class="fs13">${esc(m.display_name)}</b><span class="muted fs13" style="margin-left:auto">${esc(m.email||'')}</span></div>`).join("")}
        <div class="rowb mt"><input class="box" id="m_email" placeholder="friend@email.com" style="max-width:220px"><button class="btn sm" onclick="addMember()">Invite</button></div>
        <p class="muted fs13 mt">No account? We create a placeholder so you can split now.</p></div>
      <div class="card mt"><h3>Expenses</h3>${g.expenses.map(e=>`<div class="listrow" style="padding:10px 0"><span class="micon" style="width:36px;height:36px;font-size:15px">🧾</span>
        <div><b class="fs13">${esc(e.description)}</b> ${e.recurring?'<span class="pill sub">↻ monthly</span>':''}<div class="muted" style="font-size:11px">${esc(e.payer)} paid · ${esc(e.method)}</div></div>
        <b class="fs13" style="margin-left:auto">${inr2(e.amount)}</b></div>`).join("")||'<span class="muted fs13">No expenses yet.</span>'}</div>`;
    right=`<div class="card mb"><h3>Group Summary</h3><div class="lbl">NET BALANCE</div>
      <div style="font-size:30px;font-weight:800;color:${(myGet-myOwed)>=0?'var(--teal)':'var(--red)'}">${inr2(Math.abs(myGet-myOwed))}</div>
      <p class="muted fs13">Overall, you ${myGet>=myOwed?'are owed':'owe'} across ${g.members.length-1} ${g.members.length-1===1?'person':'people'}.</p>
      <div style="border-top:1px solid var(--line);margin:12px 0;padding-top:12px">
        <div class="rowb fs13"><span>● Gets back</span><b style="color:var(--green)">${inr(myGet)}</b></div>
        <div class="rowb fs13 mt" style="margin-top:6px"><span style="color:var(--red)">● Owes</span><b style="color:var(--red)">${inr(myOwed)}</b></div></div>
      <button class="btn ghost" style="width:100%" onclick="toast('Sheet export is a demo stub')">Export Sheet</button></div>
      <div class="card" style="background:var(--peach)"><b>Automate Splits?</b><p class="fs13 muted mt">Set up recurring rent/bills with automatic UPI reminders.</p>
        <button class="link" onclick="toast('Pro plan coming soon')">Upgrade to Pro</button></div>`;
  }
  $("view").innerHTML=`<h2 class="page">Split Expenses</h2><div class="sub">Splitwise-style groups with debt simplification &amp; UPI settle-up.</div>
    ${rec.map(s=>`<div class="alert peach"><span style="font-size:18px">💡</span><div>${esc(s.message)}</div>
      <button class="btn dark sm" style="margin-left:auto" onclick="autoSettle(${s.group_id},${s.from_user},${s.amount})">Mark settled</button></div>`).join("")}
    <div style="display:grid;grid-template-columns:260px 1fr 300px;gap:18px;align-items:start">
      <div class="card"><div class="rowb mb"><h3 style="margin:0">Groups</h3><button class="iconbtn" onclick="groupModal()">＋</button></div>
        <input class="box mb" placeholder="🔍 Search groups...">${gl}</div>
      <div>${center}</div>
      <div>${right}</div>
    </div>`;
};
function groupModal(){modal(`<div class="cardtitle mb">New group</div>
  <label class="fld">NAME</label><input class="box" id="gp_name" placeholder="Goa Trip 2026">
  <label class="fld">TYPE</label><select class="box" id="gp_kind"><option value="trip">Trip</option><option value="flat">Flatmates</option><option value="family">Family</option><option value="general">General</option></select>
  <div class="rowb mt"><button class="link" onclick="closeModal()">Cancel</button><button class="btn sm" onclick="groupGo()">Create</button></div>`);}
async function groupGo(){const n=$("gp_name").value.trim();if(!n){toast("Name it");return;}
  const d=await api("/groups","POST",{name:n,kind:$("gp_kind").value});CURGROUP=d.id;closeModal();go("split");}
async function addMember(){const e=$("m_email").value.trim();if(!e)return;await api(`/groups/${CURGROUP}/members`,"POST",{email:e});toast("Added");go("split");}
async function autoSettle(gid,from,amt){await api(`/groups/${gid}/settle`,"POST",{from_user:from,to_user:ME.id,amount:amt});toast("Settled");go("split");}
async function settleUp(gid,from,to,amt){await api(`/groups/${gid}/settle`,"POST",{from_user:from,to_user:to,amount:amt});toast("Recorded");go("split");}
async function upiLink(gid,to,amt){const d=await api(`/groups/${gid}/upi?to_user=${to}&amount=${amt}`);
  if(!d.upi_link){toast("That member has no UPI ID set");return;}
  modal(`<div class="cardtitle mb">UPI settle-up</div><p class="fs13">Open in a UPI app to pay ${inr2(amt)}:</p>
    <p style="word-break:break-all;font-size:12px;background:var(--mintbg);padding:10px;border-radius:8px">${esc(d.upi_link)}</p>
    <div class="rowb mt"><button class="link" onclick="closeModal()">Close</button><a class="btn sm" href="${esc(d.upi_link)}">Open UPI app</a></div>`);}
async function expenseModal(){
  const g=await api("/groups/"+CURGROUP);window._MEM=g.members;
  modal(`<div class="cardtitle mb">Add expense</div>
    <label class="fld">DESCRIPTION</label><input class="box" id="e_desc" placeholder="Dinner at Thalassa">
    <label class="fld">AMOUNT ₹</label><input class="box" id="e_amt" type="number">
    <label class="fld">PAID BY</label><select class="box" id="e_by">${g.members.map(m=>`<option value="${m.user_id}" ${m.user_id===ME.id?'selected':''}>${esc(m.display_name)}</option>`).join("")}</select>
    <label class="fld">SPLIT METHOD</label><select class="box" id="e_method" onchange="splitInputs()"><option value="equal">Equally</option><option value="exact">Exact amounts</option><option value="percent">By percent</option><option value="shares">By shares</option></select>
    <div id="e_shares"></div>
    <label style="display:flex;gap:8px;font-size:13px;margin-top:12px;align-items:center"><input type="checkbox" id="e_rec" style="width:auto"> Repeats monthly (rent/utilities)</label>
    <div class="rowb mt"><button class="link" onclick="closeModal()">Cancel</button><button class="btn sm" onclick="expenseGo()">Add</button></div>`);}
function splitInputs(){const m=$("e_method").value,mem=window._MEM,box=$("e_shares");
  if(m==="equal"){box.innerHTML=`<p class="muted fs13 mt">Split equally among ${mem.length} members.</p>`;return;}
  const lbl=m==="percent"?"%":m==="shares"?"shares":"₹";
  box.innerHTML=`<label class="fld">PER MEMBER (${lbl})</label>`+mem.map(mm=>`<div class="rowb" style="margin:5px 0"><span style="width:140px">${esc(mm.display_name)}</span><input class="box e_share" data-uid="${mm.user_id}" type="number" placeholder="${lbl}" style="max-width:120px"></div>`).join("");}
async function expenseGo(){const desc=$("e_desc").value.trim(),amt=parseFloat($("e_amt").value);
  if(!desc||!amt){toast("Description and amount needed");return;}
  const method=$("e_method").value,values={};
  if(method!=="equal")document.querySelectorAll(".e_share").forEach(i=>{if(i.value)values[i.dataset.uid]=parseFloat(i.value);});
  await api(`/groups/${CURGROUP}/expenses`,"POST",{description:desc,amount:amt,paid_by:parseInt($("e_by").value),method,values,recurring:$("e_rec").checked?1:0});
  closeModal();toast("Added");go("split");}

/* ---------- SETTINGS ---------- */
let setTab="profile";
VIEWS.settings=async function(){renderSettings();};
function renderSettings(){
  const u=ME, prefs=u.prefs||{}, notif=u.notif||{};
  const items=[["profile","Profile","👤"],["preferences","Preferences","🎚️"],["notifications","Notifications","🔔"],
    ["categories","Categories","🏷️"],["security","Security","🛡️"],["data","Data","🗄️"],["plan","Plan","🏅"]];
  const nav=items.map(([k,l,i])=>`<button class="${setTab===k?'on':''}" onclick="setTab='${k}';renderSettings()">${i} ${l}</button>`).join("");
  let panel="";
  if(setTab==="profile") panel=`<h3>Profile</h3>
    <div style="display:flex;gap:16px;align-items:center;margin-bottom:10px"><div class="avatar" style="width:64px;height:64px;font-size:22px">${u.photo?`<img src="${esc(u.photo)}">`:initials(u.name)}</div>
      <div><label class="btn sm mint" for="pf_photo">Change photo</label><input id="pf_photo" type="file" accept="image/*" style="display:none" onchange="uploadPhoto(this)"></div></div>
    <label class="fld">NAME</label><input class="box" id="pf_name" value="${esc(u.name)}">
    <label class="fld">EMAIL</label><input class="box" value="${esc(u.email)}" disabled>
    <label class="fld">PHONE</label><input class="box" id="pf_phone" value="${esc(u.phone||'')}" placeholder="+91 …">
    <label class="fld">UPI ID</label><input class="box" id="pf_upi" value="${esc(u.upi_id||'')}" placeholder="name@okhdfcbank">
    <label class="fld">MONTHLY INCOME (improves forecast)</label><input class="box" id="pf_income" type="number" value="${u.monthly_income||''}">
    <div class="mt"><button class="btn sm" onclick="saveProfile()">Save Profile</button></div>`;
  else if(setTab==="preferences") panel=`<h3>Preferences</h3>
    <div class="rowb" style="padding:14px 0;border-bottom:1px solid var(--line)"><div><b>Interface Appearance</b><div class="muted fs13">How ExpenseSort looks.</div></div>
      <div class="seg"><button class="${(prefs.theme||'light')==='light'?'on':''}" onclick="setPref('theme','light')">☀ Light</button>
        <button class="${prefs.theme==='dark'?'on':''}" onclick="setPref('theme','dark')">🌙 Dark</button>
        <button class="${prefs.theme==='system'?'on':''}" onclick="setPref('theme','system')">💻 System</button></div></div>
    <div class="rowb" style="padding:14px 0;border-bottom:1px solid var(--line)"><div><b>Preferred Language</b><div class="muted fs13">Dashboard language.</div></div>
      <select class="box" style="width:180px" onchange="setPref('language',this.value)"><option ${prefs.language!=='hi'?'selected':''}>English (India)</option><option value="hi" ${prefs.language==='hi'?'selected':''}>हिन्दी</option></select></div>
    <div class="rowb" style="padding:14px 0"><div><b>Currency Display</b><div class="muted fs13">Transaction value format.</div></div><b style="color:var(--teal)">₹ INR</b></div>`;
  else if(setTab==="notifications"){const sw=(k,def)=>`<div class="sw ${notif[k]!==false&&(notif[k]||def)?'on':''}" onclick="toggleNotif('${k}')"></div>`;
    panel=`<h3>Notifications</h3>
    ${[["budget","Budget Overrun Alerts","When a category exceeds 80% of its limit.","🧾",true],
       ["reminders","Transaction Reminders","Daily nudge to log cash expenses.","⏰",true],
       ["weekly","Weekly Summaries","Email report of your weekly spending.","📈",false]].map(([k,t,d,ic,def])=>
      `<div class="rowb" style="padding:14px 0;border-bottom:1px solid var(--line)"><div style="display:flex;gap:12px;align-items:center">
        <span class="micon" style="width:40px;height:40px;font-size:17px">${ic}</span><div><b>${t}</b><div class="muted fs13">${d}</div></div></div>
        <div class="sw ${(notif[k]===undefined?def:notif[k])?'on':''}" onclick="toggleNotif('${k}',${def})"></div></div>`).join("")}
    <div class="alert mt" style="border-color:var(--teal);background:var(--mintbg)"><span>ⓘ</span><div class="fs13">Email notifications are sent to <b>${esc(u.email)}</b></div></div>`;}
  else if(setTab==="categories") panel=`<h3>Categories</h3><p class="muted fs13 mb">Manage your spending categories.</p>
    <div id="catlist"></div>
    <div class="rowb mt"><input class="box" id="c_name" placeholder="Custom category" style="max-width:180px">
      <input class="box" id="c_icon" placeholder="📦" style="max-width:70px" value="📦">
      <input class="box" id="c_color" type="color" value="#12b3a6" style="max-width:60px;padding:2px">
      <button class="btn sm" onclick="addCat()">Add</button></div>`;
  else if(setTab==="security") panel=`<h3>Security</h3>
    <label class="fld">CURRENT PASSWORD</label><input class="box" id="sec_cur" type="password">
    <label class="fld">NEW PASSWORD</label><input class="box" id="sec_new" type="password">
    <div class="mt"><button class="btn sm" onclick="changePw()">Change Password</button></div>
    <div class="alert mt" style="border-color:var(--teal);background:var(--mintbg)"><span>🔒</span><div class="fs13">Two-factor authentication & session management are on the roadmap.</div></div>`;
  else if(setTab==="data") panel=`<h3>Data &amp; Privacy</h3>
    <p class="fs13 mb">Your data stays private — stored locally per account, never sold.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn sm mint" onclick="exportCSV()">Export my data (CSV)</button>
      <button class="btn sm ghost" onclick="wipeData()">Delete all transactions</button>
      <button class="btn sm" style="background:var(--red);box-shadow:none" onclick="deleteAccount()">Delete account</button></div>`;
  else panel=`<h3>Plan</h3><div class="gradcard"><div class="cardtitle" style="color:#fff">Free plan</div>
    <p style="opacity:.9;font-size:13.5px;margin-top:6px">All core features. Upgrade for automated recurring splits, UPI reminders & priority support.</p>
    <button class="btn mint mt" onclick="toast('Pro plan coming soon')">Upgrade to Premium</button></div>`;
  $("view").innerHTML=`<div class="rowb mb"><h2 class="page">Settings</h2><button class="link" onclick="logout()">Log out</button></div>
    <div style="display:grid;grid-template-columns:240px 1fr;gap:18px;align-items:start">
      <div class="card subnav">${nav}
        <div class="mt" style="margin-top:18px"><div class="eyebrow">STORAGE</div><div class="bar mt" style="margin-top:6px"><div style="width:12%"></div></div><div class="muted fs13 mt">Local database</div></div></div>
      <div class="card">${panel}
        <div class="rowb mt" style="margin-top:20px;border-top:1px solid var(--line);padding-top:16px">
          <button class="link" onclick="go('dashboard')">← Back to app</button></div></div>
    </div>`;
  if(setTab==="categories") loadCatList();
}
async function saveProfile(){await api("/me","POST",{name:$("pf_name").value.trim(),phone:$("pf_phone").value.trim(),
  upi_id:$("pf_upi").value.trim(),monthly_income:parseFloat($("pf_income").value)||0});
  ME=await api("/me");renderNav();toast("Saved");}
function uploadPhoto(inp){const f=inp.files[0];if(!f)return;const rd=new FileReader();
  rd.onload=async()=>{await api("/me","POST",{photo:rd.result});ME=await api("/me");renderNav();renderSettings();toast("Photo updated");};rd.readAsDataURL(f);}
async function setPref(k,v){const p={...(ME.prefs||{}),[k]:v};await api("/me","POST",{prefs:p});ME.prefs=p;applyTheme();renderSettings();}
async function toggleNotif(k,def){const cur=ME.notif||{};const now=cur[k]===undefined?def:cur[k];const n={...cur,[k]:!now};
  await api("/me","POST",{notif:n});ME.notif=n;renderSettings();}
async function loadCatList(){const c=await api("/categories");
  $("catlist").innerHTML=c.categories.map(x=>`<div class="listrow" style="padding:8px 0"><span class="tdot" style="background:${x.color};width:12px;height:12px"></span>
    <span>${x.icon} ${esc(x.name)}</span>${x.custom?`<button class="link" style="margin-left:auto" onclick="delCat('${esc(x.name)}')">remove</button>`:'<span class="pill g" style="margin-left:auto">default</span>'}</div>`).join("");}
async function addCat(){const n=$("c_name").value.trim();if(!n)return;
  await api("/categories","POST",{name:n,icon:$("c_icon").value||"📦",color:$("c_color").value});
  const c=await api("/categories");CATS=c.categories.map(x=>x.name);CATMETA={};c.categories.forEach(x=>CATMETA[x.name]={color:x.color,icon:x.icon});
  $("c_name").value="";loadCatList();toast("Category added");}
async function delCat(n){await api("/categories/"+encodeURIComponent(n),"DELETE");loadCatList();}
async function changePw(){const cur=$("sec_cur").value,nw=$("sec_new").value;if(!cur||!nw){toast("Fill both fields");return;}
  try{await api("/password","POST",{current:cur,new:nw});toast("Password changed");$("sec_cur").value="";$("sec_new").value="";}catch(e){toast(e.message);}}
async function exportCSV(){const d=await api("/transactions?size=100000");
  const lines=[["date","description","category","direction","amount"]].concat(d.rows.map(r=>[r.txn_date||"",`"${(r.description||'').replace(/"/g,'""')}"`,r.category,r.direction||"",r.amount]));
  const csv=lines.map(l=>l.join(",")).join("\n");const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="expensesort_data.csv";a.click();toast("Exported");}
async function wipeData(){if(!confirm("Delete all your transactions? Groups are kept."))return;await api("/data","DELETE");toast("Cleared");go("dashboard");}
async function deleteAccount(){if(!confirm("Permanently delete your account and ALL data? This cannot be undone."))return;
  await api("/account","DELETE");logout();}

/* ---------- start ---------- */
if(TOKEN){boot();}else{renderAuth();}
