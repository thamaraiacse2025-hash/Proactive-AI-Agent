
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

sender = os.getenv("EMAIL_SENDER")
password = os.getenv("EMAIL_APP_PASSWORD")
receiver = os.getenv("EMAIL_RECEIVER")

if not all([sender, password, receiver]):
    print("Email configuration missing. Check your .env file.")
    raise SystemExit(1)

message = EmailMessage()
message["Subject"] = "Internship Agent - Test Email"
message["From"] = sender
message["To"] = receiver

message.set_content("""
Hello!

Your Proactive AI Agent email notification system
is successfully configured.

Day 11 email notification test completed!

Regards,
Internship Agent
""")

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(message)

    print("Test email sent successfully!")

except Exception as error:
    print("Email sending failed:", error)
