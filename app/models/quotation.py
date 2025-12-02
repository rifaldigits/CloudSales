import uuid
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    Integer,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class QuotationStatus(str, Enum):
    """Status enum untuk entitas QUOTATIONS sesuai SRS."""

    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Quotation(Base):
    """
    QUOTATIONS

    Menyimpan penawaran harga yang disusun oleh Sales di platform dan
    menghubungkan data internal dengan quotation resmi di Cosmic.
    """

    __tablename__ = "quotations"
    __allow_unmapped__ = True

    id: uuid.UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Relasi ke CLIENTS
    client_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relasi ke USERS (Sales yang membuat)
    sales_user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Nomor quotation internal
    number: str = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    # Status enum: DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED
    status: str = Column(
        String(20),
        nullable=False,
        default=QuotationStatus.DRAFT.value,
        index=True,
    )

    # Total nilai quotation menurut platform (mata uang internal, default USD)
    total_amount = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Mata uang internal (misalnya "USD")
    currency: str = Column(
        String(10),
        nullable=False,
        default="USD",
    )

    # Mata uang client (misalnya "IDR")
    client_currency: str = Column(
        String(10),
        nullable=False,
        default="IDR",
    )

    # Kurs yang diinput Sales saat quotation dibuat
    exchange_rate = Column(
        Numeric(18, 6),
        nullable=False,
        default=1,
    )

    # Total nilai quotation dalam client_currency (misalnya IDR) yang ditampilkan di PDF
    total_amount_client = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Tanggal berakhirnya masa berlaku quotation
    valid_until = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Nullable; diisi jika quotation sudah diwujudkan menjadi subscription
    related_subscription_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ID quotation di sistem Cosmic
    cosmic_id: Optional[str] = Column(
        String(255),
        nullable=True,
        unique=True,
    )

    # URL PDF quotation yang dihasilkan oleh Cosmic
    pdf_url: Optional[str] = Column(
        String(1024),
        nullable=True,
    )

    # ID thread Gmail untuk tracking percakapan dengan client (optional)
    gmail_thread_id: Optional[str] = Column(
        String(255),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # -------------------
    # SQLAlchemy relationships
    # -------------------

    # Satu quotation dimiliki oleh satu client
    client = relationship(
        "Client",
        back_populates="quotations",
    )

    # Satu quotation dibuat oleh satu user (Sales)
    sales_user = relationship(
        "User",
        back_populates="sales_quotations",
    )

    # Satu quotation bisa dikaitkan ke satu subscription
    subscription = relationship(
        "Subscription",
        back_populates="quotation",
        uselist=False,
    )

    # Satu quotation memiliki banyak quotation_items
    items = relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Satu quotation dapat memiliki banyak email_logs (akan diimplementasikan di model EmailLog)
    email_logs = relationship(
        "EmailLog",
        back_populates="quotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class QuotationItem(Base):
    """
    QUOTATION_ITEMS

    Menyimpan line item pada quotation, misalnya seat Google Workspace,
    VM GCP, domain, atau managed service fee bulanan.
    """

    __tablename__ = "quotation_items"
    __allow_unmapped__ = True

    id: uuid.UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Relasi ke QUOTATIONS
    quotation_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relasi ke PRODUCTS (boleh nullable jika item custom)
    product_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Deskripsi baris (bisa lebih spesifik)
    description: Optional[str] = Column(
        Text,
        nullable=True,
    )

    # Jumlah unit
    quantity: int = Column(
        Integer,
        nullable=False,
        default=1,
    )

    # Harga per unit dalam mata uang internal (default USD)
    unit_price = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Harga per unit dalam client_currency (default IDR)
    unit_price_client = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Diskon dalam persen, jika ada (misal 10.00 = 10%)
    discount_percent = Column(
        Numeric(5, 2),
        nullable=True,
    )

    # Nilai setelah diskon dalam mata uang internal (USD)
    subtotal_amount = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Nilai setelah diskon dalam client_currency (IDR)
    subtotal_amount_client = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # -------------------
    # SQLAlchemy relationships
    # -------------------

    # Banyak QUOTATION_ITEMS terkait ke satu QUOTATION
    quotation = relationship(
        "Quotation",
        back_populates="items",
    )

    # product_id (jika diisi) mengacu ke satu PRODUCTS
    product = relationship(
        "Product",
        back_populates="quotation_items",
    )
