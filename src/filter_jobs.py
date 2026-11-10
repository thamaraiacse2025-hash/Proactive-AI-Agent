
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

state = input("Enter preferred state (or leave blank): ").strip()
district = input("Enter preferred district/city: ").strip()
role = input("Enter preferred job role: ").strip()

query = """
    SELECT job_title, company, location, apply_link
    FROM jobs
    WHERE job_title LIKE ?
      AND location LIKE ?
"""

params = [f"%{role}%", f"%{district}%"]

if state:
    query += " AND location LIKE ?"
    params.append(f"%{state}%")

cursor.execute(query, params)
jobs = cursor.fetchall()

if jobs:
    print("\nMatching internships:")

    for job in jobs:
        print("\n-------------------------")
        print("Title:", job[0])
        print("Company:", job[1])
        print("Location:", job[2])
        print("Apply Link:", job[3])
else:
    print("\nNo matching internships found.")
    print("Try another district/city or job role.")

connection.close()
