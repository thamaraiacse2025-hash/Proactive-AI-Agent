import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
SELECT name FROM sqlite_master
WHERE type = 'table'
ORDER BY name
""")

tables = cursor.fetchall()

print("Database tables:")
for table in tables:
    print("-", table[0])

connection.close()
