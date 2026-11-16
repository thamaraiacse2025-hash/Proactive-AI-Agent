import os
import json
import sqlite3
import requests
import smtplib
import re
import html

from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlsplit, unquote
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from email.message import EmailMessage


# ---------- PATHS AND SETTINGS ----------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"
PROFILE_PATH = BASE_DIR / "data" / "user_profile.json"

# Persistent JSearch cache
SEARCH_CACHE_PATH = BASE_DIR / "data" / "jsearch_cache.json"
SEARCH_CACHE_TTL_HOURS = 6

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST") or "jsearch.p.rapidapi.com"
API_URL = "https://jsearch.p.rapidapi.com/search-v2"

_embedding_model = None

# Stops all further JSearch requests after HTTP 429
RATE_LIMITED = False

# AI matching weights
SEMANTIC_WEIGHT = 0.45
SKILL_WEIGHT = 0.15
ROLE_WEIGHT = 0.20
LOCATION_WEIGHT = 0.20

MINIMUM_QUALITY_THRESHOLD = 0.55

# Expired-link verification settings
LINK_CHECK_TIMEOUT = 10
UNKNOWN_RECHECK_DAYS = 7
MAX_PAGE_TEXT_LENGTH = 1_000_000

LINK_CHECK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

EXPIRED_URL_KEYWORDS = [
    "expired",
    "closed",
    "unavailable",
    "not-available",
    "not_available",
    "no-longer-available",
    "no-longer-accepting",
    "application-closed",
    "applications-closed",
    "job-closed",
    "position-closed",
    "job-expired",
    "position-expired",
    "filled-position",
    "position-filled"
]

EXPIRED_PAGE_PHRASES = [
    "this job is no longer accepting applications",
    "job is no longer accepting applications",
    "no longer accepting applications",
    "this position is no longer available",
    "position is no longer available",
    "this job is no longer available",
    "job is no longer available",
    "job has expired",
    "this job has expired",
    "job is expired",
    "position has expired",
    "applications are closed",
    "application is closed",
    "applications have closed",
    "application period has ended",
    "this job is closed",
    "this position is closed",
    "position has been filled",
    "the position has been filled",
    "vacancy has been filled",
    "no longer hiring",
    "job is not available",
    "this job is not available",
    "position is not available",
    "this position is not available",
    "job posting has expired",
    "job posting is no longer available",
    "recruitment is closed",
    "hiring for this position has ended"
]

BLOCKED_PAGE_PHRASES = [
    "verify you are human",
    "checking your browser",
    "access denied",
    "captcha",
    "security verification",
    "please enable javascript",
    "sign in to continue",
    "login to continue",
    "log in to continue"
]


# ---------- HELPERS ----------

def parse_json_list(value):
    if isinstance(value, list):
        return value

    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def get_notification_threshold(profile):
    try:
        threshold = float(
            profile.get("notification_threshold", 0.25)
        )
    except (ValueError, TypeError):
        threshold = 0.25

    return max(0.0, min(1.0, threshold))


def normalize_profile(profile):
    profile["skills"] = parse_json_list(profile.get("skills"))
    profile["preferred_roles"] = parse_json_list(
        profile.get("preferred_roles")
    )

    profile["preferred_location"] = (
        profile.get("preferred_location") or ""
    ).strip()

    profile["work_mode"] = (
        profile.get("work_mode") or "Any"
    )

    profile["email"] = (
        profile.get("email") or ""
    ).strip()

    return profile


def normalize_location_part(value):
    value = re.sub(
        r"[^a-zA-Z0-9 ]",
        " ",
        str(value or "").lower()
    )

    value = " ".join(value.split())

    country_aliases = {
        "in": "india",
        "ind": "india",
        "usa": "united states",
        "us": "united states",
        "uk": "united kingdom",
        "gb": "united kingdom"
    }

    return country_aliases.get(value, value)


def get_location_parts(location):
    return [
        normalize_location_part(part)
        for part in str(location or "").split(",")
        if normalize_location_part(part)
    ]


def _normalize_location_token(value):
    """Normalize location names and common country abbreviations."""

    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = " ".join(value.split())

    country_aliases = {
        "in": "india",
        "ind": "india",
        "usa": "united states",
        "us": "united states",
        "uk": "united kingdom",
        "gb": "united kingdom",
        "uae": "united arab emirates",
    }

    return country_aliases.get(value, value)


