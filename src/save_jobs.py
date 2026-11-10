
import os
import sqlite3
import requests
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("RAPIDAPI_KEY")
api_host = os.getenv("RAPIDAPI_HOST")

DB_PATH = BASE_DIR / "data" / "internships.db"

url = "https://jsearch.p.rapidapi.com/search-v2"

headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": api_host
}

params = {
    "query": "software developer internship in India",
    "page": "1",
    "num_pages": "1"
}

if not api_key or not api_host:
    print("API credentials missing! Check your .env file.")
    raise SystemExit

connection = None

try:
    print("Sending one API request...")

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print("API Status Code:", response.status_code)

    if response.status_code != 200:
        print("API request failed.")
        print("Response:", response.text[:500])
        raise SystemExit

    data = response.json()

    # Handle the response structure used by the current project.
    result_data = data.get("data", {})
    jobs = (
        result_data.get("jobs", [])
        if isinstance(result_data, dict)
        else result_data if isinstance(result_data, list)
        else []
    )

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM jobs
    """)
    before_count = cursor.fetchone()[0]

    updated_count = 0
    missing_description_count = 0

    for job in jobs:
        apply_link = job.get("job_apply_link")
        description = job.get("job_description")

        if not apply_link:
            continue

        if not description or not description.strip():
            missing_description_count += 1
            continue

        cursor.execute("""
            UPDATE jobs
            SET description = ?
            WHERE apply_link = ?
              AND (description IS NULL OR description = '')
        """, (description.strip(), apply_link))

        if cursor.rowcount > 0:
            updated_count += cursor.rowcount

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    after_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE description IS NOT NULL
          AND TRIM(description) != ''
    """)
    jobs_with_descriptions = cursor.fetchone()[0]

    print("\n--- Results ---")
    print("Jobs returned by API:", len(jobs))
    print("Existing descriptions added:", updated_count)
    print("API jobs without descriptions:", missing_description_count)
    print("Database jobs before:", before_count)
    print("Database jobs after:", after_count)
    print("Total jobs with descriptions:", jobs_with_descriptions)

    if updated_count == 0:
        print(
            "\nNo existing job descriptions were updated. "
            "The returned jobs may not match your stored apply links."
        )

except requests.RequestException as error:
    print("Connection error:", error)

except sqlite3.Error as error:
    print("Database error:", error)

finally:
    if connection:
        connection.close()
