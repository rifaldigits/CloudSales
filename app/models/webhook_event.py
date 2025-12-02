import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class WebhookEvent(Base):
    """
    Menyimpan log webhook dari Xendit (payment success, failed, subscription charge).

    Mengacu ke spesifikasi:
    - id – Primary key.
    - source – Untuk saat ini misalnya XENDIT.
    - event_type – Misalnya:
        - PAYMENT_SUCCEEDED
        - PAYMENT_FAILED
        - SUBSCRIPTION_CHARGED
    - raw_payload_json – Payload lengkap dari Xendit untuk audit/debug.
    - xendit_subscription_id – ID subscription yang terkait (jika ada).
    - xendit_invoice_id – ID invoice di Xendit (jika ada).
    - processed – Boolean, menandakan apakah event sudah diproses oleh workflow.
    - processed_at – Timestamp pemrosesan.
    - created_at – Timestamp event diterima.
    """

    __tablename__ = "webhook_events"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Sumber webhook, misalnya: "XENDIT"
    source = Column(
        String(50),
        nullable=False,
        doc="Sumber webhook, saat ini biasanya 'XENDIT'.",
    )

    # Jenis event, contoh: PAYMENT_SUCCEEDED, PAYMENT_FAILED, SUBSCRIPTION_CHARGED
    event_type = Column(
        String(100),
        nullable=False,
        doc="Jenis event dari webhook, misalnya PAYMENT_SUCCEEDED, PAYMENT_FAILED, SUBSCRIPTION_CHARGED.",
    )

    # Payload mentah untuk keperluan audit & debug
    raw_payload_json = Column(
        JSONB,
        nullable=False,
        doc="Payload JSON lengkap sebagaimana diterima dari Xendit.",
    )

    # Referensi ke subscription di Xendit (kalau ada)
    xendit_subscription_id = Column(
        String(255),
        nullable=True,
        doc="ID subscription di Xendit yang terkait event ini (jika ada).",
    )

    # Referensi ke invoice di Xendit (kalau ada)
    xendit_invoice_id = Column(
        String(255),
        nullable=True,
        doc="ID invoice di Xendit yang terkait event ini (jika ada).",
    )

    # Status apakah event sudah diproses oleh workflow internal
    processed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Menandakan apakah event sudah diproses oleh workflow internal.",
    )

    # Kapan event ini diproses oleh sistem internal
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Waktu saat event diproses oleh workflow (NULL jika belum diproses).",
    )

    # Waktu event diterima oleh sistem (log time)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Waktu ketika webhook pertama kali diterima oleh sistem.",
    )

    # Relasi ke PAYMENTS akan ditambahkan di sisi Payment model,
    # misalnya dengan ForeignKey + relationship("WebhookEvent", back_populates="payments")
    # di sini nantinya bisa ditambahkan:
    # payments = relationship("Payment", back_populates="webhook_event")

    __table_args__ = (
        # Untuk query cepat berdasarkan sumber & jenis event
        Index(
            "ix_webhook_events_source_event_type",
            "source",
            "event_type",
        ),
        # Cari cepat berdasarkan invoice id dari Xendit
        Index(
            "ix_webhook_events_xendit_invoice_id",
            "xendit_invoice_id",
        ),
        # Cari cepat berdasarkan subscription id dari Xendit
        Index(
            "ix_webhook_events_xendit_subscription_id",
            "xendit_subscription_id",
        ),
    )

    def mark_processed(self, processed_at: datetime | None = None) -> None:
        """
        Helper method untuk menandai event sudah diproses.
        Bisa dipakai di service layer.
        """
        self.processed = True
        self.processed_at = processed_at or datetime.utcnow()
