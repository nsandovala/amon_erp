"""Small, server-side RBAC helpers for local ERP roles."""
from functools import wraps

from flask import abort, current_app, g


READ_ROLES = {"owner", "manager", "operator", "accountant_readonly"}
WRITE_ROLES = {"owner", "manager", "operator"}
ADMIN_VIEW_ROLES = {"owner", "manager"}


def require_roles(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            # Existing non-security tests deliberately use the documented test
            # bypass. Security tests install a real local tenant context.
            if current_app.testing and not getattr(g, "tenant_enforced", True):
                return view(*args, **kwargs)
            if getattr(g, "erp_role", None) not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


require_operational_write = require_roles(*WRITE_ROLES)
require_admin_view = require_roles(*ADMIN_VIEW_ROLES)
require_owner = require_roles("owner")
