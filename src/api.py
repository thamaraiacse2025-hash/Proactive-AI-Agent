
import smtplib
import secrets
import hashlib
from email.message import EmailMessage
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import sqlite3
import json
import os

from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from jose import jwt, JWTError


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(
    title="Personalized Internship Agent API",
    description="API for the Proactive Internship Agent",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# DATABASE
# ==========================================

def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_password_column(conn):
    columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    ]

    if "password_hash" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN password_hash TEXT"
        )
        conn.commit()


def ensure_recommendation_table(conn):
    conn.execute("""
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

    conn.commit()


# ==========================================
# REQUEST MODELS
# ==========================================

class ProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    skills: List[str]
    preferred_location: str
    preferred_roles: List[str]
    work_mode: str = "Any"
    notification_threshold: float = Field(
        default=0.25,
        ge=0,
        le=1
    )


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    skills: List[str]
    preferred_location: str
    preferred_roles: List[str]
    work_mode: str = "Any"
    notification_threshold: float = Field(
        default=0.25,
        ge=0,
        le=1
    )


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(
        min_length=8,
        max_length=128
    )


# ==========================================
# PROFILE FORMAT
# ==========================================

def format_profile(user, profile):
    try:
        skills = json.loads(profile["skills"] or "[]")
    except (ValueError, TypeError):
        skills = []

    try:
        roles = json.loads(
            profile["preferred_roles"] or "[]"
        )
    except (ValueError, TypeError):
        roles = []

    return {
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "skills": skills,
        "preferred_location": profile["preferred_location"],
        "preferred_roles": roles,
        "work_mode": profile["work_mode"],
        "notification_threshold": profile["notification_threshold"]
    }


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Personalized Internship Agent API is running!"
    }


# ==========================================
# INTERNSHIP ENDPOINTS
# ==========================================

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

        jobs = [
            dict(row)
            for row in cursor.fetchall()
        ]

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

        jobs = [
            dict(row)
            for row in cursor.fetchall()
        ]

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
            raise HTTPException(
                status_code=404,
                detail="Internship not found"
            )

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


# ==========================================
# PROFILE ENDPOINTS
# ==========================================

@app.post("/profiles", status_code=201)
def create_profile(data: ProfileCreate):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN")

        email = data.email.strip().lower()

        cursor.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        )

        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        cursor.execute("""
            INSERT INTO users (name, email)
            VALUES (?, ?)
        """, (
            data.name.strip(),
            email
        ))

        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO user_profiles (
                user_id,
                skills,
                preferred_location,
                preferred_roles,
                work_mode,
                notification_threshold
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            json.dumps(data.skills),
            data.preferred_location,
            json.dumps(data.preferred_roles),
            data.work_mode,
            data.notification_threshold
        ))

        connection.commit()

        return {
            "message": "User profile created successfully",
            "user_id": user_id
        }

    except HTTPException:
        connection.rollback()
        raise

    except sqlite3.Error:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail="Could not save user profile"
        )

    finally:
        connection.close()


@app.get("/profiles/{user_id}")
def get_profile(user_id: int):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                users.id,
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
            WHERE users.id = ?
        """, (user_id,))

        result = cursor.fetchone()

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )

        try:
            skills = json.loads(result["skills"] or "[]")
        except (ValueError, TypeError):
            skills = []

        try:
            roles = json.loads(
                result["preferred_roles"] or "[]"
            )
        except (ValueError, TypeError):
            roles = []

        return {
            "user_id": result["id"],
            "name": result["name"],
            "email": result["email"],
            "skills": skills,
            "preferred_location": result["preferred_location"],
            "preferred_roles": roles,
            "work_mode": result["work_mode"],
            "notification_threshold": result["notification_threshold"]
        }

    finally:
        connection.close()


@app.put("/profiles/{user_id}")
def update_profile(user_id: int, data: ProfileUpdate):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        cursor.execute("""
            UPDATE users
            SET name = ?
            WHERE id = ?
        """, (
            data.name.strip(),
            user_id
        ))

        cursor.execute("""
            UPDATE user_profiles
            SET skills = ?,
                preferred_location = ?,
                preferred_roles = ?,
                work_mode = ?,
                notification_threshold = ?
            WHERE user_id = ?
        """, (
            json.dumps(data.skills),
            data.preferred_location,
            json.dumps(data.preferred_roles),
            data.work_mode,
            data.notification_threshold,
            user_id
        ))

        connection.commit()

        return {
            "message": "Profile updated successfully",
            "user_id": user_id
        }

    except HTTPException:
        connection.rollback()
        raise

    except sqlite3.Error:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail="Could not update profile"
        )

    finally:
        connection.close()


