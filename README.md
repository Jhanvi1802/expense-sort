# ExpenseSort

A **cloud, multi-user, India-first** money app: drop your bank statement (or
paste transactions) and it sorts spending, tracks budgets, detects subscriptions,
forecasts cash flow, flags tax-saver spend — **and** splits shared expenses with
friends, Splitwise-style. Statement-native analysis + splitting + coaching in one
place, the combination no competitor offers.

## Screens (all wired to real data)
- **Auth** — split-hero sign-up / log-in, UPI-optional, Google/GitHub stubs.
- **Onboarding** — 4-step wizard (welcome → profile → income → first statement).
- **Dashboard** — upload/paste, Money In/Out/Net KPIs, spending donut, insights,
  Savings Coach, profile-completion.
- **Transactions** — real running balance, saving-goal card, search, pagination,
  inline category editing, recurring badges.
- **Recurring** — monthly-commitment card, subscription detection, optimization alert.
- **Budgets** — overall-spend card, per-category budget-vs-actual, financial-health score.
- **Trends** — income-vs-expense chart, avg savings, burn rate, top merchant,
  anomaly/price-hike/duplicate alerts, monthly breakdown.
- **Forecast** — projected surplus/shortfall, upcoming bills, burn rate,
  what-if simulation, forecast reliability.
- **Tax** — 80C/80D/80CCD planner, Old/New regime toggle, manual entries,
  projected tax saved, optimization tips.
- **Split** — groups, equal/exact/percent/shares splits, debt simplification,
  UPI settle links, auto-settle reconciliation, group summary.
- **Settings** — Profile, Preferences (theme/language), Notifications, Categories,
  Security (change password), Data (export CSV / delete data / delete account), Plan.

## Run
```bash
pip install -r requirements.txt
python app.py        # then open http://localhost:8001
```
No external database or services — data is stored in a local SQLite file
(`expensesort.db`). Auth (pbkdf2 password hashing + HMAC-signed tokens) and the
DB layer use only the Python standard library, so there is nothing extra to install.

## Architecture
```
app.py                 FastAPI: REST API + serves the SPA + favicon
web/index.html         design-system CSS + app shell (light/dark)
web/app.js             SPA: auth, onboarding, all tabs, settings
src/
  db.py                SQLite schema + migrations (stdlib sqlite3)
  security.py          pbkdf2 passwords + HMAC tokens + auth dependency
  extract.py           text from PDF/CSV/TXT
  parse.py             text/CSV/statement -> dated transactions (+ running balance)
  categorizer.py       rule-based category + merchant-key
  ingest.py            parse -> categorize -> tax-tag -> persist per user
  categories.py        default + per-user custom categories
  recurring.py         recurring / subscription detection
  budgets.py           per-category budgets vs actual
  trends.py            monthly trends + anomaly / duplicate detection
  forecast.py          cash-flow forecast + burn rate + upcoming bills
  goals.py             savings goals
  health.py            financial-health score (composite of real metrics)
  tax.py               80C/80D/80CCD tagging, regimes, manual entries
  insights.py          dashboard aggregation + current balance + savings coach
  splitting.py         groups, splits, debt simplification, UPI, reconciliation
ROADMAP.md             product plan
```

## Honesty notes (what's real vs. approximate)
- **Real, computed from your data:** balances, income/expense/net, categories,
  recurring detection, budgets, trends, burn rate, top merchant, tax totals,
  all splitting math, financial-health score (from savings rate + budget
  adherence + recurring load).
- **Approximate / heuristic:** upcoming-bill dates (estimated from recurring
  cadence), forecast reliability (scales with months of history).
- **Demo stubs (clearly labelled in-app):** Google/GitHub login, report/sheet
  export buttons, 2FA, Pro plan.
- **Categorization** is a rule engine tuned for Indian bank narrations, not a
  trained ML model (a hybrid rules+ML fallback is on the roadmap).

## Roadmap
See [ROADMAP.md](ROADMAP.md).
