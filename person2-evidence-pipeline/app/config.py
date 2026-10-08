import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("EVIDENCE_DATA_DIR", BASE_DIR / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://localhost:8000")
PERSON3_EVALUATION_URL = os.getenv("PERSON3_EVALUATION_URL")
PERSON3_TIMEOUT_SECONDS = float(os.getenv("PERSON3_TIMEOUT_SECONDS", "10"))
