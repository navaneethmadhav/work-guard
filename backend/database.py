from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, DB_NAME

client     = AsyncIOMotorClient(MONGODB_URI)
db         = client[DB_NAME]
users_col  = db["users"]
alerts_col = db["alerts"]

async def create_indexes():
    await users_col.create_index("email",    unique=True)
    await users_col.create_index("username", unique=True)
    await alerts_col.create_index("user_id")
    await alerts_col.create_index("timestamp")