# ==========================================
# AUTHENTICATION SYSTEM
# ==========================================

security = HTTPBearer()
password_hasher = PasswordHash.recommended()

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
AUTH_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def create_access_token(user_id):
    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        AUTH_SECRET_KEY,
        algorithm=AUTH_ALGORITHM
    )


def send_reset_otp(receiver_email, otp):
    sender = os.getenv("EMAIL_SENDER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER") or "smtp.gmail.com"
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not all([sender, app_password, smtp_server]):
        raise ValueError(
            "Email configuration is incomplete."
        )

    message = EmailMessage()
    message["Subject"] = "Password Reset OTP"
    message["From"] = sender
    message["To"] = receiver_email

    message.set_content(f"""
Hello,

Your password reset OTP is: {otp}

This OTP expires in 10 minutes.
Do not share this OTP with anyone.

If you did not request this, ignore this email.
""")

    if smtp_port == 465:
        with smtplib.SMTP_SSL(
            smtp_server,
            smtp_port
        ) as server:
            server.login(
                sender,
                app_password.replace(" ", "")
            )
            server.send_message(message)

    else:
        with smtplib.SMTP(
            smtp_server,
            smtp_port
        ) as server:
            server.starttls()
            server.login(
                sender,
                app_password.replace(" ", "")
            )
            server.send_message(message)


@app.post("/auth/register")
def register_user(data: RegisterRequest):
    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters."
        )

    if not data.name.strip() or "@" not in data.email:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid name and email."
        )

    conn = get_db_connection()

    try:
        ensure_password_column(conn)

        email = data.email.strip().lower()

        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Email already registered."
            )

        hashed_password = password_hasher.hash(
            data.password
        )

        cursor = conn.execute("""
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
        """, (
            data.name.strip(),
            email,
            hashed_password
        ))

        user_id = cursor.lastrowid

        conn.execute("""
            INSERT INTO user_profiles (
                user_id,
                skills,
                preferred_location,
                preferred_roles,
                work_mode,
                notification_threshold
            )
            VALUES (?, '[]', '', '[]', 'Any', 0.25)
        """, (user_id,))

        conn.commit()

        token = create_access_token(user_id)

        return {
            "message": "Registration successful.",
            "user_id": user_id,
            "name": data.name.strip(),
            "email": email,
            "access_token": token,
            "token_type": "bearer"
        }

    except HTTPException:
        conn.rollback()
        raise

    except sqlite3.IntegrityError:
        conn.rollback()

        raise HTTPException(
            status_code=409,
            detail="Email already registered."
        )

    finally:
        conn.close()


@app.post("/auth/login")
def login_user(data: LoginRequest):
    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    conn = get_db_connection()

    try:
        ensure_password_column(conn)

        user = conn.execute("""
            SELECT id, name, email, password_hash
            FROM users
            WHERE email = ?
        """, (
            data.email.strip().lower(),
        )).fetchone()

        if (
            not user
            or not user["password_hash"]
            or not password_hasher.verify(
                data.password,
                user["password_hash"]
            )
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password."
            )

        token = create_access_token(user["id"])

        return {
            "message": "Login successful.",
            "user_id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        conn.close()


@app.get("/auth/me")
def get_logged_in_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            AUTH_SECRET_KEY,
            algorithms=[AUTH_ALGORITHM]
        )

        user_id = int(payload.get("sub"))

    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    conn = get_db_connection()

    try:
        user = conn.execute("""
            SELECT id, name, email
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return dict(user)

    finally:
        conn.close()


# ==========================================
# FORGOT PASSWORD / OTP
# ==========================================

def hash_otp(otp):
    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    return hashlib.sha256(
        (AUTH_SECRET_KEY + otp).encode()
    ).hexdigest()


@app.post("/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    email = data.email.strip().lower()

    conn = get_db_connection()

    try:
        ensure_password_column(conn)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_otps (
                email TEXT PRIMARY KEY,
                otp_hash TEXT NOT NULL,
                expires_at REAL NOT NULL,
                attempts INTEGER DEFAULT 0
            )
        """)

        user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user is None:
            return {
                "message": "If the account exists, an OTP will be sent."
            }

        otp = f"{secrets.randbelow(1000000):06d}"

        expiry = (
            datetime.now(timezone.utc).timestamp() + 600
        )

        conn.execute("""
            INSERT OR REPLACE INTO password_reset_otps
            (email, otp_hash, expires_at, attempts)
            VALUES (?, ?, ?, 0)
        """, (
            email,
            hash_otp(otp),
            expiry
        ))

        conn.commit()

        try:
            send_reset_otp(email, otp)

        except Exception:
            conn.execute(
                "DELETE FROM password_reset_otps WHERE email = ?",
                (email,)
            )
            conn.commit()

            raise HTTPException(
                status_code=500,
                detail="Could not send OTP. Check email configuration."
            )

        return {
            "message": "OTP sent to your registered email."
        }

    finally:
        conn.close()


