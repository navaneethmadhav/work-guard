from fastapi import APIRouter, Depends, HTTPException, Header
from database import alerts_col
from utils.jwt_utils import decode_token
from bson import ObjectId

router = APIRouter(prefix="/alerts", tags=["alerts"])

async def get_user(authorization: str = Header(...)):
    token   = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    return payload

@router.get("/")
async def list_alerts(limit: int = 20, user=Depends(get_user)):
    cursor = alerts_col.find(
        {"user_id": user["user_id"]},
        {"frame_snapshot": 0}
    ).sort("timestamp", -1).limit(limit)

    alerts = []
    async for a in cursor:
        a["_id"]       = str(a["_id"])
        a["timestamp"] = a["timestamp"].isoformat()
        alerts.append(a)
    return {"alerts": alerts}

@router.get("/{alert_id}")
async def get_alert(alert_id: str, user=Depends(get_user)):
    a = await alerts_col.find_one({
        "_id": ObjectId(alert_id), "user_id": user["user_id"]
    })
    if not a:
        raise HTTPException(404, "Not found")
    a["_id"]       = str(a["_id"])
    a["timestamp"] = a["timestamp"].isoformat()
    return a

@router.delete("/{alert_id}")
async def delete_alert(alert_id: str, user=Depends(get_user)):
    r = await alerts_col.delete_one({
        "_id": ObjectId(alert_id), "user_id": user["user_id"]
    })
    if r.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"message": "Deleted"}