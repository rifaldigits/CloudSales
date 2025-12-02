import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------
# Tambah path project ke sys.path
# ---------------------------------------------------------
# __file__ = .../alembic/env.py
# dirname(__file__)      -> .../alembic
# dirname(dirname(...))  -> root project (yang berisi folder "app")
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import settings & Base dari project kita
from app.core.config import settings  # type: ignore
from app.db.base import Base  # type: ignore
import app.models.base  # noqa: F401  # penting: supaya semua model diregister

# ---------------------------------------------------------
# Alembic config & logging
# ---------------------------------------------------------
config = context.config
print("=== ALEMBIC DB URL ===", settings.DATABASE_URL)

# Set SQLAlchemy URL ke DATABASE_URL dari settings
# (override nilai di alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata untuk autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # supaya perubahan tipe kolom juga terdeteksi
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # sama: cek perubahan tipe
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
