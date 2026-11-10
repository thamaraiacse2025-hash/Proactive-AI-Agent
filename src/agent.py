import os
import json
import sqlite3
import requests
import smtplib

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from email.message import EmailMessage


# ---------- PATHS AND SETTINGS ----------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"
PROFILE_PATH = BASE_DIR / "data" / "user_profile.json"

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST")

API_URL = "https://jsearch.p.rapidapi.com/search-v2"


# ---------- LOAD USER PROFILE ----------

def load_profile():
    with open(PROFILE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------- DISPLAY USER PREFERENCES ----------

def display_profile(profile):
    print("\n====================================")
    print("   PROACTIVE INTERNSHIP AGENT")
    print("====================================")

    print(
        "Preferred location:",
        profile.get("preferred_location", "India")
    )

    print(
        "Preferred roles:",
        ", ".join(profile.get("preferred_roles", []))
    )

    print(
        "Skills:",
        ", ".join(profile.get("skills", []))
    )


# ---------- DAY 11: EMAIL NOTIFICATIONS ----------

def send_email_notification(item):

    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_APP_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    if not all([sender, password, receiver]):
        print("Email configuration missing.")
        return False

    title, company, location, apply_link, description = item["job"]

    matched_skills = item["matched_skills"]
    matched_roles = item["matched_roles"]
    score = item["final_score"]

    message = EmailMessage()

    message["Subject"] = f"New Internship Match: {title}"
    message["From"] = sender
    message["To"] = receiver

    message.set_content(f"""
Hello!

A new internship matching your profile has been found.

Internship: {title}
Company: {company}
Location: {location}

Matching Skills:
{', '.join(matched_skills) or 'No direct skill match'}

Matching Roles:
{', '.join(matched_roles) or 'No direct role match'}

Match Score: {score:.3f}

Apply Here:
{apply_link}

Regards,
Proactive AI Agent
""")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(message)

        print(f"Email sent for: {title}")
        return True

    except Exception as error:
        print("Email notification failed:", error)
        return False


# ---------- FETCH NEW INTERNSHIPS ----------

def discover_jobs(profile):

    if not API_KEY or not API_HOST:
        print("\nAPI credentials missing. Check your .env file.")
        return []

    preferred_location = profile.get(
        "preferred_location", "India"
    )

    query = (
        f"software developer internship OR "
        f"Python developer internship OR "
        f"machine learning internship in {preferred_location}"
    )

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    params = {
        "query": query,
        "page": "1",
        "num_pages": "1"
    }

    try:
        print("\nSearching for new internships...")

        response = requests.get(
            API_URL,
            headers=headers,
            params=params,
            timeout=30
        )

        print("API status:", response.status_code)

        if response.status_code != 200:
            print("API request failed:", response.text[:300])
            return []

        payload = response.json()
        result_data = payload.get("data", [])

        if isinstance(result_data, dict):
            jobs = result_data.get("jobs", [])
        elif isinstance(result_data, list):
            jobs = result_data
        else:
            jobs = []

        print("Jobs received:", len(jobs))
        return jobs

    except requests.RequestException as error:
        print("Network error:", error)
        return []

    except ValueError:
        print("Could not read the API response.")
        return []


# ---------- SAVE ONLY NEW JOBS ----------

def save_new_jobs(api_jobs):

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    new_count = 0
    duplicate_count = 0
    skipped_count = 0
    new_job_links = []

    try:
        for job in api_jobs:

            title = job.get("job_title") or "Unknown title"
            company = job.get("employer_name") or "Unknown company"

            city = job.get("job_city") or ""
            state = job.get("job_state") or ""
            country = job.get("job_country") or ""

            job_location = ", ".join(
                part for part in [city, state, country] if part
            ) or "Location not specified"

            apply_link = job.get("job_apply_link")

            description = (
                job.get("job_description") or ""
            ).strip()

            # Skip jobs without an application link
            if not apply_link:
                skipped_count += 1
                continue

            posted_date = (
                job.get("job_posted_at_datetime_utc")
                or datetime.now().strftime("%Y-%m-%d")
            )

            # Check whether internship already exists
            cursor.execute(
                "SELECT 1 FROM jobs WHERE apply_link = ?",
                (apply_link,)
            )

            existing_job = cursor.fetchone()

            if existing_job:
                duplicate_count += 1
                continue

            # Insert only newly discovered internships
            cursor.execute("""
                INSERT INTO jobs
                (job_title, company, location, apply_link,
                 date_found, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title,
                company,
                job_location,
                apply_link,
                posted_date,
                description
            ))

            new_count += 1
            new_job_links.append(apply_link)

        connection.commit()

        print("\n========== DAY 10 DISCOVERY REPORT ==========")
        print("Internships received:", len(api_jobs))
        print("New internships saved:", new_count)
        print("Already existing internships:", duplicate_count)
        print("Internships skipped:", skipped_count)
        print("=============================================")

    except sqlite3.Error as error:
        connection.rollback()
        new_job_links = []
        print("Database error:", error)

    finally:
        connection.close()

    return new_job_links


# ---------- PERSONALIZED INTERNSHIP RECOMMENDATIONS ----------

def recommend_jobs(profile, new_job_links=None):

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT job_title, company, location,
               apply_link, description
        FROM jobs
    """)

    jobs = cursor.fetchall()
    connection.close()

    if not jobs:
        print("\nNo internships available in the database.")
        return

    skills = profile.get("skills", [])
    roles = profile.get("preferred_roles", [])

    preferred_location = profile.get(
        "preferred_location", ""
    )

    preferred_city = (
        preferred_location.split(",")[0].strip().lower()
    )

    # ---------- DAY 6: IMPROVED SEMANTIC MATCHING ----------

    profile_text = (
        f"Skills: {', '.join(skills)}. "
        f"Preferred roles: {', '.join(roles)}. "
        f"Preferred location: {preferred_location}."
    )

    job_texts = []

    for title, company, job_location, _, description in jobs:

        job_text = (
            f"Internship title: {title}. "
            f"Company: {company}. "
            f"Location: {job_location}. "
            f"Job description: {description or title}."
        )

        job_texts.append(job_text)

    print("\nLoading semantic matching model...")

    model = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = model.encode(
        [profile_text] + job_texts,
        convert_to_numpy=True
    )

    semantic_scores = cosine_similarity(
        embeddings[0:1],
        embeddings[1:]
    )[0]

    ranked_jobs = []

    # Score every internship using profile preferences
    for job, semantic_score in zip(jobs, semantic_scores):

        title, company, job_location, apply_link, description = job

        title_lower = title.lower()
        location_lower = job_location.lower()

        job_text = (
            f"{title} {description or ''}"
        ).lower()

        # 1. Identify matching skills
        matched_skills = [
            skill for skill in skills
            if skill.lower() in job_text
        ]

        # 2. Identify skills that are not mentioned
        missing_skills = [
            skill for skill in skills
            if skill.lower() not in job_text
        ]

        skill_bonus = min(
            len(matched_skills) * 0.04,
            0.20
        )

        # 3. Identify matching preferred roles
        matched_roles = []

        for role in roles:

            role_words = [
                word.lower()
                for word in role.split()
                if word.lower() not in {
                    "intern", "internship"
                }
            ]

            if role_words and any(
                word in title_lower
                for word in role_words
            ):
                matched_roles.append(role)

        role_bonus = 0.15 if matched_roles else 0.0

        # 4. Prefer the user's selected location
        location_match = (
            preferred_city in location_lower
            if preferred_city else False
        )

        location_bonus = (
            0.15 if location_match else 0.0
        )

        # 5. Calculate final ranking score
        semantic_score = max(
            0.0,
            float(semantic_score)
        )

        final_score = (
            semantic_score * 0.50
            + skill_bonus * 1.25
            + role_bonus
            + location_bonus * (10 / 15)
        )

        ranked_jobs.append({
            "final_score": final_score,
            "semantic_score": semantic_score,
            "job": job,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_roles": matched_roles,
            "location_match": location_match
        })

    # Rank highest-scoring internships first
    ranked_jobs.sort(
        key=lambda item: item["final_score"],
        reverse=True
    )

    # ---------- DAY 11: EMAIL NEW RELEVANT INTERNSHIPS ----------

    new_job_links = set(new_job_links or [])

    notification_threshold = float(
        profile.get("notification_threshold", 0.25)
    )

    email_count = 0
    eligible_new_count = 0

    for item in ranked_jobs:

        apply_link = item["job"][3]

        # Notify only for internships newly inserted in this run.
        if apply_link not in new_job_links:
            continue

        # Send email only when personalized score meets threshold.
        if item["final_score"] >= notification_threshold:

            eligible_new_count += 1

            if send_email_notification(item):
                email_count += 1

    print("\n========== DAY 11 EMAIL REPORT ==========")
    print("New internships eligible for notification:", eligible_new_count)
    print("Emails sent successfully:", email_count)
    print("Notification threshold:", notification_threshold)
    print("=========================================")

    # ---------- DISPLAY RESULTS ----------

    print("\n========== PERSONALIZED TOP INTERNSHIPS ==========")

    for rank, item in enumerate(ranked_jobs[:10], start=1):

        title, company, job_location, apply_link, _ = item["job"]

        print(f"\n{rank}. {title}")
        print("   Company:", company)
        print("   Location:", job_location)

        print(
            f"   Final ranking score: "
            f"{item['final_score']:.3f}"
        )

        print(
            f"   Semantic score: "
            f"{item['semantic_score']:.3f}"
        )

        print(
            "   Matching skills:",
            ", ".join(item["matched_skills"])
            if item["matched_skills"]
            else "No direct skill match"
        )

        print(
            "   Skills not mentioned in description:",
            ", ".join(item["missing_skills"])
            if item["missing_skills"]
            else "All profile skills mentioned"
        )

        print(
            "   Matching roles:",
            ", ".join(item["matched_roles"])
            if item["matched_roles"]
            else "No direct role match"
        )

        print(
            "   Preferred location match:",
            "Yes" if item["location_match"] else "No"
        )

        print("   Apply:", apply_link)

    print("\n===================================================")
    print("Day 8 improved internship ranking completed.")
    print("Scores are ranking signals, not eligibility percentages.")


# ---------- DAY 9: PROACTIVE AGENT WORKFLOW ----------

def run_proactive_agent():

    print("\n========== PROACTIVE INTERNSHIP AGENT ==========")

    # 1. Load saved user profile
    profile = load_profile()

    if not profile:
        print("User profile not found.")
        return

    # 2. Display user preferences
    display_profile(profile)

    # 3. Discover internships based on profile
    print("\nStarting internship discovery...")

    discovered_jobs = discover_jobs(profile)

    # 4. Save newly discovered internships
    if discovered_jobs:
        new_job_links = save_new_jobs(discovered_jobs)
    else:
        print("No new internships received.")
        new_job_links = []

    # 5. Generate personalized recommendations and email new matches
    print("\nGenerating personalized recommendations...")

    recommend_jobs(profile, new_job_links)

    print("\nProactive agent workflow completed.")
    print("================================================")


# ---------- MAIN AGENT WORKFLOW ----------

if __name__ == "__main__":

    if not DB_PATH.exists():
        print("Database not found:", DB_PATH)
        raise SystemExit(1)

    if not PROFILE_PATH.exists():
        print("User profile not found:", PROFILE_PATH)
        raise SystemExit(1)

    run_proactive_agent()