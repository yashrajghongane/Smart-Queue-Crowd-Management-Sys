import sqlite3
conn = sqlite3.connect("smartqueue.db")
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("Tables found:", len(tables))
for t in tables:
    print(" -", t)
conn.close()
