"""Rule-based categorizer built for real bank-statement narrations.

Matching is space/punctuation-insensitive (statements often jam words together,
e.g. "UPI-BURGERKING"), so keywords match whether or not the bank kept spaces.
Income vs expense is decided by the transaction direction (from the balance
change in parse.py), which is accurate; categories describe where money went.
"""
import re

# order matters: distinctive / non-spending buckets first
RULES = [
    ("Investments", ["hslsec", "hdfcsec", "securities", "edelweiss", "zerodha", "groww", "upstox",
                     "indmoney", "mutualfund", "rifusion", "sambhvg", "91tb", "demat", "netpitohsl"]),
    ("Insurance",   ["licofindia", "licindia", "hdfclife", "maxlife", "insurance", "policybazaar"]),
    ("Bank Charges", ["ambchrg", "ambchgs", "ambchgsreversed", "chrginclgst", "minbalcharge"]),
    ("Entertainment", ["netflix", "spotify", "hotstar", "disney", "youtube", "primevideo", "amazonprime",
                       "googleplay", "applemedia", "appleservices", "bookmyshow", "steam", "playstation"]),
    ("Food & Dining", ["swiggy", "zomato", "dominos", "burgerking", "mcdonald", "kfc", "pizzahut",
                       "restaurant", "mehfil", "starbucks", "dunkin", "behrouz", "eatclub", "haldiram",
                       "restaurantbrands"]),
    ("Groceries",   ["bigbasket", "blinkit", "zepto", "dmart", "grofers", "reliancefresh", "grocery",
                     "departmental", "supermarket", "kirana", "guptadepartmental"]),
    ("Transport",   ["uber", "ola", "rapido", "petrol", "indianoil", "iocl", "hpcl", "bharatpetroleum",
                     "indianrailways", "irctc", "railsbi", "fastag", "redbus", "makemytrip", "agoda"]),
    ("Health",      ["pharmacy", "apollo", "medplus", "1mg", "pharmeasy", "hospital", "medical", "clinic",
                     "diagnostic", "healthkart"]),
    ("Shopping",    ["amazon", "flipkart", "myntra", "ajio", "nykaa", "luluinternation", "meesho",
                     "reliancedigital", "croma", "decathlon"]),
    ("Bills & Utilities", ["electricity", "billdesk", "recharge", "jio", "airtel", "vodafone", "broadband",
                          "tatapower", "dthrecharge", "postpaid", "gaspipeline"]),
    ("Income",      ["salary", "interestpaid", "refund", "cashback", "dividend"]),
    ("Transfers",   ["transfertofamily", "upikushagra", "satyenderkumar", "alkanarang", "imps", "sihgahp",
                     "achdrazorpay"]),
]

CATEGORIES = ["Food & Dining", "Groceries", "Transport", "Shopping", "Bills & Utilities",
              "Entertainment", "Health", "Rent", "Insurance", "Investments", "Transfers",
              "Bank Charges", "Income", "Others"]

NON_EXPENSE = {"Income"}


def _compact(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def categorize_one(desc):
    if re.search(r"\brent\b", desc or "", re.I):   # "…109 RENT", "monthly rent"
        return "Rent", 1.0
    c = _compact(desc)
    for category, keywords in RULES:
        for kw in keywords:
            if kw in c:
                return category, 1.0
    return "Others", 0.0


def categorize(transactions):
    rows, totals = [], {}
    total = income = expense = 0.0
    for t in transactions:
        desc = t.get("description", "")
        amount = float(t.get("amount", 0) or 0)
        direction = t.get("direction")
        cat, conf = categorize_one(desc)
        if direction == "credit" and cat == "Others":
            cat = "Income"            # a credit with no known merchant is money in
        rows.append({"description": desc, "amount": amount, "category": cat,
                     "confidence": conf, "direction": direction})
        total += amount
        if direction == "credit":
            income += amount
        else:                          # debit or unknown -> outflow
            expense += amount
            totals[cat] = round(totals.get(cat, 0.0) + amount, 2)

    by_category = dict(sorted(totals.items(), key=lambda kv: -kv[1]))
    return {
        "rows": rows,
        "totals": by_category,
        "total": round(total, 2),
        "count": len(rows),
        "income_total": round(income, 2),
        "expense_total": round(expense, 2),
        "net": round(income - expense, 2),
        "categories_list": CATEGORIES,
    }
