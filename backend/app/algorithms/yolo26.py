from pathlib import Path

from .base import BaseAlgorithm
from ..config import MODEL_PATH

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None


class Yolo26Algorithm(BaseAlgorithm):
    name = "yolo26"

    def __init__(self, model_path: Path | None = None):
        self.model_path = model_path or MODEL_PATH
        self.model = None
        self.label_aliases = {
            "0": "defect",
            "1": "normal",
            "defect": "defect",
            "normal": "normal",
            "异常": "defect",
            "正常": "normal",
            "有缺陷": "defect",
            "无缺陷": "normal",
        }
        self._load()

    def _load(self) -> None:
        if YOLO is None or not self.model_path.exists():
            self.model = None
            return
        self.model = YOLO(str(self.model_path))

    @property
    def ready(self) -> bool:
        return self.model is not None

    def predict(self, image_source) -> dict:
        if not self.model:
            raise RuntimeError(f"YOLO 模型未就绪，请确认权重文件存在: {self.model_path}")

        if getattr(self.model, 'task', None) == 'classify':
            result = self.model.predict(source=image_source, verbose=False)[0]
            top1 = int(result.probs.top1)
            label = result.names[top1]
            label = self.label_aliases.get(str(label), str(label))
            confidence = float(result.probs.top1conf)
            return {
                "task": "classify",
                "label": label,
                "confidence": confidence,
                "boxes": [],
            }

        results = self.model.predict(source=image_source, verbose=False, conf=0.25)
        detections: list[dict] = []
        for result in results:
            names = result.names or {}
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                label = names.get(cls_id, str(cls_id))
                label = self.label_aliases.get(str(label), str(label))
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                detections.append(
                    {
                        "label": label,
                        "confidence": confidence,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    }
                )

        defect_boxes = [item for item in detections if item["label"] == "defect"]
        confidence = max((item["confidence"] for item in defect_boxes), default=0.0)
        label = "defect" if defect_boxes else "normal"
        return {
            "task": "detect",
            "label": label,
            "confidence": confidence,
            "boxes": detections,
        }
