# Save as backend/test_email.py and run it once to verify email works

import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")

async def test():
    print(f"Testing email...")
    print(f"Host : {EMAIL_HOST}:{EMAIL_PORT}")
    print(f"User : {EMAIL_USER}")
    print(f"Pass : {'*' * len(EMAIL_PASS)} ({len(EMAIL_PASS)} chars)")

    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ EMAIL_USER or EMAIL_PASS is empty in .env")
        return

    msg            = MIMEText("This is a test email from WorkGuard.")
    msg["From"]    = EMAIL_USER
    msg["To"]      = EMAIL_USER
    msg["Subject"] = "WorkGuard Test Email ✅"

    try:
        async with aiosmtplib.SMTP(
            hostname=EMAIL_HOST, port=EMAIL_PORT,
            start_tls=True, timeout=30
        ) as smtp:
            await smtp.login(EMAIL_USER, EMAIL_PASS)
            await smtp.send_message(msg)
        print("✅ Test email sent! Check your inbox.")
    except aiosmtplib.SMTPAuthenticationError:
        print("❌ Wrong email or password")
        print("   Use Gmail App Password from: https://myaccount.google.com/apppasswords")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())