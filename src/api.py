
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pathlib import Path

app = FastAPI(
    title="Personalized Internship Agent API",
    description="API for the Proactive Internship Agent",
    version="1.0.0"
)

# Allow frontend to connect with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@app.get("/")
def home():
    return {
        "message": "Personalized Internship Agent API is running!"
    }


@app.get("/jobs")
def get_all_jobs():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT *
            FROM jobs
            ORDER BY date_found DESC
        """)

        jobs = [dict(row) for row in cursor.fetchall()]

        return {
            "total_jobs": len(jobs),
            "jobs": jobs
        }

    finally:
        connection.close()


@app.get("/jobs/search")
def search_jobs(keyword: str):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM jobs
            WHERE job_title LIKE ?
               OR company LIKE ?
               OR location LIKE ?
               OR description LIKE ?
            ORDER BY date_found DESC
        """, (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%"
        ))

        jobs = [dict(row) for row in cursor.fetchall()]

        return {
            "keyword": keyword,
            "total_jobs": len(jobs),
            "jobs": jobs
        }

    finally:
        connection.close()


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,)
        )

        job = cursor.fetchone()

        if job is None:
            return {"message": "Internship not found"}

        return dict(job)

    finally:
        connection.close()


@app.get("/stats")
def get_statistics():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM jobs
            WHERE description IS NOT NULL
              AND description != ''
        """)
        jobs_with_descriptions = cursor.fetchone()[0]

        return {
            "total_jobs": total_jobs,
            "jobs_with_descriptions": jobs_with_descriptions
        }

    finally:
        connection.close()
