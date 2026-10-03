from sqlalchemy import func, inspect, select, text


EXPECTED_SCHEMA = {
    "work_sessions": {
        "id", "business_date", "opened_at", "opening_cash", "closing_cash_counted",
        "status", "deleted_at", "organization_id", "branch_id",
    },
    "sales": {"id", "work_session_id", "occurred_at", "amount", "status", "deleted_at", "organization_id", "branch_id"},
    "expenses": {"id", "work_session_id", "occurred_at", "amount", "status", "deleted_at", "organization_id", "branch_id"},
    "audit_logs": {"id", "action", "entity_type", "entity_id", "created_at", "organization_id", "branch_id", "actor_user_id"},
}


def database_is_available(bind):
    try:
        with bind.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def schema_errors(bind):
    if not database_is_available(bind):
        return ["No fue posible conectar con la base de datos."]

    try:
        inspector = inspect(bind)
        existing_tables = set(inspector.get_table_names())
        errors = []
        for table_name, expected_columns in EXPECTED_SCHEMA.items():
            if table_name not in existing_tables:
                errors.append(f"Falta la tabla requerida: {table_name}.")
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name in sorted(expected_columns - existing_columns):
                errors.append(f"Falta la columna requerida: {table_name}.{column_name}.")
        if "work_sessions" in existing_tables:
            indexes = {index["name"]: index for index in inspector.get_indexes("work_sessions")}
            open_index = indexes.get("uq_work_sessions_open_per_branch")
            dialect_option = f"{bind.dialect.name}_where"
            predicate = str((open_index or {}).get("dialect_options", {}).get(dialect_option, "")).lower()
            if (
                not open_index
                or not open_index.get("unique")
                or open_index.get("column_names") != ["organization_id", "branch_id"]
                or "status" not in predicate
                or "'open'" not in predicate
                or "deleted_at" not in predicate
            ):
                errors.append("Falta el índice único requerido para la jornada abierta.")
        return errors
    except Exception:
        return ["No fue posible inspeccionar el schema de la base de datos."]


def record_counts(bind):
    from models.audit_log import AuditLog
    from models.expense import Expense
    from models.sale import Sale
    from models.work_session import WorkSession

    models = {
        "sales": Sale,
        "expenses": Expense,
        "work_sessions": WorkSession,
        "audit_logs": AuditLog,
    }
    with bind.connect() as connection:
        return {
            table_name: connection.execute(
                select(func.count()).select_from(model)
            ).scalar_one()
            for table_name, model in models.items()
        }
