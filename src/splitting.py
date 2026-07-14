"""Splitwise-style engine: groups, flexible splitting, debt simplification,
UPI settle links, and auto-settle reconciliation from the user's statement.

Members are users. Inviting an email that has no account yet creates a
placeholder user so you can split immediately (our 'split with non-users' edge
over Splitwise) — they can claim the account later by setting a password.
"""
import os
import urllib.parse

from db import query, execute
from security import hash_password


# ---------- groups & members ----------
def create_group(user_id, name, kind="general"):
    gid = execute("INSERT INTO groups (name, kind, created_by, created_at) VALUES (?,?,?,datetime('now'))",
                  (name, kind, user_id))
    me = query("SELECT name FROM users WHERE id=?", (user_id,), one=True)
    _add_member_row(gid, user_id, me["name"] if me else "Me")
    return gid


def _add_member_row(group_id, user_id, display_name):
    execute("""INSERT OR IGNORE INTO group_members (group_id, user_id, display_name)
               VALUES (?,?,?)""", (group_id, user_id, display_name))


def _find_or_create_user(email, name=None):
    u = query("SELECT id, name FROM users WHERE email=?", (email.lower(),), one=True)
    if u:
        return u["id"]
    nm = name or email.split("@")[0]
    return execute("""INSERT INTO users (email, name, pw_hash, created_at)
                      VALUES (?,?,?,datetime('now'))""",
                   (email.lower(), nm, "pending$" + os.urandom(8).hex()))


def add_member(group_id, email, display_name=None):
    uid = _find_or_create_user(email, display_name)
    name = display_name or query("SELECT name FROM users WHERE id=?", (uid,), one=True)["name"]
    _add_member_row(group_id, uid, name)
    return {"user_id": uid, "display_name": name}


def members(group_id):
    return query("""SELECT gm.user_id, gm.display_name, u.email, u.upi_id
                    FROM group_members gm JOIN users u ON u.id=gm.user_id
                    WHERE gm.group_id=?""", (group_id,))


def user_groups(user_id):
    return query("""SELECT g.id, g.name, g.kind FROM groups g
                    JOIN group_members gm ON gm.group_id=g.id
                    WHERE gm.user_id=? ORDER BY g.created_at DESC""", (user_id,))


def is_member(group_id, user_id):
    return query("SELECT 1 FROM group_members WHERE group_id=? AND user_id=?",
                 (group_id, user_id), one=True) is not None


# ---------- expenses & splitting ----------
def _compute_shares(amount, mem_ids, method, values):
    """Return {user_id: owed}. values keyed by user_id (as str or int)."""
    values = {int(k): float(v) for k, v in (values or {}).items()}
    n = len(mem_ids)
    if method == "exact":
        return {u: round(values.get(u, 0.0), 2) for u in mem_ids}
    if method == "percent":
        return {u: round(amount * values.get(u, 0.0) / 100.0, 2) for u in mem_ids}
    if method == "shares":
        total = sum(values.get(u, 0) for u in mem_ids) or 1
        return {u: round(amount * values.get(u, 0) / total, 2) for u in mem_ids}
    # equal (default) — distribute remainder to first member so it sums exactly
    base = round(amount / n, 2)
    shares = {u: base for u in mem_ids}
    diff = round(amount - base * n, 2)
    if mem_ids:
        shares[mem_ids[0]] = round(shares[mem_ids[0]] + diff, 2)
    return shares


def add_expense(group_id, description, amount, paid_by, method="equal", values=None,
                participants=None, recurring=0):
    amount = float(amount)
    mem_ids = participants or [m["user_id"] for m in members(group_id)]
    shares = _compute_shares(amount, mem_ids, method, values)
    eid = execute("""INSERT INTO expenses (group_id, description, amount, paid_by, method,
                     created_by, created_at, recurring) VALUES (?,?,?,?,?,?,datetime('now'),?)""",
                  (group_id, description, amount, paid_by, method, paid_by, recurring))
    for u, owed in shares.items():
        execute("INSERT INTO expense_shares (expense_id, user_id, owed) VALUES (?,?,?)", (eid, u, owed))
    return {"id": eid, "shares": shares}


