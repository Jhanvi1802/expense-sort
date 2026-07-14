"""Category catalog: built-in defaults + per-user custom categories."""
from db import query, execute
from categorizer import CATEGORIES as DEFAULTS

DEFAULT_META = {
    "Food & Dining": ("#ef4444", "🍔"), "Groceries": ("#16a34a", "🛒"),
    "Transport": ("#3b82f6", "🚗"), "Shopping": ("#a855f7", "🛍️"),
    "Bills & Utilities": ("#f59e0b", "💡"), "Entertainment": ("#ec4899", "🎬"),
    "Health": ("#06b6d4", "🏥"), "Rent": ("#84cc16", "🏠"), "Insurance": ("#f97316", "🛡️"),
    "Investments": ("#0ea5e9", "📈"), "Transfers": ("#64748b", "🔁"),
    "Bank Charges": ("#78716c", "🏦"), "Income": ("#0d9488", "💰"), "Others": ("#94a3b8", "📦"),
}


def list_categories(user_id):
    out = [{"name": n, "color": DEFAULT_META[n][0], "icon": DEFAULT_META[n][1], "custom": False}
           for n in DEFAULTS]
    for c in query("SELECT name, color, icon FROM custom_categories WHERE user_id=?", (user_id,)):
        out.append({"name": c["name"], "color": c["color"], "icon": c["icon"], "custom": True})
    return out


def add(user_id, name, color="#94a3b8", icon="📦"):
    execute("""INSERT OR REPLACE INTO custom_categories (user_id, name, color, icon)
               VALUES (?,?,?,?)""", (user_id, name, color, icon))


def delete(user_id, name):
    execute("DELETE FROM custom_categories WHERE user_id=? AND name=?", (user_id, name))
