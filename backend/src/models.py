from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum, Table, Text, Numeric, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    ACCOUNTANT = "accountant"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(Enum(UserRole, name='userrole'), default=UserRole.EMPLOYEE, nullable=False)  # PostgreSQL ENUM
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
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
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
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="sessions")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON stored as text
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


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
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", backref="intent_mandates")
    cart_mandates = relationship("CartMandate", back_populates="intent_mandate", cascade="all, delete-orphan")


class CartMandate(Base):
    """AP2 Cart Mandate - Specific items for approval"""
    __tablename__ = "cart_mandates"

    id = Column(String(255), primary_key=True)
    intent_mandate_id = Column(String(255), ForeignKey("intent_mandates.id"), nullable=False, index=True)
    items = Column(Text, nullable=False)  # JSON stored as text
    total = Column(Numeric(10, 2), nullable=False)
    merchant = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    user_signature = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    intent_mandate = relationship("IntentMandate", back_populates="cart_mandates")
    payment_mandates = relationship("PaymentMandate", back_populates="cart_mandate", cascade="all, delete-orphan")


class PaymentMandate(Base):
    """AP2 Payment Mandate - Payment execution record"""
    __tablename__ = "payment_mandates"

    id = Column(String(255), primary_key=True)
    cart_mandate_id = Column(String(255), ForeignKey("cart_mandates.id"), nullable=False, index=True)
    payment_method = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    audit_trail = Column(Text, nullable=False)  # JSON stored as text
    timestamp = Column(DateTime, nullable=False)
    payment_processor_response = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    cart_mandate = relationship("CartMandate", back_populates="payment_mandates")


# ============================================================================
# Subscription & Billing Models
# ============================================================================

class SubscriptionTier(str, enum.Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"


class Subscription(Base):
    """User/Organization subscription"""
    __tablename__ = "subscriptions"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(Enum(SubscriptionTier, name='subscriptiontier'), nullable=False, default=SubscriptionTier.STARTER)
    status = Column(String(50), nullable=False, default="active", index=True)  # active, canceled, past_due, trialing

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Billing
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    # Limits
    max_users = Column(Integer, nullable=False, default=25)
    max_expenses_per_month = Column(Integer, nullable=True)  # NULL = unlimited
    max_ai_categorizations = Column(Integer, nullable=True)
    max_ap2_transactions = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", backref="subscriptions")
    usage_records = relationship("UsageRecord", back_populates="subscription", cascade="all, delete-orphan")


class UsageRecord(Base):
    """Track usage for billing"""
    __tablename__ = "usage_records"

    id = Column(String(255), primary_key=True)
    subscription_id = Column(String(255), ForeignKey("subscriptions.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)

    # Usage types
    usage_type = Column(String(50), nullable=False, index=True)  # expense, ai_categorization, ocr_scan, ap2_transaction
    quantity = Column(Integer, nullable=False, default=1)

    # Billing
    billable = Column(Boolean, nullable=False, default=False)  # Is this over the tier limit?
    fee = Column(Numeric(10, 4), nullable=True)  # Fee charged for this usage

    # Metadata
    metadata = Column(Text, nullable=True)  # JSON stored as text

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")
    user = relationship("User", backref="usage_records")


class Invoice(Base):
    """Monthly invoices"""
    __tablename__ = "invoices"

    id = Column(String(255), primary_key=True)
    subscription_id = Column(String(255), ForeignKey("subscriptions.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)

    # Stripe integration
    stripe_invoice_id = Column(String(255), nullable=True, index=True)

    # Invoice details
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Amounts
    subscription_amount = Column(Numeric(10, 2), nullable=False)  # Base subscription fee
    usage_amount = Column(Numeric(10, 2), nullable=False, default=0)  # Overage fees
    total_amount = Column(Numeric(10, 2), nullable=False)

    # Status
    status = Column(String(50), nullable=False, default="draft", index=True)  # draft, open, paid, void
    paid_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    subscription = relationship("Subscription", backref="invoices")
    user = relationship("User", backref="invoices")