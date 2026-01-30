"""
Court Holiday Models

Per-jurisdiction court holiday calendars for accurate business day calculations.
Supports federal, state, and local court holidays with recurring patterns.
"""

from sqlalchemy import (
    Column, String, Date, DateTime, ForeignKey, Text, Boolean, Integer,
    func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CourtHoliday(Base):
    """
    Individual court holiday entries.

    Holidays can be:
    - Fixed: Same date every year (e.g., July 4th)
    - Floating: Varies by year (e.g., Thanksgiving, Easter)
    - Observed: The observed date when holiday falls on weekend
    """
    __tablename__ = "court_holidays"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Which jurisdiction this holiday applies to
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Holiday identification
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Date information
    holiday_date = Column(Date, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)

    # Is this an observed date (when actual holiday falls on weekend)?
    is_observed = Column(Boolean, default=False)
    actual_date = Column(Date)  # The actual holiday date if different from observed

    # Holiday type
    holiday_type = Column(String(50), default="federal")  # federal, state, local, court_specific

    # Is court closed on this day?
    court_closed = Column(Boolean, default=True)

    # Additional data
    extra_data = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction")


class HolidayPattern(Base):
    """
    Recurring holiday patterns for automatic calendar generation.

    Patterns define rules for when holidays occur:
    - Fixed: month/day (e.g., 7/4 for Independence Day)
    - Floating: nth weekday of month (e.g., 4th Thursday of November)
    - Easter-relative: days before/after Easter
    - Election: rules for election day
    """
    __tablename__ = "holiday_patterns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Which jurisdiction this pattern applies to (NULL = all jurisdictions)
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="CASCADE"), index=True)

    # Holiday identification
    name = Column(String(255), nullable=False)

    # Pattern type
    pattern_type = Column(String(50), nullable=False)  # fixed, floating, easter_relative, custom

    # Pattern definition (structure depends on pattern_type)
    # Fixed: { "month": 7, "day": 4 }
    # Floating: { "month": 11, "weekday": 3, "occurrence": 4 }  # 4th Thursday of November
    # Easter-relative: { "days_offset": -2 }  # Good Friday
    pattern_definition = Column(JSONB, nullable=False)

    # Should observed date be calculated when falls on weekend?
    observe_if_weekend = Column(Boolean, default=True)

    # Federal holidays move to Friday if Saturday, Monday if Sunday
    federal_observation_rules = Column(Boolean, default=True)

    # Is court closed on this holiday?
    court_closed = Column(Boolean, default=True)

    # Holiday type
    holiday_type = Column(String(50), default="federal")

    # Is this pattern active?
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction")


class HarvestSchedule(Base):
    """
    Scheduled harvesting jobs for automatic rule updates.

    Allows users to set up recurring checks of court rule URLs
    to detect when rules change and propose updates.
    """
    __tablename__ = "harvest_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Who created this schedule
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Target jurisdiction
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), index=True)

    # URL to monitor
    url = Column(Text, nullable=False)
    name = Column(String(255))  # Friendly name for the schedule

    # Schedule configuration
    frequency = Column(String(50), nullable=False)  # daily, weekly, monthly
    day_of_week = Column(Integer)  # 0-6 for weekly schedules
    day_of_month = Column(Integer)  # 1-31 for monthly schedules

    # Content tracking
    last_content_hash = Column(String(64))
    last_checked_at = Column(DateTime(timezone=True))
    last_change_detected_at = Column(DateTime(timezone=True))

    # Harvesting options
    use_extended_thinking = Column(Boolean, default=True)
    auto_approve_high_confidence = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    error_count = Column(Integer, default=0)
    last_error = Column(Text)

    # Statistics
    total_checks = Column(Integer, default=0)
    changes_detected = Column(Integer, default=0)
    rules_harvested = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    next_run_at = Column(DateTime(timezone=True), index=True)

    # Relationships
    user = relationship("User")
    jurisdiction = relationship("Jurisdiction")
    runs = relationship("HarvestScheduleRun", back_populates="schedule", cascade="all, delete-orphan")


class HarvestScheduleRun(Base):
    """
    Individual runs of a harvest schedule.

    Tracks each execution of a scheduled harvest job.
    """
    __tablename__ = "harvest_schedule_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Parent schedule
    schedule_id = Column(String(36), ForeignKey("harvest_schedules.id", ondelete="CASCADE"), nullable=False, index=True)

    # Run status
    status = Column(String(50), nullable=False)  # pending, running, completed, failed

    # Content tracking
    content_hash = Column(String(64))
    content_changed = Column(Boolean, default=False)

    # Results
    rules_found = Column(Integer, default=0)
    proposals_created = Column(Integer, default=0)

    # Error handling
    error_message = Column(Text)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    schedule = relationship("HarvestSchedule", back_populates="runs")
