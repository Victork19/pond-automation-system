"""Authentication, sessions, CSRF protection, and encrypted provider secrets."""
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta
import hashlib
import hmac
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from .core import settings, now_utc
from .db import User, AuthSession

def _required_secret(value: str | None, name: str) -> bytes:
    if not value:
        raise RuntimeError(f'{name} must be configured')
    return value.encode()

def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 240_000)
    return f'{urlsafe_b64encode(salt).decode()}${urlsafe_b64encode(digest).decode()}'

def password_matches(password: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split('$', 1)
        actual = password_hash(password, urlsafe_b64decode(salt + '===' )).split('$', 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def ensure_bootstrap_admin(s: Session) -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    email = settings.bootstrap_admin_email.strip().lower()
    user = s.query(User).filter_by(email=email).one_or_none()
    if not user:
        s.add(User(email=email, password_hash=password_hash(settings.bootstrap_admin_password), role='owner', active=True))
        s.commit()

def production_guard() -> None:
    if settings.app_env.lower() == 'production':
        _required_secret(settings.session_secret, 'SESSION_SECRET')
        _required_secret(settings.google_token_encryption_key, 'GOOGLE_TOKEN_ENCRYPTION_KEY')
        if not settings.cookie_secure:
            raise RuntimeError('COOKIE_SECURE must be true in production')
        if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
            raise RuntimeError('BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD must be configured')

def create_session(s: Session, user: User) -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    secret = _required_secret(settings.session_secret or 'development-only-session-secret', 'SESSION_SECRET')
    token_hash = hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()
    s.add(AuthSession(token_hash=token_hash, csrf_token=csrf, user_id=user.id,
                      expires_at=now_utc() + timedelta(hours=settings.session_ttl_hours)))
    s.commit()
    return token, csrf

def authenticated_user(request, s: Session, session_token: str | None = None) -> User:
    if settings.app_env.lower() != 'production' and not settings.session_secret:
        # Development mode remains convenient; production cannot use this bypass.
        return User(id=0, email='local-operator@example.invalid', role='owner', active=True)
    if not session_token:
        raise HTTPException(401, 'Authentication required')
    secret = _required_secret(settings.session_secret, 'SESSION_SECRET')
    token_hash = hmac.new(secret, session_token.encode(), hashlib.sha256).hexdigest()
    item = s.query(AuthSession).filter_by(token_hash=token_hash).one_or_none()
    expiry = item.expires_at.replace(tzinfo=__import__('datetime').timezone.utc) if item else None
    if not item or not item.user.active or expiry < now_utc():
        raise HTTPException(401, 'Session expired or invalid')
    item.last_seen_at = now_utc()
    return item.user

def require_role(user: User, *roles: str) -> User:
    if user.role not in roles:
        raise HTTPException(403, 'Insufficient role for this operation')
    return user

def require_csrf(request: Request, csrf_header: str | None, session_token: str | None, s: Session) -> None:
    if request.method in {'GET', 'HEAD', 'OPTIONS'} or (settings.app_env.lower() != 'production' and not settings.session_secret):
        return
    if not session_token or not csrf_header:
        raise HTTPException(403, 'CSRF token required')
    secret = _required_secret(settings.session_secret, 'SESSION_SECRET')
    token_hash = hmac.new(secret, session_token.encode(), hashlib.sha256).hexdigest()
    item = s.query(AuthSession).filter_by(token_hash=token_hash).one_or_none()
    if not item or not hmac.compare_digest(item.csrf_token, csrf_header):
        raise HTTPException(403, 'Invalid CSRF token')

def encrypt_secret(value: str) -> str:
    key = _required_secret(settings.google_token_encryption_key or 'development-only-google-key-32', 'GOOGLE_TOKEN_ENCRYPTION_KEY')
    key = hashlib.sha256(key).digest()
    nonce = os.urandom(12)
    return urlsafe_b64encode(nonce + AESGCM(key).encrypt(nonce, value.encode(), None)).decode()

def decrypt_secret(value: str) -> str:
    key = _required_secret(settings.google_token_encryption_key or 'development-only-google-key-32', 'GOOGLE_TOKEN_ENCRYPTION_KEY')
    key = hashlib.sha256(key).digest()
    raw = urlsafe_b64decode(value.encode())
    return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode()
