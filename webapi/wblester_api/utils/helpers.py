"""Shared helpers: case conversion, serialization, audit logging."""

import re

from mongoengine.base import BaseDocument

from ..models.documents import AuditTrail, utcnow

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])[A-Z]")


def camel_to_snake(name: str) -> str:
    return _CAMEL_RE.sub(lambda m: "_" + m.group(0), name).lower()


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    first = parts[0].lower() if parts else ""
    rest = [p[:1].upper() + p[1:].lower() for p in parts[1:] if p]
    return first + "".join(rest)


def document_to_dict(doc: BaseDocument) -> dict:
    """Serialize a MongoEngine document into a JSON-safe dict (snake_case)."""
    data = {}
    for field_name in doc._fields_ordered:
        value = getattr(doc, field_name)
        if isinstance(value, BaseDocument):
            data[field_name] = document_to_dict(value)
            continue
        if hasattr(value, "isoformat"):
            data[field_name] = value.isoformat(sep=" ") if field_name.endswith(
                ("datetime", "date")
            ) else value.isoformat()
        elif isinstance(value, bytes):
            data[field_name] = value.decode("utf-8", errors="replace")
        elif isinstance(value, (int, float, str, bool)) or value is None:
            data[field_name] = value
        elif isinstance(value, dict):
            data[field_name] = value
        elif isinstance(value, (list, tuple)):
            data[field_name] = list(value)
        else:
            data[field_name] = str(value)
    # Mongo internal id is not part of the sync contract.
    data.pop("id", None)
    return data


def apply_payload(doc: BaseDocument, payload: dict) -> None:
    """Apply a camelCase or snake_case payload onto a document instance."""
    for key, value in payload.items():
        field_name = camel_to_snake(key) if not key.islower() else key
        if field_name == "id" or field_name not in doc._fields_ordered:
            continue
        if field_name in ("created_datetime", "last_modified_date", "current_version"):
            # Managed server-side.
            continue
        setattr(doc, field_name, value)


def log_audit(
    change_type: str,
    affected_table: str,
    old_data: dict,
    new_data: dict,
    username: str | None = None,
    user_id=None,
    description: str | None = None,
) -> AuditTrail:
    trail = AuditTrail(
        description=description
        or f"{change_type} on {affected_table}",
        old_data=old_data or {},
        new_data=new_data or {},
        change_time=utcnow(),
        change_type=change_type,
        affected_table=affected_table,
        username=username,
        user_id=str(user_id) if user_id is not None else None,
    )
    trail.save()
    return trail


def next_id(doc_class, id_field: str) -> int:
    """Generate the next sequential integer for an external id field."""
    highest = doc_class.objects.order_by("-" + id_field).first()
    return (getattr(highest, id_field) + 1) if highest else 1
