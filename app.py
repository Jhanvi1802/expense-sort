"""ExpenseSort API — cloud, multi-user, India-first money app.

Combines: statement ingest + ML-ish categorization, recurring/subscription
detection, budgets, multi-month trends & anomalies, cash-flow forecast, India
tax tagging, and a Splitwise-style group splitting engine (debt simplification,
UPI settle links, auto-settle reconciliation).

Run:  python app.py   ->  http://localhost:8001
"""
import os
import sys

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json

import budgets as budgets_svc
import categories as cat_svc
import forecast as forecast_svc
import goals as goals_svc
import health as health_svc
import insights as insights_svc
import recurring as recurring_svc
import splitting as split_svc
import tax as tax_svc
import trends as trends_svc
from db import init_db, query, execute
from extract import extract_text
from ingest import ingest_text, user_transactions
from security import (hash_password, verify_password, create_token, current_user)

app = FastAPI(title="ExpenseSort", version="4.0")
init_db()

WEB = os.path.join(os.path.dirname(__file__), "web")


# ---------------- schemas ----------------
class Register(BaseModel):
    email: str
    name: str
    password: str
    upi_id: str = ""


class Login(BaseModel):
    email: str
    password: str


class TextReq(BaseModel):
    text: str = ""


class BudgetReq(BaseModel):
    category: str
    limit_amount: float


class GroupReq(BaseModel):
    name: str
    kind: str = "general"


class MemberReq(BaseModel):
    email: str
    display_name: str = ""


class ExpenseReq(BaseModel):
    description: str
    amount: float
    paid_by: int
    method: str = "equal"
    values: dict = {}
    participants: list = []
    recurring: int = 0


class SettleReq(BaseModel):
    from_user: int
    to_user: int
    amount: float
    note: str = ""


# ---------------- auth ----------------
@app.post("/api/register")
def register(r: Register):
    if query("SELECT 1 FROM users WHERE email=?", (r.email.lower(),), one=True):
        # allow claiming a placeholder account (created via group invite)
        existing = query("SELECT id, pw_hash FROM users WHERE email=?", (r.email.lower(),), one=True)
        if existing["pw_hash"].startswith("pending$"):
            execute("UPDATE users SET name=?, pw_hash=?, upi_id=? WHERE id=?",
                    (r.name, hash_password(r.password), r.upi_id, existing["id"]))
            return {"token": create_token(existing["id"]), "name": r.name}
        raise HTTPException(400, "Email already registered")
    uid = execute("""INSERT INTO users (email, name, upi_id, pw_hash, created_at)
                     VALUES (?,?,?,?,datetime('now'))""",
                  (r.email.lower(), r.name, r.upi_id, hash_password(r.password)))
    return {"token": create_token(uid), "name": r.name}