def _parse_location_components(location):
    """
    Supports:
      Chennai, India
      Chennai, Tamil Nadu, India
      Perungudi, Chennai, Tamil Nadu, India

    Returns city, state, country.
    """

    parts = [
        _normalize_location_token(part)
        for part in str(location or "").split(",")
    ]

    parts = [part for part in parts if part]

    if not parts:
        return None, None, None

    known_countries = {
        "india",
        "united states",
        "united kingdom",
        "canada",
        "australia",
        "germany",
        "france",
        "singapore",
        "united arab emirates",
        "japan",
        "china",
        "ireland",
        "netherlands",
        "new zealand",
    }

    if len(parts) == 1:
        return parts[0], None, None

    if len(parts) == 2:
        first, second = parts

        if second in known_countries:
            return first, None, second

        return first, second, None

    city = parts[-3]
    state = parts[-2]
    country = parts[-1]

    return city, state, country


def calculate_location_score(preferred_location, job_location):
    """
    Exact city match: 1.00
    Same state:       0.40
    Same country:     0.10
    No match:         0.00
    """

    preferred_city, preferred_state, preferred_country = (
        _parse_location_components(preferred_location)
    )

    job_city, job_state, job_country = (
        _parse_location_components(job_location)
    )

    if not preferred_city or not job_city:
        return 0.0

    if (
        preferred_country
        and job_country
        and preferred_country != job_country
    ):
        return 0.0

    if preferred_city == job_city:
        if (
            preferred_state
            and job_state
            and preferred_state != job_state
        ):
            return 0.0

        return 1.0

    if (
        preferred_state
        and job_state
        and preferred_state == job_state
    ):
        return 0.40

    if (
        preferred_country
        and job_country
        and preferred_country == job_country
    ):
        return 0.10

    return 0.0


# ---------- PERSISTENT JSEARCH CACHE ----------

def load_search_cache():
    """
    Load successful JSearch responses from disk.

    Only cache entries younger than SEARCH_CACHE_TTL_HOURS
    are reused.
    """

    SEARCH_CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not SEARCH_CACHE_PATH.exists():
        return {}

    try:
        with open(
            SEARCH_CACHE_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            stored_cache = json.load(file)

        if not isinstance(stored_cache, dict):
            return {}

        valid_cache = {}
        current_time = datetime.now()

        for cache_key, entry in stored_cache.items():
            try:
                # Support the older list-based cache format too.
                if isinstance(entry, list):
                    continue

                if not isinstance(entry, dict):
                    continue

                cached_at = datetime.fromisoformat(
                    entry["cached_at"]
                )

                jobs = entry.get("jobs")

                if not isinstance(jobs, list):
                    continue

                age = current_time - cached_at

                if age < timedelta(0):
                    continue

                if age <= timedelta(
                    hours=SEARCH_CACHE_TTL_HOURS
                ):
                    valid_cache[cache_key] = {
                        "cached_at": cached_at.isoformat(),
                        "jobs": jobs
                    }

            except (KeyError, ValueError, TypeError):
                continue

        print(
            "Valid persistent JSearch cache entries:",
            len(valid_cache)
        )

        return valid_cache

    except (OSError, json.JSONDecodeError) as error:
        print("Could not load JSearch cache:", error)
        return {}


def save_search_cache(search_cache):
    """Save successful JSearch responses to a JSON file."""

    SEARCH_CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        with open(
            SEARCH_CACHE_PATH,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                search_cache,
                file,
                ensure_ascii=False,
                indent=2
            )

    except (OSError, TypeError, ValueError) as error:
        print("Could not save JSearch cache:", error)


def get_cached_jobs(search_cache, cache_key):
    """Return cached jobs only when the entry is still valid."""

    entry = search_cache.get(cache_key)

    if not entry:
        return None

    # Compatibility with an older in-memory list cache.
    if isinstance(entry, list):
        return entry

    if not isinstance(entry, dict):
        return None

    try:
        cached_at = datetime.fromisoformat(entry["cached_at"])
        age = datetime.now() - cached_at

        if (
            age < timedelta(0)
            or age > timedelta(hours=SEARCH_CACHE_TTL_HOURS)
        ):
            search_cache.pop(cache_key, None)
            return None

        jobs = entry.get("jobs")

        return jobs if isinstance(jobs, list) else None

    except (KeyError, ValueError, TypeError):
        search_cache.pop(cache_key, None)
        return None


def store_cached_jobs(search_cache, cache_key, jobs):
    """Store only successful HTTP responses."""

    search_cache[cache_key] = {
        "cached_at": datetime.now().isoformat(),
        "jobs": jobs
    }

    # Save immediately so a later interruption does not
    # lose successful API responses.
    save_search_cache(search_cache)


# ---------- EXPIRED INTERNSHIP DETECTION ----------

def normalize_page_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL
    )
    value = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL
    )
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)

    return " ".join(value.lower().split())


