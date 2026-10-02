"""Clerk validates identity; the local allowlist controls ERP admission.

No Clerk role/organization claims grant AMON permissions. Full RBAC is deferred.
"""
import base64
import binascii
import re

from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions
from flask import abort, g, redirect, render_template, request, url_for


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

    @app.context_processor
    def auth_context():
        key = app.config['CLERK_PUBLISHABLE_KEY']
        return {'clerk_publishable_key': key, 'clerk_domain': frontend_domain(key)}

    @app.before_request
    def authenticate():
        g.user_id = None
        g.erp_access = False
        if request.endpoint == 'health':
            return None
        if app.testing and app.config['AUTH_TEST_BYPASS']:
            g.erp_access = True
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
            g.erp_access = g.user_id in app.config['AMON_ALLOWED_USER_IDS']
        if request.endpoint == 'auth_access':
            if g.user_id and g.erp_access:
                return redirect(url_for('dashboard.index'))
            return None
        if not g.user_id:
            if request.method in ('GET', 'HEAD'):
                return redirect(url_for('auth_access'))
            abort(401)
        if not g.erp_access:
            return render_template('auth/access.html'), 403
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
