import asyncio
from datetime import datetime
from typing import Dict
import numpy as np
from bson import ObjectId
from database import alerts_col, users_col
from services.face_service import FaceService
from services.email_service import send_intruder_alert
from utils.image_utils import base64_to_numpy, numpy_to_base64
from config import ALERT_COOLDOWN

face_svc        = FaceService()
last_alert_time: Dict[str, datetime] = {}


async def process_frame(user_id: str, frame_b64: str) -> dict:
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        return {"status": "error", "message": "User not found"}

    registered_encodings = [
        np.array(enc) for enc in user.get("face_encodings", [])
    ]

    try:
        frame_rgb = base64_to_numpy(frame_b64)
    except Exception as e:
        return {"status": "error", "message": f"Bad frame: {e}"}

    result = face_svc.analyze_frame(frame_rgb, registered_encodings)

    response = {
        "status":           result["status"],
        "face_count":       result["face_count"],
        "registered_found": result["registered_found"],
        "timestamp":        datetime.utcnow().isoformat(),
    }

    if result["status"] == "intruder":
        intruder_b64 = None
        if result["unknown_faces"]:
            crop        = face_svc.crop_face(frame_rgb, result["unknown_faces"][0])
            intruder_b64 = numpy_to_base64(crop)

        alert_doc = {
            "user_id":        user_id,
            "timestamp":      datetime.utcnow(),
            "intruder_image": intruder_b64,
            "face_count":     result["face_count"],
            "frame_snapshot": numpy_to_base64(frame_rgb),
        }
        await alerts_col.insert_one(alert_doc)

        last = last_alert_time.get(user_id)
        should_email = (
            last is None or
            (datetime.utcnow() - last).seconds >= ALERT_COOLDOWN
        )
        if should_email:
            last_alert_time[user_id] = datetime.utcnow()
            asyncio.create_task(
                send_intruder_alert(
                    to_email=user["email"],
                    username=user["username"],
                    timestamp=datetime.utcnow(),
                    intruder_image_b64=intruder_b64
                )
            )

        response["alert_sent"]     = should_email
        response["intruder_image"] = intruder_b64

    return response