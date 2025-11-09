import enum
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ACCOUNTANT = "accountant"
    EMPLOYEE = "employee"


class OrganizationRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


# ============================================================================
# Multi-Tenancy Models
# ============================================================================


class Organization(Base):
    """Organization/Tenant for multi-tenancy"""

    __tablename__ = "organizations"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Settings
    currency = Column(String(10), nullable=False, default="USD")
    timezone = Column(String(50), nullable=False, default="UTC")

    # Subscription
    subscription_id = Column(String(255), ForeignKey("subscriptions.id"), nullable=True)

    # Limits
    max_members = Column(Integer, nullable=False, default=25)
    max_expenses_per_month = Column(Integer, nullable=True)

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
        Enum(OrganizationRole, name="organizationrole"),
        nullable=False,
        default=OrganizationRole.MEMBER,
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime, server_default=func.now())

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", backref="organization_memberships")

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
        Enum(OrganizationRole, name="organizationrole"),
        nullable=False,
        default=OrganizationRole.MEMBER,
    )

    invited_by = Column(String(255), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

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
        Enum(UserRole, name="userrole"), default=UserRole.EMPLOYEE, nullable=False
    )
    department_id = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    backup_codes = Column(Text, nullable=True)

    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)

    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-_
