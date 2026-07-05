import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from categorizer import categorize, categorize_one
from parse import parse_transactions


def test_known_categories():
    assert categorize_one("swiggy order")[0] == "Food & Dining"
    assert categorize_one("uber ride")[0] == "Transport"
    assert categorize_one("amazon purchase")[0] == "Shopping"
    assert categorize_one("salary credited")[0] == "Income"
    assert categorize_one("electricity bill")[0] == "Bills & Utilities"


def test_parse_line_amount():
    rows = parse_transactions("Swiggy order 320")
    assert rows[0]["amount"] == 320.0
    assert "swiggy" in rows[0]["description"].lower()


def test_parse_csv():
    rows = parse_transactions("2026-07-01, Amazon purchase, 1499\nUber ride, 180")
    assert len(rows) == 2
    assert rows[0]["amount"] == 1499.0
    assert rows[1]["amount"] == 180.0


def test_categorize_summary_totals():
    res = categorize(parse_transactions("Swiggy 320\nUber 180\nSwiggy again 100"))
    assert res["count"] == 3
    assert round(res["total"], 2) == 600.0
    assert res["totals"]["Food & Dining"] == 420.0


def test_labels_are_plain_strings():
    res = categorize(parse_transactions("Netflix 199"))
    assert all(isinstance(k, str) for k in res["totals"])
