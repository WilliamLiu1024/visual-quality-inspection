from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    image_name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    has_defect: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    top_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    defect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    boxes_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