def get_url_expired_reason(url):
    try:
        parsed = urlsplit(url)

        url_text = unquote(
            (parsed.path or "") + " " + (parsed.query or "")
        )

        normalized = normalize_page_text(url_text)

        for keyword in EXPIRED_URL_KEYWORDS:
            keyword_normalized = normalize_page_text(keyword)

            if keyword_normalized and keyword_normalized in normalized:
                return f"Expired keyword in URL: {keyword}"

    except Exception:
        return None

    return None


def get_page_expired_reason(page_text):
    normalized = normalize_page_text(page_text)

    for phrase in EXPIRED_PAGE_PHRASES:
        phrase_normalized = normalize_page_text(phrase)

        if phrase_normalized and phrase_normalized in normalized:
            return f"Expired message on page: {phrase}"

    return None


def is_blocked_page(page_text):
    normalized = normalize_page_text(page_text)

    return any(
        normalize_page_text(phrase) in normalized
        for phrase in BLOCKED_PAGE_PHRASES
    )


def check_application_link(apply_link):
    if not apply_link:
        return "unknown", "Missing application link"

    original_url_reason = get_url_expired_reason(apply_link)

    print("\n[LINK VERIFICATION DEBUG]")
    print("Original URL:", repr(apply_link))
    print("Original URL expiry reason:", repr(original_url_reason))

    if original_url_reason:
        return "expired", f"Original URL: {original_url_reason}"

    try:
        response = requests.get(
            apply_link,
            headers=LINK_CHECK_HEADERS,
            timeout=LINK_CHECK_TIMEOUT,
            allow_redirects=True
        )

        page_text = response.text[:MAX_PAGE_TEXT_LENGTH]

        page_reason = get_page_expired_reason(page_text)
        final_url_reason = get_url_expired_reason(response.url)

        print("Final redirected URL:", repr(response.url))
        print("HTTP status:", response.status_code)
        print("Page expiry reason:", repr(page_reason))
        print("Redirect URL expiry reason:", repr(final_url_reason))

        if page_reason:
            return "expired", f"Page content: {page_reason}"

        if final_url_reason:
            return "expired", f"Redirect URL: {final_url_reason}"

        if is_blocked_page(page_text):
            return "unknown", "Website blocked automated verification"

        if 200 <= response.status_code < 300:
            return (
                "not_flagged",
                "Page responded; no explicit expired message detected"
            )

        return (
            "unknown",
            f"HTTP status {response.status_code}; expiry not confirmed"
        )

    except requests.Timeout:
        return "unknown", "Website request timed out"

    except requests.RequestException as error:
        return "unknown", f"Website request failed: {str(error)[:180]}"

    except Exception as error:
        return "unknown", f"Verification error: {str(error)[:180]}"


def ensure_expiry_columns(cursor):
    existing_columns = {
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(jobs)"
        ).fetchall()
    }

    if "application_status" not in existing_columns:
        cursor.execute("""
            ALTER TABLE jobs
            ADD COLUMN application_status TEXT DEFAULT 'unknown'
        """)

    if "status_checked_at" not in existing_columns:
        cursor.execute("""
            ALTER TABLE jobs
            ADD COLUMN status_checked_at TEXT
        """)

    if "status_reason" not in existing_columns:
        cursor.execute("""
            ALTER TABLE jobs
            ADD COLUMN status_reason TEXT
        """)