def expenses(group_id):
    rows = query("""SELECT e.*, u.name AS payer FROM expenses e JOIN users u ON u.id=e.paid_by
                    WHERE e.group_id=? ORDER BY e.created_at DESC, e.id DESC""", (group_id,))
    return rows


# ---------- balances & simplification ----------
def balances(group_id):
    mem = {m["user_id"]: m["display_name"] for m in members(group_id)}
    net = {u: 0.0 for u in mem}

    for e in query("SELECT id, amount, paid_by FROM expenses WHERE group_id=?", (group_id,)):
        net[e["paid_by"]] = net.get(e["paid_by"], 0) + e["amount"]
    for s in query("""SELECT es.user_id, es.owed FROM expense_shares es
                      JOIN expenses e ON e.id=es.expense_id WHERE e.group_id=?""", (group_id,)):
        net[s["user_id"]] = net.get(s["user_id"], 0) - s["owed"]
    for st in query("SELECT from_user, to_user, amount FROM settlements WHERE group_id=?", (group_id,)):
        net[st["from_user"]] = net.get(st["from_user"], 0) + st["amount"]
        net[st["to_user"]] = net.get(st["to_user"], 0) - st["amount"]

    return [{"user_id": u, "name": mem.get(u, "?"), "net": round(v, 2)} for u, v in net.items()]


def simplify(group_id):
    """Greedy debt simplification -> minimal set of 'A pays B' transactions."""
    bal = balances(group_id)
    names = {b["user_id"]: b["name"] for b in bal}
    creditors = sorted([[b["user_id"], b["net"]] for b in bal if b["net"] > 0.01], key=lambda x: -x[1])
    debtors = sorted([[b["user_id"], -b["net"]] for b in bal if b["net"] < -0.01], key=lambda x: -x[1])

    txns, i, j = [], 0, 0
    while i < len(debtors) and j < len(creditors):
        d, c = debtors[i], creditors[j]
        pay = round(min(d[1], c[1]), 2)
        if pay > 0:
            txns.append({"from": d[0], "from_name": names[d[0]],
                         "to": c[0], "to_name": names[c[0]], "amount": pay})
        d[1] = round(d[1] - pay, 2)
        c[1] = round(c[1] - pay, 2)
        if d[1] <= 0.01:
            i += 1
        if c[1] <= 0.01:
            j += 1
    return txns


# ---------- settle up ----------
def settle(group_id, from_user, to_user, amount, note=None):
    return execute("""INSERT INTO settlements (group_id, from_user, to_user, amount, note, created_at)
                      VALUES (?,?,?,?,?,datetime('now'))""",
                   (group_id, from_user, to_user, float(amount), note))


def upi_link(to_user_id, amount, note="ExpenseSort settle"):
    u = query("SELECT upi_id, name FROM users WHERE id=?", (to_user_id,), one=True)
    if not u or not u["upi_id"]:
        return None
    q = urllib.parse.urlencode({"pa": u["upi_id"], "pn": u["name"],
                                "am": f"{float(amount):.2f}", "cu": "INR", "tn": note})
    return f"upi://pay?{q}"


def reconcile_suggestions(user_id):
    """Auto-settle: match incoming credits in the user's statement to amounts
    they're owed, and suggest marking those debts settled — closing the loop
    that Splitwise leaves manual."""
    owed_to_me = []
    for g in user_groups(user_id):
        for t in simplify(g["id"]):
            if t["to"] == user_id:
                owed_to_me.append({"group_id": g["id"], "group": g["name"], **t})
    if not owed_to_me:
        return []
    credits = query("""SELECT description, amount, txn_date FROM transactions
                       WHERE user_id=? AND direction='credit'""", (user_id,))
    suggestions = []
    for t in owed_to_me:
        for c in credits:
            if abs(c["amount"] - t["amount"]) <= max(1, t["amount"] * 0.02):
                suggestions.append({
                    "group_id": t["group_id"], "group": t["group"],
                    "from_user": t["from"], "from_name": t["from_name"],
                    "amount": t["amount"],
                    "message": f"Credit of Rs {round(c['amount'])} on {c['txn_date'] or 'your statement'} "
                               f"looks like {t['from_name']} settling up in '{t['group']}'.",
                })
                break
    return suggestions
