import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(jobs)")
columns = cursor.fetchall()

print("Columns available in the jobs table:\n")

for column in columns:
    print(column[1])

connection.close()
