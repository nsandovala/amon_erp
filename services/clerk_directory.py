"""Read-only Clerk identity directory.

Clerk only supplies *visual identity* (name, email, avatar) and email -> user id
resolution. Roles, status and access always come from the local Membership.
Nothing returned here is persisted, and no Clerk role/org claim is trusted.
"""
from dataclasses import dataclass

from clerk_backend_api import Clerk
from flask import current_app

LOOKUP_TIMEOUT_MS = 3000
MAX_IDS_PER_REQUEST = 100


class ClerkDirectoryError(Exception):
    """The Clerk API could not be consulted (never carries SDK/secret details)."""


@dataclass(frozen=True)
class ClerkIdentity:
    user_id: str
    name: str | None
    email: str | None
    image_url: str | None


def _client():
    secret = current_app.config.get("CLERK_SECRET_KEY") or ""
    if not secret or current_app.config.get("AUTH_TEST_BYPASS"):
        raise ClerkDirectoryError("Clerk no está configurado.")
    return Clerk(bearer_auth=secret)


def _text(value):
    """Clerk's Nullable fields can be None or an UNSET sentinel; keep only real strings."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _primary_email(user):
    emails = getattr(user, "email_addresses", None)
    if not isinstance(emails, list):
        return None
    primary_id = getattr(user, "primary_email_address_id", None)
    chosen = next((e for e in emails if getattr(e, "id", None) == primary_id), None) or (emails[0] if emails else None)
    return _text(getattr(chosen, "email_address", None)) if chosen else None


def _identity(user):
    name = " ".join(part for part in (_text(getattr(user, "first_name", None)), _text(getattr(user, "last_name", None))) if part)
    return ClerkIdentity(
        user_id=user.id,
        name=name or _text(getattr(user, "username", None)),
        email=_primary_email(user),
        image_url=_text(getattr(user, "image_url", None)) if getattr(user, "has_image", False) else None,
    )


def identities_for(user_ids):
    """Best-effort {clerk_user_id: ClerkIdentity}. Any failure degrades to {}."""
    ids = sorted({value for value in user_ids if value})
    if not ids:
        return {}
    found = {}
    try:
        client = _client()
        for start in range(0, len(ids), MAX_IDS_PER_REQUEST):
            chunk = ids[start:start + MAX_IDS_PER_REQUEST]
            users = client.users.list(
                request={"user_id": chunk, "limit": len(chunk)}, timeout_ms=LOOKUP_TIMEOUT_MS,
            )
            for user in users or []:
                found[user.id] = _identity(user)
    except Exception:
        # Never log SDK exceptions: they may include request details.
        current_app.logger.warning("Clerk directory unavailable")
        return {}
    return found


def find_user_id_by_email(email):
    """Resolve an exact email to a Clerk user id; None if no such user.

    Raises ClerkDirectoryError when Clerk cannot be consulted, so callers can
    tell "no such user" from "directory unavailable". No user is ever created.
    """
    wanted = (email or "").strip().lower()
    if not wanted or "@" not in wanted or len(wanted) > 254:
        return None
    try:
        users = _client().users.list(
            request={"email_address": [wanted], "limit": 2}, timeout_ms=LOOKUP_TIMEOUT_MS,
        )
    except ClerkDirectoryError:
        raise
    except Exception:
        current_app.logger.warning("Clerk directory unavailable")
        raise ClerkDirectoryError("No se pudo consultar Clerk.") from None
    matches = []
    for user in users or []:
        emails = [e.email_address.lower() for e in (getattr(user, "email_addresses", None) or []) if isinstance(getattr(e, "email_address", None), str)]
        if wanted in emails:
            matches.append(user.id)
    return matches[0] if len(matches) == 1 else None
