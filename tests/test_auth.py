import base64
import time
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import g

from services.auth import frontend_domain


@pytest.fixture
def auth_app(app):
    app.config.update(
        AUTH_TEST_BYPASS=False,
        CLERK_SECRET_KEY='sk_test_not_a_real_key',
        CLERK_PUBLISHABLE_KEY='pk_test_' + base64.b64encode(b'example.clerk.accounts.dev$').decode(),
        CLERK_AUTHORIZED_PARTIES=['http://localhost'],
        AMON_ALLOWED_USER_IDS=['user_allowed'],
    )
    from models import db_session
    from models.membership import Membership
    from services.organizations import bootstrap_the_best_burger
    with app.app_context():
        organization, _branch = bootstrap_the_best_burger()
        db_session.add(Membership(
            organization_id=organization.id,
            clerk_user_id='user_allowed',
            role='owner',
        ))
        db_session.commit()
    return app


@pytest.fixture
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def signed_token(key, **overrides):
    claims = dict(sub='user_allowed', sid='sess_test', azp='http://localhost',
                  iat=int(time.time()), nbf=int(time.time()) - 10,
                  exp=int(time.time()) + 300)
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm='RS256', headers={'kid': 'test'})


@pytest.fixture
def verified_client(auth_app, signing_key):
    from services import auth
    real_authenticate = auth.authenticate_request
    public_key = signing_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    def authenticate_locally(request, options):
        assert options.accepts_token == ['session_token']
        options.jwt_key = public_key
        return real_authenticate(request, options)

    with patch.object(auth, 'authenticate_request', side_effect=authenticate_locally):
        yield auth_app.test_client()


@pytest.mark.parametrize('path', ['/', '/monthly-summary.csv', '/history', '/sales'])
def test_anonymous_cannot_read_erp(auth_app, path):
    response = auth_app.test_client().get(path)
    assert response.status_code == 302
    assert response.location == '/auth'
    assert response.headers['Cache-Control'] == 'no-store'


def test_anonymous_cannot_write(auth_app):
    assert auth_app.test_client().post('/backup').status_code == 401


def test_public_access_does_not_query_finances(auth_app):
    with patch('app.active_work_session', side_effect=AssertionError('financial query')):
        response = auth_app.test_client().get('/auth')
    assert response.status_code == 200
    assert 'Gestiona tu negocio desde un solo lugar.'.encode() in response.data
    assert b'Ingresa con tu cuenta AMON para continuar.' in response.data
    assert b'Crear cuenta' not in response.data
    assert b'sk_test_not_a_real_key' not in response.data


def test_missing_configuration_fails_closed(auth_app):
    auth_app.config['CLERK_SECRET_KEY'] = ''
    assert auth_app.test_client().get('/').status_code == 503


def test_valid_bearer_sets_identity(verified_client, signing_key):
    with verified_client:
        response = verified_client.get('/', headers={'Authorization': 'Bearer ' + signed_token(signing_key)})
        assert response.status_code == 200
        assert g.user_id == 'user_allowed'


def test_valid_cookie(verified_client, signing_key):
    verified_client.set_cookie('__session', signed_token(signing_key))
    assert verified_client.get('/').status_code == 200


def test_authorized_account_is_redirected_from_auth(verified_client, signing_key):
    response = verified_client.get('/auth', headers={'Authorization': 'Bearer ' + signed_token(signing_key)})
    assert response.status_code == 302
    assert response.location == '/'


def test_multiple_valid_memberships_require_context_selection(auth_app, verified_client, signing_key):
    from models import db_session
    from models.branch import Branch
    from models.membership import Membership
    from models.organization import Organization
    with auth_app.app_context():
        organization = Organization(name="2MUCH", slug="2much", entity_type="company")
        db_session.add(organization); db_session.flush()
        db_session.add_all([
            Branch(organization_id=organization.id, name="Principal", slug="principal"),
            Membership(organization_id=organization.id, clerk_user_id="user_allowed", role="owner"),
        ])
        db_session.commit()
    response = verified_client.get('/', headers={'Authorization': 'Bearer ' + signed_token(signing_key)})
    assert response.status_code == 302
    assert response.location == '/contexto/'


def test_signed_in_account_without_access_sees_safe_access_state(verified_client, signing_key):
    response = verified_client.get('/auth', headers={'Authorization': 'Bearer ' + signed_token(signing_key, sub='user_new')})
    assert response.status_code == 200
    assert 'Tu cuenta está activa, pero aún no tiene acceso a una organización.'.encode() in response.data
    assert b'user_new' not in response.data


@pytest.mark.parametrize('claims', [
    {'exp': 1}, {'nbf': 9999999999}, {'azp': 'https://untrusted.example'},
    {'azp': None}, {'sub': None}, {'sts': 'pending'},
])
def test_invalid_claims_denied(verified_client, signing_key, claims):
    response = verified_client.get('/', headers={'Authorization': 'Bearer ' + signed_token(signing_key, **claims)})
    assert response.status_code == 302


def test_forged_signature_denied(verified_client):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    response = verified_client.get('/', headers={'Authorization': 'Bearer ' + signed_token(other_key)})
    assert response.status_code == 302


def test_signup_does_not_grant_access_or_trust_clerk_role(verified_client, signing_key):
    response = verified_client.get('/', headers={'Authorization': 'Bearer ' + signed_token(
        signing_key, sub='user_new', role='owner', org_role='org:admin')})
    assert response.status_code == 403
    html = response.get_data(as_text=True)
    assert "Tu cuenta está activa, pero aún no tiene acceso a una organización." in html
    assert "The Best Burger" not in html
    assert "user_new" not in html


def test_csrf_still_required(verified_client, signing_key):
    response = verified_client.post('/backup', headers={'Authorization': 'Bearer ' + signed_token(signing_key)})
    assert response.status_code == 400


def test_sdk_failure_fails_closed(auth_app):
    with patch('services.auth.authenticate_request', side_effect=RuntimeError('private detail')):
        response = auth_app.test_client().get('/')
    assert response.status_code == 503
    assert b'private detail' not in response.data


def test_invalid_publishable_key_is_not_a_script_url():
    assert frontend_domain('pk_test_' + base64.b64encode(b'evil.example/path$').decode()) is None


def test_test_bypass_rejected_outside_testing():
    from flask import Flask
    from services.auth import init_auth
    app = Flask(__name__)
    app.config['AUTH_TEST_BYPASS'] = True
    with pytest.raises(RuntimeError, match='solo se permite en tests'):
        init_auth(app)
