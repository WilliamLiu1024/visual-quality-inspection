import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(r"D:\05Data\visual-quality-inspection\data")
UPLOAD_DIR = DATA_DIR / "uploads"
RUNTIME_DIR = DATA_DIR / "runtime"
MODEL_DIR = BASE_DIR / "backend" / "models"
TEST_DIR = DATA_DIR / "test"
ULTRALYTICS_DIR = RUNTIME_DIR / "ultralytics"
DETECTION_MODEL_PATH = MODEL_DIR / "yolo26-steel.pt"
CLASSIFICATION_MODEL_PATH = MODEL_DIR / "yolo26-steel.pt"
MODEL_PATH = CLASSIFICATION_MODEL_PATH if CLASSIFICATION_MODEL_PATH.exists() else DETECTION_MODEL_PATH
DETECTOR_NAME = os.getenv("DETECTOR_NAME", "yolo26")
DEFAULT_VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", str(TEST_DIR))
STREAM_INFERENCE_INTERVAL = int(os.getenv("STREAM_INFERENCE_INTERVAL", "5"))
STREAM_SAVE_INTERVAL_SECONDS = float(os.getenv("STREAM_SAVE_INTERVAL_SECONDS", "3"))
DATABASE_URL = f"sqlite:///{(DATA_DIR / 'database.db').as_posix()}"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEST_DIR.mkdir(parents=True, exist_ok=True)
ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_DIR))
os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(ULTRALYTICS_DIR))