def verify_and_remove_expired_jobs():
    if not DB_PATH.exists():
        return 0

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    deleted_count = 0

    try:
        cursor = conn.cursor()
        ensure_expiry_columns(cursor)

        retry_before = (
            datetime.now() - timedelta(days=UNKNOWN_RECHECK_DAYS)
        ).strftime("%Y-%m-%d %H:%M:%S")

        rows = cursor.execute("""
            SELECT id, apply_link
            FROM jobs
            WHERE apply_link IS NOT NULL
              AND TRIM(apply_link) != ''
              AND (
                  status_checked_at IS NULL
                  OR (
                      application_status = 'unknown'
                      AND status_checked_at < ?
                  )
              )
        """, (retry_before,)).fetchall()

        print("\n========== EXPIRY VERIFICATION ==========")
        print("Links to verify:", len(rows))

        for row in rows:
            job_id = row["id"]
            apply_link = row["apply_link"]

            status, reason = check_application_link(apply_link)

            checked_at = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print("\nJob ID:", job_id)
            print("Status:", status)
            print("Reason:", reason)

            if status == "expired":
                cursor.execute(
                    "DELETE FROM user_job_matches WHERE job_id = ?",
                    (job_id,)
                )

                cursor.execute(
                    "DELETE FROM user_job_notifications WHERE job_id = ?",
                    (job_id,)
                )

                cursor.execute(
                    "DELETE FROM jobs WHERE id = ?",
                    (job_id,)
                )

                deleted_count += 1
                print("CONFIRMED EXPIRED - DELETED")

            else:
                cursor.execute("""
                    UPDATE jobs
                    SET application_status = ?,
                        status_checked_at = ?,
                        status_reason = ?
                    WHERE id = ?
                """, (
                    status,
                    checked_at,
                    reason,
                    job_id
                ))

                print("PRESERVED -", status)

        conn.commit()

        print("\n========== EXPIRY SUMMARY ==========")
        print("Checked:", len(rows))
        print("Deleted confirmed expired:", deleted_count)
        print("====================================")

    except Exception as error:
        conn.rollback()
        print("Expiry verification error:", error)

    finally:
        conn.close()

    return deleted_count


# ---------- LOAD AI MODEL ONCE ----------

