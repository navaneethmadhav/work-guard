# backend/services/email_service.py

import aiosmtplib
import base64
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.image     import MIMEImage
from datetime             import datetime
from config               import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS


async def send_intruder_alert(
    to_email:           str,
    username:           str,
    timestamp:          datetime,
    intruder_image_b64: str = None
):
    """
    Send intruder alert email with optional intruder face image attached.
    Logs every step so failures are visible in backend terminal.
    """

    # ── Validate config before trying ────────────────────────────────────────
    if not EMAIL_USER or not EMAIL_PASS:
        print("[Email] ❌ EMAIL_USER or EMAIL_PASS is empty in .env — skipping email")
        return

    if not to_email:
        print("[Email] ❌ Recipient email is empty — skipping email")
        return

    print(f"[Email] Preparing alert email to: {to_email}")

    # ── Build email ───────────────────────────────────────────────────────────
    msg            = MIMEMultipart("related")
    msg["From"]    = f"WorkGuard Security <{EMAIL_USER}>"
    msg["To"]      = to_email
    msg["Subject"] = "⚠️ WorkGuard Security Alert: Unauthorized Access Detected"

    time_str = timestamp.strftime("%d %B %Y at %I:%M:%S %p")

    has_image = intruder_image_b64 is not None

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">

      <!-- Header -->
      <div style="background: #dc2626; color: white; padding: 24px;
                  border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 24px;">⚠️ Security Alert</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">WorkGuard Workspace Monitor</p>
      </div>

      <!-- Body -->
      <div style="background: #f9fafb; padding: 24px;
                  border: 1px solid #e5e7eb; border-top: none;">

        <p style="font-size: 16px; color: #111827;">
          Hello <strong>{username}</strong>,
        </p>

        <p style="color: #374151;">
          An <strong style="color: #dc2626;">unauthorized person</strong> was
          detected accessing your workspace account.
        </p>

        <!-- Details Table -->
        <table style="width: 100%; border-collapse: collapse;
                      margin: 20px 0; border-radius: 8px; overflow: hidden;">
          <tr style="background: #fef2f2;">
            <td style="padding: 12px 16px; color: #6b7280;
                       font-weight: bold; width: 40%;">👤 Account</td>
            <td style="padding: 12px 16px; color: #111827;">{username}</td>
          </tr>
          <tr style="background: #fff;">
            <td style="padding: 12px 16px; color: #6b7280; font-weight: bold;">📧 Email</td>
            <td style="padding: 12px 16px; color: #111827;">{to_email}</td>
          </tr>
          <tr style="background: #fef2f2;">
            <td style="padding: 12px 16px; color: #6b7280; font-weight: bold;">🕐 Time</td>
            <td style="padding: 12px 16px; color: #111827;">{time_str}</td>
          </tr>
        </table>

        <!-- Intruder Image -->
        {"<p style='font-weight: bold; color: #374151;'>📸 Intruder Captured:</p><img src='cid:intruder_img' style='max-width: 300px; border-radius: 10px; border: 2px solid #dc2626; display: block; margin: 10px 0;'/>" if has_image else "<p style='color: #6b7280;'>📸 No image captured for this alert.</p>"}

        <!-- Warning -->
        <div style="background: #fef2f2; border: 1px solid #fecaca;
                    border-radius: 8px; padding: 16px; margin-top: 20px;">
          <p style="color: #dc2626; font-weight: bold; margin: 0;">
            🔐 Action Required
          </p>
          <p style="color: #374151; margin: 8px 0 0 0;">
            If this was not you, please change your password immediately
            and contact your system administrator.
          </p>
        </div>

      </div>

      <!-- Footer -->
      <div style="background: #f3f4f6; padding: 16px; text-align: center;
                  border-radius: 0 0 12px 12px;
                  border: 1px solid #e5e7eb; border-top: none;">
        <p style="color: #9ca3af; font-size: 12px; margin: 0;">
          This is an automated alert from WorkGuard Workspace Monitor.
        </p>
      </div>

    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    # Attach intruder image if available
    if has_image:
        try:
            img_bytes = base64.b64decode(intruder_image_b64)
            img_part  = MIMEImage(img_bytes, name="intruder.jpg")
            img_part.add_header("Content-ID", "<intruder_img>")
            img_part.add_header(
                "Content-Disposition", "inline", filename="intruder.jpg"
            )
            msg.attach(img_part)
            print("[Email] Intruder image attached")
        except Exception as e:
            print(f"[Email] ⚠️ Could not attach image: {e}")

    # ── Send Email ────────────────────────────────────────────────────────────
    try:
        print(f"[Email] Connecting to {EMAIL_HOST}:{EMAIL_PORT}...")

        async with aiosmtplib.SMTP(
            hostname  = EMAIL_HOST,
            port      = EMAIL_PORT,
            start_tls = True,
            timeout   = 30
        ) as smtp:
            print(f"[Email] Logging in as {EMAIL_USER}...")
            await smtp.login(EMAIL_USER, EMAIL_PASS)
            print("[Email] Login successful, sending...")
            await smtp.send_message(msg)

        print(f"[Email] ✅ Alert email sent successfully to {to_email}")

    except aiosmtplib.SMTPAuthenticationError:
        print("[Email] ❌ Authentication failed!")
        print("[Email]    Check EMAIL_USER and EMAIL_PASS in .env")
        print("[Email]    Make sure you are using Gmail App Password, not regular password")
        print("[Email]    Generate App Password at: https://myaccount.google.com/apppasswords")

    except aiosmtplib.SMTPConnectError:
        print("[Email] ❌ Could not connect to Gmail SMTP server")
        print("[Email]    Check your internet connection")
        print(f"[Email]    Host: {EMAIL_HOST}, Port: {EMAIL_PORT}")

    except TimeoutError:
        print("[Email] ❌ Connection timed out")
        print("[Email]    Check internet connection and firewall settings")

    except Exception as e:
        print(f"[Email] ❌ Unexpected error: {e}")
        print(traceback.format_exc())