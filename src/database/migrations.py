from sqlalchemy import inspect

from src.core.logger import logger
from src.database.database import engine
from src.database.models import Base


def run_migrations() -> None:
    logger.info("Running migrations (create_all)")
    Base.metadata.create_all(bind=engine)


def check_database_status() -> dict:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    missing_tables = expected_tables - existing_tables

    return {
        "existing_tables": sorted(existing_tables),
        "expected_tables": sorted(expected_tables),
        "missing_tables": sorted(missing_tables),
        "up_to_date": not missing_tables,
    }
