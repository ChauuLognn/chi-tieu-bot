import sqlite3
from datetime import datetime

def get_conn():
    conn = sqlite3.connect("chitieu.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_expense(amount, category, description):
    conn = get_conn()
    conn.execute(
        "INSERT INTO expenses (amount, category, description, date) VALUES (?,?,?,?)",
        (amount, category, description, datetime.now().strftime("%Y-%m-%d"))
    )
    conn.commit()
    conn.close()

def get_summary(period="month"):
    conn = get_conn()
    if period == "today":
        date_filter = "date = date('now')"
    elif period == "week":
        date_filter = "date >= date('now', '-7 days')"
    else:
        date_filter = "date >= date('now', 'start of month')"

    rows = conn.execute(f"""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE {date_filter}
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return rows

def get_recent(limit=5):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows

def delete_last():
    conn = get_conn()
    row = conn.execute("SELECT id FROM expenses ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        conn.execute("DELETE FROM expenses WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False