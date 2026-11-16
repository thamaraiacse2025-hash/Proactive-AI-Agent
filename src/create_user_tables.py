
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# Enable foreign key support
cursor.execute("PRAGMA foreign_keys = ON")

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Individual user profiles
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    skills TEXT,
    preferred_location TEXT,
    preferred_roles TEXT,
    work_mode TEXT DEFAULT 'Any',
    notification_threshold REAL DEFAULT 0.25,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
)
""")

connection.commit()
connection.close()

print("Users and User Profiles tables created successfully!")
