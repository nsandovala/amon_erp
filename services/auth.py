"""Clerk validates identity; the local Membership decides ERP admission.

AMON_ADMISSION_MODE selects how admission is decided (always fail-closed):
- "allowlist" (transitional default): the Clerk user id must be in
  AMON_ALLOWED_USER_IDS *and* resolve to a valid local tenant context.
- "membership": the allowlist is ignored; a valid local tenant context (active
  Membership, active Organization, active Branch) is the only admission rule.

No Clerk role/organization claim ever grants AMON permissions: roles and tenancy
come from the local Membership.
"""
import base64
import binascii
import re

from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions
from flask import abort, g, redirect, render_template, request, url_for

from config import resolve_admission_mode
from services.tenancy import TenantResolutionError, TenantSelectionRequired, resolve_request_tenant


def frontend_domain(key):
    try:
        if not key.startswith(('pk_test_', 'pk_live_')):
            return None
        encoded = key.split('_', 2)[2]
        domain = base64.b64decode(encoded + '=' * (-len(encoded) % 4), validate=True).decode().removesuffix('$')
        return domain if re.fullmatch(r'[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)+', domain) else None
    except (ValueError, UnicodeError, binascii.Error):
        return None


def init_auth(app):
    if app.config['AUTH_TEST_BYPASS'] and not app.testing:
        raise RuntimeError('AUTH_TEST_BYPASS solo se permite en tests.')
    admission_mode = resolve_admission_mode(app.config.get('AMON_ADMISSION_MODE'))

    @app.context_processor
    def auth_context():
        key = app.config['CLERK_PUBLISHABLE_KEY']
        return {'clerk_publishable_key': key, 'clerk_domain': frontend_domain(key)}

    @app.before_request
    def authenticate():
        g.user_id = None
        g.erp_access = False
        g.membership = None
        g.erp_role = None
        g.organization = None
        g.organization_id = None
        g.branch = None
        g.branch_id = None
        g.tenant_enforced = True
        g.tenant_selection_required = False
        if request.endpoint == 'health':
            return None
        if app.testing and app.config['AUTH_TEST_BYPASS']:
            g.erp_access = True
            g.tenant_enforced = False
            return None
        if request.endpoint == 'static':
            return None
        if not (app.config['CLERK_SECRET_KEY'] and
                frontend_domain(app.config['CLERK_PUBLISHABLE_KEY']) and
                app.config['CLERK_AUTHORIZED_PARTIES']):
            return render_template('auth/access.html', auth_unavailable=True), 503
        try:
            state = authenticate_request(request, AuthenticateRequestOptions(
                secret_key=app.config['CLERK_SECRET_KEY'],
                authorized_parties=app.config['CLERK_AUTHORIZED_PARTIES'],
                accepts_token=['session_token'],
            ))
        except Exception:
            # Never log credentials, tokens, request headers or SDK exceptions.
            app.logger.warning('Clerk authentication unavailable')
            return render_template('auth/access.html', auth_unavailable=True), 503
        payload = state.payload or {}
        if (state.is_signed_in and isinstance(payload.get('sub'), str)
                and payload['sub'].startswith('user_')
                and payload.get('sts') != 'pending'
                and payload.get('azp') in app.config['CLERK_AUTHORIZED_PARTIES']):
            g.user_id = payload['sub']
            # The allowlist is an extra gate only in "allowlist" mode; in "membership"
            # mode the local tenant resolution below is the sole admission rule.
            g.erp_access = (admission_mode == 'membership'
                            or g.user_id in app.config['AMON_ALLOWED_USER_IDS'])
            if g.erp_access:
                try:
                    resolve_request_tenant(g.user_id)
                except TenantSelectionRequired:
                    g.tenant_selection_required = True
                except TenantResolutionError:
                    # An authenticated identity never gets tenant access without an
                    # active local Membership, Organization and Branch.
                    g.erp_access = False
        selector_endpoint = 'tenant_context.selector'
        if request.endpoint == 'auth_access':
            if g.user_id and g.erp_access:
                return redirect(url_for(selector_endpoint if g.tenant_selection_required else 'dashboard.index'))
            return None
        if not g.user_id:
            if request.method in ('GET', 'HEAD'):
                return redirect(url_for('auth_access'))
            abort(401)
        if not g.erp_access:
            return render_template('auth/access.html'), 403
        if g.tenant_selection_required and request.endpoint != selector_endpoint:
            if request.method in ('GET', 'HEAD'):
                return redirect(url_for(selector_endpoint))
            abort(403)
        return None

    @app.route('/auth')
    def auth_access():
        return render_template('auth/access.html')

    @app.after_request
    def private_response(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Referrer-Policy'] = 'same-origin'
        return response
