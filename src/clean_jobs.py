import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT id, job_title, company, location, apply_link
    FROM jobs
""")

jobs = cursor.fetchall()

print("Total jobs checked:", len(jobs))

valid_count = 0
invalid_count = 0

for job in jobs:
    job_id, title, company, location, link = job
    missing = []

    if not title or not title.strip():
        missing.append("Job Title")

    if not company or not company.strip():
        missing.append("Company")

    if not location or not location.strip():
        missing.append("Location")

    if not link or not link.strip():
        missing.append("Apply Link")

    if missing:
        invalid_count += 1
        print(f"Job ID {job_id}: Missing {', '.join(missing)}")
    else:
        valid_count += 1
        print(f"Job ID {job_id}: Valid")

print("\n--- Data Quality Summary ---")
print("Valid jobs:", valid_count)
print("Jobs with missing data:", invalid_count)
cursor.execute("""
    SELECT apply_link, COUNT(*)
    FROM jobs
    GROUP BY apply_link
    HAVING COUNT(*) > 1
""")

duplicates = cursor.fetchall()

if duplicates:
    print("\nDuplicate jobs found:")
    for link, count in duplicates:
        print(f"Count: {count} | Apply link: {link}")
else:
    print("\nNo duplicate apply links found!")
connection.close()
