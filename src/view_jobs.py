import sqlite3
from pathlib import Path

# Find the database file
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

# Connect to the database
connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# Retrieve saved jobs
cursor.execute("""
    SELECT id, job_title, company, location, apply_link
    FROM jobs
""")

jobs = cursor.fetchall()

print("Total jobs stored:", len(jobs))

for job in jobs:
    print("\n-------------------------")
    print("ID:", job[0])
    print("Title:", job[1])
    print("Company:", job[2])
    print("Location:", job[3])
    print("Apply Link:", job[4])

connection.close()