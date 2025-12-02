import uuid
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SqlEnum

from app.db.base import Base


class ProvisioningAction(str, Enum):
    ACTIVATE = "ACTIVATE"
    SUSPEND = "SUSPEND"
    CHANGE_QUANTITY = "CHANGE_QUANTITY"
    TERMINATE = "TERMINATE"


class ProvisioningTargetSystem(str, Enum):
    GWORKSPACE = "GWORKSPACE"
    GCP = "GCP"


class ProvisioningStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ProvisioningTask(Base):
    """
    Menyimpan unit kerja untuk otomatisasi aktivasi/penonaktifan di Google Workspace dan GCP.

    Sesuai spesifikasi:
    - Banyak PROVISIONING_TASKS terkait ke satu SUBSCRIPTION_ITEMS (FK subscription_item_id).
    - Memuat action, target_system, payload_json, status, external_reference, error_message,
      dan timestamps created_at, executed_at.
    """

    __tablename__ = "provisioning_tasks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    subscription_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    action = Column(
        SqlEnum(
            ProvisioningAction,
            name="provisioning_action_enum",
            create_type=True,
        ),
        nullable=False,
    )

    target_system = Column(
        SqlEnum(
            ProvisioningTargetSystem,
            name="provisioning_target_system_enum",
            create_type=True,
        ),
        nullable=False,
    )

    payload_json = Column(
        JSONB,
        nullable=True,
        doc="Data untuk panggilan API eksternal (domain, user list, project ID, dsb).",
    )

    status = Column(
        SqlEnum(
            ProvisioningStatus,
            name="provisioning_status_enum",
            create_type=True,
        ),
        nullable=False,
        default=ProvisioningStatus.PENDING,
    )

    external_reference = Column(
        String(255),
        nullable=True,
        doc="ID job/task di sistem eksternal (jika ada).",
    )

    error_message = Column(
        Text,
        nullable=True,
        doc="Keterangan error (jika gagal).",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    executed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Waktu task benar-benar dieksekusi (berhasil/gagal).",
    )

    # Relationships
    subscription_item = relationship(
        "SubscriptionItem",
        back_populates="provisioning_tasks",
    )

    def __repr__(self) -> str:
        return (
            f"<ProvisioningTask(id={self.id}, "
            f"subscription_item_id={self.subscription_item_id}, "
            f"action={self.action}, "
            f"target_system={self.target_system}, "
            f"status={self.status})>"
        )
