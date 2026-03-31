import json
import uuid
from pathlib import Path

import cv2
from fastapi import UploadFile

from .config import UPLOAD_DIR


async def save_upload(file: UploadFile) -> Path:
    extension = Path(file.filename or "capture.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename

    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

    await file.close()
    return destination


def save_frame(frame, prefix: str = "stream") -> Path:
    filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
    destination = UPLOAD_DIR / filename
    cv2.imwrite(str(destination), frame)
    return destination


def save_annotated_image(image, prefix: str = "annotated") -> Path:
    filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
    destination = UPLOAD_DIR / filename
    cv2.imwrite(str(destination), image)
    return destination


def serialize_boxes(boxes: list[dict]) -> str:
    return json.dumps(boxes, ensure_ascii=False)


def deserialize_boxes(boxes_json: str) -> list[dict]:
    return json.loads(boxes_json)
