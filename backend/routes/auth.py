# backend/routes/auth.py

from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from passlib.context import CryptContext
from database import users_col
from utils.jwt_utils import create_token
from utils.image_utils import base64_to_numpy
from services.face_service import FaceService
from datetime import datetime
import json

router  = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(
    username:    str = Form(...),
    email:       str = Form(...),
    password:    str = Form(...),
    face_images: str = Form(...)
):
    face_svc = FaceService()  # singleton — loads model once

    # Check duplicates
    if await users_col.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    if await users_col.find_one({"username": username}):
        raise HTTPException(400, "Username already taken")

    # Parse face images
    try:
        images_b64 = json.loads(face_images)
    except Exception:
        raise HTTPException(400, "Invalid face image data")

    if len(images_b64) < 3:
        raise HTTPException(400, "Capture at least 3 face images")

    # Convert base64 to numpy arrays
    images_np = []
    for b64 in images_b64:
        try:
            images_np.append(base64_to_numpy(b64))
        except Exception:
            raise HTTPException(400, "Invalid image in captured set")

    # Extract face embeddings using CNN model
    encodings = face_svc.extract_encodings_from_multiple(images_np)

    if not encodings:
        raise HTTPException(
            400,
            "No face detected in photos. "
            "Please retake in good lighting facing the camera."
        )

    # Save user to MongoDB
    user_doc = {
        "username":       username,
        "email":          email,
        "password":       pwd_ctx.hash(password[:72]),  # bcrypt 72 byte limit
        "face_encodings": [enc.tolist() for enc in encodings],
        "face_count":     len(encodings),
        "created_at":     datetime.utcnow(),
    }

    result = await users_col.insert_one(user_doc)
    token  = create_token({
        "user_id":  str(result.inserted_id),
        "username": username
    })

    return {
        "message":          "Account created successfully",
        "token":            token,
        "username":         username,
        "encodings_stored": len(encodings)
    }


@router.post("/login")
async def login(req: LoginRequest):
    user = await users_col.find_one({"email": req.email})

    if not user or not pwd_ctx.verify(req.password[:72], user["password"]):
        raise HTTPException(401, "Invalid email or password")

    token = create_token({
        "user_id":  str(user["_id"]),
        "username": user["username"]
    })

    return {
        "token":    token,
        "username": user["username"]
    }