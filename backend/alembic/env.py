from logging.config import fileConfig
import importlib
import pkgutil

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import Base

# Import every module inside app.models so SQLAlchemy registers
# all mapped tables in Base.metadata before Alembic autogenerate runs.
import app.models as models_package

for module_info in pkgutil.iter_modules(models_package.__path__):
    module_name = module_info.name

    if module_name.startswith("_"):
        continue

    importlib.import_module(
        f"{models_package.__name__}.{module_name}"
    )


# Alembic Config object.
config = context.config


# Configure Python logging from alembic.ini when available.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# All SQLAlchemy tables registered by the project models.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without creating a live SQLAlchemy connection.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations using the same DATABASE_URL as the FastAPI app.
    """
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
