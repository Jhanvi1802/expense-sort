"""Financial-health score — an honest composite of real metrics (not a credit
score). 0-900, mapped to a rating. Components:
  - savings rate (net / income)
  - budget adherence (how many budgets are within limit)
  - recurring load (recurring spend as a share of income; lower is better)
"""
from db import query
from budgets import status as budget_status
from recurring import detect


def _band(score):
    if score >= 800: return "EXCELLENT"
    if score >= 650: return "GOOD"
    if score >= 500: return "FAIR"
    return "NEEDS WORK"


def score(user_id):
    agg = query("""SELECT
        SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) income,
        SUM(CASE WHEN direction!='credit' OR direction IS NULL THEN amount ELSE 0 END) expense
        FROM transactions WHERE user_id=?""", (user_id,), one=True)
    income = (agg["income"] or 0) if agg else 0
    expense = (agg["expense"] or 0) if agg else 0

    # savings rate component (0-450)
    rate = (income - expense) / income if income > 0 else 0
    save_pts = max(0, min(1, rate / 0.30)) * 450   # 30% savings rate = full marks

    # budget adherence (0-250)
    b = budget_status(user_id)["budgets"]
    if b:
        ok = sum(1 for x in b if x["state"] != "over")
        adhere_pts = ok / len(b) * 250
    else:
        adhere_pts = 150   # neutral if no budgets set

    # recurring load (0-200) — lower recurring/income is better
    rec = detect(user_id)["recurring_total"]
    load = rec / income if income > 0 else 0
    load_pts = max(0, min(1, 1 - load / 0.5)) * 200   # >50% of income on recurring = 0

    total = round(save_pts + adhere_pts + load_pts)
    return {"score": total, "max": 900, "band": _band(total),
            "savings_rate": round(rate * 100),
            "components": {"savings": round(save_pts), "budget": round(adhere_pts),
                           "recurring": round(load_pts)}}
