from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import DB_URL

engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)
    equipment = Column(String(300), default="")
    location = Column(String(200), default="")
    is_active = Column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, nullable=False)
    user_name = Column(String(50), nullable=False)
    user_id = Column(String(50), default="")
    title = Column(String(200), default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="active")
    note = Column(Text, default="")


class MeetingMinutes(Base):
    """会议纪要表：存储生成的结构化会议纪要。"""
    __tablename__ = "meeting_minutes"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, nullable=False)
    room_name = Column(String(50), default="")
    title = Column(String(200), default="")
    host = Column(String(50), default="")
    attendees = Column(String(500), default="")
    meeting_date = Column(DateTime, nullable=False)
    start_time = Column(String(10), default="")
    end_time = Column(String(10), default="")
    summary = Column(Text, default="")
    key_points = Column(Text, default="")
    action_items = Column(Text, default="")
    next_meeting = Column(String(300), default="")
    raw_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(engine)
