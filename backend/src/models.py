import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.types import String as SQLString
from sqlalchemy.types import TypeDecorator

Base = declarative_base()


# Custom enum type that stores string values instead of names
class StringEnum(TypeDecorator):
    """
    Custom SQLAlchemy type for enums that stores the enum VALUE (not name)
    Works with both PostgreSQL native enums and SQLite CHECK constraints
    """

    impl = SQLString
    cache_ok = True

    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        # Get length from the longest enum value
        max_length = max(len(e.value) for e in enum_class)
        kwargs.setdefault("length", max_length + 10)
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """Convert enum to string value for storage"""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        # If already a string, validate it's a valid enum value
        if isinstance(value, str):
            try:
                # Try to get the enum member by value
                return self.enum_class(value).value
            except ValueError:
                # Maybe it's an enum name, try that
                try:
                    return self.enum_class[value.upper()].value
                except (KeyError, AttributeError):
                    return value  # Return as-is if can't convert
        return value

    def process_result_value(self, value, dialect):
        """Convert string value back to enum"""
        if value is None:
            return None
        try:
            return self.enum_class(value)
        except ValueError:
            return value  # Return as-is if can't convert


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"
    MANAGER = "manager"
    # ACCOUNTANT = "accountant"  # TEMPORARILY DISABLED — kept in DB ENUM


class OrganizationRole(str, enum.Enum):
    OWNER = "owner"  # Organization owner (highest level)
    ADMIN = "admin"  # Organization admin
    MANAGER = "manager"  # Organization manager
    EMPLOYEE = "employee"  # Regular employee


# ============================================================================
# Multi-Tenancy Models
# ============================================================================


