"""Auth-related exceptions. Framework-agnostic."""


class AuthError(Exception):
    """Base class for all authentication errors."""

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason or message


class InvalidToken(AuthError):
    """Token signature, audience, issuer, or structure is invalid."""


class TokenExpired(AuthError):
    """Token signature is valid but the token has expired."""


class JWKSFetchError(AuthError):
    """JWKS endpoint unreachable or returned malformed data."""








"""Auth configuration loaded from environment variables."""
from __future__ import annotations

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """OIDC/JWT verification settings.

    In this deployment the gateway (CASSO/Apigee) handles the full OIDC flow.
    FastAPI only verifies the JWT in the Authorization header, so we need
    the JWKS URI, the issuer, and the audience (which equals client_id).
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=None,
        extra="ignore",
        case_sensitive=True,
    )

    env: str = Field(alias="ENV")
    auth_enabled: bool = Field(alias="AUTH_ENABLED", default=True)

    oidc_client_id: str = Field(alias="OIDC_CLIENT_ID")
    oidc_client_secret: str | None = Field(alias="OIDC_CLIENT_SECRET", default=None)
    oidc_issuer: HttpUrl = Field(alias="OIDC_ISSUER")
    oidc_jwks_uri: HttpUrl = Field(alias="OIDC_JWKS_URI")
    oidc_userinfo_endpoint: HttpUrl | None = Field(
        alias="OIDC_USERINFO_ENDPOINT", default=None
    )

    jwks_cache_ttl_seconds: int = Field(default=900, ge=60)
    jwks_http_timeout_seconds: float = Field(default=5.0, gt=0)

    @field_validator("env")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def _reject_unsafe_bypass(self) -> AuthSettings:
        if not self.auth_enabled and self.env in {"stg", "prd"}:
            raise ValueError(
                f"AUTH_ENABLED=false is forbidden in env={self.env!r}"
            )
        return self

    @property
    def audience(self) -> str:
        return self.oidc_client_id

    @property
    def issuer(self) -> str:
        return str(self.oidc_issuer).rstrip("/")




"""JWKS client with TTL cache and unknown-kid refresh."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
from jwt.algorithms import RSAAlgorithm
from loguru import logger

from .exceptions import JWKSFetchError


@dataclass(frozen=True)
class _CacheEntry:
    keys: dict[str, Any]
    fetched_at: float