@app.post("/auth/reset-password")
def reset_password(data: ResetPasswordRequest):
    email = data.email.strip().lower()

    conn = get_db_connection()

    try:
        ensure_password_column(conn)

        record = conn.execute("""
            SELECT otp_hash, expires_at, attempts
            FROM password_reset_otps
            WHERE email = ?
        """, (email,)).fetchone()

        if record is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP."
            )

        if (
            datetime.now(timezone.utc).timestamp()
            > record["expires_at"]
            or record["attempts"] >= 5
        ):
            conn.execute(
                "DELETE FROM password_reset_otps WHERE email = ?",
                (email,)
            )
            conn.commit()

            raise HTTPException(
                status_code=400,
                detail="OTP expired. Request a new OTP."
            )

        if not secrets.compare_digest(
            hash_otp(data.otp),
            record["otp_hash"]
        ):
            conn.execute("""
                UPDATE password_reset_otps
                SET attempts = attempts + 1
                WHERE email = ?
            """, (email,))

            conn.commit()

            raise HTTPException(
                status_code=400,
                detail="Incorrect OTP."
            )

        new_hash = password_hasher.hash(
            data.new_password
        )

        conn.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE email = ?
        """, (
            new_hash,
            email
        ))

        conn.execute(
            "DELETE FROM password_reset_otps WHERE email = ?",
            (email,)
        )

        conn.commit()

        return {
            "message": "Password reset successful. Please login."
        }

    finally:
        conn.close()


# ==========================================
# PERSONALIZED AI RECOMMENDATIONS
# ==========================================

@app.get("/my/recommendations")
def get_my_recommendations(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Return only the logged-in user's AI recommendations
    whose scores meet their personal notification threshold.
    """

    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    # Authenticate the current user.
    try:
        payload = jwt.decode(
            credentials.credentials,
            AUTH_SECRET_KEY,
            algorithms=[AUTH_ALGORITHM]
        )

        user_id = int(payload.get("sub"))

    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    conn = get_db_connection()

    try:
        # Get this user's current threshold.
        user_profile = conn.execute("""
            SELECT notification_threshold
            FROM user_profiles
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if user_profile is None:
            raise HTTPException(
                status_code=404,
                detail="User profile not found."
            )

        threshold = user_profile["notification_threshold"]

        if threshold is None:
            threshold = 0.25

        threshold = max(0.55, threshold)

        # Ensure matching table exists.
        ensure_recommendation_table(conn)

        # Get all matches for this user.
        # The threshold filter is applied here.
        rows = conn.execute("""
            SELECT
                jobs.id,
                jobs.job_title,
                jobs.company,
                jobs.location,
                jobs.apply_link,
                jobs.date_found,
                jobs.description,

                matches.final_score,
                matches.semantic_score,
                matches.matched_skills,
                matches.missing_skills,
                matches.matched_roles,
                matches.location_match,
                matches.updated_at

            FROM user_job_matches AS matches

            INNER JOIN jobs
                ON jobs.apply_link = matches.apply_link

            WHERE matches.user_id = ?
              AND matches.final_score >= ?

            ORDER BY
                matches.final_score DESC,
                jobs.date_found DESC
        """, (
            user_id,
            threshold
        )).fetchall()

        recommendations = []

        for row in rows:
            item = dict(row)

            # Convert stored JSON strings into arrays.
            for field in (
                "matched_skills",
                "missing_skills",
                "matched_roles"
            ):
                try:
                    item[field] = json.loads(
                        item[field] or "[]"
                    )
                except (ValueError, TypeError):
                    item[field] = []

            item["location_match"] = bool(
                item["location_match"]
            )

            recommendations.append(item)

        # Also count all evaluated jobs, including
        # those below the threshold.
        total_scored = conn.execute("""
            SELECT COUNT(*)
            FROM user_job_matches
            WHERE user_id = ?
        """, (user_id,)).fetchone()[0]

        return {
            "user_id": user_id,
            "notification_threshold": threshold,
            "total_scored_matches": total_scored,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations
        }

    finally:
        conn.close()
