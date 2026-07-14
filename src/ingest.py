"""Turn raw text (paste / CSV / statement PDF text) into persisted, categorized
transactions for a user. Reuses parse + categorizer + tax tagging.
"""
import re

from categorizer import categorize_one, merchant_key
from db import execute, executemany
from parse import parse_transactions
from tax import tax_section


def _month(iso):
    return iso[:7] if iso and len(iso) >= 7 else None


def _clean_desc(d):
    """Tidy a description for display: drop leading date remnants and collapse
    stray separators (e.g. '- - Amazon' -> 'Amazon')."""
    d = d or ""
    d = re.sub(r"^\s*\d{2,4}[-/]\d{1,2}[-/]\d{1,4}\b", "", d)   # leading date
    d = re.sub(r"[\s\-–—]{2,}", " ", d)                          # collapse "  - - "
    d = re.sub(r"\s+", " ", d).strip(" -–—,:|*#")
    return d or "Transaction"


def ingest_text(user_id, text, source="paste"):
    parsed = parse_transactions(text)
    if not parsed:
        return {"added": 0, "rows": []}

    stmt_id = execute("INSERT INTO statements (user_id, source, uploaded_at) VALUES (?,?,datetime('now'))",
                      (user_id, source))

    seq, preview = [], []
    for t in parsed:
        desc = _clean_desc(t.get("description", ""))
        amount = float(t.get("amount", 0) or 0)
        direction = t.get("direction")
        date = t.get("date")
        cat, conf = categorize_one(desc)
        if direction == "credit" and cat == "Others":
            cat = "Income"
        if direction is None and cat == "Income":
            direction = "credit"          # income with no explicit direction is money in
        sec = tax_section(desc) if direction != "credit" else None
        seq.append((user_id, stmt_id, date, _month(date), desc, merchant_key(desc),
                    amount, t.get("balance"), direction, cat, conf, sec))
        preview.append({"description": desc, "amount": amount, "category": cat,
                        "direction": direction, "date": date})

    executemany(
        """INSERT INTO transactions
           (user_id, statement_id, txn_date, month, description, merchant_key,
            amount, balance, direction, category, confidence, tax_section)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", seq)
    return {"added": len(seq), "rows": preview, "statement_id": stmt_id}


def user_transactions(user_id, month=None):
    from db import query
    if month:
        return query("SELECT * FROM transactions WHERE user_id=? AND month=? ORDER BY txn_date, id",
                     (user_id, month))
    return query("SELECT * FROM transactions WHERE user_id=? ORDER BY txn_date, id", (user_id,))
