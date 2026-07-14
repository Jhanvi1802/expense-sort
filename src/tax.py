"""India tax-saver tagging: flag transactions eligible under common
deduction sections so the user gets a filing-ready summary.

Heuristic keyword match — informational, not tax advice.
"""
import re

from categorizer import _compact

# section -> (keywords, human label)
SECTIONS = {
    "80C": (["licofindia", "licindia", "hdfclife", "maxlife", "ppf", "elss", "sukanya",
             "nsc", "tuitionfee", "mutualfundelss", "taxsaver"], "Life insurance / PPF / ELSS / tuition"),
    "80D": (["healthinsurance", "mediclaim", "starhealth", "religarehealth", "carehealth",
             "healthpremium"], "Health insurance premium"),
    "80CCD": (["npscontribution", "nps", "nationalpension"], "NPS contribution"),
}


def tax_section(desc):
    c = _compact(desc)
    for section, (kws, _label) in SECTIONS.items():
        if any(k in c for k in kws):
            return section
    # generic insurance -> 80C unless clearly health
    if "insurance" in c:
        return "80D" if re.search(r"health|medi", c) else "80C"
    return None


LIMITS = {"80C": 150000, "80D": 25000, "80CCD": 50000}
# rough marginal rate used to estimate tax saved (new-regime blended vs old-regime)
_RATE = {"old": 0.31, "new": 0.15}


def summarize(rows, manual=None, regime="new"):
    """rows: auto-detected txns (amount+tax_section). manual: user-entered
    investment entries. Returns per-section totals, headroom, tips, tax saved."""
    by = {}
    detail = {}
    for r in rows:
        s = r.get("tax_section")
        if s:
            by[s] = round(by.get(s, 0.0) + float(r.get("amount", 0) or 0), 2)
    for m in (manual or []):
        s = m["section"]
        by[s] = round(by.get(s, 0.0) + float(m["amount"] or 0), 2)
        detail.setdefault(s, []).append({"label": m["label"], "amount": m["amount"], "id": m.get("id")})

    out, total = [], 0.0
    for s in sorted(set(list(by) + list(LIMITS))):
        amt = by.get(s, 0.0)
        cap = LIMITS.get(s, 0)
        eligible = min(amt, cap) if cap else amt
        out.append({"section": s, "label": SECTIONS.get(s, (None, s))[1],
                    "claimed": amt, "limit": cap,
                    "headroom": round(max(0, cap - amt), 2),
                    "entries": detail.get(s, [])})
        total += eligible
    saved = round(total * _RATE.get(regime, 0.15))
    return {"sections": out, "total_claimable": round(total, 2),
            "tax_saved": saved, "regime": regime}
