# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_indexes
from routes import auth, monitor, alerts

app = FastAPI(title="WorkGuard API", version="2.0.0")

# CORS must be added BEFORE including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await create_indexes()
    print("[WorkGuard] Server started")

app.include_router(auth.router)
app.include_router(monitor.router)
app.include_router(alerts.router)

@app.get("/")
async def root():
    return {"message": "WorkGuard API Running"}