class JWKSClient:
    """Fetches and caches JWKS keys with TTL.

    Refresh policy: serve from cache while fresh; on unknown kid or expiry,
    refetch once. Bad signatures of known kids do NOT trigger a refresh
    (DoS protection).
    """

    def __init__(
        self,
        jwks_uri: str,
        *,
        ttl_seconds: int = 900,
        http_timeout: float = 5.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._jwks_uri = jwks_uri
        self._ttl = ttl_seconds
        self._timeout = http_timeout
        self._client = http_client or httpx.Client(timeout=http_timeout)
        self._cache: _CacheEntry | None = None
        self._lock = threading.Lock()

    def get_key(self, kid: str) -> Any:
        """Return the public key object for the given kid.

        Raises JWKSFetchError if the kid cannot be found even after refresh.
        """
        entry = self._cache
        if entry is None or self._is_stale(entry) or kid not in entry.keys:
            entry = self._refresh()
        key = entry.keys.get(kid)
        if key is None:
            entry = self._refresh()
            key = entry.keys.get(kid)
        if key is None:
            raise JWKSFetchError(f"Unknown kid: {kid}", reason="unknown_kid")
        return key

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None

    def _is_stale(self, entry: _CacheEntry) -> bool:
        return (time.monotonic() - entry.fetched_at) > self._ttl

    def _refresh(self) -> _CacheEntry:
        with self._lock:
            if self._cache and not self._is_stale(self._cache):
                return self._cache
            try:
                resp = self._client.get(self._jwks_uri)
                resp.raise_for_status()
                payload = resp.json()
            except httpx.HTTPError as exc:
                logger.error("jwks_fetch_failed", uri=self._jwks_uri, error=str(exc))
                raise JWKSFetchError("Failed to fetch JWKS") from exc

            keys = self._parse_jwks(payload)
            self._cache = _CacheEntry(keys=keys, fetched_at=time.monotonic())
            logger.info("jwks_refreshed", key_count=len(keys))
            return self._cache

    @staticmethod
    def _parse_jwks(payload: dict[str, Any]) -> dict[str, Any]:
        raw_keys = payload.get("keys")
        if not isinstance(raw_keys, list):
            raise JWKSFetchError("Malformed JWKS: missing 'keys' array")
        result: dict[str, Any] = {}
        for jwk in raw_keys:
            kid = jwk.get("kid")
            if not kid:
                continue
            try:
                result[kid] = RSAAlgorithm.from_jwk(jwk)
            except Exception as exc:  # noqa: BLE001
                logger.warning("jwks_skip_bad_key", kid=kid, error=str(exc))
        if not result:
            raise JWKSFetchError("JWKS contained no usable keys")
        return result









"""Framework-agnostic JWT verifier. No FastAPI imports."""
from __future__ import annotations

from typing import Any

import jwt
from loguru import logger

from .exceptions import InvalidToken, TokenExpired
from .jwks import JWKSClient


class JWTVerifier:
    """Verifies RS256 JWTs against a JWKS source.

    Pure verification logic — no HTTP framework dependencies. Inject the
    JWKSClient for testability (swap with a stub in unit tests).
    """

    _ALGORITHMS = ("RS256",)

    def __init__(
        self,
        jwks_client: JWKSClient,
        *,
        audience: str,
        issuer: str,
    ) -> None:
        self._jwks = jwks_client
        self._audience = audience
        self._issuer = issuer

    def verify(self, token: str) -> dict[str, Any]:
        """Verify token and return the decoded payload.

        Raises TokenExpired or InvalidToken on failure.
        """
        kid = self._extract_kid(token)
        key = self._jwks.get_key(kid)

        try:
            return jwt.decode(
                token,
                key=key,
                algorithms=list(self._ALGORITHMS),
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "aud", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            logger.warning("jwt_expired", kid=kid)
            raise TokenExpired("Token has expired", reason="expired") from exc
        except jwt.InvalidAudienceError as exc:
            logger.warning("jwt_bad_audience", expected=self._audience)
            raise InvalidToken("Invalid audience", reason="bad_audience") from exc
        except jwt.InvalidIssuerError as exc:
            logger.warning("jwt_bad_issuer", expected=self._issuer)
            raise InvalidToken("Invalid issuer", reason="bad_issuer") from exc
        except jwt.InvalidSignatureError as exc:
            logger.warning("jwt_bad_signature", kid=kid)
            raise InvalidToken("Invalid signature", reason="bad_signature") from exc
        except jwt.InvalidTokenError as exc:
            logger.warning("jwt_invalid", error=str(exc))
            raise InvalidToken(str(exc), reason="invalid") from exc

    @staticmethod
    def _extract_kid(token: str) -> str:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.DecodeError as exc:
            raise InvalidToken("Malformed token header", reason="malformed") from exc
        kid = header.get("kid")
        if not kid:
            raise InvalidToken("Token header missing 'kid'", reason="missing_kid")
        return kid





"""FastAPI dependency for protecting routes."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from .config import AuthSettings
from .exceptions import AuthError
from .jwks import JWKSClient
from .verifier import JWTVerifier

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_settings() -> AuthSettings:
    return AuthSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def _get_verifier() -> JWTVerifier:
    settings = _get_settings()
    jwks = JWKSClient(
        jwks_uri=str(settings.oidc_jwks_uri),
        ttl_seconds=settings.jwks_cache_ttl_seconds,
        http_timeout=settings.jwks_http_timeout_seconds,
    )
    return JWTVerifier(
        jwks_client=jwks,
        audience=settings.audience,
        issuer=settings.issuer,
    )


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Return decoded JWT payload for the authenticated caller.

    Raises HTTP 401 if the token is missing, invalid, or expired.
    Honors AUTH_ENABLED=false for local dev (rejected in stg/prd by config).
    """
    from fastapi import HTTPException, status

    settings = _get_settings()
    if not settings.auth_enabled:
        return {"sub": "dev-bypass", "aud": settings.audience, "_bypass": True}

    client_ip = request.client.host if request.client else "unknown"

    if creds is None or creds.scheme.lower() != "bearer":
        logger.warning("auth_missing_bearer", path=request.url.path, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = _get_verifier().verify(creds.credentials)
    except AuthError as exc:
        logger.warning(
            "auth_rejected",
            path=request.url.path,
            ip=client_ip,
            reason=exc.reason,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return payload

from .dependencies import get_current_user
from .exceptions import AuthError, InvalidToken, JWKSFetchError, TokenExpired

__all__ = [
    "AuthError",
    "InvalidToken",
    "JWKSFetchError",
    "TokenExpired",
    "get_current_user",
]





from fastapi import APIRouter, Depends, FastAPI

from src.auth import get_current_user

app = FastAPI(title="QDI API", docs_url="/docs", openapi_url="/openapi.json")

public_router = APIRouter(prefix="/api")
protected_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@public_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@protected_router.get("/rates/{currency}")
def get_rate(currency: str, user: dict = Depends(get_current_user)) -> dict:
    mock_rates = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5}
    rate = mock_rates.get(currency.upper())
    if rate is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown currency: {currency}")
    return {
        "currency": currency.upper(),
        "rate": rate,
        "requested_by": user.get("sub"),
    }


app.include_router(public_router)
app.include_router(protected_router)




pyjwt[crypto]==2.9.0
cryptography>=43.0.0
httpx>=0.27.0
pydantic-settings>=2.5.0
loguru==0.7.0
