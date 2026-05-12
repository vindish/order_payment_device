from sqlalchemy import create_engine, inspect, text

from app.core.config import settings


INITIAL_REVISION = "202605120001"
BASELINE_TABLES = {"users", "devices", "orders"}


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column(connection, columns: set[str], table_name: str, column_name: str, definition: str) -> None:
    if column_name not in columns:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
        columns.add(column_name)


def _set_not_null(connection, table_name: str, column_name: str, fill_expression: str | None = None) -> None:
    if fill_expression is not None:
        connection.execute(text(f"UPDATE {table_name} SET {column_name} = {fill_expression} WHERE {column_name} IS NULL"))
    connection.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL"))


def _create_index(connection, indexes: set[str], name: str, table_name: str, columns: str, unique: bool = False) -> None:
    if name in indexes:
        return

    unique_sql = "UNIQUE " if unique else ""
    connection.execute(text(f"CREATE {unique_sql}INDEX {name} ON {table_name} ({columns})"))
    indexes.add(name)


def _reconcile_baseline_schema(connection, inspector) -> None:
    user_columns = _column_names(inspector, "users")
    _add_column(connection, user_columns, "users", "is_active", "BOOLEAN")
    _add_column(connection, user_columns, "users", "created_at", "TIMESTAMP WITHOUT TIME ZONE")
    _add_column(connection, user_columns, "users", "updated_at", "TIMESTAMP WITHOUT TIME ZONE")
    _set_not_null(connection, "users", "username")
    _set_not_null(connection, "users", "password")
    _set_not_null(connection, "users", "is_active", "TRUE")
    _set_not_null(connection, "users", "created_at", "CURRENT_TIMESTAMP")
    _set_not_null(connection, "users", "updated_at", "CURRENT_TIMESTAMP")

    user_indexes = _index_names(inspector, "users")
    _create_index(connection, user_indexes, "ix_users_id", "users", "id")
    _create_index(connection, user_indexes, "ix_users_username", "users", "username", unique=True)

    device_columns = _column_names(inspector, "devices")
    _add_column(connection, device_columns, "devices", "name", "VARCHAR(128)")
    _add_column(connection, device_columns, "devices", "last_seen_at", "TIMESTAMP WITHOUT TIME ZONE")
    _add_column(connection, device_columns, "devices", "created_at", "TIMESTAMP WITHOUT TIME ZONE")
    _add_column(connection, device_columns, "devices", "updated_at", "TIMESTAMP WITHOUT TIME ZONE")
    _set_not_null(connection, "devices", "sn")
    _set_not_null(connection, "devices", "status", "'offline'")
    _set_not_null(connection, "devices", "created_at", "CURRENT_TIMESTAMP")
    _set_not_null(connection, "devices", "updated_at", "CURRENT_TIMESTAMP")

    device_indexes = _index_names(inspector, "devices")
    _create_index(connection, device_indexes, "ix_devices_id", "devices", "id")
    _create_index(connection, device_indexes, "ix_devices_sn", "devices", "sn", unique=True)

    order_columns = _column_names(inspector, "orders")
    _add_column(connection, order_columns, "orders", "amount", "NUMERIC(10, 2)")
    _add_column(connection, order_columns, "orders", "currency", "VARCHAR(8)")
    _add_column(connection, order_columns, "orders", "payment_provider", "VARCHAR(32)")
    _add_column(connection, order_columns, "orders", "payment_trade_no", "VARCHAR(128)")
    _add_column(connection, order_columns, "orders", "retry_count", "INTEGER")
    _add_column(connection, order_columns, "orders", "error_message", "VARCHAR(512)")
    _add_column(connection, order_columns, "orders", "paid_at", "TIMESTAMP WITHOUT TIME ZONE")
    _add_column(connection, order_columns, "orders", "unlocked_at", "TIMESTAMP WITHOUT TIME ZONE")
    _add_column(connection, order_columns, "orders", "created_at", "TIMESTAMP WITHOUT TIME ZONE")
    _add_column(connection, order_columns, "orders", "updated_at", "TIMESTAMP WITHOUT TIME ZONE")
    _set_not_null(connection, "orders", "user_id")
    _set_not_null(connection, "orders", "device_id")
    _set_not_null(connection, "orders", "amount", "0")
    _set_not_null(connection, "orders", "currency", "'CNY'")
    _set_not_null(connection, "orders", "status", "'init'")
    _set_not_null(connection, "orders", "retry_count", "0")
    _set_not_null(connection, "orders", "created_at", "CURRENT_TIMESTAMP")
    _set_not_null(connection, "orders", "updated_at", "CURRENT_TIMESTAMP")

    order_indexes = _index_names(inspector, "orders")
    _create_index(connection, order_indexes, "ix_orders_device_id", "orders", "device_id")
    _create_index(connection, order_indexes, "ix_orders_id", "orders", "id")
    _create_index(connection, order_indexes, "ix_orders_payment_trade_no", "orders", "payment_trade_no")
    _create_index(connection, order_indexes, "ix_orders_status", "orders", "status")
    _create_index(connection, order_indexes, "ix_orders_user_id", "orders", "user_id")


def _stamp_baseline(connection) -> None:
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        )
    )
    connection.execute(
        text(
            "INSERT INTO alembic_version (version_num) VALUES (:revision) "
            "ON CONFLICT (version_num) DO NOTHING"
        ),
        {"revision": INITIAL_REVISION},
    )


def main() -> None:
    engine = create_engine(settings.DATABASE_URL)

    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        if not BASELINE_TABLES.issubset(tables):
            return

        _reconcile_baseline_schema(connection, inspector)
        _stamp_baseline(connection)
        print(f"Prepared existing baseline schema for Alembic revision {INITIAL_REVISION}.")


if __name__ == "__main__":
    main()
