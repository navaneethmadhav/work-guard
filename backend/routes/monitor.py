from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from utils.jwt_utils import decode_token
from services.monitor_service import process_frame
import json

router = APIRouter(tags=["monitor"])

@router.websocket("/ws/monitor")
async def monitor_ws(websocket: WebSocket, token: str = Query(...)):
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = payload["user_id"]
    await websocket.accept()
    print(f"[WS] User {user_id} connected")

    try:
        while True:
            data    = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "frame":
                result = await process_frame(user_id, message["frame"])
                await websocket.send_json(result)

            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print(f"[WS] User {user_id} disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")