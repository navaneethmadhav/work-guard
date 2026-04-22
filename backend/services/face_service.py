import numpy as np
import cv2
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # suppress TF logs

from deepface import DeepFace
from typing import List
from config import SIMILARITY_THRESHOLD


class FaceService:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        print("[FaceService] Initializing DeepFace...")
        # Model name — Facenet gives best accuracy/speed balance on CPU
        # Options: "VGG-Face", "Facenet", "Facenet512", "OpenFace", "ArcFace"
        self.model_name    = "Facenet"
        self.detector      = "opencv"   # face detector backend
        self.distance_metric = "cosine" # cosine | euclidean
        self._initialized  = True
        print(f"[FaceService] Ready — model: {self.model_name}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _numpy_to_tempfile(self, img_rgb: np.ndarray) -> str:
        """
        Save numpy array as a temp jpg file.
        DeepFace works best with file paths or BGR arrays.
        """
        import tempfile
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        cv2.imwrite(tmp.name, img_bgr)
        return tmp.name

    def _get_embedding(self, img_rgb: np.ndarray):
        """
        Get face embedding vector using DeepFace + Facenet model.
        Returns 128-d numpy array or None if no face detected.
        """
        try:
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            result = DeepFace.represent(
                img_path      = img_bgr,
                model_name    = self.model_name,
                detector_backend = self.detector,
                enforce_detection = False  # don't crash if no face found
            )
            if result and len(result) > 0:
                return np.array(result[0]["embedding"])
            return None
        except Exception as e:
            print(f"[FaceService] Embedding error: {e}")
            return None

    def _cosine_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Cosine distance between two embedding vectors. Lower = more similar."""
        dot    = np.dot(emb1, emb2)
        norm   = np.linalg.norm(emb1) * np.linalg.norm(emb2)
        if norm == 0:
            return 1.0
        return 1.0 - (dot / norm)

    def detect_faces(self, frame_rgb: np.ndarray) -> list:
        """
        Detect face bounding boxes using OpenCV Haar Cascade.
        Returns list of (top, right, bottom, left) tuples.
        """
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )
        locations = []
        for (x, y, w, h) in faces:
            locations.append((y, x + w, y + h, x))
        return locations

    # ── Registration ──────────────────────────────────────────────────────────

    def extract_encodings_from_multiple(
        self,
        images: List[np.ndarray]
    ) -> List[np.ndarray]:
        """
        Extract face embeddings from multiple registration photos.
        Called during signup. More images = better recognition.
        Returns list of embedding vectors.
        """
        encodings = []
        for i, img in enumerate(images):
            emb = self._get_embedding(img)
            if emb is not None:
                encodings.append(emb)
                print(f"[FaceService] Registration image {i+1}: embedding extracted")
            else:
                print(f"[FaceService] Registration image {i+1}: no face detected, skipped")

        print(f"[FaceService] Total encodings stored: {len(encodings)}")
        return encodings

    # ── Monitoring ────────────────────────────────────────────────────────────

    def analyze_frame(
        self,
        frame_rgb: np.ndarray,
        registered_encodings: List[np.ndarray]
    ) -> dict:
        """
        Analyze a webcam frame against registered face encodings.

        Rules:
        - No face detected           → status: no_face
        - Registered user present    → status: clear
          (safe even if other people also in frame)
        - Only unknown face(s)       → status: intruder
        """
        # Step 1 — detect face locations
        locations = self.detect_faces(frame_rgb)

        if not locations:
            return {
                "status":           "no_face",
                "registered_found": False,
                "unknown_faces":    [],
                "all_locations":    [],
                "face_count":       0
            }

        registered_found = False
        unknown_faces    = []

        # Step 2 — for each detected face, get embedding and compare
        for location in locations:
            top, right, bottom, left = location

            # Crop the face from frame
            face_crop = frame_rgb[top:bottom, left:right]
            if face_crop.size == 0:
                continue

            # Get embedding for this face using DeepFace
            live_emb = self._get_embedding(face_crop)
            if live_emb is None:
                unknown_faces.append(location)
                continue

            if not registered_encodings:
                unknown_faces.append(location)
                continue

            # Step 3 — compare against all registered embeddings
            distances = [
                self._cosine_distance(live_emb, reg_emb)
                for reg_emb in registered_encodings
            ]
            min_distance = min(distances)

            # Cosine distance threshold — lower = stricter
            # 0.3 works well for Facenet cosine distance
            cosine_threshold = 0.3

            if min_distance <= cosine_threshold:
                registered_found = True
            else:
                unknown_faces.append(location)

        # Step 4 — determine final status
        if registered_found:
            status = "clear"      # registered user present — workspace safe
        elif unknown_faces:
            status = "intruder"   # only unknown faces detected
        else:
            status = "clear"

        return {
            "status":           status,
            "registered_found": registered_found,
            "unknown_faces":    unknown_faces,
            "all_locations":    locations,
            "face_count":       len(locations)
        }

    # ── Face Crop ─────────────────────────────────────────────────────────────

    def crop_face(
        self,
        frame_rgb: np.ndarray,
        location: tuple,
        padding: int = 20
    ) -> np.ndarray:
        """Crop face from frame with padding. Used to save intruder image."""
        top, right, bottom, left = location
        h, w = frame_rgb.shape[:2]
        return frame_rgb[
            max(0, top  - padding) : min(h, bottom + padding),
            max(0, left - padding) : min(w, right  + padding)
        ]