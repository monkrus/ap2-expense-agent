"""
Approval Policy Models
Defines rules for automated expense approval
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class ApprovalPolicy(Base):
    """
    Approval Policy: Defines rules for automatic expense approval

    Configurable by organization owners/admins to streamline expense processing
    """

    __tablename__ = "approval_policies"

    # Primary key
    id = Column(String, primary_key=True)
    organization_id = Column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    # Policy details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(
        Integer, nullable=False, default=0
    )  # Higher priority checked first
    is_active = Column(Boolean, nullable=False, default=True)

    # Auto-approval settings
    auto_approve = Column(Boolean, nullable=False, default=False)
    require_receipt = Column(Boolean, nullable=False, default=True)
    notify_on_auto_approve = Column(Boolean, nullable=False, default=True)

    # Conditions (flexible JSON structure)
    # Example:
    # {
    #   "categories": ["Meals", "Office Supplies"],
    #   "vendors": ["Starbucks", "Amazon"],
    #   "user_ids": ["user_123", "user_456"],
    #   "user_roles": ["EMPLOYEE"],
    #   "exclude_vendors": ["Casino", "Bar"],
    #   "min_amount": 5.00,
    #   "days_of_week": [1, 2, 3, 4, 5],  # Mon-Fri only
    #   "time_range": {"start": "09:00", "end": "18:00"},
    #   "require_manager_approval_above": 100.00
    # }
    conditions = Column(JSON, nullable=True)

    # Limits
    max_amount_per_expense = Column(Numeric(10, 2), nullable=True)
    daily_limit_per_user = Column(Numeric(10, 2), nullable=True)
    monthly_limit_per_user = Column(Numeric(10, 2), nullable=True)
    yearly_limit_per_user = Column(Numeric(10, 2), nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by = Column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by = Column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    organization = relationship("Organization", back_populates="approval_policies")
    expenses = relationship(
        "Expense",
        back_populates="approval_policy",
        foreign_keys="Expense.approval_policy_id",
    )
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    def __repr__(self):
        return f"<ApprovalPolicy {self.id} - {self.name} (Org: {self.organization_id})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "is_active": self.is_active,
            "auto_approve": self.auto_approve,
            "require_receipt": self.require_receipt,
            "notify_on_auto_approve": self.notify_on_auto_approve,
            "conditions": self.conditions or {},
            "limits": {
                "max_amount_per_expense": (
                    float(self.max_amount_per_expense)
                    if self.max_amount_per_expense
                    else None
                ),
                "daily_limit_per_user": (
                    float(self.daily_limit_per_user)
                    if self.daily_limit_per_user
                    else None
                ),
                "monthly_limit_per_user": (
                    float(self.monthly_limit_per_user)
                    if self.monthly_limit_per_user
                    else None
                ),
                "yearly_limit_per_user": (
                    float(self.yearly_limit_per_user)
                    if self.yearly_limit_per_user
                    else None
                ),
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }


# Update Organization model to include approval_policies relationship
# This would be added to models.py:
# approval_policies = relationship("ApprovalPolicy", back_populates="organization", cascade="all, delete-orphan")

# Update Expense model to include approval policy tracking
# This would be added to models.py:
# auto_approved = Column(Boolean, nullable=False, default=False)
# approval_policy_id = Column(String, ForeignKey("approval_policies.id", ondelete="SET NULL"), nullable=True)
# approval_policy = relationship("ApprovalPolicy", foreign_keys=[approval_policy_id])
