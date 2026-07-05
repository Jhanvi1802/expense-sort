"""Parse transactions from pasted text, a simple CSV, or a real bank statement.

Bank-statement mode is generic (works across banks): it finds dated rows with
money amounts, treats the last amount on a row as the running Balance, and infers
income vs expense from how the balance changed (up = money in, down = money out).
So it does not depend on a particular bank's column names.
"""
import csv
import io
import re

DATE = re.compile(r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})")
DEC = re.compile(r"\d{1,3}(?:,\d{2,3})*\.\d{2}")          # money, e.g. 1,60,000.00
GEN = re.compile(r"(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", re.I)
CRDR = re.compile(r"\b(cr|dr)\b", re.I)


def _num(s):
    return float(str(s).replace(",", ""))


def looks_like_statement(text):
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 4:
        return False
    dated = sum(1 for l in lines if DATE.search(l))
    deci = sum(1 for l in lines if DEC.search(l))
    return dated >= 3 and deci >= 3


def parse_bank_statement(text):
    rows, prev_bal = [], None
    for line in text.splitlines():
        if not DATE.search(line):
            continue
        amts = DEC.findall(line)
        if not amts:
            continue

        desc = DATE.sub(" ", line)
        for a in amts:
            desc = desc.replace(a, " ", 1)
        desc = CRDR.sub(" ", desc)
        desc = re.sub(r"[|*#]+", " ", desc)
        desc = re.sub(r"\s+", " ", desc).strip(" -,:").strip()

        if len(amts) >= 2:
            txn, bal = _num(amts[-2]), _num(amts[-1])
        else:
            txn, bal = _num(amts[-1]), None

        direction = None
        m = CRDR.search(line)
        if m:
            direction = "credit" if m.group(1).lower() == "cr" else "debit"
        if direction is None and bal is not None and prev_bal is not None:
            delta = round(bal - prev_bal, 2)
            if abs(delta) > 0.001:
                direction = "credit" if delta > 0 else "debit"
                txn = abs(delta)          # balance change is the true transaction amount
        if bal is not None:
            prev_bal = bal

        if desc and txn > 0:
            rows.append({"description": desc, "amount": round(txn, 2), "direction": direction})
    return rows


def _amount_from(text):
    m = GEN.findall(text or "")
    return _num(m[-1]) if m else 0.0


def _strip_amount(text):
    return GEN.sub(" ", text or "").strip(" ,\t")


def _parse_simple(text):
    rows = []
    if "," in text and any(len(line.split(",")) >= 2 for line in text.splitlines()):
        for parts in csv.reader(io.StringIO(text)):
            parts = [p.strip() for p in parts if p.strip()]
            if not parts:
                continue
            amount, desc_parts = 0.0, []
            for p in parts:
                if re.fullmatch(r"(?:rs\.?|inr|₹)?\s*[0-9][0-9,]*(?:\.[0-9]+)?", p, re.I):
                    amount = _amount_from(p)
                elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", p) or re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", p):
                    continue
                else:
                    desc_parts.append(p)
            desc = " ".join(desc_parts).strip()
            if not amount:
                amount = _amount_from(" ".join(parts))
            if desc:
                rows.append({"description": desc, "amount": amount, "direction": None})
        if rows:
            return rows
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append({"description": _strip_amount(line) or line, "amount": _amount_from(line), "direction": None})
    return rows


def parse_transactions(text):
    text = (text or "").strip()
    if not text:
        return []
    if looks_like_statement(text):
        rows = parse_bank_statement(text)
        if rows:
            return rows
    return _parse_simple(text)