class Organization(Base):
    """Organization/Tenant for multi-tenancy"""

    __tablename__ = "organizations"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(
        String(255), unique=True, nullable=False, index=True
    )  # URL-friendly identifier
    description = Column(Text, nullable=True)

    # Settings
    currency = Column(String(10), nullable=False, default="USD")
    timezone = Column(String(50), nullable=False, default="UTC")

    # Limits
    max_members = Column(Integer, nullable=False, default=1)
    max_expenses_per_month = Column(Integer, nullable=True)

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    members = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations = relationship(
        "OrganizationInvitation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    expenses = relationship(
        "Expense", back_populates="organization", cascade="all, delete-orphan"
    )
    approval_policies = relationship(
        "ApprovalPolicy", back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    """User membership in an organization"""

    __tablename__ = "organization_members"

    id = Column(String(255), primary_key=True)
    organization_id = Column(
        String(255),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        StringEnum(OrganizationRole),
        nullable=False,
        default=OrganizationRole.EMPLOYEE.value,
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    joined_at = Column(DateTime, server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", backref="organization_memberships")

    # Unique constraint: user can only be member once per organization
    from sqlalchemy import UniqueConstraint

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="unique_org_user"),
    )


class OrganizationInvitation(Base):
    """Pending invitations to join an organization"""

    __tablename__ = "organization_invitations"

    id = Column(String(255), primary_key=True)
    organization_id = Column(
        String(255),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    role = Column(
        StringEnum(OrganizationRole),
        nullable=False,
        default=OrganizationRole.EMPLOYEE.value,
    )

    # Invitation details
    invited_by = Column(String(255), ForeignKey("users.id"), nullable=False)
    token = Column(
        String(255), unique=True, nullable=False, index=True
    )  # Unique invitation token

    # Status
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, accepted, expired, revoked
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    inviter = relationship("User")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(
        StringEnum(UserRole),
        default=UserRole.EMPLOYEE.value,
        nullable=False,
    )  # Works with both PostgreSQL and SQLite
    department_id = Column(
        String(255), nullable=True, index=True
    )  # Department for filtering (managers see their department)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # 2FA fields
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    backup_codes = Column(Text, nullable=True)  # Use Text for longer strings

    # Account lockout fields
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)

    # Relations
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    device_info = Column(Text, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False)

    user = relationship("User", back_populates="password_reset_tokens")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    """
    Tamper-proof audit log with hash chain linking

    Each log entry contains:
    - previous_hash: SHA-256 hash of the previous log entry
    - entry_hash: SHA-256 hash of current entry (id + action + details + previous_hash)

    This creates a blockchain-like chain where any modification to any entry
    will break the chain and be detectable.
    """

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON stored as text
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Hash chain fields for tamper detection
    previous_hash = Column(
        String(64), nullable=True, index=True
    )  # SHA-256 of previous entry
    entry_hash = Column(
        String(64), nullable=True, index=True, default=""
    )  # SHA-256 of this entry
    sequence_number = Column(
        Integer, nullable=True, index=True, default=0
    )  # Monotonically increasing


# ============================================================================
# Expense Models
# ============================================================================


class ExpenseStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSING = "PROCESSING"
    WITHDRAWN = "WITHDRAWN"


class ExpenseCategory(str, enum.Enum):
    TRAVEL = "TRAVEL"
    MEALS = "MEALS"
    SOFTWARE = "SOFTWARE"
    OFFICE_SUPPLIES = "OFFICE_SUPPLIES"
    OTHER = "OTHER"


class Expense(Base):
    """Expense submission record"""

    __tablename__ = "expenses"

    id = Column(String(255), primary_key=True)
    organization_id = Column(
        String(255), ForeignKey("organizations.id"), nullable=False, index=True
    )  # Multi-tenancy
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    vendor = Column(String(255), nullable=False)
    category = Column(
        StringEnum(ExpenseCategory),
        nullable=False,
    )
    description = Column(Text, nullable=False)
    status = Column(
        StringEnum(ExpenseStatus),
        nullable=False,
        default=ExpenseStatus.PENDING.value,
        index=True,
    )
    date = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Approval tracking
    approved_by = Column(String(255), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Auto-approval tracking
    auto_approved = Column(Boolean, nullable=False, default=False)
    auto_approved_via = Column(String(50), nullable=True)  # "intent_mandate" or "approval_policy"
    approval_policy_id = Column(String(255), ForeignKey("approval_policies.id", ondelete="SET NULL"), nullable=True)

    # AP2 Integration
    transaction_id = Column(
        String(255), nullable=True, index=True
    )  # Payment mandate ID
    intent_mandate_id = Column(
        String(255), ForeignKey("intent_mandates.id"), nullable=True
    )
    cart_mandate_id = Column(String(255), ForeignKey("cart_mandates.id"), nullable=True)
    payment_mandate_id = Column(
        String(255), ForeignKey("payment_mandates.id"), nullable=True
    )

    # AI Analysis
    ai_analysis = Column(Text, nullable=True)  # JSON stored as text
    risk_level = Column(String(50), nullable=True)
    compliance_check = Column(Boolean, nullable=True)

    # Archive tracking
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    archived_at = Column(DateTime, nullable=True)
    archived_by = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="expenses")
    user = relationship("User", foreign_keys=[user_id], backref="expenses")
    approver = relationship("User", foreign_keys=[approved_by])
    archiver = relationship("User", foreign_keys=[archived_by])
    intent_mandate = relationship("IntentMandate", backref="expenses")
    cart_mandate = relationship("CartMandate", backref="expenses")
    payment_mandate = relationship("PaymentMandate", backref="expenses")
    approval_policy = relationship("ApprovalPolicy", foreign_keys=[approval_policy_id])
    receipts = relationship(
        "Receipt", back_populates="expense", cascade="all, delete-orphan"
    )


class Receipt(Base):
    """Receipt/attachment for an expense"""

    __tablename__ = "receipts"

    id = Column(String(255), primary_key=True)
    expense_id = Column(
        String(255),
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Local path or Cloud Storage URL
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String(100), nullable=False)  # MIME type

    # Optional OCR/AI extracted data
    ocr_text = Column(Text, nullable=True)
    extracted_amount = Column(Numeric(10, 2), nullable=True)
    extracted_vendor = Column(String(255), nullable=True)
    extracted_date = Column(DateTime, nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    expense = relationship("Expense", back_populates="receipts")


class ExpenseComment(Base):
    """Comments/notes on expenses for communication between employees and managers"""

    __tablename__ = "expense_comments"

    id = Column(String(255), primary_key=True)
    expense_id = Column(
        String(255),
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)

    # Comment content
    comment = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    expense = relationship("Expense", backref="comments")
    user = relationship("User", backref="expense_comments")


# ============================================================================
# Recurring Expense Models
# ============================================================================


class RecurringFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RecurringExpenseTemplate(Base):
    """Template for recurring expense auto-submission"""

    __tablename__ = "recurring_expense_templates"

    id = Column(String(255), primary_key=True)
    organization_id = Column(
        String(255), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)

    # Expense template details
    vendor = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(
        StringEnum(ExpenseCategory),
        nullable=False,
    )
    description = Column(Text, nullable=False)

    # Recurring schedule
    frequency = Column(
        StringEnum(RecurringFrequency),
        nullable=False,
    )
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # Optional end date
    next_run_date = Column(
        DateTime, nullable=False, index=True
    )  # Next scheduled submission

    # Intent Mandate integration (optional)
    intent_mandate_id = Column(
        String(255), ForeignKey("intent_mandates.id"), nullable=True
    )
    auto_submit = Column(
        Boolean, default=True, nullable=False
    )  # Auto-submit or just notify

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_paused = Column(Boolean, default=False, nullable=False)

    # Statistics
    total_submitted = Column(Integer, default=0, nullable=False)
    last_submitted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    organization = relationship("Organization", backref="recurring_expenses")
    user = relationship("User", backref="recurring_expense_templates")
    intent_mandate = relationship("IntentMandate", backref="recurring_expenses")
    scheduled_expenses = relationship(
        "ScheduledExpense", back_populates="template", cascade="all, delete-orphan"
    )


class ScheduledExpense(Base):
    """Individual scheduled expense instance from a recurring template"""

    __tablename__ = "scheduled_expenses"

    id = Column(String(255), primary_key=True)
    template_id = Column(
        String(255),
        ForeignKey("recurring_expense_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scheduled details
    scheduled_date = Column(DateTime, nullable=False, index=True)
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, submitted, failed, skipped

    # Result tracking
    expense_id = Column(
        String(255), ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True
    )
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    template = relationship(
        "RecurringExpenseTemplate", back_populates="scheduled_expenses"
    )
    expense = relationship("Expense", backref="scheduled_from")


class ExpenseNotification(Base):
    """Notifications for expense-related events"""

    __tablename__ = "expense_notifications"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)

    # Notification details
    notification_type = Column(
        String(100), nullable=False, index=True
    )  # recurring_submitted, expense_approved, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entities
    expense_id = Column(
        String(255), ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True
    )
    template_id = Column(
        String(255),
        ForeignKey("recurring_expense_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", backref="expense_notifications")
    expense = relationship("Expense", backref="notifications")
    template = relationship("RecurringExpenseTemplate", backref="notifications")


# ============================================================================
# Budget Management Models
# ============================================================================


class BudgetPeriod(str, enum.Enum):
    """Budget period types"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Budget(Base):
    """Budget tracking for organizations or users"""

    __tablename__ = "budgets"

    id = Column(String(255), primary_key=True)
    organization_id = Column(
        String(255),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # Optional: user-specific budget

    # Budget details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        StringEnum(ExpenseCategory),
        nullable=True,
    )  # Optional: category-specific budget

    # Budget amounts
    amount = Column(Numeric(12, 2), nullable=False)  # Total budget amount
    period = Column(
        StringEnum(BudgetPeriod),
        nullable=False,
        default=BudgetPeriod.MONTHLY.value,
    )

    # Alert thresholds (percentages)
    warning_threshold = Column(Integer, nullable=False, default=75)  # Alert at 75%
    critical_threshold = Column(Integer, nullable=False, default=90)  # Alert at 90%

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # Optional: for fixed-term budgets
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", backref="budgets")
    alerts = relationship(
        "BudgetAlert", back_populates="budget", cascade="all, delete-orphan"
    )


class BudgetAlert(Base):
    """Budget alert records"""

    __tablename__ = "budget_alerts"

    id = Column(String(255), primary_key=True)
    budget_id = Column(
        String(255),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Alert details
    alert_type = Column(
        String(50), nullable=False, index=True
    )  # warning, critical, exceeded
    threshold_percentage = Column(Integer, nullable=False)
    actual_amount = Column(Numeric(12, 2), nullable=False)
    budget_amount = Column(Numeric(12, 2), nullable=False)

    # Alert message
    message = Column(Text, nullable=False)

    # Status
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(255), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    budget = relationship("Budget", back_populates="alerts")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])


# ============================================================================
# AP2 Protocol Mandate Models
# ============================================================================


class IntentMandate(Base):
    """AP2 Intent Mandate - User's authorization constraints"""

    __tablename__ = "intent_mandates"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    constraints = Column(Text, nullable=False)  # JSON stored as text
    timestamp = Column(DateTime, nullable=False)
    expiration = Column(DateTime, nullable=False)
    signature = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", backref="intent_mandates")
    cart_mandates = relationship(
        "CartMandate", back_populates="intent_mandate", cascade="all, delete-orphan"
    )


class CartMandate(Base):
    """AP2 Cart Mandate - Specific items for approval"""

    __tablename__ = "cart_mandates"

    id = Column(String(255), primary_key=True)
    intent_mandate_id = Column(
        String(255), ForeignKey("intent_mandates.id"), nullable=False, index=True
    )
    items = Column(Text, nullable=False)  # JSON stored as text
    total = Column(Numeric(10, 2), nullable=False)
    merchant = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    user_signature = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    intent_mandate = relationship("IntentMandate", back_populates="cart_mandates")
    payment_mandates = relationship(
        "PaymentMandate", back_populates="cart_mandate", cascade="all, delete-orphan"
    )


class PaymentMandate(Base):
    """AP2 Payment Mandate - Payment execution record"""

    __tablename__ = "payment_mandates"

    id = Column(String(255), primary_key=True)
    cart_mandate_id = Column(
        String(255), ForeignKey("cart_mandates.id"), nullable=False, index=True
    )
    payment_method = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    audit_trail = Column(Text, nullable=False)  # JSON stored as text
    timestamp = Column(DateTime, nullable=False)
    payment_processor_response = Column(Text, nullable=True)  # JSON stored as text
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    cart_mandate = relationship("CartMandate", back_populates="payment_mandates")


# ============================================================================
# Approval Policy Models
# ============================================================================


class ApprovalPolicy(Base):
    """
    Approval Policy: Defines rules for automatic expense approval

    Configurable by organization owners/admins to streamline expense processing
    """

    __tablename__ = "approval_policies"

    # Primary key
    id = Column(String(255), primary_key=True)
    organization_id = Column(
        String(255), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
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
    #   "categories": ["MEALS", "OFFICE_SUPPLIES"],
    #   "vendors": ["Starbucks", "Amazon"],
    #   "user_ids": ["user_123", "user_456"],
    #   "user_roles": ["EMPLOYEE"],
    #   "exclude_vendors": ["Casino", "Bar"],
    #   "min_amount": 5.00,
    #   "days_of_week": [1, 2, 3, 4, 5],  # Mon-Fri only
    #   "time_range": {"start": "09:00", "end": "18:00"}
    # }
    conditions = Column(JSON, nullable=True)

    # Limits
    max_amount_per_expense = Column(Numeric(10, 2), nullable=True)
    daily_limit_per_user = Column(Numeric(10, 2), nullable=True)
    monthly_limit_per_user = Column(Numeric(10, 2), nullable=True)
    yearly_limit_per_user = Column(Numeric(10, 2), nullable=True)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(
        String(255), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by = Column(
        String(255), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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

    def to_dict(self):
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


class NotificationType(str, enum.Enum):
    """Notification types for different events"""
    EXPENSE_SUBMITTED = "expense_submitted"
    EXPENSE_APPROVED = "expense_approved"
    EXPENSE_REJECTED = "expense_rejected"
    RECURRING_SUBMITTED = "recurring_submitted"
    RECURRING_REMINDER = "recurring_reminder"
    COMMENT_ADDED = "comment_added"
    BUDGET_THRESHOLD = "budget_threshold"


class Notification(Base):
    """
    In-app notifications for users
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)

    notification_type = Column(StringEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Optional reference to related entities
    expense_id = Column(String(36), ForeignKey("expenses.id"), nullable=True)
    recurring_template_id = Column(String(36), ForeignKey("recurring_expense_templates.id"), nullable=True)

    # Metadata
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    organization = relationship("Organization")
    expense = relationship("Expense")
    recurring_template = relationship("RecurringExpenseTemplate")

    def __repr__(self):
        return f"<Notification {self.id} - {self.notification_type} for User {self.user_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "notification_type": self.notification_type,
            "title": self.title,
            "message": self.message,
            "expense_id": self.expense_id,
            "recurring_template_id": self.recurring_template_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
