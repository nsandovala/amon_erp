from flask import g
import pytest
from werkzeug.exceptions import Forbidden

from services.authorization import require_operational_write, require_owner


def test_accountant_is_read_only_and_owner_can_administer(app):
    with app.app_context(), app.test_request_context("/"):
        g.tenant_enforced = True
        g.erp_role = "accountant_readonly"
        with pytest.raises(Forbidden):
            require_operational_write(lambda: "ok")()
        g.erp_role = "owner"
        assert require_owner(lambda: "ok")() == "ok"


def test_operator_cannot_administer_but_can_write_operationally(app):
    with app.app_context(), app.test_request_context("/"):
        g.tenant_enforced = True
        g.erp_role = "operator"
        assert require_operational_write(lambda: "ok")() == "ok"
        with pytest.raises(Forbidden):
            require_owner(lambda: "ok")()
