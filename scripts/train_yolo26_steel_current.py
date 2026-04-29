from pathlib import Path
import shutil

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "classification_current_balanced"
MODEL = BASE_DIR / "yolo26n-cls.pt"
PROJECT = BASE_DIR / "runs" / "classify"
NAME = "steel_cls_current_balanced_v1"
EXPORT_PATH = BASE_DIR / "backend" / "models" / "yolo26-steel.pt"

model = YOLO(MODEL)
results = model.train(
    data=str(DATA_DIR),
    epochs=30,
    imgsz=224,
    batch=32,
    device="cpu",
    project=str(PROJECT),
    name=NAME,
    pretrained=True,
    patience=10,
    workers=4,
    degrees=0.0,
    translate=0.0,
    scale=0.1,
    fliplr=0.5,
    mixup=0.0,
    auto_augment="randaugment",
)

best_path = Path(results.save_dir) / "weights" / "best.pt"
EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(best_path, EXPORT_PATH)
print(f"exported_to={EXPORT_PATH.as_posix()}")
