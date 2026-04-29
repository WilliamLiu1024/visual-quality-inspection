import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
from fastapi.responses import StreamingResponse

from .config import BLUR_THRESHOLD, DEFAULT_VIDEO_SOURCE, DEFECT_DIR, STREAM_INFERENCE_INTERVAL, STREAM_SAVE_INTERVAL_SECONDS, TEST_DIR
from .storage import save_frame
from .database import SessionLocal
from .record_service import create_detection_record
from .schemas import BoundingBox, VideoStatusResponse
from .visualization import draw_detections

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.m4v', '.ts', '.flv', '.wmv'}


def _is_blurry(frame, threshold: float) -> bool:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var() < threshold


class ImageSequenceCapture:
    """循环播放文件夹及其子文件夹内所有图片。"""

    def __init__(self, directory: Path, fps: float = 5.0):
        self.directory = directory
        self.fps = fps
        self.delay = 1.0 / fps
        self.images = sorted([
            f for f in directory.rglob('*')
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ])
        self.index = 0
        self.opened = bool(self.images)
        self.last_read = 0.0
        self.current_path: Path | None = None  # 当前帧对应的文件路径

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        if not self.images:
            return False, None
        now = time.time()
        if self.last_read:
            sleep_for = self.delay - (now - self.last_read)
            if sleep_for > 0:
                time.sleep(sleep_for)
        self.current_path = self.images[self.index]
        frame = cv2.imread(str(self.current_path))
        self.index = (self.index + 1) % len(self.images)
        self.last_read = time.time()
        return frame is not None, frame

    def release(self) -> None:
        self.opened = False


class LoopingVideoCapture:
    """循环播放单个视频文件。"""

    def __init__(self, video_path: Path):
        self.video_path = video_path
        self._cap = cv2.VideoCapture(str(video_path))

    def isOpened(self) -> bool:
        return self._cap.isOpened()

    def read(self):
        ok, frame = self._cap.read()
        if not ok:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        return ok, frame

    def release(self) -> None:
        self._cap.release()


