import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SAEnum

from app.db.base import Base


class WalletTransactionType(str, enum.Enum):
    TOPUP = "TOPUP"
    CHARGE = "CHARGE"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"


class WalletTransactionDirection(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"


class WalletTransactionRelatedType(str, enum.Enum):
    PAYMENT = "PAYMENT"
    SUBSCRIPTION = "SUBSCRIPTION"
    MANUAL = "MANUAL"


class WalletAccount(Base):
    """
    WALLET_ACCOUNTS

    Tujuan:
    Menyediakan mekanisme deposit / wallet untuk client (opsional).

    Relasi:
    - Satu CLIENTS memiliki tepat satu WALLET_ACCOUNTS.
    - Satu WALLET_ACCOUNTS memiliki banyak WALLET_TRANSACTIONS.
    """

    __tablename__ = "wallet_accounts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Relasi ke CLIENTS (unique per client)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Saldo saat ini
    balance = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    # Mata uang saldo (contoh: IDR, USD)
    currency = Column(
        String(10),
        nullable=False,
    )

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

    # Relationship
    client = relationship(
        "Client",
        back_populates="wallet_account",
        lazy="joined",
    )

    transactions = relationship(
        "WalletTransaction",
        back_populates="wallet_account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WalletTransaction(Base):
    """
    WALLET_TRANSACTIONS

    Tujuan:
    Menyimpan semua mutasi saldo pada wallet account.

    Relasi:
    - Satu WALLET_ACCOUNTS memiliki banyak WALLET_TRANSACTIONS.
    """

    __tablename__ = "wallet_transactions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    wallet_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wallet_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Misalnya: TOPUP, CHARGE, REFUND, ADJUSTMENT
    type = Column(
        SAEnum(WalletTransactionType, name="wallet_transaction_type"),
        nullable=False,
    )

    # IN atau OUT
    direction = Column(
        SAEnum(WalletTransactionDirection, name="wallet_transaction_direction"),
        nullable=False,
    )

    # Jumlah perubahan saldo
    amount = Column(
        Numeric(18, 2),
        nullable=False,
    )

    # Misalnya: PAYMENT, SUBSCRIPTION, MANUAL
    related_type = Column(
        SAEnum(WalletTransactionRelatedType, name="wallet_transaction_related_type"),
        nullable=True,
    )

    # ID entitas terkait (payment_id, subscription_id, dsb)
    related_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    wallet_account = relationship(
        "WalletAccount",
        back_populates="transactions",
        lazy="joined",
    )
