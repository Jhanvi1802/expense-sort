# ExpenseSort

Paste or upload your transactions and a trained ML model sorts each one into a
spending category (Food, Transport, Bills, Shopping, and so on), then shows a
summary of where your money goes.

## Features
- Paste transactions (one per line) or upload a CSV / TXT
- ML text classifier categorizes each transaction automatically
- Spending summary: total, per-category totals with bars, and a transaction table
- Clean web UI; runs fully locally

## How it works
- A TF-IDF + logistic-regression classifier is trained on a seed set of labeled
  transaction descriptions (Indian merchants and services).
- Input lines are parsed into description + amount, each description is classified,
  and amounts are aggregated per category.

## Run
```bash
pip install -r requirements.txt
python app.py        # then open http://localhost:8001
pytest -q            # run tests
```

## Structure
```
app.py               FastAPI app: web UI, /categorize, /extract (file upload)
src/categorizer.py   train the model, classify, summarize
src/parse.py         parse pasted text / CSV into transactions
tests/               unit tests
```

## Notes / next steps
- Add more seed examples per category to improve accuracy
- Let users correct a category and retrain (active learning)
- Add monthly trends and a downloadable summary
