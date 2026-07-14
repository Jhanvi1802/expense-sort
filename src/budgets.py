"""Per-category monthly budgets and budget-vs-actual with alerts."""
from db import query, execute


def set_budget(user_id, category, limit_amount):
    execute("""INSERT INTO budgets (user_id, category, limit_amount) VALUES (?,?,?)
               ON CONFLICT(user_id, category) DO UPDATE SET limit_amount=excluded.limit_amount""",
            (user_id, category, float(limit_amount)))


def delete_budget(user_id, category):
    execute("DELETE FROM budgets WHERE user_id=? AND category=?", (user_id, category))


def status(user_id, month=None):
    budgets = query("SELECT category, limit_amount FROM budgets WHERE user_id=?", (user_id,))
    if month:
        actuals = query("""SELECT category, SUM(amount) AS spent FROM transactions
                           WHERE user_id=? AND month=? AND (direction='debit' OR direction IS NULL)
                           GROUP BY category""", (user_id, month))
    else:
        actuals = query("""SELECT category, SUM(amount) AS spent FROM transactions
                           WHERE user_id=? AND (direction='debit' OR direction IS NULL)
                           GROUP BY category""", (user_id,))
    spent = {a["category"]: a["spent"] or 0 for a in actuals}
    out = []
    for b in budgets:
        s = spent.get(b["category"], 0)
        limit = b["limit_amount"]
        pct = round(s / limit * 100) if limit else 0
        out.append({
            "category": b["category"], "limit": limit, "spent": round(s, 2),
            "remaining": round(limit - s, 2), "pct": pct,
            "state": "over" if s > limit else ("warn" if pct >= 80 else "ok"),
        })
    out.sort(key=lambda x: -x["pct"])
    return {"budgets": out, "month": month}
