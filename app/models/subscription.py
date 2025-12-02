import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SubscriptionStatus(str, enum.Enum):
    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class BillingPeriod(str, enum.Enum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class SubscriptionPaymentMethodType(str, enum.Enum):
    XENDIT_SUBSCRIPTION = "XENDIT_SUBSCRIPTION"
    MANUAL = "MANUAL"
    WALLET = "WALLET"
    # kalau nanti di dokumen ada tipe lain, bisa ditambah di sini


class ProvisioningStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


# ---------------------------------------------------------------------------
# Model: SUBSCRIPTIONS
# ---------------------------------------------------------------------------


class Subscription(Base):
    """
    Representasi entitas SUBSCRIPTIONS.

    Tujuan:
    - Menyimpan informasi subscription yang sudah berjalan / akan berjalan.
    - Menghubungkan client dengan kontrak langganan jangka panjang.
    """

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Status lifecycle subscription
    status = Column(
        Enum(
            SubscriptionStatus,
            name="subscription_status_enum",
            native_enum=False,
        ),
        nullable=False,
        default=SubscriptionStatus.PENDING_ACTIVATION,
    )

    # Billing config
    billing_period = Column(
        Enum(
            BillingPeriod,
            name="billing_period_enum",
            native_enum=False,
        ),
        nullable=False,
    )

    # Timeline subscription
    start_date = Column(Date, nullable=True)  # setelah pembayaran pertama sukses
    end_date = Column(Date, nullable=True)  # boleh null untuk ongoing contract
    next_billing_date = Column(Date, nullable=True)

    # Payment method
    payment_method_type = Column(
        Enum(
            SubscriptionPaymentMethodType,
            name="subscription_payment_method_enum",
            native_enum=False,
        ),
        nullable=False,
    )
    is_manual = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="True jika subscription dibuat manual (mis. ketika Xendit down)",
    )
    xendit_subscription_id = Column(String(255), nullable=True)

    # Finance meta
    currency = Column(String(10), nullable=False)
    notes = Column(Text, nullable=True)

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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    client = relationship(
        "Client",
        back_populates="subscriptions",
    )

    created_by_user = relationship(
        "User",
        back_populates="created_subscriptions",
        foreign_keys=[created_by_user_id],
    )

    # Satu subscription punya banyak item
    items = relationship(
        "SubscriptionItem",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    # Satu subscription punya banyak billing cycles
    billing_cycles = relationship(
        "BillingCycle",
        back_populates="subscription",
    )

    # Satu subscription punya banyak payments
    payments = relationship(
        "Payment",
        back_populates="subscription",
    )

    # Satu subscription bisa terkait ke satu quotation (via related_subscription_id di QUOTATIONS)
    quotation = relationship(
        "Quotation",
        back_populates="subscription",
        uselist=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - hanya untuk debugging
        return f"<Subscription id={self.id} status={self.status} client_id={self.client_id}>"


# ---------------------------------------------------------------------------
# Model: SUBSCRIPTION_ITEMS
# ---------------------------------------------------------------------------


class SubscriptionItem(Base):
    """
    Representasi entitas SUBSCRIPTION_ITEMS.

    Tujuan:
    - Menyimpan detail isi subscription (produk, jumlah seat/resource, dsb).
    """

    __tablename__ = "subscription_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Deskripsi dan nilai finansial
    description = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    amount = Column(
        Numeric(18, 2),
        nullable=False,
        doc="Total nilai per baris (quantity * unit_price)",
    )

    # Provisioning state
    provisioning_status = Column(
        Enum(
            ProvisioningStatus,
            name="provisioning_status_enum",
            native_enum=False,
        ),
        nullable=False,
        default=ProvisioningStatus.PENDING,
    )

    google_workspace_subscription_id = Column(String(255), nullable=True)
    gcp_resource_id = Column(String(255), nullable=True)

    # config_json untuk pengaturan tambahan (jenis VM, region, dsb)
    config_json = Column(JSONB, nullable=True)

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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    subscription = relationship(
        "Subscription",
        back_populates="items",
    )

    product = relationship(
        "Product",
        back_populates="subscription_items",
    )

    # Satu SubscriptionItem bisa memicu banyak provisioning tasks
    provisioning_tasks = relationship(
        "ProvisioningTask",
        back_populates="subscription_item",
    )

    def __repr__(self) -> str:  # pragma: no cover - hanya untuk debugging
        return (
            f"<SubscriptionItem id={self.id} "
            f"subscription_id={self.subscription_id} "
            f"product_id={self.product_id} "
            f"quantity={self.quantity} amount={self.amount}>"
        )
