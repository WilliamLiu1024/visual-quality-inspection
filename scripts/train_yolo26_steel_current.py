from pathlib import Path
import shutil

from ultralytics import YOLO

MODEL = 'yolo26n-cls.pt'
DATA_DIR = r'D:\05Data\visual-quality-inspection\data\classification_current_balanced'
PROJECT = 'runs/classify'
NAME = 'steel_cls_current_balanced_v1'
EXPORT_PATH = Path('backend/models/yolo26-steel.pt')

model = YOLO(MODEL)
results = model.train(
    data=DATA_DIR,
    epochs=10,
    imgsz=224,
    batch=16,
    device='cpu',
    project=PROJECT,
    name=NAME,
    pretrained=True,
    patience=4,
    workers=0,
    degrees=0.0,
    translate=0.0,
    scale=0.1,
    fliplr=0.5,
    mixup=0.0,
    auto_augment='randaugment',
)

best_path = Path(results.save_dir) / 'weights' / 'best.pt'
EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(best_path, EXPORT_PATH)
print(f'exported_to={EXPORT_PATH.as_posix()}')
