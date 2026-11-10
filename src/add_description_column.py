
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(jobs)")
columns = [column[1] for column in cursor.fetchall()]

if "description" not in columns:
    cursor.execute("ALTER TABLE jobs ADD COLUMN description TEXT")
    connection.commit()
    print("Description column added successfully!")
else:
    print("Description column already exists.")

cursor.execute("SELECT COUNT(*) FROM jobs")
total_jobs = cursor.fetchone()[0]

print("Existing internships preserved:", total_jobs)

connection.close()
