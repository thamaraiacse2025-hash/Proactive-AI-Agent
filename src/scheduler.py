from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3
import sys

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

# Background scheduler log file
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "scheduler.log"
sys.stdout = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
sys.stderr = sys.stdout

# Import agent after log setup
from agent import run_proactive_agent

# Indian Standard Time
TIMEZONE = ZoneInfo("Asia/Kolkata")

# Search interval
INTERVAL_HOURS = 6

# Search interval
INTERVAL_HOURS = 6


# Create scheduler state table
def initialize_scheduler_database():

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_run_time TEXT
            )
        """)

        connection.commit()

    finally:
        connection.close()


# Get last search time
def get_last_run_time():

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT last_run_time
            FROM scheduler_state
            WHERE id = 1
        """)

        result = cursor.fetchone()

        if result is None or result[0] is None:
            return None

        return datetime.fromisoformat(result[0])

    finally:
        connection.close()


# Save current search attempt time
def save_last_run_time(run_time):

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("""
            INSERT INTO scheduler_state (id, last_run_time)
            VALUES (1, ?)
            ON CONFLICT(id)
            DO UPDATE SET last_run_time = excluded.last_run_time
        """, (run_time.isoformat(),))

        connection.commit()

    finally:
        connection.close()


# Run the internship agent
def scheduled_agent_run():

    current_time = datetime.now(TIMEZONE)

    print("\n====================================")
    print("AUTOMATIC INTERNSHIP SEARCH STARTED")
    print("Time:", current_time)
    print("====================================")

    # Save attempt time before running the agent.
    # This prevents repeated requests after an unexpected restart.
    save_last_run_time(current_time)

    try:
        run_proactive_agent()

        print("Automatic internship search completed.")

    except Exception as error:
        print("Scheduled agent error:", error)


# Initialize database
initialize_scheduler_database()


# Calculate next search time
last_run = get_last_run_time()
current_time = datetime.now(TIMEZONE)

if last_run is None:

    # First-time startup: run immediately
    next_run = current_time

    print("First-time scheduler startup.")
    print("Initial internship search will run immediately.")

else:

    next_run = last_run + timedelta(hours=INTERVAL_HOURS)

    if next_run <= current_time:

        # Search interval already completed while laptop was OFF
        next_run = current_time

        print("A scheduled search is pending.")
        print("It will run immediately.")

    else:

        remaining = next_run - current_time

        print("Previous search:", last_run)
        print("Next search:", next_run)
        print("Remaining time:", remaining)


# Create scheduler
scheduler = BlockingScheduler(
    timezone=TIMEZONE
)


# Add recurring job
scheduler.add_job(
    scheduled_agent_run,
    trigger=IntervalTrigger(
        hours=INTERVAL_HOURS,
        timezone=TIMEZONE
    ),
    id="internship_agent_job",
    max_instances=1,
    coalesce=True,
    next_run_time=next_run
)


print("\n====================================")
print("PROACTIVE INTERNSHIP AGENT SCHEDULER")
print("====================================")
print("Frequency: Every 6 hours")
print("Timezone: Asia/Kolkata")
print("Database:", DB_PATH)
print("Press CTRL + C to stop.")
print("====================================\n")


# Start scheduler
scheduler.start()
