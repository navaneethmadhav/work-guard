# backend/services/monitor_service.py

import asyncio
from datetime  import datetime
from typing    import Dict
import numpy   as np
from bson      import ObjectId

from database              import alerts_col, users_col
from services.face_service import FaceService
from services.email_service import send_intruder_alert
from utils.image_utils     import base64_to_numpy, numpy_to_base64
from config                import ALERT_COOLDOWN

face_svc = FaceService()

# Tracks last alert time per user to prevent email spam
last_alert_time: Dict[str, datetime] = {}


async def process_frame(user_id: str, frame_b64: str) -> dict:
    """
    Main monitoring pipeline — called for every frame received over WebSocket.

    Steps:
    1. Load user + their registered face encodings from MongoDB
    2. Convert base64 frame to numpy array
    3. Run face analysis using FaceService (DeepFace)
    4. If intruder detected:
       a. Save alert + intruder image to MongoDB
       b. Send email alert (with cooldown)
    5. Return result to frontend via WebSocket
    """

    # ── Load user from DB ─────────────────────────────────────────────────────
    try:
        user = await users_col.find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        print(f"[Monitor] DB error fetching user: {e}")
        return {"status": "error", "message": "Database error"}

    if not user:
        return {"status": "error", "message": "User not found"}

    # ── Load registered face encodings ────────────────────────────────────────
    registered_encodings = []
    for enc_list in user.get("face_encodings", []):
        try:
            registered_encodings.append(np.array(enc_list))
        except Exception:
            continue

    if not registered_encodings:
        print(f"[Monitor] ⚠️ User {user_id} has no face encodings stored")

    # ── Convert frame ─────────────────────────────────────────────────────────
    try:
        frame_rgb = base64_to_numpy(frame_b64)
    except Exception as e:
        return {"status": "error", "message": f"Invalid frame: {e}"}

    # ── Analyze frame ─────────────────────────────────────────────────────────
    result = face_svc.analyze_frame(frame_rgb, registered_encodings)

    response = {
        "status":           result["status"],
        "face_count":       result["face_count"],
        "registered_found": result["registered_found"],
        "timestamp":        datetime.utcnow().isoformat(),
    }

    # ── Handle intruder ───────────────────────────────────────────────────────
    if result["status"] == "intruder":
        print(f"[Monitor] 🚨 INTRUDER detected for user {user['username']}")

        # Crop intruder face image
        intruder_b64 = None
        if result["unknown_faces"]:
            try:
                crop         = face_svc.crop_face(frame_rgb, result["unknown_faces"][0])
                intruder_b64 = numpy_to_base64(crop)
            except Exception as e:
                print(f"[Monitor] Could not crop intruder face: {e}")

        # Save alert to MongoDB
        try:
            alert_doc = {
                "user_id":        user_id,
                "timestamp":      datetime.utcnow(),
                "intruder_image": intruder_b64,
                "face_count":     result["face_count"],
                "frame_snapshot": numpy_to_base64(frame_rgb),
            }
            await alerts_col.insert_one(alert_doc)
            print(f"[Monitor] Alert saved to database")
        except Exception as e:
            print(f"[Monitor] Failed to save alert: {e}")

        # ── Email alert with cooldown ─────────────────────────────────────────
        now       = datetime.utcnow()
        last_time = last_alert_time.get(user_id)

        # Calculate seconds since last email
        seconds_since_last = (
            (now - last_time).total_seconds()
            if last_time else float("inf")
        )

        print(
            f"[Monitor] Last email: "
            f"{'never' if last_time is None else f'{seconds_since_last:.0f}s ago'} "
            f"(cooldown: {ALERT_COOLDOWN}s)"
        )

        should_send_email = seconds_since_last >= ALERT_COOLDOWN

        if should_send_email:
            last_alert_time[user_id] = now
            print(f"[Monitor] Sending alert email to {user['email']}...")

            # Send email directly with await so errors are visible
            await send_intruder_alert(
                to_email           = user["email"],
                username           = user["username"],
                timestamp          = now,
                intruder_image_b64 = intruder_b64
            )
        else:
            remaining = ALERT_COOLDOWN - seconds_since_last
            print(
                f"[Monitor] Email cooldown active — "
                f"next email in {remaining:.0f} seconds"
            )

        response["alert_sent"]     = should_send_email
        response["intruder_image"] = intruder_b64

    # ── Handle no face ────────────────────────────────────────────────────────
    elif result["status"] == "no_face":
        print(f"[Monitor] ⚠️ No face detected for user {user['username']}")

    return response