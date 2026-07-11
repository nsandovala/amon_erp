import json

from models.audit_log import AuditLog


def create_audit_log(action, entity_type, entity_id, old_values=None, new_values=None):
    return AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=_serialize(old_values),
        new_values=_serialize(new_values),
    )


def _serialize(values):
    if values is None:
        return None
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
