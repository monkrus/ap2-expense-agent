"""
Usage Tracking Models for billing metering.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from .models import Base


class UsageEvent(Base):
    """
    Track individual usage events for metered billing

    Examples:
    - AI categorization: event_type='ai_categorizations', quantity=1
    - AP2 transaction: event_type='ap2_transactions', quantity=1
    - Receipt OCR: event_type='receipt_ocr', quantity=1
    """

    __tablename__ = "usage_events"

    id = Column(String(36), primary_key=True)
    organization_id = Column(
        String(36),
        ForeignKey(
            "organizations.id", ondelete="RESTRICT"
        ),  # SAFEGUARD: Preserve billing history
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    metadata = Column(JSON, nullable=True)  # Additional event data
    occurred_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    organization = relationship("Organization", back_populates="usage_events")

    def __repr__(self):
        return (
            f"<UsageEvent(id={self.id}, org={self.organization_id}, "
            f"type={self.event_type}, qty={self.quantity})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "event_type": self.event_type,
            "quantity": self.quantity,
            "metadata": self.metadata,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BillingEvent(Base):
    """
    Track billing events (overages, credits, etc.)

    Used for:
    - Usage overages (when customer exceeds tier limits)
    - Credits (refunds, discounts)
    - One-time charges
    """

    __tablename__ = "billing_events"

    id = Column(String(36), primary_key=True)
    organization_id = Column(
        String(36),
        ForeignKey(
            "organizations.id", ondelete="RESTRICT"
        ),  # SAFEGUARD: Preserve billing history
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False)  # 'usage_overage', 'credit', etc.
    amount = Column(Numeric(10, 2), nullable=False)  # Dollar amount
    currency = Column(String(3), nullable=False, default="USD")
    metadata = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    processed = Column(Boolean, nullable=False, default=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    organization = relationship("Organization", back_populates="billing_events")

    def __repr__(self):
        return (
            f"<BillingEvent(id={self.id}, org={self.organization_id}, "
            f"type={self.event_type}, amount=${self.amount})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "event_type": self.event_type,
            "amount": float(self.amount),
            "currency": self.currency,
            "metadata": self.metadata,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "processed": self.processed,
            "processed_at": (
                self.processed_at.isoformat() if self.processed_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UsageReportingLog(Base):
    """
    Log of usage reports sent for billing

    Tracks what we've reported to prevent duplicate reporting
    and enable retry logic for failed reports
    """

    __tablename__ = "usage_reporting_log"

    id = Column(String(36), primary_key=True)
    organization_id = Column(
        String(36),
        ForeignKey(
            "organizations.id", ondelete="RESTRICT"
        ),  # SAFEGUARD: Preserve billing history
        nullable=False,
        index=True,
    )
    report_date = Column(Date, nullable=False, index=True)
    usage_data = Column(JSON, nullable=False)  # What was reported
    reported_at = Column(DateTime, nullable=False)
    status = Column(
        String(20), nullable=False, index=True
    )  # 'success', 'failed', 'pending'
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Ensure we don't report the same data twice
    __table_args__ = (
        UniqueConstraint("organization_id", "report_date", name="uq_usage_report"),
    )

    # Relationship
    organization = relationship("Organization", back_populates="usage_reporting_logs")

    def __repr__(self):
        return (
            f"<UsageReportingLog(id={self.id}, org={self.organization_id}, "
            f"date={self.report_date}, status={self.status})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "usage_data": self.usage_data,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Add relationships to Organization model
# These should be added to backend/src/models.py in the Organization class:
"""
# Add these to Organization class in models.py:

from .models_usage import UsageEvent, BillingEvent, UsageReportingLog

class Organization(Base):
    # ... existing fields ...

    # Usage tracking relationships
    usage_events = relationship(
        "UsageEvent",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    billing_events = relationship(
        "BillingEvent",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    usage_reporting_logs = relationship(
        "UsageReportingLog",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
"""
