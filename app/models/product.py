import uuid
from enum import Enum

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProductType(str, Enum):
    """
    Nilai yang sesuai dengan dokumen:

    - GWORKSPACE
    - GCP
    - DOMAIN
    - ADDON
    - SERVICE

    Disimpan di DB sebagai string (kolom `type`).
    """
    GWORKSPACE = "GWORKSPACE"
    GCP = "GCP"
    DOMAIN = "DOMAIN"
    ADDON = "ADDON"
    SERVICE = "SERVICE"


class BillingPeriod(str, Enum):
    """
    Contoh di dokumen:

    - MONTHLY
    - YEARLY

    Disimpan di DB sebagai string (kolom `default_billing_period`).
    """
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Product(Base):
    """
    Entitas PRODUCTS (SRS 4.3)

    Menyimpan semua produk yang bisa dikutip dan disubscribe oleh client:
    - Produk utama: Google Workspace, GCP
    - Produk lain: domain, managed service fee, addon backup, support, dsb.
    """

    __tablename__ = "products"

    # --- Kolom utama sesuai dokumen ---

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Primary key (UUID v4)."
    )

    code = Column(
        String(100),
        nullable=False,
        unique=True,
        doc="Kode produk internal (misal GW_BUS_STD, GCP_VM, DOMAIN_ID)."
    )

    name = Column(
        String(255),
        nullable=False,
        doc="Nama produk."
    )

    # Disimpan sebagai string; di layer Python dianjurkan pakai enum ProductType
    type = Column(
        String(50),
        nullable=False,
        doc="Kategori produk (GWORKSPACE, GCP, DOMAIN, ADDON, SERVICE, dll)."
    )

    description = Column(
        String,
        nullable=True,
        doc="Deskripsi produk."
    )

    # Disimpan sebagai string; di layer Python dianjurkan pakai enum BillingPeriod
    default_billing_period = Column(
        String(20),
        nullable=True,
        doc="Billing period default, misal MONTHLY atau YEARLY."
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Menandakan apakah produk masih dijual."
    )

    google_sku = Column(
        String(255),
        nullable=True,
        doc="SKU resmi dari Google (Workspace/GCP) jika ada."
    )

    metadata_json = Column(
        JSONB,
        nullable=True,
        doc="Konfigurasi tambahan dalam bentuk JSON (region GCP, jenis VM, dsb)."
    )

    # --- Timestamp standar untuk semua entitas ---

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Waktu record dibuat."
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Waktu record terakhir diperbarui."
    )

    # --- Relasi (arah kebalikan dari FK di QUOTATION_ITEMS & SUBSCRIPTION_ITEMS) ---

    quotation_items = relationship(
        "QuotationItem",
        back_populates="product",
        lazy="selectin",
        doc="Semua QUOTATION_ITEMS yang memakai produk ini."
    )

    subscription_items = relationship(
        "SubscriptionItem",
        back_populates="product",
        lazy="selectin",
        doc="Semua SUBSCRIPTION_ITEMS yang memakai produk ini."
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} code={self.code!r} name={self.name!r}>"
