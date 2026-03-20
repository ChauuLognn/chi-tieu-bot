import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_expense(amount, category, description):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (amount, category, description, date) VALUES (%s,%s,%s,%s)",
        (amount, category, description, datetime.now().strftime("%Y-%m-%d"))
    )
    conn.commit()
    cur.close()
    conn.close()

def get_summary(period="month"):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if period == "today":
        date_filter = "date = CURRENT_DATE::text"
    elif period == "week":
        date_filter = "date >= (CURRENT_DATE - INTERVAL '7 days')::text"
    else:
        date_filter = "date >= DATE_TRUNC('month', CURRENT_DATE)::text"

    cur.execute(f"""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE {date_filter}
        GROUP BY category
        ORDER BY total DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_recent(limit=5):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def delete_last():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM expenses ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM expenses WHERE id=%s", (row[0],))
        conn.commit()
        cur.close()
        conn.close()
        return True
    cur.close()
    conn.close()
    return False