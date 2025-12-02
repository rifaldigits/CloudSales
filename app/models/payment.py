import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    XENDIT_EWALLET = "XENDIT_EWALLET"
    XENDIT_CC = "XENDIT_CC"
    XENDIT_VA = "XENDIT_VA"
    MANUAL = "MANUAL"


class Payment(Base):
    """
    PAYMENTS

    Tujuan:
        Menyimpan catatan pembayaran aktual melalui Xendit atau manual.

    Relasi:
        - Banyak PAYMENTS terkait ke satu CLIENTS (client_id → clients.id)
        - Banyak PAYMENTS dapat terkait ke satu SUBSCRIPTIONS (subscription_id → subscriptions.id)
        - Banyak PAYMENTS dapat terkait ke satu BILLING_CYCLES (billing_cycle_id → billing_cycles.id)
        - Satu PAYMENTS dapat direferensikan oleh WALLET_TRANSACTIONS sebagai sumber topup/charge
          (relasi akan didefinisikan di model wallet/transaction nantinya).
    """

    __tablename__ = "payments"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign keys
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    billing_cycle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("billing_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Nilai pembayaran
    amount = Column(
        NUMERIC(18, 2),
        nullable=False,
    )
    currency = Column(
        String(10),
        nullable=False,
    )

    # Status & method
    status = Column(
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )

    method = Column(
        Enum(PaymentMethod, name="payment_method_enum"),
        nullable=False,
    )

    # Integrasi Xendit
    xendit_payment_id = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    xendit_subscription_id = Column(
        String(255),
        nullable=True,
        index=True,
    )

    # Waktu pembayaran & alasan gagal
    paid_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_reason = Column(
        String(500),
        nullable=True,
    )

    # Audit timestamps
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

    # Relationships (akan aktif penuh setelah model lain dibuat)
    client = relationship(
        "Client",
        back_populates="payments",
        lazy="joined",
    )
    subscription = relationship(
        "Subscription",
        back_populates="payments",
        lazy="joined",
    )
    billing_cycle = relationship(
        "BillingCycle",
        back_populates="payments",
        lazy="joined",
    )
    # wallet_transactions: akan didefinisikan di model wallet/transaction,
    # contoh nanti:
    # wallet_transactions = relationship(
    #     "WalletTransaction",
    #     back_populates="payment",
    # )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} client_id={self.client_id} "
            f"amount={self.amount} {self.currency} status={self.status}>"
        )