class MultiVideoCapture:
    """顺序播放多个视频文件，全部播完后循环。"""

    def __init__(self, video_paths: list[Path]):
        self.video_paths = video_paths
        self.index = 0
        self._cap = cv2.VideoCapture(str(video_paths[0]))

    def isOpened(self) -> bool:
        return self._cap.isOpened()

    def read(self):
        ok, frame = self._cap.read()
        if not ok:
            self.index = (self.index + 1) % len(self.video_paths)
            self._cap.release()
            self._cap = cv2.VideoCapture(str(self.video_paths[self.index]))
            ok, frame = self._cap.read()
        return ok, frame

    def release(self) -> None:
        self._cap.release()


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
        self.latest_status = VideoStatusResponse(
            running=False, source=DEFAULT_VIDEO_SOURCE, message="视频流未启动"
        )
        self.last_saved_at = 0.0
        self.blur_filter_enabled: bool = True

    def set_blur_filter(self, enabled: bool) -> None:
        self.blur_filter_enabled = enabled

    def start(self, source: str | None = None) -> None:
        source = source or DEFAULT_VIDEO_SOURCE
        if self.running and self.source == source:
            return
        self.stop()
        self.stop_event.clear()
        self.source = source
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
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
        stop = self.stop_event

        def generate():
            while not stop.is_set():
                with self.lock:
                    frame = self.latest_jpeg
                if frame is None:
                    time.sleep(0.05)
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                time.sleep(0.04)  # 限制最高 25fps，避免空转

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    def _open_source(self, source_text: str):
        source_path = Path(source_text)

        # 直接指向一个视频文件
        if source_path.is_file() and source_path.suffix.lower() in VIDEO_EXTENSIONS:
            return LoopingVideoCapture(source_path)

        # 目录：递归查找视频文件，其次找图片（含子文件夹）
        if source_path.is_dir():
            videos = sorted([
                f for f in source_path.rglob('*')
                if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
            ])
            if videos:
                return MultiVideoCapture(videos) if len(videos) > 1 else LoopingVideoCapture(videos[0])
            return ImageSequenceCapture(source_path)

        # 兜底：使用默认测试目录
        return ImageSequenceCapture(TEST_DIR)

    def _run(self) -> None:
        self.capture = self._open_source(str(self.source))
        if not self.capture.isOpened():
            with self.lock:
                self.latest_status = VideoStatusResponse(
                    running=False,
                    source=str(self.source),
                    predicted_label="normal",
                    inference_task="classify",
                    message=f"无法打开文件源: {self.source}，请检查路径或文件是否存在",
                )
            return

        self.running = True
        frame_index = 0
        last_prediction = {"task": "classify", "label": "normal", "confidence": 0.0, "boxes": []}
        last_saved_path: str | None = None  # 记录上一次保存的图片路径，避免同一张重复保存

        while not self.stop_event.is_set():
            ok, frame = self.capture.read()
            if not ok:
                time.sleep(0.1)
                continue

            # 每帧重置，防止模糊状态跨帧残留（当 STREAM_INFERENCE_INTERVAL > 1 时尤为重要）
            blurry = False
            current_path = str(getattr(self.capture, 'current_path', None))

            frame_index += 1
            if frame_index % STREAM_INFERENCE_INTERVAL == 0 and self.detector.ready:
                blurry = self.blur_filter_enabled and _is_blurry(frame, BLUR_THRESHOLD)
                if not blurry:
                    try:
                        last_prediction = self.detector.predict(frame)
                    except Exception as exc:
                        last_prediction = {
                            "task": "classify",
                            "label": "normal",
                            "confidence": 0.0,
                            "boxes": [],
                            "message": f"检测失败: {exc}",
                        }
                    # 图片序列：每张图只保存一次（force=True 跳过时间节流）
                    # 视频文件：按时间间隔保存（force=False）
                    is_new_image = current_path != last_saved_path
                    self._save_if_needed(frame, last_prediction, force=is_new_image)
                    if is_new_image:
                        last_saved_path = current_path

            annotated = draw_detections(frame.copy(), last_prediction)
            if blurry:
                cv2.putText(annotated, "BLURRY", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2, cv2.LINE_AA)
            success, jpeg = cv2.imencode('.jpg', annotated)
            if not success:
                continue

            status_message = "图像模糊，跳过检测" if blurry else last_prediction.get('message', '检测正常运行中')
            with self.lock:
                self.latest_jpeg = jpeg.tobytes()
                self.latest_status = VideoStatusResponse(
                    running=True,
                    source=str(self.source),
                    has_defect=last_prediction.get('label') == 'defect',
                    predicted_label=last_prediction.get('label', 'normal'),
                    inference_task=last_prediction.get('task', 'classify'),
                    top_confidence=float(last_prediction.get('confidence', 0.0)),
                    defect_count=len([
                        b for b in last_prediction.get('boxes', []) if b['label'] == 'defect'
                    ]),
                    boxes=[BoundingBox(**b) for b in last_prediction.get('boxes', [])],
                    last_updated=datetime.utcnow(),
                    message=status_message,
                )

        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.running = False

    def _save_if_needed(self, frame, prediction: dict, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last_saved_at < STREAM_SAVE_INTERVAL_SECONDS:
            return
        try:
            is_defect = prediction.get('label') == 'defect'
            if is_defect:
                annotated = draw_detections(frame.copy(), prediction)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
                defect_filename = f"defect_{ts}.jpg"
                defect_path = DEFECT_DIR / defect_filename
                cv2.imwrite(str(defect_path), annotated)
                image_path = defect_path
            else:
                image_path = save_frame(frame, prefix='stream')
            db = SessionLocal()
            try:
                create_detection_record(db, str(image_path), image_path.name, prediction)
            finally:
                db.close()
            self.last_saved_at = now
        except Exception:
            pass  # 保存失败不影响主检测流程
