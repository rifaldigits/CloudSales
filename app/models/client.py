import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClientStatus(str, enum.Enum):
    """
    Status lifecycle client:
    - LEAD: masih prospek, belum ada pembayaran.
    - ACTIVE: sudah jadi customer aktif, pembayaran berjalan normal.
    - SUSPENDED: layanan disuspend (misal karena telat bayar).
    - CHURNED: sudah berhenti berlangganan / putus kontrak.
    """
    LEAD = "LEAD"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CHURNED = "CHURNED"


class Client(Base):
    """
    Model CLIENTS

    Tujuan:
    - Menyimpan data perusahaan pelanggan, termasuk yang masih prospek (LEAD).
    - Membedakan kontak billing vs kontak korespondensi Sales.
    - Menjadi root entity yang berelasi ke:
      - USERS (user internal client, portal)
      - QUOTATIONS
      - SUBSCRIPTIONS
      - PAYMENTS
      - WALLET_ACCOUNTS (1:1 jika wallet dipakai)
    """

    __tablename__ = "clients"

    # --- Primary Key ---

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # --- Informasi identitas perusahaan ---

    # Nama perusahaan yang dipakai sehari-hari
    name = Column(String(255), nullable=False)

    # Nama hukum perusahaan (bisa beda dari name)
    legal_name = Column(String(255), nullable=True)

    # --- Kontak & Billing ---

    # Email utama untuk menerima invoice & faktur pajak
    billing_email = Column(String(255), nullable=False)

    # Email utama untuk komunikasi Sales (boleh sama dengan billing_email)
    contact_email = Column(String(255), nullable=True)

    # Nomor telepon kontak perusahaan
    phone = Column(String(50), nullable=True)

    # Alamat billing (bisa panjang, jadi Text)
    billing_address = Column(Text, nullable=True)

    # --- Pajak ---

    # NPWP atau nomor pajak lain
    tax_number = Column(String(64), nullable=True)

    # URL / path scan kartu NPWP yang disimpan di storage
    tax_card_file_url = Column(Text, nullable=True)

    # --- Status lifecycle & portal ---

    status = Column(
        Enum(ClientStatus, name="client_status"),
        nullable=False,
        default=ClientStatus.LEAD,
        server_default=ClientStatus.LEAD.value,
    )

    # Domain Google Workspace client (misal: example.com)
    workspace_domain = Column(String(255), nullable=True)

    # True setelah pembayaran pertama sukses & portal account dibuat
    has_portal_account = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # Identifier client di ekosistem Google (optional)
    google_customer_id = Column(String(255), nullable=True)

    # --- Timestamps ---

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

    # --- Relationships ---

    # Satu CLIENT punya banyak USERS (user portal/internal client)
    users = relationship(
        "User",
        back_populates="client",
        lazy="selectin",
    )

    # Satu CLIENT punya banyak QUOTATIONS
    quotations = relationship(
        "Quotation",
        back_populates="client",
        lazy="selectin",
    )

    # Satu CLIENT punya banyak SUBSCRIPTIONS
    subscriptions = relationship(
        "Subscription",
        back_populates="client",
        lazy="selectin",
    )

    # Satu CLIENT punya banyak PAYMENTS
    payments = relationship(
        "Payment",
        back_populates="client",
        lazy="selectin",
    )

    # Satu CLIENT tepat satu WALLET_ACCOUNT (1:1)
    wallet_account = relationship(
        "WalletAccount",
        back_populates="client",
        uselist=False,
        lazy="selectin",
    )
