from sqlalchemy.orm import Session

from .models import DetectionRecord
from .schemas import BoundingBox, DetectionResponse
from .storage import serialize_boxes


def create_detection_record(db: Session, image_path: str, image_name: str, prediction: dict) -> DetectionRecord:
    boxes = prediction.get("boxes", [])
    label = prediction.get("label", "normal")
    confidence = float(prediction.get("confidence", 0.0))
    has_defect = label == "defect"
    # 检测模型：按 boxes 计数；分类模型无 boxes，异常图计 1，正常图计 0
    defect_count = len([b for b in boxes if b["label"] == "defect"]) if boxes else (1 if has_defect else 0)

    record = DetectionRecord(
        image_name=image_name,
        image_path=image_path,
        has_defect=has_defect,
        top_confidence=confidence if has_defect else confidence,
        defect_count=defect_count,
        boxes_json=serialize_boxes(boxes),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def build_detection_response(record: DetectionRecord, prediction: dict, image_url: str | None = None) -> DetectionResponse:
    boxes = prediction.get("boxes", [])
    label = prediction.get("label", "normal")
    return DetectionResponse(
        record_id=record.id,
        image_url=image_url or f"/uploads/{record.image_name}",
        has_defect=record.has_defect,
        predicted_label=label,
        inference_task=prediction.get("task", "classify"),
        top_confidence=record.top_confidence,
        defect_count=record.defect_count,
        boxes=[BoundingBox(**box) for box in boxes],
        created_at=record.created_at,
    )