def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        print("\nLoading semantic matching model...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    return _embedding_model


# ---------- DATABASE SETUP ----------

def setup_agent_tables():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        ensure_expiry_columns(cursor)

        cursor.execute("""
            DELETE FROM jobs
            WHERE apply_link IS NOT NULL
              AND TRIM(apply_link) <> ''
              AND rowid NOT IN (
                  SELECT MIN(rowid)
                  FROM jobs
                  WHERE apply_link IS NOT NULL
                    AND TRIM(apply_link) <> ''
                  GROUP BY apply_link
              )
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_jobs_unique_apply_link
            ON jobs(apply_link)
            WHERE apply_link IS NOT NULL
              AND TRIM(apply_link) <> ''
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_job_notifications (
                user_id INTEGER NOT NULL,
                apply_link TEXT NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, apply_link)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_job_matches (
                user_id INTEGER NOT NULL,
                apply_link TEXT NOT NULL,
                final_score REAL NOT NULL,
                semantic_score REAL NOT NULL,
                matched_skills TEXT,
                missing_skills TEXT,
                matched_roles TEXT,
                location_match INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, apply_link)
            )
        """)

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        raise

    finally:
        connection.close()


# ---------- PROFILE VALIDATION ----------

def is_profile_complete(profile):
    profile = normalize_profile(profile)

    return bool(
        profile["preferred_location"]
        and (profile["skills"] or profile["preferred_roles"])
    )


# ---------- LOAD ALL USER PROFILES ----------

def load_profiles():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute("""
            SELECT
                users.id AS user_id,
                users.name,
                users.email,
                user_profiles.skills,
                user_profiles.preferred_location,
                user_profiles.preferred_roles,
                user_profiles.work_mode,
                user_profiles.notification_threshold
            FROM users
            JOIN user_profiles
                ON users.id = user_profiles.user_id
            ORDER BY users.id
        """).fetchall()

        profiles = [
            normalize_profile(dict(row))
            for row in rows
        ]

        if profiles:
            return profiles

    finally:
        connection.close()

    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as file:
            profile = normalize_profile(json.load(file))

        profile["user_id"] = None
        return [profile]

    return []


# ---------- DISPLAY PROFILE ----------

def display_profile(profile):
    print("\n====================================")
    print("   PROACTIVE INTERNSHIP AGENT")
    print("====================================")

    print("User:", profile.get("name", "Student"))
    print("Email:", profile.get("email", "Not available"))
    print("Preferred location:", profile.get("preferred_location", ""))

    print(
        "Preferred roles:",
        ", ".join(profile.get("preferred_roles", []))
    )

    print(
        "Skills:",
        ", ".join(profile.get("skills", []))
    )


# ---------- EMAIL NOTIFICATIONS ----------

def send_email_notification(item, receiver_email):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_APP_PASSWORD")

    if not all([sender, password, receiver_email]):
        print("Email configuration missing.")
        return False

    title, company, location, apply_link, description = item["job"]

    message = EmailMessage()
    message["Subject"] = f"New Internship Match: {title}"
    message["From"] = sender
    message["To"] = receiver_email

    message.set_content(f"""
Hello!

A new internship matching your profile has been found.

Internship: {title}
Company: {company}
Location: {location}

Matching Skills:
{', '.join(item['matched_skills']) or 'No direct skill match'}

Matching Roles:
{', '.join(item['matched_roles']) or 'No direct role match'}

Semantic AI Score: {item['semantic_score']:.3f}
Location Score: {item['location_score']:.3f}
Final Match Score: {item['final_score']:.3f}

Apply Here:
{apply_link}

Regards,
Proactive AI Agent
""")

    smtp_server = os.getenv("SMTP_SERVER") or "smtp.gmail.com"
    smtp_port = int(os.getenv("SMTP_PORT") or 587)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(message)

        print(f"Email sent to {receiver_email}: {title}")
        return True

    except Exception as error:
        print("Email notification failed:", error)
        return False


# ---------- DISCOVER INTERNSHIPS ----------

def discover_jobs(profile, search_cache=None):
    global RATE_LIMITED

    if search_cache is None:
        search_cache = {}

    profile = normalize_profile(profile)

    roles = profile["preferred_roles"]
    skills = profile["skills"]
    full_location = profile["preferred_location"]

    if not full_location:
        print("Preferred location is missing.")
        return []

    if not API_KEY:
        print("RAPIDAPI_KEY is missing in .env")
        return []

    parts = [
        part.strip()
        for part in full_location.split(",")
        if part.strip()
    ]

    locations = [full_location]

    if len(parts) >= 4:
        city_location = ", ".join(parts[-3:])

        if city_location.lower() != full_location.lower():
            locations.append(city_location)

    role_query = (
        " OR ".join(roles[:3])
        if roles
        else "software developer"
    )

    skill_query = " ".join(skills[:3])

    search_queries = [
        (role_query, skill_query),
        (role_query, ""),
        ("software developer internship", "")
    ]

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    for location in locations:
        for role, skill in search_queries:

            # Stop immediately after an API rate-limit response.
            if RATE_LIMITED:
                print(
                    "\nJSearch rate limit already detected. "
                    "Skipping further API requests."
                )
                return []

            query = f"{role} {skill} internship in {location}".strip()
            cache_key = query.lower()

            cached_jobs = get_cached_jobs(
                search_cache,
                cache_key
            )

            if cached_jobs is not None:
                print(f"\nReusing cached search: {query}")

                if cached_jobs:
                    return cached_jobs

                # A successful empty result is also cached.
                continue

            print(f"\nSearching JSearch: {query}")

            params = {
                "query": query,
                "page": "1",
                "num_pages": "1"
            }

            try:
                response = requests.get(
                    API_URL,
                    headers=headers,
                    params=params,
                    timeout=30
                )

                # Check 429 separately before raise_for_status.
                if response.status_code == 429:
                    RATE_LIMITED = True

                    print("\n========== JSEARCH RATE LIMIT ==========")
                    print("JSearch returned HTTP 429.")
                    print(
                        "This may be temporary rate throttling "
                        "or an API plan/usage restriction."
                    )
                    print(
                        "No further JSearch requests will be made "
                        "during this run."
                    )
                    print("========================================")

                    # Do not cache failed responses.
                    return []

                response.raise_for_status()

                response_data = response.json()

                data = response_data.get("data", [])

                if isinstance(data, dict):
                    data = data.get("jobs", [])

                jobs = [
                    job for job in data
                    if isinstance(job, dict)
                ] if isinstance(data, list) else []

                # Cache only successful HTTP responses.
                # Empty results are also cached.
                store_cached_jobs(
                    search_cache,
                    cache_key,
                    jobs
                )

                print("Valid jobs received:", len(jobs))

                if jobs:
                    return jobs

            except requests.RequestException as error:
                print("JSearch API error:", error)

                # Failed requests are NOT cached.
                # Avoid making more requests after a network error.
                return []

            except (ValueError, TypeError) as error:
                print("Response parsing error:", error)

                # Invalid responses are not cached.
                return []

    print("No internships found for this profile.")
    return []


# ---------- SAVE NEW INTERNSHIPS ----------

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

            location = ", ".join(
                part for part in [city, state, country] if part
            ) or "Location not specified"

            apply_link = (
                job.get("job_apply_link") or ""
            ).strip()

            description = (
                job.get("job_description") or ""
            ).strip()

            if not apply_link:
                skipped_count += 1
                continue

            posted_date = (
                job.get("job_posted_at_datetime_utc")
                or datetime.now().strftime("%Y-%m-%d")
            )

            cursor.execute("""
                INSERT OR IGNORE INTO jobs (
                    job_title,
                    company,
                    location,
                    apply_link,
                    date_found,
                    description
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title,
                company,
                location,
                apply_link,
                posted_date,
                description
            ))

            if cursor.rowcount == 1:
                new_count += 1
                new_job_links.append(apply_link)
            else:
                duplicate_count += 1

        connection.commit()

        print("\n========== DISCOVERY REPORT ==========")
        print("Internships received:", len(api_jobs))
        print("New internships saved:", new_count)
        print("Already existing internships:", duplicate_count)
        print("Internships skipped:", skipped_count)
        print("======================================")

    except sqlite3.Error as error:
        connection.rollback()
        new_job_links = []
        print("Database error:", error)

    finally:
        connection.close()

    return list(set(new_job_links))


# ---------- PERSONALIZED AI MATCHING ----------

def recommend_jobs(profile, new_job_links=None):
    profile = normalize_profile(profile)

    if not is_profile_complete(profile):
        print("\nProfile incomplete. Skipping AI matching.")
        return []

    setup_agent_tables()
    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        jobs = cursor.execute("""
            SELECT job_title, company, location,
                   apply_link, description
            FROM jobs
            WHERE apply_link IS NOT NULL
              AND TRIM(apply_link) <> ''
        """).fetchall()

        if not jobs:
            print("No internships available.")
            return []

        user_id = profile.get("user_id")

        receiver_email = (
            profile.get("email")
            or os.getenv("EMAIL_RECEIVER")
            or ""
        ).strip()

        skills = profile["skills"]
        roles = profile["preferred_roles"]
        preferred_location = profile["preferred_location"]

        profile_text = (
            f"Candidate skills: {', '.join(skills)}. "
            f"Target internship roles: {', '.join(roles)}."
        )

        job_texts = [
            f"Job title: {title}. "
            f"Job description: {description or title}."
            for title, company, location, link, description in jobs
        ]

        model = get_embedding_model()

        embeddings = model.encode(
            [profile_text] + job_texts,
            convert_to_numpy=True
        )

        semantic_scores = cosine_similarity(
            embeddings[0:1],
            embeddings[1:]
        )[0]

        def clean_words(value):
            return set(re.findall(
                r"[a-zA-Z0-9+#.]+",
                str(value).lower()
            ))

        stop_words = {
            "intern", "internship", "the", "and", "for",
            "with", "of", "in", "at", "to", "a", "an"
        }

        ranked_jobs = []

        for job, raw_semantic in zip(jobs, semantic_scores):
            title, company, location, apply_link, description = job

            job_text = f"{title} {description or ''}".lower()

            semantic_score = max(
                0.0,
                min(1.0, float(raw_semantic))
            )

            matched_skills = []

            for skill in skills:
                pattern = (
                    r"(?<![a-zA-Z0-9])"
                    + re.escape(skill.lower())
                    + r"(?![a-zA-Z0-9])"
                )

                if re.search(pattern, job_text):
                    matched_skills.append(skill)

            missing_skills = [
                skill for skill in skills
                if skill not in matched_skills
            ]

            skill_score = (
                len(matched_skills) / len(skills)
                if skills else 0.0
            )

            title_words = clean_words(title) - stop_words
            job_words = clean_words(job_text) - stop_words

            matched_roles = []
            best_role_score = 0.0

            for role in roles:
                role_words = clean_words(role) - stop_words

                if not role_words:
                    continue

                title_overlap = len(role_words & title_words)
                description_overlap = len(role_words & job_words)

                title_score = title_overlap / len(role_words)
                description_score = (
                    description_overlap / len(role_words)
                )

                role_similarity = max(
                    title_score,
                    description_score * 0.75
                )

                best_role_score = max(
                    best_role_score,
                    role_similarity
                )

                if role_similarity >= 0.5:
                    matched_roles.append(role)

            role_score = min(1.0, best_role_score)

            location_score = calculate_location_score(
                preferred_location,
                location
            )

            location_match = location_score >= 0.60

            weighted_total = (
                SEMANTIC_WEIGHT * semantic_score
                + LOCATION_WEIGHT * location_score
            )

            available_weight = (
                SEMANTIC_WEIGHT + LOCATION_WEIGHT
            )

            if skills:
                weighted_total += SKILL_WEIGHT * skill_score
                available_weight += SKILL_WEIGHT

            if roles:
                weighted_total += ROLE_WEIGHT * role_score
                available_weight += ROLE_WEIGHT

            final_score = (
                weighted_total / available_weight
                if available_weight else 0.0
            )

            ranked_jobs.append({
                "final_score": final_score,
                "semantic_score": semantic_score,
                "skill_score": skill_score,
                "role_score": role_score,
                "location_score": location_score,
                "job": job,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "matched_roles": matched_roles,
                "location_match": location_match
            })

        ranked_jobs.sort(
            key=lambda item: item["final_score"],
            reverse=True
        )

        if user_id is not None:
            for item in ranked_jobs:
                cursor.execute("""
                    INSERT INTO user_job_matches (
                        user_id, apply_link, final_score,
                        semantic_score, matched_skills,
                        missing_skills, matched_roles,
                        location_match, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, apply_link)
                    DO UPDATE SET
                        final_score = excluded.final_score,
                        semantic_score = excluded.semantic_score,
                        matched_skills = excluded.matched_skills,
                        missing_skills = excluded.missing_skills,
                        matched_roles = excluded.matched_roles,
                        location_match = excluded.location_match,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    user_id,
                    item["job"][3],
                    item["final_score"],
                    item["semantic_score"],
                    json.dumps(item["matched_skills"]),
                    json.dumps(item["missing_skills"]),
                    json.dumps(item["matched_roles"]),
                    int(item["location_match"])
                ))

            connection.commit()

        threshold = max(
            MINIMUM_QUALITY_THRESHOLD,
            get_notification_threshold(profile)
        )

        new_job_links = set(new_job_links or [])

        email_count = 0
        eligible_count = 0

        for item in ranked_jobs:
            apply_link = item["job"][3]

            if apply_link not in new_job_links:
                continue

            if item["final_score"] < threshold:
                continue

            if not receiver_email or user_id is None:
                continue

            already_sent = cursor.execute("""
                SELECT 1
                FROM user_job_notifications
                WHERE user_id = ? AND apply_link = ?
            """, (user_id, apply_link)).fetchone()

            if already_sent:
                continue

            eligible_count += 1

            if send_email_notification(item, receiver_email):
                email_count += 1

                cursor.execute("""
                    INSERT OR IGNORE INTO user_job_notifications
                    (user_id, apply_link)
                    VALUES (?, ?)
                """, (user_id, apply_link))

                connection.commit()

        print("\n========== AI MATCHING REPORT ==========")
        print("Total jobs evaluated:", len(ranked_jobs))

        print(
            "Strong matches:",
            sum(
                1 for item in ranked_jobs
                if item["final_score"] >= threshold
            )
        )

        print(
            "Rejected by AI:",
            sum(
                1 for item in ranked_jobs
                if item["final_score"] < threshold
            )
        )

        print("Minimum match threshold:", threshold)
        print("Eligible new internships:", eligible_count)
        print("Emails sent:", email_count)

        print("\nAI WEIGHT DISTRIBUTION")
        print("Semantic AI:", f"{SEMANTIC_WEIGHT * 100:.0f}%")
        print("Skills:", f"{SKILL_WEIGHT * 100:.0f}%")
        print("Roles:", f"{ROLE_WEIGHT * 100:.0f}%")
        print("Location:", f"{LOCATION_WEIGHT * 100:.0f}%")

        print("========================================")

        print("\n========== TOP AI RECOMMENDATIONS ==========")

        qualified_jobs = [
            item for item in ranked_jobs
            if item["final_score"] >= threshold
        ]

        for rank, item in enumerate(qualified_jobs[:10], start=1):
            title, company, location, apply_link, _ = item["job"]

            print(f"\n{rank}. {title}")
            print("Company:", company)
            print("Location:", location)

            print(f"Final score: {item['final_score']:.3f}")
            print(f"Semantic AI score: {item['semantic_score']:.3f}")
            print(f"Skill score: {item['skill_score']:.3f}")
            print(f"Role score: {item['role_score']:.3f}")
            print(f"Location score: {item['location_score']:.3f}")

            print(
                "Matching skills:",
                ", ".join(item["matched_skills"]) or "None"
            )

            print(
                "Matching roles:",
                ", ".join(item["matched_roles"]) or "None"
            )

            print(
                "Preferred location match:",
                "Yes" if item["location_match"] else "No / Partial"
            )

            print("Apply:", apply_link)

        print("\nAI matching completed.")
        return ranked_jobs

    finally:
        connection.close()


