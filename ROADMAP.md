# ExpenseSort — Product Roadmap

> Turning the local statement-analyzer into a **cloud, multi-user, India-first**
> money app that combines **expense sorting + Splitwise-style splitting +
> actionable savings coaching** — the intersection no competitor owns today.

## Decisions locked
- **Architecture:** Cloud, multi-user (accounts, shared ledgers, real-time balances).
- **Market:** India-first (UPI, INR, Indian merchant lexicon, 80C/80D tax tagging).
- **Build first:** Recurring/subscription detection + Budgets + Trends.

## Positioning — why users pick us over the alternatives
| Competitor | Their weakness we exploit |
|---|---|
| Splitwise | Splits bills but never analyzes *your* spending |
| Fi / Jupiter / INDmoney / Cred | Require bank linking + KYC; upsell; data leaves device |
| YNAB / Monarch | Paid, manual, US-centric, no India merchants, no splitting |

**Our wedge:** drop a statement PDF → instant analysis (no bank linking) **+**
split those same expenses with friends **+** "here's exactly where to save."
The statement parser (balance-delta direction inference in `src/parse.py`) is the
moat — it removes the onboarding friction every competitor has.

---

## Phase 0 — Foundations (required before anything multi-user)
- [ ] **Database layer** — SQLAlchemy models; SQLite (dev) → PostgreSQL (prod).
- [ ] **Accounts & auth** — email + password + Google OAuth; JWT sessions.
      (Phone OTP later — India-natural but adds SMS cost.)
- [ ] **Reconcile the ML claim** — README says TF-IDF/93.6% but `categorizer.py`
      is pure rules. Build the real hybrid: rules first → ML classifier for the
      "Others" fallback → "user corrects category" feedback loop that retrains.
- [ ] **Refactor the monolith** — split `app.py` (300-line file w/ inline HTML)
      into routers + services + templates/SPA.
- [ ] **Security & compliance** — this is financial data: upload size/type limits,
      encryption at rest, per-user data isolation, DPDP Act (India) basics,
      "delete my data" flow.
- [ ] **Deploy** — Render/Railway/Fly + managed Postgres; CI on push.

## Phase 1 — Recurring + Budgets + Trends  ← **WE START HERE**
- [ ] **Recurring/subscription detection** — cluster repeating merchant+amount
      charges; surface "6 subscriptions = ₹1,240/mo", flag forgotten ones.
- [ ] **Budgets** — per-category monthly budget, budget-vs-actual bars, alerts.
- [ ] **Multi-month trends** — spend over time; "Food up 30% vs last month."
- [ ] **Duplicate / refund detection** — catch double charges & track refunds.

## Phase 2 — The Splitwise engine (headline feature)
- [ ] **Groups** — trip / flatmates / family, each with its own ledger.
- [ ] **Split a transaction** — equal / unequal / shares / % across members.
- [ ] **Debt simplification** — minimize IOUs ("A pays B ₹500, done").
- [ ] **Settle up via UPI deep link** — tap → opens GPay/PhonePe pre-filled.
- [ ] **Killer combo:** import statement → auto-detect the shared Swiggy/Uber/rent
      charge → one-tap split. Nobody else does this.

## Phase 3 — Standout / unique
- [ ] **Tax-saver tagger (India)** — auto-flag 80C/80D spend, export for filing.
- [ ] **"Money leaks" report** — forgotten subs + bank charges + ATM fees, one number.
- [ ] **Natural-language query** ("how much on food last month?") — optional local LLM, privacy-preserving.
- [ ] **Merchant insights** ("Swiggy 12×/month = ₹4,300").

## Backlog / extra ideas
Savings goals · cash vs digital · bill-due reminders · forex/travel mode ·
shareable read-only reports · household shared view · multi-statement merge
(bank + credit card).

---

## Proposed stack (pragmatic for a solo build → market)
- **Backend:** FastAPI (keep) + SQLAlchemy + Alembic migrations.
- **DB:** PostgreSQL (prod), SQLite (dev).
- **Auth:** JWT; email/password + Google OAuth.
- **Frontend:** keep server-rendered + HTMX near-term; extract to React only when
  real-time shared ledgers demand it (Phase 2).
- **Categorizer:** hybrid rules + scikit-learn fallback + feedback loop.

## Data model sketch (Phase 0/1)
```
User(id, email, name, auth)
Statement(id, user_id, source, uploaded_at)
Transaction(id, user_id, statement_id, date, description, amount,
            direction, category, confidence, is_recurring, merchant_key)
Budget(id, user_id, category, month, limit_amount)
RecurringSeries(id, user_id, merchant_key, cadence, avg_amount, last_seen)
-- Phase 2 --
Group(id, name, created_by)
GroupMember(group_id, user_id, role)
Split(id, transaction_id, group_id, method)
SplitShare(split_id, user_id, amount_owed)
Settlement(id, group_id, from_user, to_user, amount, upi_ref)
```
