from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import DATA_DIR, DEFAULT_VIDEO_SOURCE, DEFECT_DIR, UPLOAD_DIR
from .database import Base, SessionLocal, engine, get_db
from .detector import DetectorService
from .models import DetectionRecord
from .schemas import DetectionHistoryItem, HealthResponse, VideoStatusResponse
from .storage import deserialize_boxes
from .video_stream import VideoStreamService

NORMAL_RETENTION_DAYS = 7
DEFECT_RETENTION_DAYS = 15


def cleanup_old_records() -> None:
    now = datetime.now(timezone.utc).astimezone()
    db = SessionLocal()
    try:
        normal_cutoff = now - timedelta(days=NORMAL_RETENTION_DAYS)
        for record in db.query(DetectionRecord).filter(
            DetectionRecord.has_defect == False,
            DetectionRecord.created_at < normal_cutoff,
        ).all():
            if record.image_name:
                (UPLOAD_DIR / record.image_name).unlink(missing_ok=True)
            db.delete(record)

        defect_cutoff = now - timedelta(days=DEFECT_RETENTION_DAYS)
        for record in db.query(DetectionRecord).filter(
            DetectionRecord.has_defect == True,
            DetectionRecord.created_at < defect_cutoff,
        ).all():
            if record.image_name:
                (DEFECT_DIR / record.image_name).unlink(missing_ok=True)
            db.delete(record)

        db.commit()
    finally:
        db.close()


detector = DetectorService()
video_stream = VideoStreamService(detector)
ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / 'frontend'


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    cleanup_old_records()
    yield
    video_stream.stop()


app = FastAPI(title='Steel Defect Detection', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/uploads', StaticFiles(directory=DATA_DIR / 'uploads'), name='uploads')
app.mount('/defects', StaticFiles(directory=DATA_DIR / 'defects'), name='defects')


_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}


def _no_cache_file(path: Path, media_type: str) -> Response:
    content = path.read_bytes()
    return Response(content=content, media_type=media_type, headers=_NO_CACHE)


@app.get('/', include_in_schema=False)
async def index():
    return _no_cache_file(FRONTEND_DIR / 'index.html', 'text/html; charset=utf-8')


@app.get('/styles.css', include_in_schema=False)
async def styles():
    return _no_cache_file(FRONTEND_DIR / 'styles.css', 'text/css; charset=utf-8')


@app.get('/app.js', include_in_schema=False)
async def script():
    return _no_cache_file(FRONTEND_DIR / 'app.js', 'text/javascript; charset=utf-8')


@app.get('/api/health', response_model=HealthResponse)
async def health():
    return HealthResponse(
        status='ok',
        model_ready=detector.ready,
        detector_name=detector.name,
        source_dir=str(DEFAULT_VIDEO_SOURCE),
    )


@app.post('/api/video/start', response_model=VideoStatusResponse)
async def start_video():
    if not detector.ready:
        raise HTTPException(status_code=503, detail='模型未就绪，请先放置权重文件。')
    video_stream.start(DEFAULT_VIDEO_SOURCE)
    return video_stream.get_status()


@app.post('/api/video/stop', response_model=VideoStatusResponse)
async def stop_video():
    video_stream.stop()
    return video_stream.get_status()


@app.get('/api/video/status', response_model=VideoStatusResponse)
async def video_status():
    return video_stream.get_status()


@app.get('/api/video/stream')
async def video_feed():
    return video_stream.stream()


@app.get('/api/blur-filter')
async def get_blur_filter():
    return {"enabled": video_stream.blur_filter_enabled}


@app.post('/api/blur-filter')
async def set_blur_filter(enabled: bool = Body(..., embed=True)):
    video_stream.set_blur_filter(enabled)
    return {"enabled": video_stream.blur_filter_enabled}


@app.get('/api/records', response_model=list[DetectionHistoryItem])
async def records(
    has_defect: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(DetectionRecord).order_by(DetectionRecord.created_at.desc())
    if has_defect is not None:
        query = query.filter(DetectionRecord.has_defect == has_defect)
    items = query.limit(limit).all()
    return [
        DetectionHistoryItem(
            id=item.id,
            image_url=(
                f"/defects/{item.image_name}" if item.has_defect
                else f"/uploads/{item.image_name}" if item.image_name
                else None
            ),
            has_defect=item.has_defect,
            predicted_label='defect' if item.has_defect else 'normal',
            inference_task='classify' if item.defect_count == 0 else 'detect',
            top_confidence=item.top_confidence,
            defect_count=item.defect_count,
            boxes=deserialize_boxes(item.boxes_json),
            created_at=item.created_at,
        )
        for item in items
    ]