# ---------- MULTI-USER AGENT ----------

def run_proactive_agent():
    global RATE_LIMITED

    # Reset the rate-limit flag for each scheduled run.
    RATE_LIMITED = False

    print("\n========== MULTI-USER PROACTIVE AGENT ==========")

    if not DB_PATH.exists():
        print("Database not found:", DB_PATH)
        return

    setup_agent_tables()

    # STEP 1: Check previously stored jobs.
    verify_and_remove_expired_jobs()

    profiles = load_profiles()

    if not profiles:
        print("No user profiles found.")
        return

    print("Total user profiles:", len(profiles))

    active_profiles = []
    skipped_profiles = []

    for profile in profiles:
        if is_profile_complete(profile):
            active_profiles.append(profile)
        else:
            skipped_profiles.append(profile)

    print("\nComplete profiles:", len(active_profiles))
    print("Incomplete profiles:", len(skipped_profiles))

    for profile in skipped_profiles:
        print(
            "\nSkipping incomplete profile:",
            profile.get("email", "Unknown email")
        )

        print(
            "Reason: Add preferred location and at least "
            "one skill or preferred role."
        )

    if not active_profiles:
        print("\nNo complete profiles available.")
        return

    # Load persistent cache instead of starting with an empty dictionary.
    search_cache = load_search_cache()

    all_new_job_links = set()

    print(
        "\nPersistent cache entries available:",
        len(search_cache)
    )

    # STEP 2: DISCOVER INTERNSHIPS
    for profile in active_profiles:
        print("\n------------------------------------")
        print("Discovering for:", profile.get("email"))

        display_profile(profile)

        discovered_jobs = discover_jobs(
            profile,
            search_cache
        )

        if discovered_jobs:
            new_links = save_new_jobs(discovered_jobs)
            all_new_job_links.update(new_links)
        else:
            print("No internships received for this user.")

        # If one profile triggered HTTP 429, do not search
        # for any remaining profiles during this run.
        if RATE_LIMITED:
            print(
                "\nJSearch HTTP 429 detected. "
                "Skipping discovery for remaining profiles."
            )
            break

    print(
        "\nTotal unique new internships discovered:",
        len(all_new_job_links)
    )

    print(
        "Valid persistent cache entries:",
        len(search_cache)
    )

    if RATE_LIMITED:
        print(
            "\nJSearch requests were stopped because HTTP 429 "
            "was returned. Existing database jobs will still "
            "be processed."
        )

    # STEP 3: Verify newly discovered jobs before AI matching.
    verify_and_remove_expired_jobs()

    # STEP 4: MATCH REMAINING DATABASE JOBS AGAINST EACH USER
    for profile in active_profiles:
        print("\n====================================")
        print("Processing user:", profile.get("email"))

        recommend_jobs(
            profile,
            all_new_job_links
        )

    print("\nAll complete user workflows finished.")
    print("================================================")


# ---------- MAIN ----------

if __name__ == "__main__":
    run_proactive_agent()