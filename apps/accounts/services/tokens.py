import hashlib
from datetime import timedelta

from django.core.signing import BadSignature, SignatureExpired, dumps, loads
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PasswordSetupToken, User

TOKEN_TTL = timedelta(days=7)
TOKEN_SALT = "merrymeal.password_setup_token.v1"


class InvalidTokenError(Exception):
    """Signature failed or payload malformed."""


class ExpiredTokenError(Exception):
    """Token age > TTL or DB row past `expires_at`."""


class ConsumedTokenError(Exception):
    """Token was already used. Reuse is forbidden."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_password_setup_token(user: User) -> str:
    """Returns the signed token string. Persists the hash and expiry."""
    token = dumps({"uid": user.id}, salt=TOKEN_SALT)
    PasswordSetupToken.objects.create(
        user=user,
        token_hash=_hash(token),
        expires_at=timezone.now() + TOKEN_TTL,
    )
    return token


def _decode_payload(token: str) -> int:
    """Verify signature + extract ``uid``. Raises Invalid/Expired errors."""
    try:
        payload = loads(token, salt=TOKEN_SALT, max_age=TOKEN_TTL.total_seconds())
    except SignatureExpired as exc:
        raise ExpiredTokenError(str(exc)) from exc
    except BadSignature as exc:
        raise InvalidTokenError(str(exc)) from exc

    uid = payload.get("uid")
    if not isinstance(uid, int):
        raise InvalidTokenError("payload missing uid")
    return uid


def verify_password_setup_token(token: str) -> User:
    """Read-only token check. Returns the User the token belongs to.

    Use on GET handlers that need to know whether to show the
    set-password form or a friendly error. Does **not** mark the token
    used — the actual single-use consume happens in
    ``consume_password_setup_token`` on POST.

    Raises InvalidTokenError / ExpiredTokenError / ConsumedTokenError.
    """
    uid = _decode_payload(token)
    token_hash = _hash(token)
    row = (
        PasswordSetupToken.objects
        .filter(user_id=uid, token_hash=token_hash)
        .first()
    )
    if row is None:
        raise InvalidTokenError("token not found")
    if row.used_at is not None:
        raise ConsumedTokenError("token already used")
    if row.expires_at <= timezone.now():
        raise ExpiredTokenError("token expired (db row)")
    return User.objects.get(pk=uid)


def consume_password_setup_token(token: str) -> User:
    """Returns the User the token belongs to. Marks it used. Single-use.

    Raises InvalidTokenError / ExpiredTokenError / ConsumedTokenError.
    """
    uid = _decode_payload(token)
    token_hash = _hash(token)
    with transaction.atomic():
        row = (
            PasswordSetupToken.objects
            .select_for_update()
            .filter(user_id=uid, token_hash=token_hash)
            .first()
        )
        if row is None:
            raise InvalidTokenError("token not found")
        if row.used_at is not None:
            raise ConsumedTokenError("token already used")
        if row.expires_at <= timezone.now():
            raise ExpiredTokenError("token expired (db row)")

        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])

    return User.objects.get(pk=uid)
