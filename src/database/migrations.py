from sqlalchemy import inspect, text

from src.core.logger import logger
from src.database.database import engine
from src.database.models import Base


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue

                column_type = column.type.compile(dialect=engine.dialect)
                connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {column_type}'))
                logger.info(f"Added missing column {table_name}.{column.name}")


def run_migrations() -> None:
    logger.info("Running migrations (create_all)")
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


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
