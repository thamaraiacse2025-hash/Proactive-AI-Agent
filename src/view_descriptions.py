
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT job_title, company, description
    FROM jobs
""")

jobs = cursor.fetchall()

for job in jobs:
    print("\n-------------------------")
    print("Title:", job[0])
    print("Company:", job[1])
    print("Description:", job[2] or "Not available")

connection.close()