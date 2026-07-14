"""Detect recurring charges / subscriptions from a user's transaction history.

A merchant is "recurring" if it appears repeatedly (>=2 times, ideally across
distinct months) with a stable amount. Known subscription brands are flagged so
we can surface subscription-creep ("6 subs = Rs X/month").
"""
from db import query, execute

SUBS = {"netflix", "spotify", "hotstar", "primevideo", "amazonprime", "youtube", "disney",
        "applemedia", "appleservices", "googleplay", "gym", "linkedin", "canva", "notion"}


def _is_sub(mkey):
    return any(s in mkey for s in SUBS)


def detect(user_id):
    rows = query(
        """SELECT merchant_key, description, amount, month, txn_date
           FROM transactions
           WHERE user_id=? AND (direction='debit' OR direction IS NULL)
           ORDER BY txn_date, id""", (user_id,))
    groups = {}
    for r in rows:
        groups.setdefault(r["merchant_key"], []).append(r)

    series, sub_total, sub_count = [], 0.0, 0
    for mkey, items in groups.items():
        if len(items) < 2:
            continue
        months = {i["month"] for i in items if i["month"]}
        amounts = [i["amount"] for i in items]
        avg = sum(amounts) / len(amounts)
        spread = (max(amounts) - min(amounts)) / avg if avg else 1
        # recurring if seen in 2+ months, or 3+ times with stable amount
        stable = spread <= 0.25
        # recurring if seen across 2+ months, OR repeated 2+ times at a stable amount
        if not (len(months) >= 2 or (len(items) >= 2 and stable)):
            continue
        is_sub = _is_sub(mkey)
        cadence = "monthly" if len(months) >= 2 else "frequent"
        label = max((i["description"] for i in items), key=len)
        entry = {
            "merchant_key": mkey, "label": label.strip()[:40],
            "avg_amount": round(avg, 2), "count": len(items),
            "months": len(months), "cadence": cadence,
            "is_subscription": is_sub, "monthly_cost": round(avg, 2),
            "last_seen": max((i["txn_date"] or "" for i in items)),
        }
        series.append(entry)
        if is_sub:
            sub_total += avg
            sub_count += 1

    series.sort(key=lambda e: (-e["is_subscription"], -e["monthly_cost"]))
    # mark transactions recurring for the flagged merchants
    keys = [s["merchant_key"] for s in series]
    if keys:
        execute(f"UPDATE transactions SET is_recurring=1 WHERE user_id=? AND merchant_key IN "
                f"({','.join('?' * len(keys))})", (user_id, *keys))
    return {
        "series": series,
        "subscription_total": round(sub_total, 2),
        "subscription_count": sub_count,
        "recurring_total": round(sum(s["monthly_cost"] for s in series), 2),
    }
