from sqlalchemy import Column, String, Date, Time, DateTime, ForeignKey, Text, func, JSON
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50))  # deadline, hearing, conference, filing
    title = Column(String(500), nullable=False)
    description = Column(Text)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time)
    event_end_time = Column(Time)
    location = Column(String(500))
    attendees = Column(JSON)
    reminders = Column(JSON)  # Array of reminder times
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="calendar_events")
    deadline = relationship("Deadline", back_populates="calendar_events")
    user = relationship("User", back_populates="calendar_events")
