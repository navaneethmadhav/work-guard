import base64, io
import numpy as np
import cv2
from PIL import Image

def base64_to_numpy(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",")[1]
    raw = base64.b64decode(b64)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(img)

def numpy_to_base64(arr: np.ndarray) -> str:
    img = Image.fromarray(arr.astype("uint8"))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode()