import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    """
    Role pengguna di platform.

    Nilai ini mengikuti definisi di dokumen:
    - CLIENT
    - SALES
    - ADMIN
    - FINANCE
    """
    CLIENT = "CLIENT"
    SALES = "SALES"
    ADMIN = "ADMIN"
    FINANCE = "FINANCE"


class User(Base):
    """
    Menyimpan akun user yang bisa login ke platform.

    Atribut penting (dari dokumen):
    - id             : PK
    - email          : email login (unique)
    - password_hash  : hash password
    - full_name      : nama lengkap
    - role           : enum (CLIENT, SALES, ADMIN, FINANCE)
    - client_id      : FK ke clients.id (hanya terisi jika role = CLIENT)
    - is_active      : status aktif
    - created_at     : timestamp
    - updated_at     : timestamp

    Relasi:
    - Banyak USERS → satu CLIENT (via client_id)
    - USERS (role SALES) → QUOTATIONS via sales_user_id
    - USERS → EMAIL_LOGS sebagai pengirim/aktor
    """

    __tablename__ = "users"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Email login (unique)
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Email login user (unik per user).",
    )

    # Hash password (bukan plain text!)
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Hash password, bukan password asli.",
    )

    # Nama lengkap user
    full_name = Column(
        String(255),
        nullable=False,
        doc="Nama lengkap user.",
    )

    # Role enum
    role = Column(
        SAEnum(
            UserRole,
            name="user_role",
        ),
        nullable=False,
        doc="Role user: CLIENT / SALES / ADMIN / FINANCE.",
    )

    # Foreign key ke clients (optional, hanya untuk role=CLIENT)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="FK ke clients.id, hanya dipakai bila role = CLIENT.",
    )

    # Status aktif login (boleh login atau tidak)
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Menandakan apakah akun user masih aktif.",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ------------------------
    # Relationships
    # ------------------------

    # Banyak user (CLIENT) → satu client
    client = relationship(
        "Client",
        back_populates="users",
        doc="Relasi ke client (untuk user dengan role=CLIENT).",
    )

    # Untuk user role SALES: daftar quotation yang di-handle oleh sales ini
    sales_quotations = relationship(
        "Quotation",
        back_populates="sales_user",
        foreign_keys="Quotation.sales_user_id",
        doc="Daftar quotation yang ditangani user ini (role SALES).",
    )

    # Relasi ke email logs (user sebagai actor/pengirim)
    email_logs = relationship(
        "EmailLog",
        back_populates="user",
        doc="Log email yang berhubungan dengan user ini sebagai aktor/pengirim.",
    )
