import aiosmtplib, base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS

async def send_intruder_alert(
    to_email: str,
    username: str,
    timestamp: datetime,
    intruder_image_b64: str = None
):
    msg           = MIMEMultipart("related")
    msg["From"]   = EMAIL_USER
    msg["To"]     = to_email
    msg["Subject"]= "⚠️ Security Alert: Unauthorized Access Detected"

    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;">
      <div style="background:#dc2626;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0;">⚠️ Security Alert — WorkGuard</h2>
      </div>
      <div style="background:#f9fafb;padding:20px;border:1px solid #e5e7eb;">
        <p>Hello <strong>{username}</strong>,</p>
        <p>An unauthorized person was detected on your workspace account.</p>
        <p><strong>Time:</strong> {time_str}</p>
        {"<p><strong>Intruder Image:</strong></p><img src='cid:intruder' style='max-width:300px;border-radius:8px;'/>" if intruder_image_b64 else ""}
        <p style="color:#dc2626;"><strong>Please change your password if this was not you.</strong></p>
      </div>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))

    if intruder_image_b64:
        try:
            img_data = base64.b64decode(intruder_image_b64)
            img_part = MIMEImage(img_data, name="intruder.jpg")
            img_part.add_header("Content-ID", "<intruder>")
            img_part.add_header("Content-Disposition", "inline")
            msg.attach(img_part)
        except Exception as e:
            print(f"[Email] Image attach failed: {e}")

    try:
        async with aiosmtplib.SMTP(
            hostname=EMAIL_HOST, port=EMAIL_PORT, start_tls=True
        ) as smtp:
            await smtp.login(EMAIL_USER, EMAIL_PASS)
            await smtp.send_message(msg)
        print(f"[Email] Alert sent to {to_email}")
    except Exception as e:
        print(f"[Email] Send failed: {e}")