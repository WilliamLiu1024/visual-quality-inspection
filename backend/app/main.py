from contextlib import asynccontextmanager
from pathlib import Path

import cv2
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import DATA_DIR, DEFAULT_VIDEO_SOURCE, TEST_DIR

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}
from .database import Base, engine, get_db
from .detector import DetectorService
from .models import DetectionRecord
from .record_service import build_detection_response, create_detection_record
from .schemas import DetectionHistoryItem, HealthResponse, SampleDetectionResponse, SampleImageItem, VideoStartRequest, VideoStatusResponse
from .storage import deserialize_boxes, save_annotated_image, save_upload
from .video_stream import VideoStreamService
from .visualization import draw_detections


detector = DetectorService()
video_stream = VideoStreamService(detector)
ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / 'frontend'


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
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
app.mount('/test-images', StaticFiles(directory=TEST_DIR), name='test-images')


@app.get('/', include_in_schema=False)
async def index():
    return FileResponse(FRONTEND_DIR / 'index.html')


@app.get('/styles.css', include_in_schema=False)
async def styles():
    return FileResponse(FRONTEND_DIR / 'styles.css')


@app.get('/app.js', include_in_schema=False)
async def script():
    return FileResponse(FRONTEND_DIR / 'app.js')


@app.get('/api/health', response_model=HealthResponse)
async def health():
    return HealthResponse(status='ok', model_ready=detector.ready, detector_name=detector.name)


@app.get('/api/test-images', response_model=list[SampleImageItem])
async def list_test_images(limit: int = Query(default=100, ge=1, le=1000)):
    items = sorted([item for item in TEST_DIR.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS])[:limit]
    return [SampleImageItem(name=item.name, image_url=f'/test-images/{item.name}') for item in items]


@app.post('/api/test-images/{image_name}/detect', response_model=SampleDetectionResponse)
async def detect_test_image(image_name: str, db: Session = Depends(get_db)):
    image_path = TEST_DIR / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail='测试图片不存在')
    if not detector.ready:
        raise HTTPException(status_code=503, detail='模型未就绪，请确认权重已加载')

    try:
        prediction = detector.predict(str(image_path))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'测试图识别失败: {exc}') from exc

    record = create_detection_record(db, str(image_path), image_path.name, prediction)
    response = build_detection_response(record, prediction, image_url=f'/test-images/{image_path.name}')

    image = cv2.imread(str(image_path))
    annotated = draw_detections(image, prediction)
    annotated_path = save_annotated_image(annotated, prefix='test')

    return SampleDetectionResponse(**response.model_dump(), annotated_image_url=f'/uploads/{annotated_path.name}')


@app.post('/api/detect')
async def detect(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        image_path = await save_upload(file)
        prediction = detector.predict(str(image_path))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'检测失败: {exc}') from exc

    record = create_detection_record(db, str(image_path), image_path.name, prediction)
    return build_detection_response(record, prediction)


@app.post('/api/video/start', response_model=VideoStatusResponse)
async def start_video(request: VideoStartRequest):
    if not detector.ready:
        raise HTTPException(status_code=503, detail='模型未就绪，请先放置权重文件。')
    video_stream.start(request.source or DEFAULT_VIDEO_SOURCE)
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


@app.get('/api/records', response_model=list[DetectionHistoryItem])
async def records(has_defect: bool | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    query = db.query(DetectionRecord).order_by(DetectionRecord.created_at.desc())
    if has_defect is not None:
        query = query.filter(DetectionRecord.has_defect == has_defect)

    items = query.limit(limit).all()
    return [
        DetectionHistoryItem(
            id=item.id,
            image_url=f"/uploads/{item.image_name}" if Path(item.image_path).parent.name == 'uploads' else f"/test-images/{item.image_name}",
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
