"""Multi-month trends + anomaly / price-hike detection."""
from db import query


def monthly(user_id):
    rows = query("""SELECT month,
                       SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) AS income,
                       SUM(CASE WHEN direction!='credit' OR direction IS NULL THEN amount ELSE 0 END) AS expense
                    FROM transactions WHERE user_id=? AND month IS NOT NULL
                    GROUP BY month ORDER BY month""", (user_id,))
    series = [{"month": r["month"], "income": round(r["income"] or 0, 2),
               "expense": round(r["expense"] or 0, 2),
               "net": round((r["income"] or 0) - (r["expense"] or 0), 2)} for r in rows]
    return series


def category_trend(user_id):
    rows = query("""SELECT month, category, SUM(amount) AS amt FROM transactions
                    WHERE user_id=? AND month IS NOT NULL AND (direction='debit' OR direction IS NULL)
                    GROUP BY month, category ORDER BY month""", (user_id,))
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], {})[r["month"]] = round(r["amt"] or 0, 2)
    return by_cat


def anomalies(user_id):
    """Compare each category's latest month to its prior average; flag big jumps.
    Also flags likely duplicate charges (same merchant+amount same day)."""
    series = monthly(user_id)
    out = []
    cat = category_trend(user_id)
    months = [s["month"] for s in series]
    if len(months) >= 2:
        latest = months[-1]
        for c, m in cat.items():
            prior = [v for mo, v in m.items() if mo != latest]
            if not prior or latest not in m:
                continue
            avg = sum(prior) / len(prior)
            if avg > 0 and m[latest] > avg * 1.4 and m[latest] - avg > 500:
                out.append({"type": "price_hike", "category": c,
                            "message": f"{c} is Rs {round(m[latest])} this month vs Rs {round(avg)} average "
                                       f"(+{round((m[latest]/avg-1)*100)}%)."})
    # duplicate detection
    dups = query("""SELECT description, amount, txn_date, COUNT(*) c FROM transactions
                    WHERE user_id=? AND (direction='debit' OR direction IS NULL) AND txn_date IS NOT NULL
                    GROUP BY merchant_key, amount, txn_date HAVING c > 1""", (user_id,))
    for d in dups:
        out.append({"type": "duplicate",
                    "message": f"Possible duplicate: {d['description'][:36]} x{d['c']} of Rs {round(d['amount'])} "
                               f"on {d['txn_date']}."})
    return out