@app.post("/api/login")
def login(r: Login):
    u = query("SELECT id, name, pw_hash FROM users WHERE email=?", (r.email.lower(),), one=True)
    if not u or not verify_password(r.password, u["pw_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_token(u["id"]), "name": u["name"]}


def _hydrate(user):
    """Parse JSON prefs/notif so the client gets objects, not strings."""
    u = dict(user)
    for k in ("prefs", "notif"):
        try:
            u[k] = json.loads(u.get(k) or "{}")
        except Exception:
            u[k] = {}
    return u


@app.get("/api/me")
def me(user=Depends(current_user)):
    return _hydrate(user)


class Profile(BaseModel):
    name: str = None
    upi_id: str = None
    phone: str = None
    photo: str = None
    monthly_income: float = None
    prefs: dict = None
    notif: dict = None
    tax_regime: str = None


@app.post("/api/me")
def update_me(p: Profile, user=Depends(current_user)):
    fields, vals = [], []
    mapping = {"name": p.name, "upi_id": p.upi_id, "phone": p.phone, "photo": p.photo,
               "monthly_income": p.monthly_income, "tax_regime": p.tax_regime,
               "prefs": json.dumps(p.prefs) if p.prefs is not None else None,
               "notif": json.dumps(p.notif) if p.notif is not None else None}
    for col, val in mapping.items():
        if val is not None:
            fields.append(f"{col}=?")
            vals.append(val)
    if fields:
        vals.append(user["id"])
        execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", vals)
    return _hydrate(query("""SELECT id,email,name,upi_id,phone,photo,monthly_income,
                             prefs,notif,tax_regime,onboarded FROM users WHERE id=?""",
                          (user["id"],), one=True))


@app.post("/api/onboard")
def onboard(user=Depends(current_user)):
    execute("UPDATE users SET onboarded=1 WHERE id=?", (user["id"],))
    return {"ok": True}


class PwReq(BaseModel):
    current: str
    new: str


@app.post("/api/password")
def change_password(r: PwReq, user=Depends(current_user)):
    row = query("SELECT pw_hash FROM users WHERE id=?", (user["id"],), one=True)
    if not verify_password(r.current, row["pw_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    execute("UPDATE users SET pw_hash=? WHERE id=?", (hash_password(r.new), user["id"]))
    return {"ok": True}


@app.delete("/api/account")
def delete_account(user=Depends(current_user)):
    execute("DELETE FROM users WHERE id=?", (user["id"],))   # cascades to all user data
    return {"ok": True}


# ---------------- ingest & transactions ----------------
@app.post("/api/ingest")
def ingest(r: TextReq, user=Depends(current_user)):
    res = ingest_text(user["id"], r.text, source="paste")
    recurring_svc.detect(user["id"])       # refresh recurring flags
    return res


@app.post("/api/extract")
async def extract(file: UploadFile = File(...), user=Depends(current_user)):
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 8 MB)")
    try:
        text = extract_text(file.filename, data)
    except Exception as e:
        raise HTTPException(400, f"Could not read {file.filename}: {e}")
    res = ingest_text(user["id"], text, source=file.filename)
    recurring_svc.detect(user["id"])
    return res


@app.get("/api/transactions")
def transactions(month: str = None, q: str = None, page: int = 1, size: int = 20,
                 user=Depends(current_user)):
    where = "WHERE user_id=?"
    params = [user["id"]]
    if month:
        where += " AND month=?"; params.append(month)
    if q:
        where += " AND (description LIKE ? OR category LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    total = query(f"SELECT COUNT(*) c FROM transactions {where}", params, one=True)["c"]
    page = max(1, page)
    rows = query(f"SELECT * FROM transactions {where} ORDER BY txn_date DESC, id DESC LIMIT ? OFFSET ?",
                 params + [size, (page - 1) * size])
    return {"rows": rows, "total": total, "page": page, "size": size,
            "pages": max(1, (total + size - 1) // size)}


class RecatReq(BaseModel):
    id: int
    category: str


@app.post("/api/transactions/recategorize")
def recategorize(r: RecatReq, user=Depends(current_user)):
    execute("UPDATE transactions SET category=? WHERE id=? AND user_id=?",
            (r.category, r.id, user["id"]))
    return {"ok": True}


@app.delete("/api/data")
def wipe(user=Depends(current_user)):
    execute("DELETE FROM transactions WHERE user_id=?", (user["id"],))
    execute("DELETE FROM statements WHERE user_id=?", (user["id"],))
    return {"ok": True}


# ---------------- dashboard / analytics ----------------
@app.get("/api/dashboard")
def dashboard(month: str = None, user=Depends(current_user)):
    return insights_svc.dashboard(user["id"], month)


@app.get("/api/recurring")
def recurring(user=Depends(current_user)):
    return recurring_svc.detect(user["id"])


@app.get("/api/budgets")
def get_budgets(month: str = None, user=Depends(current_user)):
    return budgets_svc.status(user["id"], month)


@app.post("/api/budgets")
def set_budget(b: BudgetReq, user=Depends(current_user)):
    budgets_svc.set_budget(user["id"], b.category, b.limit_amount)
    return {"ok": True}


@app.delete("/api/budgets/{category}")
def del_budget(category: str, user=Depends(current_user)):
    budgets_svc.delete_budget(user["id"], category)
    return {"ok": True}


@app.get("/api/trends")
def get_trends(user=Depends(current_user)):
    return {"monthly": trends_svc.monthly(user["id"]),
            "by_category": trends_svc.category_trend(user["id"]),
            "anomalies": trends_svc.anomalies(user["id"])}


@app.get("/api/forecast")
def get_forecast(user=Depends(current_user)):
    return forecast_svc.forecast(user["id"], user.get("monthly_income") or 0)


@app.get("/api/health")
def get_health(user=Depends(current_user)):
    return health_svc.score(user["id"])


# ---------------- goals ----------------
class GoalReq(BaseModel):
    name: str
    target: float
    saved: float = 0


class ContribReq(BaseModel):
    amount: float


@app.get("/api/goals")
def get_goals(user=Depends(current_user)):
    return {"goals": goals_svc.list_goals(user["id"])}


@app.post("/api/goals")
def new_goal(g: GoalReq, user=Depends(current_user)):
    return {"id": goals_svc.create(user["id"], g.name, g.target, g.saved)}


@app.post("/api/goals/{gid}/contribute")
def contribute_goal(gid: int, c: ContribReq, user=Depends(current_user)):
    goals_svc.contribute(user["id"], gid, c.amount)
    return {"ok": True}


@app.delete("/api/goals/{gid}")
def del_goal(gid: int, user=Depends(current_user)):
    goals_svc.delete(user["id"], gid)
    return {"ok": True}


# ---------------- categories ----------------
class CatReq(BaseModel):
    name: str
    color: str = "#94a3b8"
    icon: str = "📦"


@app.get("/api/categories")
def get_categories(user=Depends(current_user)):
    return {"categories": cat_svc.list_categories(user["id"])}


@app.post("/api/categories")
def add_category(c: CatReq, user=Depends(current_user)):
    cat_svc.add(user["id"], c.name, c.color, c.icon)
    return {"ok": True}


@app.delete("/api/categories/{name}")
def del_category(name: str, user=Depends(current_user)):
    cat_svc.delete(user["id"], name)
    return {"ok": True}


# ---------------- tax ----------------
class TaxEntryReq(BaseModel):
    section: str
    label: str
    amount: float


class RegimeReq(BaseModel):
    regime: str


@app.get("/api/tax")
def get_tax(user=Depends(current_user)):
    rows = query("SELECT amount, tax_section FROM transactions WHERE user_id=? AND tax_section IS NOT NULL",
                 (user["id"],))
    manual = query("SELECT id, section, label, amount FROM tax_entries WHERE user_id=?", (user["id"],))
    return tax_svc.summarize(rows, manual, user.get("tax_regime") or "new")


@app.post("/api/tax/entry")
def add_tax_entry(e: TaxEntryReq, user=Depends(current_user)):
    return {"id": execute("INSERT INTO tax_entries (user_id, section, label, amount) VALUES (?,?,?,?)",
                          (user["id"], e.section, e.label, e.amount))}


@app.delete("/api/tax/entry/{eid}")
def del_tax_entry(eid: int, user=Depends(current_user)):
    execute("DELETE FROM tax_entries WHERE id=? AND user_id=?", (eid, user["id"]))
    return {"ok": True}


@app.post("/api/tax/regime")
def set_regime(r: RegimeReq, user=Depends(current_user)):
    execute("UPDATE users SET tax_regime=? WHERE id=?", (r.regime, user["id"]))
    return {"ok": True}


# ---------------- splitting ----------------
def _require_member(gid, user):
    if not split_svc.is_member(gid, user["id"]):
        raise HTTPException(403, "Not a member of this group")


@app.get("/api/groups")
def groups(user=Depends(current_user)):
    return {"groups": split_svc.user_groups(user["id"])}


@app.post("/api/groups")
def new_group(g: GroupReq, user=Depends(current_user)):
    gid = split_svc.create_group(user["id"], g.name, g.kind)
    return {"id": gid}


@app.get("/api/groups/{gid}")
def group_detail(gid: int, user=Depends(current_user)):
    _require_member(gid, user)
    return {
        "members": split_svc.members(gid),
        "expenses": split_svc.expenses(gid),
        "balances": split_svc.balances(gid),
        "simplified": split_svc.simplify(gid),
    }


@app.post("/api/groups/{gid}/members")
def add_member(gid: int, m: MemberReq, user=Depends(current_user)):
    _require_member(gid, user)
    return split_svc.add_member(gid, m.email, m.display_name or None)


@app.post("/api/groups/{gid}/expenses")
def add_expense(gid: int, e: ExpenseReq, user=Depends(current_user)):
    _require_member(gid, user)
    return split_svc.add_expense(gid, e.description, e.amount, e.paid_by, e.method,
                                 e.values, e.participants or None, e.recurring)


@app.post("/api/groups/{gid}/settle")
def settle(gid: int, s: SettleReq, user=Depends(current_user)):
    _require_member(gid, user)
    split_svc.settle(gid, s.from_user, s.to_user, s.amount, s.note or None)
    link = split_svc.upi_link(s.to_user, s.amount)
    return {"ok": True, "upi_link": link}


@app.get("/api/groups/{gid}/upi")
def upi(gid: int, to_user: int, amount: float, user=Depends(current_user)):
    _require_member(gid, user)
    return {"upi_link": split_svc.upi_link(to_user, amount)}


@app.get("/api/reconcile")
def reconcile(user=Depends(current_user)):
    return {"suggestions": split_svc.reconcile_suggestions(user["id"])}


# ---------------- frontend ----------------
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


@app.get("/app.js")
def appjs():
    return FileResponse(os.path.join(WEB, "app.js"), media_type="application/javascript")


@app.get("/favicon.ico")
def favicon():
    # inline ₹ emoji favicon so the browser stops 404-ing
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           '<rect width="100" height="100" rx="22" fill="#0f766e"/>'
           '<text x="50" y="72" font-size="64" text-anchor="middle" fill="#fff" '
           'font-family="Arial">₹</text></svg>')
    from fastapi.responses import Response
    return Response(svg, media_type="image/svg+xml")


if __name__ == "__main__":
    import uvicorn
    print("ExpenseSort running at http://localhost:8001  (Ctrl+C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
