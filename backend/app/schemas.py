from datetime import datetime

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionResponse(BaseModel):
    record_id: int
    image_url: str | None = None
    has_defect: bool
    predicted_label: str
    inference_task: str
    top_confidence: float
    defect_count: int
    boxes: list[BoundingBox]
    created_at: datetime


class SampleImageItem(BaseModel):
    name: str
    image_url: str


class SampleDetectionResponse(DetectionResponse):
    annotated_image_url: str


class DetectionHistoryItem(BaseModel):
    id: int
    image_url: str | None = None
    has_defect: bool
    predicted_label: str
    inference_task: str
    top_confidence: float
    defect_count: int
    boxes: list[BoundingBox]
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    model_ready: bool
    detector_name: str
    source_dir: str


class VideoStatusResponse(BaseModel):
    running: bool
    source: str | None = None
    has_defect: bool = False
    predicted_label: str = "normal"
    inference_task: str = "classify"
    top_confidence: float = 0.0
    defect_count: int = 0
    boxes: list[BoundingBox] = []
    last_updated: datetime | None = None
    message: str = ""
