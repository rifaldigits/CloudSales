import uuid
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class BillingCycleStatus(str, enum.Enum):
    PENDING = "PENDING"
    INVOICE_REQUESTED = "INVOICE_REQUESTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BillingCycle(Base):
    """
    Representasi entitas BILLING_CYCLES.

    Tujuan:
    - Menyimpan tiap periode penagihan (initial & recurring).
    - Penghubung antara quotation (harga platform), invoice Finance (harga final),
      dan pembayaran Xendit.
    """

    __tablename__ = "billing_cycles"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Relasi utama ke SUBSCRIPTIONS
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Periode penagihan
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Due date invoice (sesuai Finance)
    due_date = Column(Date, nullable=False)

    # Jumlah tagihan final (sudah termasuk pajak, mata uang client)
    amount = Column(Numeric(18, 2), nullable=False)

    # Mata uang invoice Finance (saat ini IDR)
    currency = Column(String(10), nullable=False, default="IDR")

    # Status lifecycle billing cycle
    status = Column(
        Enum(BillingCycleStatus, name="billing_cycle_status"),
        nullable=False,
        default=BillingCycleStatus.PENDING,
    )

    # True untuk tagihan pertama (initial cycle)
    is_initial_cycle = Column(Boolean, nullable=False, default=False)

    # Nilai hasil perhitungan platform sebelum finalisasi Finance (opsional)
    quoted_amount = Column(Numeric(18, 2), nullable=True)

    # Info invoice dari sistem Finance
    invoice_number_external = Column(String(100), nullable=True)
    invoice_file_url = Column(String(2048), nullable=True)
    tax_invoice_file_url = Column(String(2048), nullable=True)

    # Invoice ID dari Xendit (jika ada)
    xendit_invoice_id = Column(String(255), nullable=True)

    # Timestamp reminder terakhir dikirim ke client
    last_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps umum
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

    # ==========================
    # Relationships (ORM level)
    # ==========================

    # Satu billing cycle → satu subscription
    subscription = relationship(
        "Subscription",
        back_populates="billing_cycles",
    )

    # Satu billing cycle → banyak payments
    payments = relationship(
        "Payment",
        back_populates="billing_cycle",
    )

    # Satu billing cycle → banyak email logs
    email_logs = relationship(
        "EmailLog",
        back_populates="billing_cycle",
    )
