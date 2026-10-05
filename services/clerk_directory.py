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


@dataclass(frozen=True)
class EmailResolution:
    """Outcome of resolving an exact email to a Clerk account.

    status: "found" (verified match, user_id set), "unverified" (the address is
    attached to an account but not verified) or "not_found".
    """
    status: str
    user_id: str | None = None


def _is_verified(email_address):
    """True only for an explicit Clerk verification status of "verified".

    `verification` is None for never-verified addresses; statuses such as
    unverified/failed/expired/transferable never count.
    """
    status = getattr(getattr(email_address, "verification", None), "status", None)
    return getattr(status, "value", status) == "verified"


def resolve_user_by_email(email):
    """Resolve an exact, *verified* email to a Clerk user id (read-only).

    The requested address itself must belong to the account and be verified; an
    unverified claim on the same address never wins over a verified one. Several
    verified matches (not expected) fail closed as not_found. Raises
    ClerkDirectoryError when Clerk cannot be consulted. No user is ever created.
    """
    wanted = (email or "").strip().lower()
    if not wanted or "@" not in wanted or len(wanted) > 254:
        return EmailResolution("not_found")
    try:
        users = _client().users.list(
            request={"email_address": [wanted], "limit": 10}, timeout_ms=LOOKUP_TIMEOUT_MS,
        )
    except ClerkDirectoryError:
        raise
    except Exception:
        current_app.logger.warning("Clerk directory unavailable")
        raise ClerkDirectoryError("No se pudo consultar Clerk.") from None
    verified, unverified = set(), set()
    for user in users or []:
        user_id = getattr(user, "id", None)
        if not (isinstance(user_id, str) and user_id.startswith("user_")):
            continue
        for candidate in getattr(user, "email_addresses", None) or []:
            address = getattr(candidate, "email_address", None)
            if isinstance(address, str) and address.strip().lower() == wanted:
                (verified if _is_verified(candidate) else unverified).add(user_id)
                break
    if len(verified) == 1:
        return EmailResolution("found", next(iter(verified)))
    if not verified and unverified:
        return EmailResolution("unverified")
    return EmailResolution("not_found")
