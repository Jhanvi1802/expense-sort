"""Cash-flow forecast + burn rate + upcoming bills, all from real history."""
from db import query
from recurring import detect


def _averages(user_id):
    months = query("""SELECT month,
                        SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) inc,
                        SUM(CASE WHEN direction!='credit' OR direction IS NULL THEN amount ELSE 0 END) exp
                       FROM transactions WHERE user_id=? AND month IS NOT NULL
                       GROUP BY month ORDER BY month""", (user_id,))
    return months


def burn_rate(user_id):
    row = query("""SELECT SUM(amount) exp, COUNT(DISTINCT txn_date) days,
                          MIN(txn_date) a, MAX(txn_date) b
                   FROM transactions WHERE user_id=? AND (direction='debit' OR direction IS NULL)""",
                (user_id,), one=True)
    if not row or not row["exp"]:
        return {"per_day": 0, "days": 0}
    days = row["days"] or 30
    return {"per_day": round(row["exp"] / max(days, 1), 2), "days": days}


def upcoming(user_id, monthly_income=0):
    """Estimate the next few obligations from detected recurring charges,
    plus expected salary. Dates are estimates (last seen + ~1 cycle)."""
    rec = detect(user_id)["series"]
    items = []
    for s in rec:
        items.append({"label": s["label"], "amount": s["avg_amount"], "kind": "bill",
                      "cadence": s["cadence"]})
    if monthly_income:
        items.insert(0, {"label": "Expected salary", "amount": monthly_income, "kind": "income",
                         "cadence": "monthly"})
    items.sort(key=lambda x: (x["kind"] != "income", -x["amount"]))
    return items[:6]


def forecast(user_id, monthly_income=0):
    months = _averages(user_id)
    if not months:
        return {"available": False, "message": "Add a statement to forecast your cash flow.",
                "burn": burn_rate(user_id), "upcoming": []}

    avg_income = sum(m["inc"] or 0 for m in months) / len(months)
    avg_expense = sum(m["exp"] or 0 for m in months) / len(months)
    income = monthly_income or avg_income

    rec = detect(user_id)
    committed = rec["recurring_total"]
    projected_net = round(income - avg_expense, 2)
    shortfall = projected_net < 0
    return {
        "available": True,
        "projected_income": round(income, 2),
        "projected_expense": round(avg_expense, 2),
        "committed_recurring": round(committed, 2),
        "projected_net": projected_net,
        "shortfall": shortfall,
        "burn": burn_rate(user_id),
        "upcoming": upcoming(user_id, monthly_income),
        "months": len(months),
        "message": (f"On your averages you'll be about Rs {abs(projected_net):,.0f} short this month — "
                    f"trim discretionary spend or delay a big purchase."
                    if shortfall else
                    f"Your balance looks healthy — you're on track to keep about Rs {projected_net:,.0f} this month."),
    }
