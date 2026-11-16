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

# Ensure project root is available for imports
sys.path.insert(0, str(BASE_DIR))

# Log directory
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "scheduler.log"
log_handle = open(LOG_FILE, "a", encoding="utf-8", buffering=1)


# Show output in both terminal and log file
class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            stream.write(message)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


sys.stdout = TeeStream(sys.__stdout__, log_handle)
sys.stderr = TeeStream(sys.__stderr__, log_handle)


# Import multi-user agent
from src.agent import run_proactive_agent


# Configuration
TIMEZONE = ZoneInfo("Asia/Kolkata")
INTERVAL_HOURS = 6


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


def scheduled_agent_run():
    current_time = datetime.now(TIMEZONE)

    print("\n====================================")
    print("AUTOMATIC INTERNSHIP SEARCH STARTED")
    print("Time:", current_time)
    print("====================================")

    try:
        run_proactive_agent()
        print("Automatic internship search completed successfully.")

    except Exception as error:
        print("Scheduled agent error:", error)

    finally:
        # Save the attempt time even if an error occurs
        save_last_run_time(current_time)


# Initialize database
initialize_scheduler_database()


# Calculate next execution time
last_run = get_last_run_time()
current_time = datetime.now(TIMEZONE)

if last_run is None:
    next_run = current_time

    print("First-time scheduler startup.")
    print("Initial search will run immediately.")

else:
    next_run = last_run + timedelta(hours=INTERVAL_HOURS)

    if next_run <= current_time:
        next_run = current_time

        print("A scheduled search is pending.")
        print("It will run immediately.")

    else:
        print("Previous search:", last_run)
        print("Next search:", next_run)
        print("Remaining time:", next_run - current_time)


# Create scheduler
scheduler = BlockingScheduler(timezone=TIMEZONE)


# Add recurring multi-user agent job
scheduler.add_job(
    scheduled_agent_run,
    trigger=IntervalTrigger(
        hours=INTERVAL_HOURS,
        timezone=TIMEZONE
    ),
    id="internship_agent_job",
    max_instances=1,
    coalesce=True,
    next_run_time=next_run,
    replace_existing=True
)


print("\n====================================")
print("PROACTIVE INTERNSHIP AGENT SCHEDULER")
print("====================================")
print("Frequency: Every 6 hours")
print("Timezone: Asia/Kolkata")
print("Database:", DB_PATH)
print("Log file:", LOG_FILE)
print("Press CTRL + C to stop.")
print("====================================\n")


# Start scheduler
try:
    scheduler.start()

except (KeyboardInterrupt, SystemExit):
    print("Scheduler stopped.")

finally:
    log_handle.close()