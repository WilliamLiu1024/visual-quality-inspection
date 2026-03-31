import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
from fastapi.responses import StreamingResponse

from .config import DEFAULT_VIDEO_SOURCE, STREAM_INFERENCE_INTERVAL, STREAM_SAVE_INTERVAL_SECONDS, TEST_DIR
from .database import SessionLocal
from .record_service import create_detection_record
from .schemas import BoundingBox, VideoStatusResponse
from .storage import save_frame
from .visualization import draw_detections


class ImageSequenceCapture:
    def __init__(self, directory: Path, fps: float = 5.0):
        self.directory = directory
        self.fps = fps
        self.delay = 1.0 / fps
        patterns = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp', '*.tif', '*.tiff']
        self.images = sorted([image for pattern in patterns for image in directory.glob(pattern)])
        self.index = 0
        self.opened = bool(self.images)
        self.last_read = 0.0

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.images:
            return False, None
        now = time.time()
        if self.last_read:
            sleep_for = self.delay - (now - self.last_read)
            if sleep_for > 0:
                time.sleep(sleep_for)
        image_path = self.images[self.index]
        frame = cv2.imread(str(image_path))
        self.index = (self.index + 1) % len(self.images)
        self.last_read = time.time()
        return frame is not None, frame

    def release(self):
        self.opened = False


class VideoStreamService:
    def __init__(self, detector):
        self.detector = detector
        self.capture = None
        self.thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.running = False
        self.source = None
        self.latest_jpeg = None
        self.latest_status = VideoStatusResponse(running=False, source=DEFAULT_VIDEO_SOURCE, message="视频流未启动")
        self.last_saved_at = 0.0

    def start(self, source: str | None = None):
        source = source or DEFAULT_VIDEO_SOURCE
        if self.running and self.source == source:
            return
        self.stop()
        self.stop_event.clear()
        self.source = source
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.running = False
        with self.lock:
            self.latest_status = VideoStatusResponse(
                running=False,
                source=self.source,
                predicted_label="normal",
                inference_task="classify",
                message="视频流已停止",
            )

    def get_status(self) -> VideoStatusResponse:
        with self.lock:
            return self.latest_status.model_copy(deep=True)

    def stream(self):
        def generate():
            while True:
                with self.lock:
                    frame = self.latest_jpeg
                if frame is None:
                    time.sleep(0.1)
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    def _open_source(self, source_text: str):
        source_path = Path(source_text)
        if source_path.is_dir():
            return ImageSequenceCapture(source_path)
        if source_text.lower() == 'data/test':
            return ImageSequenceCapture(TEST_DIR)
        source = int(source_text) if str(source_text).isdigit() else source_text
        return cv2.VideoCapture(source)

    def _run(self):
        self.capture = self._open_source(str(self.source))
        if not self.capture.isOpened():
            with self.lock:
                self.latest_status = VideoStatusResponse(
                    running=False,
                    source=str(self.source),
                    predicted_label="normal",
                    inference_task="classify",
                    message=f"无法打开视频源: {self.source}",
                )
            return

        self.running = True
        frame_index = 0
        last_prediction = {"task": "classify", "label": "normal", "confidence": 0.0, "boxes": []}

        while not self.stop_event.is_set():
            ok, frame = self.capture.read()
            if not ok:
                time.sleep(0.1)
                continue

            frame_index += 1
            if frame_index % STREAM_INFERENCE_INTERVAL == 0 and self.detector.ready:
                try:
                    last_prediction = self.detector.predict(frame)
                    self._save_if_needed(frame, last_prediction)
                except Exception as exc:
                    last_prediction = {
                        "task": "classify",
                        "label": "normal",
                        "confidence": 0.0,
                        "boxes": [],
                        "message": f"检测失败: {exc}",
                    }

            annotated = draw_detections(frame.copy(), last_prediction)
            success, jpeg = cv2.imencode('.jpg', annotated)
            if not success:
                continue

            with self.lock:
                self.latest_jpeg = jpeg.tobytes()
                self.latest_status = VideoStatusResponse(
                    running=True,
                    source=str(self.source),
                    has_defect=last_prediction.get('label') == 'defect',
                    predicted_label=last_prediction.get('label', 'normal'),
                    inference_task=last_prediction.get('task', 'classify'),
                    top_confidence=float(last_prediction.get('confidence', 0.0)),
                    defect_count=len([item for item in last_prediction.get('boxes', []) if item['label'] == 'defect']),
                    boxes=[BoundingBox(**box) for box in last_prediction.get('boxes', [])],
                    last_updated=datetime.utcnow(),
                    message=last_prediction.get('message', '检测正常运行中'),
                )

        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.running = False

    def _save_if_needed(self, frame, prediction: dict):
        if prediction.get('label') != 'defect':
            return
        now = time.time()
        if now - self.last_saved_at < STREAM_SAVE_INTERVAL_SECONDS:
            return
        image_path = save_frame(frame, prefix='stream')
        db = SessionLocal()
        try:
            create_detection_record(db, str(image_path), image_path.name, prediction)
        finally:
            db.close()
        self.last_saved_at = now
