from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI         = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME             = os.getenv("DB_NAME", "workspace_monitor")
JWT_SECRET          = os.getenv("JWT_SECRET", "qwertyuiopasdfghjklzxcvbnm123456")
JWT_ALGORITHM       = "HS256"
JWT_EXPIRE_MINUTES  = 60 * 8

EMAIL_HOST          = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT          = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER          = os.getenv("EMAIL_USER", "")
EMAIL_PASS          = os.getenv("EMAIL_PASS", "")

ALERT_COOLDOWN      = int(os.getenv("ALERT_COOLDOWN_SECONDS", 60))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.5))

IMG_SIZE            = 64
EMBEDDING_MODEL_PATH = "models/embedding_model.h5"