"""Savings goals (e.g. 'New Car Fund' 65% achieved)."""
from db import query, execute


def list_goals(user_id):
    rows = query("SELECT * FROM goals WHERE user_id=? ORDER BY id", (user_id,))
    for g in rows:
        g["pct"] = round(g["saved"] / g["target"] * 100) if g["target"] else 0
    return rows


def create(user_id, name, target, saved=0):
    return execute("INSERT INTO goals (user_id, name, target, saved, created_at) VALUES (?,?,?,?,datetime('now'))",
                   (user_id, name, float(target), float(saved)))


def contribute(user_id, goal_id, amount):
    execute("UPDATE goals SET saved = saved + ? WHERE id=? AND user_id=?", (float(amount), goal_id, user_id))


def delete(user_id, goal_id):
    execute("DELETE FROM goals WHERE id=? AND user_id=?", (goal_id, user_id))
