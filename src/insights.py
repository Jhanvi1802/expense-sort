"""Personal dashboard aggregation + savings coach (server-side)."""
from db import query

NONSPEND = {"Investments", "Transfers", "Bank Charges"}
DISCRETIONARY = {"Food & Dining", "Shopping", "Entertainment"}


def dashboard(user_id, month=None):
    where = "WHERE user_id=?"
    params = [user_id]
    if month:
        where += " AND month=?"
        params.append(month)
    rows = query(f"SELECT category, amount, direction, description FROM transactions {where}", params)

    income = expense = 0.0
    by = {}
    for r in rows:
        a = r["amount"] or 0
        if r["direction"] == "credit":
            income += a
        else:
            expense += a
            by[r["category"]] = by.get(r["category"], 0) + a
    cats = sorted(by.items(), key=lambda kv: -kv[1])

    invest = by.get("Investments", 0)
    transfers = by.get("Transfers", 0)
    charges = by.get("Bank Charges", 0)
    real_spend = max(0, expense - invest - transfers - charges)

    tips = []
    if invest + transfers + charges > 0:
        tips.append(f"Of Rs {round(expense):,} that left, your actual spending was about Rs {round(real_spend):,} "
                    f"(rest went to investments/transfers/charges).")
    spend_cats = [(c, a) for c, a in cats if c not in NONSPEND]
    if spend_cats:
        c, a = spend_cats[0]
        pct = round(a / real_spend * 100) if real_spend else 0
        tips.append(f"Biggest real spend: {c} — Rs {round(a):,} ({pct}% of spending).")
    if income > 0:
        rate = round((income - expense) / income * 100)
        tips.append(f"Money in Rs {round(income):,} vs out Rs {round(expense):,} — net Rs {round(income-expense):,} "
                    f"({rate}% saved).")

    return {
        "income": round(income, 2), "expense": round(expense, 2),
        "net": round(income - expense, 2), "real_spend": round(real_spend, 2),
        "balance": current_balance(user_id),
        "top_merchant": top_merchant(user_id),
        "by_category": [{"category": c, "amount": round(a, 2)} for c, a in cats],
        "insights": tips,
        "coach": savings_coach(rows, cats, income, expense, real_spend, charges),
    }


def current_balance(user_id):
    """Latest running balance seen in a statement (real), else income - expense."""
    row = query("""SELECT balance FROM transactions
                   WHERE user_id=? AND balance IS NOT NULL
                   ORDER BY txn_date DESC, id DESC LIMIT 1""", (user_id,), one=True)
    if row and row["balance"] is not None:
        return round(row["balance"], 2)
    agg = query("""SELECT SUM(CASE WHEN direction='credit' THEN amount ELSE -amount END) bal
                   FROM transactions WHERE user_id=?""", (user_id,), one=True)
    return round((agg["bal"] or 0), 2) if agg else 0


def top_merchant(user_id):
    row = query("""SELECT description, category, SUM(amount) spent, COUNT(*) n
                   FROM transactions WHERE user_id=? AND (direction='debit' OR direction IS NULL)
                   GROUP BY merchant_key ORDER BY spent DESC LIMIT 1""", (user_id,), one=True)
    if not row:
        return None
    return {"name": row["description"][:28], "category": row["category"],
            "spent": round(row["spent"], 2), "count": row["n"]}


def savings_coach(rows, cats, income, expense, real_spend, charges):
    SUBS = ["netflix", "spotify", "hotstar", "prime", "youtube", "disney", "apple", "googleplay", "gym"]
    recs, potential = [], 0.0

    if charges > 0:
        recs.append(f"Bank charges of Rs {round(charges):,} are avoidable — keep the minimum balance.")
        potential += charges

    sub_total = sum((r["amount"] or 0) for r in rows
                    if r["direction"] != "credit"
                    and any(s in (r["description"] or "").lower().replace(" ", "") for s in SUBS))
    if sub_total > 0:
        half = round(sub_total * 0.5)
        recs.append(f"You pay Rs {round(sub_total):,} in subscriptions. Cancelling unused ones frees ~Rs {half:,}.")
        potential += half

    food = [r for r in rows if r["direction"] != "credit" and r["category"] == "Food & Dining"]
    food_sum = sum((r["amount"] or 0) for r in food)
    if len(food) >= 4:
        cut = round(food_sum * 0.3)
        recs.append(f"Rs {round(food_sum):,} on {len(food)} eating-out orders — cooking more could save ~Rs {cut:,}.")
        potential += cut

    if income > 0:
        rate = round((income - expense) / income * 100)
        recs.append(f"Savings rate is {rate}% (healthy is 20%+)."
                    if rate < 20 else f"Good — savings rate is {rate}%, above the healthy 20%.")

    return {"potential": round(potential), "recs": recs}
