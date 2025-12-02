import uuid
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    Enum as SAEnum,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class EmailDirection(str, Enum):
    """
    Arah email:
    - OUTBOUND: sistem kita mengirim email ke luar (client, finance, dsb)
    - INBOUND: email yang masuk dari client (kalau di-track)
    """
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class EmailRelatedType(str, Enum):
    """
    Tipe entitas yang terkait dengan email, sesuai dokumen:
    - QUOTATION
    - INVOICE_REQUEST
    - CLIENT_MAIL
    - REMINDER
    - PAYMENT_STATUS

    Ditambahkan OTHER untuk fleksibilitas ke depan kalau ada tipe lain.
    """
    QUOTATION = "QUOTATION"
    INVOICE_REQUEST = "INVOICE_REQUEST"
    CLIENT_MAIL = "CLIENT_MAIL"
    REMINDER = "REMINDER"
    PAYMENT_STATUS = "PAYMENT_STATUS"
    OTHER = "OTHER"


class EmailStatus(str, Enum):
    """
    Status email:
    - DRAFT: baru draft (belum dikirim)
    - SENT: sudah dikirim ke provider (Gmail / SMTP)
    - FAILED: gagal kirim
    - RECEIVED: email yang masuk dari luar
    - PARSED: email INBOUND yang sudah di-parse/simpan dengan benar
    """
    DRAFT = "DRAFT"
    SENT = "SENT"
    FAILED = "FAILED"
    RECEIVED = "RECEIVED"
    PARSED = "PARSED"


class EmailLog(Base):
    """
    Menyimpan semua email penting yang dikirim/diterima sebagai bagian dari proses otomatis:

    - Quotation ke client
    - Request invoice ke Finance
    - Email invoice & faktur + link pembayaran ke client
    - Email reminder
    - Email dari client (kalau di-track)

    Catatan desain:
    - related_type + related_id = pointer fleksibel ke berbagai entitas (QUOTATION, BILLING_CYCLE, dsb.)
    - user_id → FK ke USERS (optional, bisa null untuk email sistem murni).
    """

    __tablename__ = "email_logs"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Arah email (OUTBOUND / INBOUND)
    direction = Column(
        SAEnum(EmailDirection, name="email_direction_enum"),
        nullable=False,
    )

    # Tipe entitas terkait (QUOTATION, INVOICE_REQUEST, CLIENT_MAIL, REMINDER, PAYMENT_STATUS, ...)
    related_type = Column(
        SAEnum(EmailRelatedType, name="email_related_type_enum"),
        nullable=False,
    )

    # ID entitas terkait (misalnya quotation_id, billing_cycle_id, dsb.)
    # Kita asumsikan semua ID utama di sistem adalah UUID.
    related_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # User terkait (Sales/Admin/Finance/Client) – optional
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="email_logs",
        lazy="joined",
    )

    # Informasi email dasar
    from_email = Column(String(320), nullable=False)  # 320 = batas RFC maksimal
    to_email = Column(String(320), nullable=False)
    subject = Column(String(500), nullable=True)

    # Informasi AI
    ai_model = Column(String(100), nullable=True)        # contoh: "gemini-1.5-pro"
    ai_prompt = Column(Text, nullable=True)
    ai_generated_body = Column(Text, nullable=True)      # draft hasil AI
    final_body = Column(Text, nullable=True)             # body final yang benar-benar dikirim/disimpan

    # Status lifecycle email (DRAFT, SENT, FAILED, RECEIVED, PARSED)
    status = Column(
        SAEnum(EmailStatus, name="email_status_enum"),
        nullable=False,
        default=EmailStatus.DRAFT,
    )

    # Metadata terkait Gmail / provider lain
    gmail_message_id = Column(String(255), nullable=True)

    # Lampiran
    has_attachments = Column(Boolean, nullable=False, default=False)
    attachments_meta_json = Column(JSONB, nullable=True)
    # contoh isi JSON: [{ "filename": "invoice-123.pdf", "mime_type": "application/pdf", ... }, ...]

    # Waktu penting
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps standar sistem
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

    __table_args__ = (
        # Untuk cepat cari email berdasarkan relasi bisnis (misalnya semua email untuk 1 quotation)
        Index(
            "ix_email_logs_related_type_related_id",
            "related_type",
            "related_id",
        ),
        # Untuk lookup cepat ke Gmail / provider
        Index(
            "ix_email_logs_gmail_message_id",
            "gmail_message_id",
        ),
        # Untuk cepat ambil semua email per user
        Index(
            "ix_email_logs_user_id",
            "user_id",
        ),
        # Untuk analitik per arah email
        Index(
            "ix_email_logs_direction",
            "direction",
        ),
    )
