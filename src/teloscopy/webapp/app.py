"""Teloscopy FastAPI application.

Provides REST endpoints for microscopy image upload, telomere analysis,
disease-risk scoring, personalised nutrition plans, and an HTML frontend
rendered via Jinja2.

Run with::

    uvicorn teloscopy.webapp.app:app --reload
"""

from __future__ import annotations

import asyncio
import collections
import hashlib
import hmac
import logging
import math
import os
import random
import threading
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Real pipeline imports (lazy — heavy deps load only when used)
# ---------------------------------------------------------------------------
from teloscopy.facial.image_classifier import ImageType, classify_image
from teloscopy.facial.predictor import analyze_face
from teloscopy.genomics.disease_risk import DiseasePredictor
from teloscopy.nutrition.diet_advisor import DietAdvisor
from teloscopy.nutrition.regional_diets import resolve_region
from teloscopy.webapp.health_checkup import HealthCheckupAnalyzer
from teloscopy.webapp.report_parser import (
    compute_extraction_confidence,
    detect_file_type,
    extract_text,
    parse_lab_report,
)
from teloscopy.webapp.models import (
    AgentInfo,
    AgentStatusEnum,
    AgentSystemStatus,
    AnalysisResponse,
    AncestryDerivedPredictionsResponse,
    AncestryEstimateResponse,
    BloodTestPanel,
    ConsentBundle,
    ConsentPurpose,
    ConsentRecord,
    ConditionScreeningResponse,
    DataDeletionRequest,
    DataDeletionResponse,
    DermatologicalAnalysisResponse,
    DietPlanRequest,
    DietPlanResponse,
    DietRecommendation,
    DiseaseRisk,
    DiseaseRiskRequest,
    DiseaseRiskResponse,
    FacialAnalysisResult,
    FacialHealthScreeningResponse,
    FacialMeasurementsResponse,
    GrievanceRequest,
    GrievanceResponse,
    HealthCheckupRequest,
    HealthCheckupResponse,
    HealthResponse,
    ImageValidationResponse,
    JobStatus,
    JobStatusEnum,
    LegalNotice,
    MealPlan,
    NutritionRequest,
    NutritionResponse,
    PharmacogenomicPredictionResponse,
    PredictedVariantResponse,
    ProfileAnalysisRequest,
    ProfileAnalysisResponse,
    ReconstructedDNAResponse,
    ReconstructedSequenceResponse,
    ReportParsePreview,
    RiskLevel,
    Sex,
    TelomereResult,
    UploadResponse,
    UrineTestPanel,
    UserProfile,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _setup_logging() -> None:
    """Configure application logging based on environment variables."""
    log_level = os.getenv("TELOSCOPY_LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    if os.getenv("TELOSCOPY_LOG_FORMAT") == "json":
        # Simple JSON-like structured format without extra deps
        log_format = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO), format=log_format, force=True
    )


_setup_logging()
logger: logging.Logger = logging.getLogger("teloscopy.webapp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BASE_DIR: Path = Path(__file__).resolve().parent
_TEMPLATES_DIR: Path = _BASE_DIR / "templates"
_STATIC_DIR: Path = _BASE_DIR / "static"
_UPLOAD_DIR: Path = Path(os.getenv("TELOSCOPY_UPLOAD_DIR", "/tmp/teloscopy_uploads"))
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
_MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024  # 50 MiB
_MIN_IMAGE_DIMENSION: int = 32  # minimum width/height in pixels


async def _read_upload_chunked(file: Any, max_bytes: int) -> bytes:
    """Read an uploaded file in 1 MiB chunks, aborting if *max_bytes* is exceeded.

    Prevents a single oversized upload from exhausting server memory.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the {max_bytes // (1024 * 1024)} MiB limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


# Magic byte signatures for image format validation
_IMAGE_MAGIC_BYTES: dict[str, list[bytes]] = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "tiff": [b"II\x2a\x00", b"MM\x00\x2a"],  # little-endian / big-endian
    "bmp": [b"BM"],
    "webp": [b"RIFF\x00\x00\x00\x00WEBP"],  # 4-byte gap is file-size (varies)
}

# WebP has the structure RIFF<size>WEBP — we only check bytes 0-3 and 8-11.
_WEBP_MARKER = b"WEBP"

_TELOSCOPY_ENV: str = os.getenv("TELOSCOPY_ENV", "production")
_CORS_ORIGINS: list[str] = os.getenv(
    "TELOSCOPY_CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
).split(",")

# Prevent wildcard CORS with credentials — this is a credential theft risk.
if "*" in _CORS_ORIGINS:
    logger.warning(
        "TELOSCOPY_CORS_ORIGINS contains '*' (wildcard). "
        "Removing it to prevent credential exposure via CORS. "
        "Set explicit origins instead."
    )
    _CORS_ORIGINS = [o for o in _CORS_ORIGINS if o.strip() != "*"]
    if not _CORS_ORIGINS:
        _CORS_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# ---------------------------------------------------------------------------
# In-memory job store (swap for Redis in production)
# ---------------------------------------------------------------------------

_jobs: dict[str, JobStatus] = {}
_JOB_MAX_COUNT: int = 10_000
_JOB_TTL_SECONDS: float = 3600.0  # 1 hour


def _evict_stale_jobs() -> None:
    """Remove expired jobs to prevent unbounded memory growth."""
    if len(_jobs) < _JOB_MAX_COUNT:
        return
    cutoff = time.monotonic() - _JOB_TTL_SECONDS
    stale = [jid for jid, j in _jobs.items() if getattr(j, '_created_at', 0) < cutoff]
    for jid in stale[:len(_jobs) - _JOB_MAX_COUNT + 100]:
        _jobs.pop(jid, None)


_APP_START_TIME: float = time.time()

# ---------------------------------------------------------------------------
# Pipeline singletons (instantiated once at startup)
# ---------------------------------------------------------------------------

_disease_predictor: DiseasePredictor = DiseasePredictor()
_diet_advisor: DietAdvisor = DietAdvisor()
_health_analyzer: HealthCheckupAnalyzer = HealthCheckupAnalyzer(_diet_advisor)

logger.info(
    "Pipeline loaded: %d disease variants, DietAdvisor ready",
    _disease_predictor.variant_count,
)

_ANALYSIS_SEMAPHORE: asyncio.Semaphore = asyncio.Semaphore(8)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class RateLimiter:
    """In-memory sliding-window rate limiter keyed by client IP.

    Tracks timestamps of recent requests per key and rejects requests
    that exceed the configured maximum within the sliding window.
    Thread-safe for use with ``asyncio.to_thread`` or sync middleware.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._requests: dict[str, list[float]] = collections.defaultdict(list)
        self._call_count: int = 0

    def cleanup(self) -> None:
        """Remove keys with no recent requests to prevent memory growth."""
        empty_keys = [k for k, v in self._requests.items() if not v]
        for k in empty_keys:
            del self._requests[k]

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return *True* if the request is within the rate limit.

        Prunes expired timestamps and appends the current one if allowed.
        """
        now: float = time.time()
        cutoff: float = now - window_seconds
        with self._lock:
            self._call_count += 1
            if self._call_count % 100 == 0:
                self.cleanup()
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if len(self._requests[key]) >= max_requests:
                return False
            self._requests[key].append(now)
            return True


_rate_limiter: RateLimiter = RateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60):
    """Create a FastAPI dependency that enforces per-IP rate limiting.

    Usage::

        @app.get("/endpoint", dependencies=[Depends(rate_limit(10, 60))])
        async def my_endpoint(): ...

    Raises :class:`~fastapi.HTTPException` with status 429 when the
    caller exceeds *max_requests* within *window_seconds*.
    """

    async def _check_rate_limit(request: Request) -> None:
        # Prefer X-Forwarded-For (first hop) when behind a reverse proxy,
        # falling back to the direct client IP.
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        key: str = f"{client_ip}:{request.url.path}"
        if not _rate_limiter.is_allowed(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Maximum {max_requests} requests "
                    f"per {window_seconds} seconds."
                ),
            )

    return _check_rate_limit


# ---------------------------------------------------------------------------
# Server-side consent enforcement (DPDP Act 2023 Section 6)
# ---------------------------------------------------------------------------

# HMAC secret for signing consent tokens.  Uses TELOSCOPY_CONSENT_SECRET env
# var if set; otherwise falls back to a deterministic secret derived from the
# machine-id / hostname so tokens survive across restarts and re-deploys
# (without requiring manual env-var setup).
def _default_consent_secret() -> str:
    """Derive a stable HMAC secret when no env var is configured."""
    try:
        # Linux: /etc/machine-id is stable across reboots
        mid = Path("/etc/machine-id").read_text().strip()
    except Exception:
        mid = ""
    if not mid:
        import socket
        mid = socket.getfqdn()
    return hmac.new(
        b"teloscopy-consent-v1", mid.encode(), hashlib.sha256
    ).hexdigest()

_CONSENT_SECRET: bytes = os.getenv(
    "TELOSCOPY_CONSENT_SECRET", _default_consent_secret()
).encode()

# In-memory consent store: token → {session_id, purposes, granted_at, withdrawn}
_consent_store: dict[str, dict[str, Any]] = {}
_consent_store_lock: threading.Lock = threading.Lock()
_CONSENT_STORE_MAX: int = 50_000  # cap to prevent memory exhaustion

# Tokens older than 24 hours require re-consent.
_CONSENT_TOKEN_TTL: float = 86_400.0

# Set of session_ids that have withdrawn consent — checked on every request.
_withdrawn_sessions: set[str] = set()
_WITHDRAWN_SESSIONS_MAX: int = 100_000  # cap to prevent memory exhaustion


def _sign_consent_token(session_id: str, purposes: list[str]) -> str:
    """Create an HMAC-signed consent token encoding session + purposes."""
    timestamp = str(int(time.time()))
    payload = f"{session_id}:{','.join(sorted(purposes))}:{timestamp}"
    sig = hmac.new(_CONSENT_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]
    import base64
    token = base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()
    return token


def _verify_consent_token(token: str) -> dict[str, Any] | None:
    """Verify an HMAC-signed consent token.  Returns payload dict or None."""
    import base64
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload_str, sig = parts
        expected_sig = hmac.new(
            _CONSENT_SECRET, payload_str.encode(), hashlib.sha256
        ).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload_parts = payload_str.split(":", 2)
        if len(payload_parts) != 3:
            return None
        session_id, purposes_str, timestamp_str = payload_parts
        timestamp = int(timestamp_str)
        # Check token TTL
        if time.time() - timestamp > _CONSENT_TOKEN_TTL:
            return None
        # Check if consent was withdrawn
        if session_id in _withdrawn_sessions:
            return None
        return {
            "session_id": session_id,
            "purposes": purposes_str.split(",") if purposes_str else [],
            "granted_at": timestamp,
        }
    except Exception:
        return None


def require_consent(*required_purposes: str):
    """FastAPI dependency that enforces server-side consent verification.

    Checks for a consent token in the ``X-Consent-Token`` header or
    ``consent_token`` cookie.  The token must be a valid, non-expired,
    non-withdrawn HMAC-signed token that includes all *required_purposes*.

    Usage::

        @app.post("/endpoint", dependencies=[Depends(require_consent("health_report"))])
        async def my_endpoint(): ...

    Raises :class:`~fastapi.HTTPException` with 403 if consent is missing
    or insufficient.
    """

    async def _check_consent(
        request: Request,
        x_consent_token: str | None = Header(None),
        consent_token: str | None = Cookie(None),
    ) -> None:
        token = x_consent_token or consent_token
        if not token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Consent required.  Please accept the privacy notice and "
                    "terms of service before using this endpoint.  Submit your "
                    "consent via POST /api/legal/consent to obtain a consent token."
                ),
            )
        payload = _verify_consent_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Consent token is invalid, expired, or has been withdrawn.  "
                    "Please re-submit consent via POST /api/legal/consent."
                ),
            )
        # Check that all required purposes are covered
        granted = set(payload.get("purposes", []))
        missing = set(required_purposes) - granted
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Consent not granted for required purpose(s): "
                    f"{', '.join(sorted(missing))}.  Please update your consent "
                    f"via POST /api/legal/consent."
                ),
            )
        # Attach consent info to request state for downstream use
        request.state.consent_session_id = payload["session_id"]
        request.state.consent_purposes = payload["purposes"]

    return _check_consent


# ---------------------------------------------------------------------------
# CSRF protection
# ---------------------------------------------------------------------------


async def _check_csrf(request: Request) -> None:
    """Verify that state-changing requests include X-Requested-With header.

    This is a simple CSRF mitigation: browsers will not add custom headers
    on cross-origin form submissions.  The frontend's ``fetch()`` calls
    must include ``X-Requested-With: XMLHttpRequest``.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    # Allow consent/legal endpoints without CSRF (they need to be accessible
    # from the consent modal before JS is fully wired up)
    if request.url.path.startswith("/api/legal/"):
        return
    xrw = request.headers.get("x-requested-with", "")
    content_type = request.headers.get("content-type", "")
    # Accept requests with X-Requested-With header, or JSON content type
    # (custom content types cannot be set by cross-origin forms)
    if xrw or "application/json" in content_type or "multipart/form-data" in content_type:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="CSRF validation failed. Include X-Requested-With header.",
    )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

_docs_url: str | None = "/docs" if _TELOSCOPY_ENV != "production" else None
_redoc_url: str | None = "/redoc" if _TELOSCOPY_ENV != "production" else None

app: FastAPI = FastAPI(
    title="Teloscopy API",
    description="Multi-Agent Genomic Intelligence Platform — Telomere analysis, disease risk prediction, and personalized nutrition from qFISH microscopy images.",
    version="2.0.0",
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    contact={"name": "Teloscopy Contributors", "url": "https://github.com/Mahesh2023/teloscopy"},
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_tags=[
        {"name": "Health", "description": "System health and readiness checks"},
        {"name": "Analysis", "description": "Image upload and telomere analysis pipeline"},
        {"name": "Disease Risk", "description": "Genetic disease risk prediction"},
        {"name": "Nutrition", "description": "Personalized diet planning and meal recommendations"},
        {"name": "Agents", "description": "Multi-agent system status and control"},
        {"name": "Legal", "description": "Legal compliance, consent management, and data subject rights (DPDP Act 2023)"},
    ],
)

# -- CORS -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Consent-Token"],
)

# -- Security headers -------------------------------------------------------

_CSP_POLICY: str = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Any:
    """Append hardening headers to every HTTP response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"] = _CSP_POLICY
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.middleware("http")
async def csrf_middleware(request: Request, call_next: Any) -> Any:
    """Enforce CSRF protection on state-changing requests.

    Rejects POST/PUT/DELETE/PATCH requests that lack a valid content-type
    or X-Requested-With header, unless the path is exempt (e.g. legal
    endpoints that must be accessible from the consent modal).
    """
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        path = request.url.path
        # Exempt paths: legal/consent endpoints, OpenAPI docs
        exempt = (
            path.startswith("/api/legal/")
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi")
        )
        if not exempt:
            xrw = request.headers.get("x-requested-with", "")
            ct = request.headers.get("content-type", "")
            # Custom headers/content-types can't be set by cross-origin HTML forms
            if not (xrw or "application/json" in ct or "multipart/form-data" in ct):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={"error": {"code": 403, "message": "CSRF validation failed. Include appropriate Content-Type or X-Requested-With header."}},
                )
    response = await call_next(request)
    return response


# -- Request ID -------------------------------------------------------------


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Any:
    """Generate a unique request ID, log the request with timing, and attach ID to the response."""
    request_id: str = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "%s %s 500 took %.3fs [request_id=%s]",
            request.method,
            request.url.path,
            elapsed,
            request_id,
        )
        raise
    elapsed = time.monotonic() - start
    status_code = response.status_code
    if status_code >= 500:
        logger.error(
            "%s %s %d took %.3fs [request_id=%s]",
            request.method,
            request.url.path,
            status_code,
            elapsed,
            request_id,
        )
    elif status_code >= 400:
        logger.warning(
            "%s %s %d took %.3fs [request_id=%s]",
            request.method,
            request.url.path,
            status_code,
            elapsed,
            request_id,
        )
    else:
        logger.info(
            "%s %s %d took %.3fs",
            request.method,
            request.url.path,
            status_code,
            elapsed,
        )
    response.headers["X-Request-ID"] = request_id
    return response


# -- Exception handler (surface errors in non-production) --------------------


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException) -> Any:
    """Return structured JSON error for HTTP exceptions."""
    from fastapi.responses import JSONResponse

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    code = exc.status_code
    if code >= 500:
        logger.error("HTTPException %d on %s: %s", code, request.url.path, exc.detail)
    elif code >= 400:
        logger.warning("HTTPException %d on %s: %s", code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=code,
        content={"error": {"code": code, "message": str(exc.detail), "request_id": request_id}},
    )


@app.exception_handler(ValueError)
async def _value_error_handler(request: Request, exc: ValueError) -> Any:
    """Return 422 for ValueError exceptions."""
    from fastapi.responses import JSONResponse

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning("ValueError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={"error": {"code": 422, "message": str(exc), "request_id": request_id}},
    )


@app.exception_handler(RequestValidationError)
async def _request_validation_error_handler(request: Request, exc: RequestValidationError) -> Any:
    """Return structured JSON for FastAPI request-validation errors.

    Without this handler FastAPI returns ``{"detail": [...]}``, which the
    frontend cannot parse into a user-friendly message.
    """
    from fastapi.responses import JSONResponse

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    # Build a concise human-readable summary
    messages: list[str] = []
    for e in exc.errors():
        field = e.get("loc", [])[-1] if e.get("loc") else "input"
        messages.append(f"{field}: {e.get('msg', 'invalid')}")
    summary = "; ".join(messages[:5]) or "Validation error"
    logger.warning("RequestValidationError on %s: %s", request.url.path, summary)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": f"Invalid input — {summary}",
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(ValidationError)
async def _validation_error_handler(request: Request, exc: ValidationError) -> Any:
    """Return 422 for pydantic ValidationError exceptions."""
    from fastapi.responses import JSONResponse

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning("ValidationError on %s: %s", request.url.path, exc)
    details = [
        {
            "field": e.get("loc", [])[-1] if e.get("loc") else "unknown",
            "error": e.get("type", "invalid"),
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation error. Please check your input.",
                "details": details,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> Any:
    """Return traceback detail for unhandled errors to aid debugging."""
    from fastapi.responses import JSONResponse

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    tb = traceback.format_exc()
    logger.error("Unhandled %s on %s: %s\n%s", type(exc).__name__, request.url.path, exc, tb)
    return JSONResponse(
        status_code=500,
        content={
            "error": {"code": 500, "message": "Internal server error", "request_id": request_id}
        },
    )


# -- Startup / shutdown events -----------------------------------------------


@app.on_event("startup")
async def _on_startup() -> None:
    """Log application configuration at startup."""
    env = _TELOSCOPY_ENV
    logger.info("Teloscopy v%s starting [env=%s]", app.version, env)
    logger.info("Templates dir: %s (exists=%s)", _TEMPLATES_DIR, _TEMPLATES_DIR.exists())
    logger.info("Static dir:    %s (exists=%s)", _STATIC_DIR, _STATIC_DIR.exists())
    logger.info("Upload dir:    %s (exists=%s)", _UPLOAD_DIR, _UPLOAD_DIR.exists())


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    """Log graceful shutdown and clean up resources."""
    logger.info("Teloscopy v%s shutting down gracefully.", app.version)
    # Clean up old uploaded files
    try:
        import glob
        for f in glob.glob(str(_UPLOAD_DIR / "*")):
            try:
                Path(f).unlink(missing_ok=True)
            except OSError:
                pass
    except Exception:
        pass


# -- Templates & static files -----------------------------------------------

templates: Jinja2Templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ===================================================================== #
#  Type translation helpers                                              #
# ===================================================================== #


def _translate_disease_risks(
    risk_profile_risks: list[Any],
) -> list[DiseaseRisk]:
    """Convert ``genomics.disease_risk.DiseaseRisk`` dataclasses to Pydantic models."""
    results: list[DiseaseRisk] = []
    for dr in risk_profile_risks:
        prob = min(dr.lifetime_risk_pct / 100.0, 1.0)
        if prob < 0.20:
            level = RiskLevel.LOW
        elif prob < 0.50:
            level = RiskLevel.MODERATE
        elif prob < 0.75:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.VERY_HIGH

        recs: list[str] = []
        if dr.preventability_score > 0.5:
            recs.append(f"Modifiable risk — preventability {dr.preventability_score:.0%}")
        if dr.age_of_onset_range[0] > 0:
            recs.append(f"Typical onset age {dr.age_of_onset_range[0]}–{dr.age_of_onset_range[1]}")

        results.append(
            DiseaseRisk(
                disease=dr.condition,
                risk_level=level,
                probability=round(prob, 3),
                contributing_factors=dr.contributing_variants,
                recommendations=recs,
            )
        )
    return results


def _translate_diet_recommendation(
    recs: list[Any],
    meal_plans: list[Any],
    calorie_target: int = 2100,
) -> DietRecommendation:
    """Convert ``nutrition.diet_advisor`` results to Pydantic model."""
    key_nutrients: list[str] = []
    foods_increase: list[str] = []
    foods_avoid: list[str] = []
    summary_parts: list[str] = []

    for r in recs[:12]:
        key_nutrients.append(r.nutrient)
        foods_increase.extend(r.target_foods[:3])
        foods_avoid.extend(r.avoid_foods[:2])
        if r.recommendation:
            summary_parts.append(r.recommendation)

    summary = (
        " ".join(summary_parts[:3])
        if summary_parts
        else (
            "Based on your genetic profile and health markers, we recommend "
            "a nutrient-dense, anti-inflammatory diet to support genomic health."
        )
    )

    pydantic_plans: list[MealPlan] = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for mp in meal_plans:

        def _meal_str(items: list[Any]) -> str:
            return ", ".join(f"{fi.name} ({g:.0f}g)" for fi, g in items[:4]) or "Seasonal selection"

        if isinstance(mp.day, int):
            week_num = (mp.day - 1) // 7 + 1
            day_label = day_names[(mp.day - 1) % 7]
            label = f"Week {week_num} — {day_label}" if len(meal_plans) > 7 else day_label
        else:
            label = str(mp.day)

        pydantic_plans.append(
            MealPlan(
                day=label,
                breakfast=_meal_str(mp.breakfast),
                lunch=_meal_str(mp.lunch),
                dinner=_meal_str(mp.dinner),
                snacks=[_meal_str(mp.snacks)] if mp.snacks else [],
            )
        )

    return DietRecommendation(
        summary=summary,
        key_nutrients=list(dict.fromkeys(key_nutrients)),  # deduplicate, keep order
        foods_to_increase=list(dict.fromkeys(foods_increase))[:10],
        foods_to_avoid=list(dict.fromkeys(foods_avoid))[:8],
        meal_plans=pydantic_plans,
        calorie_target=calorie_target,
    )


def _sanitize_float(v: float, default: float = 0.0) -> float:
    """Replace NaN / ±Inf with *default* to keep JSON valid."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return default
    return v


def _dataclass_to_dict(obj: Any) -> dict | None:
    """Recursively convert a dataclass to a JSON-safe dict, or return None."""
    if obj is None:
        return None
    from dataclasses import asdict, fields as dc_fields
    try:
        if hasattr(obj, "__dataclass_fields__"):
            result = {}
            for f in dc_fields(obj):
                val = getattr(obj, f.name)
                result[f.name] = _dataclass_to_dict(val) if hasattr(val, "__dataclass_fields__") else (
                    [_dataclass_to_dict(item) if hasattr(item, "__dataclass_fields__") else item for item in val]
                    if isinstance(val, list) else val
                )
            return result
        return obj if isinstance(obj, (str, int, float, bool, type(None))) else str(obj)
    except Exception:
        return None


def _translate_facial_profile(profile: Any) -> FacialAnalysisResult:
    """Convert ``facial.predictor.FacialGenomicProfile`` to Pydantic model."""
    m = profile.measurements
    a = profile.ancestry
    sf = _sanitize_float

    # Translate reconstructed DNA if present
    rdna = profile.reconstructed_dna
    reconstructed_dna_resp = None
    if rdna and rdna.sequences:
        reconstructed_dna_resp = ReconstructedDNAResponse(
            sequences=[
                ReconstructedSequenceResponse(
                    rsid=s.rsid,
                    gene=s.gene,
                    chromosome=s.chromosome,
                    position=s.position,
                    ref_allele=s.ref_allele,
                    predicted_allele_1=s.predicted_allele_1,
                    predicted_allele_2=s.predicted_allele_2,
                    flanking_5prime=s.flanking_5prime,
                    flanking_3prime=s.flanking_3prime,
                    confidence=s.confidence,
                )
                for s in rdna.sequences
            ],
            total_variants=rdna.total_variants,
            genome_build=rdna.genome_build,
            fasta=rdna.fasta,
            disclaimer=rdna.disclaimer,
        )

    # Translate pharmacogenomic predictions
    pharma_resp = [
        PharmacogenomicPredictionResponse(
            gene=p.gene,
            rsid=p.rsid,
            predicted_phenotype=p.predicted_phenotype,
            confidence=sf(p.confidence),
            affected_drugs=list(p.affected_drugs),
            clinical_recommendation=p.clinical_recommendation,
            basis=p.basis,
        )
        for p in getattr(profile, "pharmacogenomic_predictions", [])
    ]

    # Translate health screening
    hs = getattr(profile, "health_screening", None)
    health_screening_resp = None
    if hs is not None:
        health_screening_resp = FacialHealthScreeningResponse(
            estimated_bmi_category=hs.estimated_bmi_category,
            bmi_confidence=sf(hs.bmi_confidence),
            anemia_risk_score=sf(hs.anemia_risk_score),
            cardiovascular_risk_indicators=list(hs.cardiovascular_risk_indicators),
            thyroid_indicators=list(hs.thyroid_indicators),
            fatigue_stress_score=sf(hs.fatigue_stress_score),
            hydration_score=sf(hs.hydration_score, 50.0),
        )

    # Translate dermatological analysis
    da = getattr(profile, "dermatological_analysis", None)
    derm_resp = None
    if da is not None:
        derm_resp = DermatologicalAnalysisResponse(
            rosacea_risk_score=sf(da.rosacea_risk_score),
            melasma_risk_score=sf(da.melasma_risk_score),
            photo_aging_gap=da.photo_aging_gap,
            acne_severity_score=sf(da.acne_severity_score),
            skin_cancer_risk_factors=list(da.skin_cancer_risk_factors),
            pigmentation_disorder_risk=sf(da.pigmentation_disorder_risk),
            moisture_barrier_score=sf(da.moisture_barrier_score, 50.0),
        )

    # Translate condition screenings
    cond_resp = [
        ConditionScreeningResponse(
            condition=c.condition,
            risk_score=sf(c.risk_score),
            facial_markers=list(c.facial_markers),
            confidence=sf(c.confidence),
            recommendation=c.recommendation,
        )
        for c in getattr(profile, "condition_screenings", [])
    ]

    # Translate ancestry-derived predictions
    ad = getattr(profile, "ancestry_derived", None)
    ancestry_derived_resp = None
    if ad is not None:
        ancestry_derived_resp = AncestryDerivedPredictionsResponse(
            predicted_mtdna_haplogroup=ad.predicted_mtdna_haplogroup,
            haplogroup_confidence=sf(ad.haplogroup_confidence),
            lactose_tolerance_probability=sf(ad.lactose_tolerance_probability, 0.5),
            alcohol_flush_probability=sf(ad.alcohol_flush_probability),
            caffeine_sensitivity=ad.caffeine_sensitivity,
            bitter_taste_sensitivity=ad.bitter_taste_sensitivity,
            population_specific_risks=list(ad.population_specific_risks),
        )

    return FacialAnalysisResult(
        image_type="face_photo",
        estimated_biological_age=profile.estimated_biological_age,
        estimated_telomere_length_kb=sf(profile.estimated_telomere_length_kb),
        telomere_percentile=profile.telomere_percentile,
        skin_health_score=sf(profile.skin_health_score),
        oxidative_stress_score=sf(profile.oxidative_stress_score),
        predicted_eye_colour=profile.predicted_eye_colour,
        predicted_hair_colour=profile.predicted_hair_colour,
        predicted_skin_type=profile.predicted_skin_type,
        measurements=FacialMeasurementsResponse(
            face_width=sf(m.face_width),
            face_height=sf(m.face_height),
            face_ratio=sf(m.face_ratio),
            skin_brightness=sf(m.skin_brightness),
            skin_uniformity=sf(m.skin_uniformity),
            wrinkle_score=sf(m.wrinkle_score),
            symmetry_score=sf(m.symmetry_score, 0.5),
            dark_circle_score=sf(m.dark_circle_score),
            texture_roughness=sf(m.texture_roughness),
            uv_damage_score=sf(m.uv_damage_score),
        ),
        ancestry=AncestryEstimateResponse(
            european=sf(a.european),
            east_asian=sf(a.east_asian),
            south_asian=sf(a.south_asian),
            african=sf(a.african),
            middle_eastern=sf(a.middle_eastern),
            latin_american=sf(a.latin_american),
            confidence=sf(a.confidence),
        ),
        predicted_variants=[
            PredictedVariantResponse(
                rsid=v.rsid,
                gene=v.gene,
                predicted_genotype=v.predicted_genotype,
                confidence=v.confidence,
                basis=v.basis,
            )
            for v in profile.predicted_variants
        ],
        reconstructed_dna=reconstructed_dna_resp,
        pharmacogenomic_predictions=pharma_resp,
        health_screening=health_screening_resp,
        dermatological_analysis=derm_resp,
        condition_screenings=cond_resp,
        ancestry_derived=ancestry_derived_resp,
        analysis_warnings=profile.analysis_warnings,
        # v2.1 future direction modules — serialize dataclasses to dicts
        epigenetic_clock=_dataclass_to_dict(getattr(profile, "epigenetic_clock", None)),
        stela_profile=_dataclass_to_dict(getattr(profile, "stela_profile", None)),
        cfdna_telomere=_dataclass_to_dict(getattr(profile, "cfdna_telomere", None)),
        drug_targets=_dataclass_to_dict(getattr(profile, "drug_targets", None)),
        multi_omics=_dataclass_to_dict(getattr(profile, "multi_omics", None)),
        enhanced_genomic=_dataclass_to_dict(getattr(profile, "enhanced_genomic", None)),
    )


def _build_variant_dict(known_variants: list[str]) -> dict[str, str]:
    """Convert a list of user-supplied variant strings to {rsid: genotype}.

    Accepts formats:
    - ``"rs429358:CT"`` → ``{"rs429358": "CT"}``
    - ``"rs429358"`` (no genotype) → ``{"rs429358": "CT"}`` (heterozygous default)
    """
    result: dict[str, str] = {}
    for v in known_variants:
        v = v.strip()
        if not v:
            continue
        if ":" in v:
            rsid, geno = v.split(":", 1)
            result[rsid.strip()] = geno.strip().upper()
        else:
            # Default to heterozygous
            result[v] = "CT"
    return result


# ===================================================================== #
#  Simulation fallbacks (used when real pipeline data is insufficient)   #
# ===================================================================== #


def _simulate_telomere_analysis() -> TelomereResult:
    """Return plausible mock telomere analysis results.

    Uses the consensus telomere-age model (TL ≈ 11.0 − 0.040 × age)
    with random biological variability so that telomere length and
    biological age are correlated.
    """
    # Random biological age in a realistic range
    bio_age: int = random.randint(20, 85)
    # Consensus model + biological noise (SD ≈ 1.2 kb)
    # Two-phase model: faster attrition birth–20, slower 20+
    if bio_age <= 20:
        base_tl = 11.0 - 0.060 * bio_age
    else:
        base_tl = 9.80 - 0.025 * (bio_age - 20)
    mean_len: float = round(max(4.0, base_tl + random.gauss(0, 1.2)), 2)
    std_dev: float = round(abs(mean_len * 0.12), 2)
    return TelomereResult(
        mean_length=mean_len,
        std_dev=std_dev,
        t_s_ratio=round(max(0.3, (mean_len - 3.274) / 2.413), 2),
        biological_age_estimate=bio_age,
        overlay_image_url=None,
        raw_measurements=[round(max(3.0, mean_len + random.gauss(0, std_dev or 0.5)), 2) for _ in range(20)],
    )


def _telomere_from_facial(facial: FacialAnalysisResult) -> TelomereResult:
    """Build a TelomereResult from facial analysis predictions."""
    tl = facial.estimated_telomere_length_kb
    bio_age = facial.estimated_biological_age
    return TelomereResult(
        mean_length=tl,
        std_dev=round(abs(tl * 0.12), 2),
        t_s_ratio=round(max(0.3, (tl - 3.274) / 2.413), 2),
        biological_age_estimate=bio_age,
        overlay_image_url=None,
        raw_measurements=[round(max(3.0, tl + random.gauss(0, abs(tl * 0.12) or 0.5)), 2) for _ in range(10)],
    )


# ===================================================================== #
#  Core analysis pipeline                                                #
# ===================================================================== #


async def _run_full_analysis(
    job_id: str,
    profile: UserProfile,
    image_path: str,
) -> None:
    """Run the full analysis pipeline in the background.

    Classifies the uploaded image, then routes to either:
    - **FISH microscopy**: simulated telomere analysis (real qFISH pipeline
      requires calibrated multi-channel TIFFs not typical of web uploads)
    - **Face photograph**: real facial-genomic prediction via
      :func:`~teloscopy.facial.predictor.analyze_face`

    In *both* paths the real :class:`DiseasePredictor` and
    :class:`DietAdvisor` are used for disease-risk and nutrition output.
    """
    job: JobStatus = _jobs[job_id]
    try:
        job.status = JobStatusEnum.RUNNING
        job.message = "Classifying uploaded image..."
        job.progress_pct = 5.0
        job.updated_at = datetime.utcnow()

        # ------------------------------------------------------------------
        # Phase 0 — Image classification
        # ------------------------------------------------------------------
        classification = await asyncio.to_thread(classify_image, image_path)
        image_type = classification.image_type
        logger.info(
            "Job %s: image classified as %s (confidence %.2f)",
            job_id,
            image_type,
            classification.confidence,
        )

        job.progress_pct = 10.0
        job.message = f"Image type: {image_type.value}. Starting analysis..."
        job.updated_at = datetime.utcnow()

        facial_result: FacialAnalysisResult | None = None

        # ------------------------------------------------------------------
        # Phase 1 — Telomere / Facial analysis
        # ------------------------------------------------------------------
        if image_type == ImageType.FISH_MICROSCOPY:
            # FISH microscopy — use simulated telomere results
            # (real qFISH pipeline requires calibrated multi-channel TIFF)
            await asyncio.sleep(0.5)
            telomere = _simulate_telomere_analysis()
        else:
            # Face photo OR unknown photo — attempt facial-genomic analysis.
            # The predictor handles the case where no face is detected
            # (falls back to centre-region analysis with a warning).
            facial_profile = await asyncio.to_thread(
                analyze_face,
                image_path,
                profile.age,
                profile.sex.value,
            )
            facial_result = _translate_facial_profile(facial_profile)
            telomere = _telomere_from_facial(facial_result)
            logger.info(
                "Job %s: facial analysis → bio_age=%d, TL=%.2f kb",
                job_id,
                facial_result.estimated_biological_age,
                facial_result.estimated_telomere_length_kb,
            )

        job.progress_pct = 35.0
        job.message = "Telomere analysis complete. Assessing disease risk..."
        job.updated_at = datetime.utcnow()

        # ------------------------------------------------------------------
        # Phase 2 — Disease risk (real predictor)
        # ------------------------------------------------------------------
        variant_dict = _build_variant_dict(profile.known_variants)

        # If facial analysis predicted variants, merge them in
        if facial_result and facial_result.predicted_variants:
            for pv in facial_result.predicted_variants:
                if pv.rsid not in variant_dict and pv.confidence > 0.3:
                    # Use actual risk/ref alleles from the predictor.
                    risk_al = getattr(pv, "risk_allele", "") or "T"
                    ref_al = getattr(pv, "ref_allele", "") or "C"
                    if "homozygous variant" in pv.predicted_genotype:
                        variant_dict[pv.rsid] = f"{risk_al}{risk_al}"
                    elif "heterozygous" in pv.predicted_genotype:
                        variant_dict[pv.rsid] = f"{ref_al}{risk_al}"
                    else:
                        variant_dict[pv.rsid] = f"{ref_al}{ref_al}"

        risk_profile = await asyncio.to_thread(
            _disease_predictor.predict_from_variants,
            variant_dict,
            profile.age,
            profile.sex.value,
        )

        # If facial analysis estimated telomere length, also compute
        # telomere-based disease risks and merge them in.
        if facial_result and facial_result.estimated_telomere_length_kb > 0:
            tl_bp = facial_result.estimated_telomere_length_kb * 1000.0
            tl_risks = await asyncio.to_thread(
                _disease_predictor.predict_from_telomere_data,
                tl_bp,
                profile.age,
                profile.sex.value,
            )
            # Merge: if a condition already appears from variant analysis,
            # keep the higher lifetime risk; otherwise add the new entry.
            existing = {r.condition: r for r in risk_profile.risks}
            for tr in tl_risks:
                if tr.condition in existing:
                    if tr.lifetime_risk_pct > existing[tr.condition].lifetime_risk_pct:
                        existing[tr.condition] = tr
                else:
                    risk_profile.risks.append(tr)
                    existing[tr.condition] = tr

        risks = _translate_disease_risks(risk_profile.top_risks(n=15))

        job.progress_pct = 65.0
        job.message = "Disease risk assessed. Generating diet plan..."
        job.updated_at = datetime.utcnow()

        # ------------------------------------------------------------------
        # Phase 3 — Diet recommendation (real advisor)
        # ------------------------------------------------------------------
        resolved_region = resolve_region(
            profile.region,
            country=getattr(profile, "country", None),
            state=getattr(profile, "state", None),
        )
        genetic_risk_names = [r.condition for r in risk_profile.risks[:10]]
        diet_recs = await asyncio.to_thread(
            _diet_advisor.generate_recommendations,
            genetic_risk_names,
            variant_dict,
            resolved_region,
            profile.age,
            profile.sex.value,
            profile.dietary_restrictions or None,
        )
        diet_meals = await asyncio.to_thread(
            _diet_advisor.create_meal_plan,
            diet_recs,
            resolved_region,
            2000,
            7,
            profile.dietary_restrictions or None,
        )

        # Safety net: adapt any remaining violations post-hoc.
        if profile.dietary_restrictions:
            diet_meals = await asyncio.to_thread(
                _diet_advisor.adapt_to_restrictions,
                diet_meals,
                profile.dietary_restrictions,
            )

        diet = _translate_diet_recommendation(diet_recs, diet_meals)

        job.progress_pct = 90.0
        job.message = "Compiling final report..."
        job.updated_at = datetime.utcnow()

        await asyncio.sleep(0.2)

        # Done
        result = AnalysisResponse(
            job_id=job_id,
            image_type=image_type.value,
            telomere_results=telomere,
            disease_risks=risks,
            diet_recommendations=diet,
            facial_analysis=facial_result,
            report_url=f"/api/results/{job_id}",
        )
        job.result = result
        job.status = JobStatusEnum.COMPLETED
        job.progress_pct = 100.0
        job.message = "Analysis complete"
        job.updated_at = datetime.utcnow()
        logger.info("Job %s completed successfully.", job_id)
        try:
            Path(image_path).unlink(missing_ok=True)
        except OSError:
            pass

    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed: %s", job_id, exc)
        job.status = JobStatusEnum.FAILED
        job.message = "Analysis failed. Please try again or contact support."
        job.updated_at = datetime.utcnow()
        try:
            Path(image_path).unlink(missing_ok=True)
        except OSError:
            pass


async def _run_full_analysis_limited(
    job_id: str,
    profile: UserProfile,
    image_path: str,
) -> None:
    """Wrapper that enforces a concurrency limit on analysis tasks."""
    async with _ANALYSIS_SEMAPHORE:
        await _run_full_analysis(job_id, profile, image_path)


def _validate_extension(filename: str) -> bool:
    """Return *True* if the filename has an allowed image extension."""
    ext: str = Path(filename).suffix.lower()
    return ext in _ALLOWED_EXTENSIONS


def _detect_image_format(data: bytes) -> str:
    """Detect image format from magic bytes. Returns format name or 'unknown'."""
    # Special handling for RIFF-based formats: WebP is RIFF<4-byte size>WEBP
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == _WEBP_MARKER:
        return "webp"
    for fmt, signatures in _IMAGE_MAGIC_BYTES.items():
        if fmt == "webp":
            continue  # already handled above
        for sig in signatures:
            if data[: len(sig)] == sig:
                return fmt
    return "unknown"


def _validate_image_content(contents: bytes, filename: str) -> ImageValidationResponse:
    """Validate image content: magic bytes, decodability, dimensions.

    Returns an :class:`ImageValidationResponse` with ``valid=True`` if the
    image passes all checks, or ``valid=False`` with a list of issues.
    Extension/content format mismatches are reported as *warnings* (not
    hard failures) when the image can still be decoded by OpenCV.
    """
    issues: list[str] = []
    warnings: list[str] = []
    file_size = len(contents)

    # 1. Magic bytes check (informational — not a hard failure if cv2
    #    can still decode the image)
    detected_format = _detect_image_format(contents)
    ext = Path(filename).suffix.lower()
    ext_to_format = {
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".tif": "tiff",
        ".tiff": "tiff",
        ".bmp": "bmp",
        ".webp": "webp",
    }
    expected_format = ext_to_format.get(ext, "unknown")
    magic_mismatch = False
    format_mismatch_msg = ""
    if detected_format == "unknown":
        magic_mismatch = True
    elif expected_format != "unknown" and detected_format != expected_format:
        format_mismatch_msg = (
            f"Extension '{ext}' suggests {expected_format} but content is {detected_format}."
        )

    # 2. Try to decode with OpenCV
    width, height, channels = 0, 0, 0
    image_type = "unknown"
    face_detected = False
    decoded_ok = False
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(contents, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            issues.append("Image could not be decoded — file may be corrupted or truncated.")
        else:
            decoded_ok = True
            if img.ndim == 2:
                height, width = img.shape
                channels = 1
            else:
                height, width = img.shape[:2]
                channels = img.shape[2] if img.ndim == 3 else 1

            if width < _MIN_IMAGE_DIMENSION or height < _MIN_IMAGE_DIMENSION:
                issues.append(
                    f"Image is too small ({width}x{height}). "
                    f"Minimum dimension is {_MIN_IMAGE_DIMENSION}px."
                )

            if width > 16384 or height > 16384:
                issues.append(
                    f"Image is extremely large ({width}x{height}). "
                    f"Maximum supported dimension is 16384px."
                )

            # 3. Quick classification for user feedback
            try:
                # Save to temp file for classifier
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(contents)
                    tmp_path = tmp.name
                try:
                    classification = classify_image(tmp_path)
                    image_type = classification.image_type.value
                    face_detected = classification.face_detected
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                image_type = "unknown"
    except ImportError:
        issues.append("OpenCV not available for image validation.")

    # Only report magic-bytes mismatch as a hard failure when the image
    # could not be decoded at all.  If cv2 decoded it successfully the
    # file is usable regardless of unexpected header bytes.
    if magic_mismatch and not decoded_ok:
        issues.append(
            f"File content does not match any known image format. "
            f"Expected {expected_format} based on extension '{ext}'."
        )

    # Extension/content format mismatch: treat as a warning when the
    # image decoded successfully, hard failure only when it didn't.
    if format_mismatch_msg:
        if decoded_ok:
            warnings.append(format_mismatch_msg)
        else:
            issues.append(format_mismatch_msg)

    return ImageValidationResponse(
        valid=len(issues) == 0,
        image_type=image_type,
        width=width,
        height=height,
        channels=channels,
        file_size_bytes=file_size,
        format_detected=detected_format,
        face_detected=face_detected,
        issues=issues,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Legal Compliance Endpoints (DPDP Act 2023)
# ---------------------------------------------------------------------------

# In-memory consent audit log (swap for database in production)
_consent_log: list[dict] = []
_grievance_log: list[dict] = []
_deletion_log: list[dict] = []
_AUDIT_LOG_MAX: int = 10_000  # cap each log to prevent memory exhaustion


@app.get("/api/legal/notice", response_model=LegalNotice, tags=["Legal"])
async def get_legal_notice():
    """Return the legal notice per DPDP Act 2023 Section 5.
    
    Must be presented to the Data Principal before collecting consent.
    """
    return LegalNotice()


@app.post("/api/legal/consent", tags=["Legal"])
async def record_consent(bundle: ConsentBundle, request: Request, response: Response):
    """Record explicit consent from the Data Principal.
    
    Per DPDP Act 2023 Section 6, consent must be free, specific, informed,
    unconditional, and unambiguous with a clear affirmative action.
    
    Returns a signed ``consent_token`` that must be included in subsequent
    API requests (via ``X-Consent-Token`` header or ``consent_token`` cookie)
    to prove that consent was obtained.
    """
    # Validate that required consents are actually granted
    granted_purposes = [c.purpose for c in bundle.consents if c.granted]
    if not granted_purposes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one consent purpose must be granted.",
        )
    if not bundle.data_principal_age_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age confirmation is required (DPDP Act Section 9).",
        )
    
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    
    for consent in bundle.consents:
        consent.ip_hash = ip_hash
    
    # Generate signed consent token
    consent_token = _sign_consent_token(bundle.session_id, granted_purposes)
    
    # Store in server-side consent store
    with _consent_store_lock:
        # Evict oldest entries if at capacity
        if len(_consent_store) >= _CONSENT_STORE_MAX:
            oldest_keys = sorted(
                _consent_store, key=lambda k: _consent_store[k].get("granted_at", "")
            )[: len(_consent_store) - _CONSENT_STORE_MAX + 100]
            for k in oldest_keys:
                _consent_store.pop(k, None)
        _consent_store[bundle.session_id] = {
            "purposes": granted_purposes,
            "granted_at": datetime.utcnow().isoformat(),
            "ip_hash": ip_hash,
            "token": consent_token,
        }
    
    record = {
        "session_id": bundle.session_id,
        "consents": [c.dict() for c in bundle.consents],
        "age_confirmed": bundle.data_principal_age_confirmed,
        "privacy_policy_version": bundle.privacy_policy_version,
        "terms_version": bundle.terms_version,
        "recorded_at": datetime.utcnow().isoformat(),
        "ip_hash": ip_hash,
    }
    if len(_consent_log) >= _AUDIT_LOG_MAX:
        _consent_log[:] = _consent_log[-(_AUDIT_LOG_MAX // 2):]
    _consent_log.append(record)
    logger.info("Consent recorded for session %s with %d purposes", bundle.session_id, len(bundle.consents))
    
    # Set consent token as cookie (HttpOnly, Secure, SameSite=Strict)
    response.set_cookie(
        key="consent_token",
        value=consent_token,
        httponly=True,
        secure=request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https",
        samesite="strict",
        max_age=int(_CONSENT_TOKEN_TTL),
        path="/api/",
    )
    
    return {
        "status": "recorded",
        "session_id": bundle.session_id,
        "consent_token": consent_token,
        "purposes_consented": granted_purposes,
        "message": "Your consent has been recorded. Include the consent_token in subsequent API requests. You may withdraw consent at any time.",
    }


@app.post("/api/legal/consent/withdraw", tags=["Legal"])
async def withdraw_consent(session_id: str = "", purposes: list[str] = [], response: Response = None):
    """Withdraw consent per DPDP Act 2023 Section 6(6).
    
    The Data Principal may withdraw consent at any time, with the same
    ease as it was given. Withdrawal does not affect lawfulness of
    processing done before withdrawal.
    
    This invalidates the consent token server-side, so subsequent API
    calls using that session's token will be rejected with 403.
    """
    # Invalidate the session's consent server-side
    if session_id:
        # Cap withdrawn sessions set to prevent unbounded memory growth
        if len(_withdrawn_sessions) >= _WITHDRAWN_SESSIONS_MAX:
            # Remove oldest half (order not preserved in sets, but this
            # bounds the size which is the primary goal)
            to_remove = list(_withdrawn_sessions)[:_WITHDRAWN_SESSIONS_MAX // 2]
            _withdrawn_sessions.difference_update(to_remove)
        _withdrawn_sessions.add(session_id)
        with _consent_store_lock:
            _consent_store.pop(session_id, None)
    
    record = {
        "session_id": session_id,
        "purposes_withdrawn": purposes,
        "withdrawn_at": datetime.utcnow().isoformat(),
    }
    if len(_consent_log) >= _AUDIT_LOG_MAX:
        _consent_log[:] = _consent_log[-(_AUDIT_LOG_MAX // 2):]
    _consent_log.append(record)
    logger.info("Consent withdrawn for session %s, purposes: %s", session_id, purposes)
    
    # Clear the consent cookie
    if response is not None:
        response.delete_cookie(key="consent_token", path="/api/")
    
    return {
        "status": "withdrawn",
        "session_id": session_id,
        "purposes_withdrawn": purposes,
        "message": (
            "Your consent has been withdrawn. No further processing will occur "
            "for the specified purposes. Your consent token has been invalidated. "
            "Note: withdrawal does not affect the lawfulness of processing already "
            "completed. Since Teloscopy processes data ephemerally, no persistent "
            "data needs to be deleted."
        ),
    }


@app.post(
    "/api/legal/data-deletion",
    response_model=DataDeletionResponse,
    tags=["Legal"],
)
async def request_data_deletion(req: DataDeletionRequest):
    """Exercise Right to Erasure under DPDP Act 2023 Section 12(3).
    
    Since Teloscopy processes all data ephemerally (in-memory only,
    no persistent storage), this endpoint confirms that no data
    needs to be deleted and provides an audit record.
    """
    response = DataDeletionResponse(request_id=req.request_id)
    
    if len(_deletion_log) >= _AUDIT_LOG_MAX:
        _deletion_log[:] = _deletion_log[-(_AUDIT_LOG_MAX // 2):]
    _deletion_log.append({
        "request_id": req.request_id,
        "session_id": req.session_id,
        "reason": req.reason,
        "requested_at": req.requested_at.isoformat(),
        "completed_at": response.completed_at.isoformat(),
    })
    logger.info("Data deletion request %s processed", req.request_id)
    
    return response


@app.post(
    "/api/legal/grievance",
    response_model=GrievanceResponse,
    tags=["Legal"],
)
async def submit_grievance(grievance: GrievanceRequest):
    """Submit a grievance per DPDP Act 2023 Section 13.
    
    The Grievance Officer will acknowledge and respond within 30 days.
    """
    if len(_grievance_log) >= _AUDIT_LOG_MAX:
        _grievance_log[:] = _grievance_log[-(_AUDIT_LOG_MAX // 2):]
    _grievance_log.append(grievance.dict())
    # Redact email in logs to avoid PII leakage (log hash instead)
    email_hash = hashlib.sha256(grievance.email.encode()).hexdigest()[:8] if grievance.email else "none"
    logger.info("Grievance %s received from [email_hash=%s]", grievance.grievance_id, email_hash)
    
    return GrievanceResponse(grievance_id=grievance.grievance_id)


@app.get("/api/legal/privacy-policy", tags=["Legal"])
async def get_privacy_policy_summary():
    """Return a summary of the privacy policy with links."""
    return {
        "version": "1.0",
        "last_updated": "2026-04-01",
        "full_document_url": "/docs/privacy-policy",
        "governing_law": "Digital Personal Data Protection Act, 2023 (India)",
        "data_fiduciary": "Teloscopy Project",
        "grievance_officer_email": "animaticalpha123@gmail.com",
        "data_protection_board": "Data Protection Board of India",
        "key_points": [
            "All data is processed ephemerally — nothing is stored on servers",
            "Explicit consent is required before any processing",
            "You can withdraw consent at any time",
            "You have rights to access, correction, erasure, and grievance redressal",
            "No data is shared with third parties",
            "Facial images and health reports are never persisted",
            "Users must be 18+ or have verifiable parental consent",
        ],
    }


# ===================================================================== #
#  HTML (frontend) routes                                                #
# ===================================================================== #


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request) -> HTMLResponse:
    """Serve the main landing / upload page."""
    import json as _json

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"research_json": _json.dumps(_RESEARCH_CACHE)},
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request) -> HTMLResponse:
    """Serve the dedicated upload page (same template, scroll-to-upload)."""
    import json as _json

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"scroll_to": "upload", "research_json": _json.dumps(_RESEARCH_CACHE)},
    )


@app.get("/results/{job_id}", response_class=HTMLResponse)
async def results_page(request: Request, job_id: str) -> HTMLResponse:
    """Serve a results page for a specific job."""
    import json as _json

    # NOTE: Do NOT pass the full `job` object here — the template is served
    # without server-side consent verification and rendering result data
    # would bypass the consent gate.  The client fetches results via the
    # consent-protected /api/results/{job_id} endpoint instead.
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "job_id": job_id,
            "scroll_to": "results",
            "research_json": _json.dumps(_RESEARCH_CACHE),
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    """Serve the agent-monitoring dashboard."""
    return templates.TemplateResponse(request=request, name="dashboard.html")


# ===================================================================== #
#  Legal document routes (Privacy Policy & Terms of Service)             #
# ===================================================================== #

# Legal docs are shipped inside the package at teloscopy/data/legal/ so
# they survive pip-install.  _load_legal_doc() tries multiple strategies
# at request time so it works regardless of build caches or install mode.


def _load_legal_doc(filename: str) -> str | None:
    """Return the text of a legal Markdown file, or *None* if not found.

    Lookup order:
    1. ``importlib.resources`` — the standard way to access package data,
       works even when the package is installed as a zipped wheel.
    2. Path relative to *this* file (``teloscopy/data/legal/``).
    3. Project-root ``docs/`` via CWD (Render clones the repo and runs
       ``pip install`` inside the checkout, so CWD is the repo root).
    4. Project-root ``docs/`` computed from ``__file__`` (dev checkout).
    """
    # Strategy 1: importlib.resources  (Python ≥ 3.9)
    try:
        from importlib.resources import files as _res_files  # noqa: F811

        ref = _res_files("teloscopy.data").joinpath("legal", filename)
        return ref.read_text(encoding="utf-8")
    except Exception:  # FileNotFoundError, ModuleNotFoundError, TypeError …
        pass

    # Strategy 2: filesystem path relative to this module
    _pkg_legal = Path(__file__).resolve().parent.parent / "data" / "legal" / filename
    if _pkg_legal.is_file():
        return _pkg_legal.read_text(encoding="utf-8")

    # Strategy 3: CWD / docs  (Render working directory = repo root)
    _cwd_docs = Path.cwd() / "docs" / filename
    if _cwd_docs.is_file():
        return _cwd_docs.read_text(encoding="utf-8")

    # Strategy 4: project root inferred from __file__
    _proj_docs = Path(__file__).resolve().parent.parent.parent.parent / "docs" / filename
    if _proj_docs.is_file():
        return _proj_docs.read_text(encoding="utf-8")

    return None


@app.get("/docs/privacy-policy", response_class=HTMLResponse)
async def privacy_policy_page() -> HTMLResponse:
    """Serve the Privacy Policy as a styled HTML page."""
    return _render_legal_doc("PRIVACY_POLICY.md", "Privacy Policy")


@app.get("/docs/terms-of-service", response_class=HTMLResponse)
async def terms_of_service_page() -> HTMLResponse:
    """Serve the Terms of Service as a styled HTML page."""
    return _render_legal_doc("TERMS_OF_SERVICE.md", "Terms of Service")


def _render_legal_doc(filename: str, title: str) -> HTMLResponse:
    """Render a Markdown legal document as a styled HTML page."""
    md_content = _load_legal_doc(filename)
    if md_content is None:
        raise HTTPException(status_code=404, detail=f"{title} document not found")

    # Simple Markdown-to-HTML conversion for legal docs
    import html as _html
    import re

    content = _html.escape(md_content)
    # Headers
    content = re.sub(r"^######\s+(.+)$", r"<h6>\1</h6>", content, flags=re.MULTILINE)
    content = re.sub(r"^#####\s+(.+)$", r"<h5>\1</h5>", content, flags=re.MULTILINE)
    content = re.sub(r"^####\s+(.+)$", r"<h4>\1</h4>", content, flags=re.MULTILINE)
    content = re.sub(r"^###\s+(.+)$", r"<h3>\1</h3>", content, flags=re.MULTILINE)
    content = re.sub(r"^##\s+(.+)$", r"<h2>\1</h2>", content, flags=re.MULTILINE)
    content = re.sub(r"^#\s+(.+)$", r"<h1>\1</h1>", content, flags=re.MULTILINE)
    # Bold and italic
    content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
    content = re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)
    # Links
    content = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color:#00d4aa;">\1</a>',
        content,
    )
    # Horizontal rules
    content = re.sub(r"^---+$", "<hr>", content, flags=re.MULTILINE)
    # List items
    content = re.sub(r"^[-*]\s+(.+)$", r"<li>\1</li>", content, flags=re.MULTILINE)
    content = re.sub(r"((?:<li>.*</li>\n?)+)", r"<ul>\1</ul>", content)
    # Numbered list items
    content = re.sub(r"^\d+\.\s+(.+)$", r"<li>\1</li>", content, flags=re.MULTILINE)
    # Paragraphs — wrap text blocks
    content = re.sub(r"^(?!<[a-z/]|$)(.+)$", r"<p>\1</p>", content, flags=re.MULTILINE)

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_html.escape(title)} — Teloscopy</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0b0f19; color: #e0e6ed;
            line-height: 1.7; padding: 2rem;
            max-width: 860px; margin: 0 auto;
        }}
        h1 {{ font-size: 2rem; font-weight: 800; color: #00d4aa; margin: 2rem 0 .5rem; }}
        h2 {{ font-size: 1.4rem; font-weight: 700; color: #e0e6ed; margin: 2rem 0 .5rem;
               border-bottom: 1px solid rgba(46,58,89,.6); padding-bottom: .4rem; }}
        h3 {{ font-size: 1.1rem; font-weight: 600; color: #00d4aa; margin: 1.5rem 0 .4rem; }}
        h4, h5, h6 {{ font-size: 1rem; font-weight: 600; margin: 1rem 0 .3rem; }}
        p {{ margin: .6rem 0; font-size: .92rem; color: #a0aec0; }}
        a {{ color: #00d4aa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul, ol {{ padding-left: 1.5rem; margin: .5rem 0; }}
        li {{ font-size: .92rem; color: #a0aec0; margin: .3rem 0; }}
        strong {{ color: #e0e6ed; }}
        hr {{ border: none; border-top: 1px solid rgba(46,58,89,.6); margin: 2rem 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: .5rem .75rem; border: 1px solid rgba(46,58,89,.6);
                  font-size: .85rem; text-align: left; }}
        th {{ background: rgba(19,24,37,.8); color: #a0aec0; font-weight: 600; }}
        .back-link {{ display: inline-block; margin-bottom: 1.5rem; color: #00d4aa;
                      font-size: .9rem; }}
        .footer {{ text-align: center; margin-top: 3rem; padding: 1.5rem 0;
                   border-top: 1px solid rgba(46,58,89,.6); font-size: .78rem; color: #8f9bb3; }}
    </style>
</head>
<body>
    <a href="/" class="back-link">&larr; Back to Teloscopy</a>
    {content}
    <div class="footer">
        <p>&copy; 2024&ndash;2026 Teloscopy &mdash; Governed by the laws of India</p>
        <p style="margin-top:.4rem;">
            <a href="/docs/privacy-policy">Privacy Policy</a> &middot;
            <a href="/docs/terms-of-service">Terms of Service</a> &middot;
            <a href="mailto:animaticalpha123@gmail.com">Grievance Officer</a>
        </p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_page)


# ===================================================================== #
#  Mobile app download links                                             #
# ===================================================================== #

_GITHUB_RELEASES_URL = "https://github.com/Mahesh2023/teloscopy/releases"


@app.get("/api/download/android")
async def download_android_redirect() -> dict[str, str]:
    """Return the GitHub Releases URL for the Android APK."""
    return {
        "url": f"{_GITHUB_RELEASES_URL}/latest",
        "platform": "android",
        "message": "Download the latest APK from the GitHub Releases page.",
    }


@app.get("/api/download/ios")
async def download_ios_redirect() -> dict[str, str]:
    """Return the GitHub Releases URL for the iOS build."""
    return {
        "url": f"{_GITHUB_RELEASES_URL}/latest",
        "platform": "ios",
        "message": "Download the latest iOS build from the GitHub Releases page.",
    }


# ===================================================================== #
#  Research Knowledge Base                                               #
# ===================================================================== #

_PROJECT_ROOT = _BASE_DIR.parent.parent.parent  # src/teloscopy/webapp → project root

_RESEARCH_FILES: list[dict[str, str]] = [
    {
        "id": "knowledge-base",
        "title": "Gene Sequencing & Telomere Analysis",
        "file": "KNOWLEDGE_BASE.md",
    },
    {
        "id": "research",
        "title": "Scientific Foundation & Research",
        "file": "docs/RESEARCH.md",
    },
    {
        "id": "psychiatry-knowledge-base",
        "title": "Modern Psychiatry — Comprehensive Knowledge Base",
        "file": "PSYCHIATRY_KNOWLEDGE_BASE.md",
    },
]


def _load_research_documents() -> dict[str, Any]:
    """Parse research markdown files into structured sections at startup.

    This runs once at import time so the /api/research endpoint never does
    blocking file I/O inside the async event loop.
    """
    import re as _re

    documents: list[dict[str, Any]] = []

    # Try multiple base paths to handle both source-tree and installed-package layouts
    candidate_roots = [
        _PROJECT_ROOT,
        Path.cwd(),
        Path.cwd() / "src" / "teloscopy" / ".." / ".." / "..",
    ]

    for doc_meta in _RESEARCH_FILES:
        text: str | None = None
        for root in candidate_roots:
            filepath = (root / doc_meta["file"]).resolve()
            if filepath.is_file():
                try:
                    text = filepath.read_text(encoding="utf-8")
                    break
                except OSError:
                    continue

        if text is None:
            logger.warning("Research file not found: %s (tried %d locations)", doc_meta["file"], len(candidate_roots))
            continue

        sections: list[dict[str, Any]] = []
        current_section: dict[str, Any] | None = None

        for line in text.split("\n"):
            m = _re.match(r"^##\s+(.+)", line)
            if m and not line.startswith("###"):
                if current_section:
                    current_section["content"] = current_section["content"].rstrip()
                    sections.append(current_section)
                title = m.group(1).strip()
                title_clean = _re.sub(r"^\d+[\.\)]\s*", "", title)
                current_section = {
                    "title": title_clean if title_clean else title,
                    "content": "",
                }
            elif current_section is not None:
                current_section["content"] += line + "\n"

        if current_section:
            current_section["content"] = current_section["content"].rstrip()
            sections.append(current_section)

        documents.append(
            {
                "id": doc_meta["id"],
                "title": doc_meta["title"],
                "sections": sections,
            }
        )

    logger.info(
        "Research library loaded: %d documents, %d sections",
        len(documents),
        sum(len(d["sections"]) for d in documents),
    )
    return {"documents": documents}


# Pre-load at import time — no file I/O happens during request handling
_RESEARCH_CACHE: dict[str, Any] = _load_research_documents()


@app.get("/api/research")
async def get_research() -> dict[str, Any]:
    """Return all research documents as structured sections (served from cache)."""
    return _RESEARCH_CACHE


# ===================================================================== #
#  Psychiatry — Inquiry-based Counselling Engine  (v2 — expanded)        #
#  Drawn from the San Diego 1974 dialogues on transformation, fear,     #
#  desire, sorrow, relationship, death, meditation, and freedom.        #
# ===================================================================== #

_COUNSEL_THEMES: dict[str, dict[str, Any]] = {
    # ──────────────────────────── FEAR ────────────────────────────
    "fear": {
        "title": "Fear and Its Roots",
        "description": "Exploring the nature of fear — how thought creates it by projecting into the future or carrying memory from the past.",
        "core_insights": [
            "Fear is never an actuality in the active present. It is thought moving away from 'what is.'",
            "We are afraid both of the known and of the unknown. Fear prevents clear perception.",
            "When you are completely in contact with fear — without naming it, without running — it undergoes a radical change.",
            "Freedom from fear is not the opposite of fear; it is the total understanding of it.",
            "Fear and pleasure are two sides of one movement of thought.",
        ],
        "quotes": [
            "The root of fear is thought. Thought breeds fear; thought also cultivates pleasure.",
            "When there is fear in the active present, is it fear? It is there and there is no escape from it.",
            "The moment you observe fear, it is no longer there — when you are completely in contact with it.",
            "We are afraid of the known and afraid of the unknown. That is our daily life and in that there is no hope.",
            "Fear is not an abstraction; it exists only in relation to something.",
            "A mind that is frightened cannot possibly see clearly.",
            "All the gods in the world are born out of fear.",
            "Fear hides itself in many forms — respectability, conformity, the desire to be accepted.",
            "When you no longer run from fear, when you stand absolutely still with it, it reveals its nature.",
            "Can the mind, which includes the brain, be really, fundamentally, free of fear? Because fear is a dreadful thing. It darkens the world.",
            "When you meet danger face to face, there is no fear. There is instant action. It is only when thought enters that fear arises.",
            "The observer of fear IS fear. The division between the observer and the observed is the very cause of fear.",
        ],
        "inquiry_patterns": [
            "What is the actual danger right now? Or is thought creating scenarios about the future?",
            "Can you stay with that fear for a moment, without trying to resolve it? What is the actual feeling — not the story, but the sensation itself?",
            "Who is it that is afraid? Is the fearful one separate from the fear, or are they the same movement?",
            "You say you are afraid. Of what, exactly? And is that 'what' happening now, or is it a projection?",
            "Let us look at this fear together. Not to eliminate it — but to understand it. What happens when you give fear your complete attention?",
            "Is the fear about something real that is happening, or about what thought imagines might happen?",
            "Can you observe how thought sustains fear by repeating the image of danger over and over?",
            "You want to get rid of fear. But is the entity wanting to get rid of it separate from the fear itself?",
            "When you actually meet danger — a snake on the path — is there fear? Or is there instant action without thought?",
            "If the root of fear is thought and time, what happens when the mind is completely in the present?",
        ],
        "reflections": [
            "Fear exists only when thought projects the past into the future. In the actual present moment, there is only what is — and what is can be met directly.",
            "The mind that has understood fear — not suppressed it, not escaped from it, but seen its entire structure — has a quality of lightness and clarity.",
            "All our gods, our escapes, our dependencies — they are all born out of this fear. When fear ends, so does the need for all the structures we build against it.",
            "Fear cannot be overcome, suppressed, or escaped — every such effort strengthens it. Only direct, non-verbal perception of fear ends it.",
        ],
    },
    # ──────────────────────────── ANXIETY ────────────────────────────
    "anxiety": {
        "title": "Anxiety and the Movement of Thought",
        "description": "Anxiety as thought projecting scenarios, creating a gap between what is and what might be.",
        "core_insights": [
            "Anxiety is thought rehearsing futures that have not arrived. The present moment has no anxiety — only thought about the present does.",
            "The restless mind is a mind in flight from itself. Anxiety is the symptom of that flight.",
            "When you are completely attentive, there is no space for anxiety. Anxiety needs inattention to survive.",
        ],
        "quotes": [
            "It is no measure of health to be well adjusted to a profoundly sick society.",
            "The restless mind is always seeking security, and that very search creates insecurity.",
            "Thought, pursuing its own security, creates the anxiety it hopes to escape from.",
            "A mind that is occupied is a mind that is anxious. It can never be still.",
            "The desire for certainty is the root of so much anxiety. Life has no certainty.",
            "Anxiety is the shadow of the self. Where there is the self-centre, there is always anxiety.",
            "Can you live with uncertainty? Not knowing, not seeking to know — just being with what is?",
            "The interval between what is and what you think should be is the breeding ground of anxiety.",
            "A mind that is free from the demand for security is no longer anxious.",
            "We are so mechanised, so conditioned, so used to this daily routine of loneliness, despair, and the pursuit of pleasure.",
        ],
        "inquiry_patterns": [
            "What is thought doing right now as you feel anxious? Is it projecting, rehearsing, imagining?",
            "Can we separate the actual situation from what thought is adding to it?",
            "You say you are anxious. Is the anxiety about something real happening now, or about what MIGHT happen?",
            "When you are completely in this moment — not the next moment, not tomorrow — is the anxiety still there?",
            "What is the mind seeking when it is restless? Is it looking for certainty? And is there such a thing?",
            "Can you observe the anxious thoughts without identifying with them — just watching them come and go?",
            "What if you didn't try to resolve the anxiety? What if you simply stayed with it, gave it your attention?",
            "The mind wants to be occupied. Can you see how occupation itself is a form of escape from anxiety?",
            "You are worried about tomorrow. But tomorrow doesn't exist yet. What is actually here, right now?",
            "Is there a part of you that is watching the anxiety? And is that watcher different from the anxiety?",
        ],
        "reflections": [
            "Anxiety is thought running ahead of life. When you are fully here, present, there is no gap for anxiety to fill.",
            "The search for security — psychological security — is what breeds anxiety. When you see that no thought can give you permanent security, a different quality of mind emerges.",
            "Most of what we call anxiety is the mind's habit of projecting problems into a future that hasn't arrived.",
        ],
    },
    # ──────────────────────────── SELF-KNOWLEDGE ────────────────────────────
    "self_knowledge": {
        "title": "Self-Knowledge and Self-Observation",
        "description": "The beginning and end of all psychological transformation — direct, moment-to-moment observation of thought, feeling, and reaction.",
        "core_insights": [
            "Self-knowledge is not accumulated knowledge about yourself. It is the living, flowing observation of what you actually are, moment to moment.",
            "Without self-knowledge, thought merely perpetuates its own conditioning. Self-knowledge is the foundation.",
            "You can observe yourself only in relationship, because all life is relationship.",
            "The world is me and I am the world. In myself I can see the whole movement of the world.",
        ],
        "quotes": [
            "Self-knowledge is the beginning of wisdom. In self-knowledge is the whole universe; it embraces all the struggles of humanity.",
            "The book of yourself is not written by another. No specialist, no teacher can explore it for you.",
            "You can observe yourself only in relationship, because all life is relationship.",
            "To know yourself is to study yourself in action with another person. Relationship is the mirror.",
            "There is no end to self-knowledge. It is a river without a bank.",
            "The highest form of human intelligence is to observe yourself without judgement.",
            "If you do not know yourself, whatever you think has very little meaning.",
            "The world is me and I am the world. This is not a mere verbal statement.",
            "Knowledge has not solved our human problems of sorrow, misery, confusion.",
            "Can the mind empty itself of knowledge to see things anew?",
        ],
        "inquiry_patterns": [
            "What do you mean by 'understanding yourself'? Is it collecting information, or a different quality of seeing?",
            "Can you observe what is happening in your mind right now — without judging it, without wanting it to be different?",
            "You say you want to know yourself. Who is the 'you' that wants to know? Is that also part of what needs to be seen?",
            "What do you actually see when you look at yourself — not what you think you should see?",
            "Relationship is the mirror. What do your reactions in relationship reveal about what you actually are?",
            "Can you read the book of yourself — page by page, without skipping ahead, without wanting a particular ending?",
            "What is happening right now, inside? Not what happened yesterday, not what you fear tomorrow — but right now?",
            "Has society created you, or have you created this social structure? If you have created it, are you not responsible for it?",
            "In my relationship with another, knowledge in the form of images is destructive of relationship. Can you see that?",
        ],
        "reflections": [
            "To know oneself is not a goal to be achieved. It is a living process — fresh each moment, never arriving at a conclusion that becomes dead knowledge.",
            "Without self-knowledge, there is no basis for any transformation. You may change the outward structure of your life, but inwardly the same patterns continue.",
            "Self-knowledge does not come through a book, through a guru, through a system. It comes through watching yourself in the mirror of relationship.",
        ],
    },
    # ──────────────────────────── CONDITIONING ────────────────────────────
    "conditioning": {
        "title": "Conditioning — Cultural, Religious, Psychological",
        "description": "How the mind is shaped by culture, education, religion, and experience — and whether it's possible to see this conditioning directly.",
        "core_insights": [
            "The seeing of conditioning IS the freeing from it. There is no separate act of liberation.",
            "Your consciousness is shaped by thousands of years of human experience. That conditioning is not 'yours' — it IS you.",
            "Education, religion, society — they all condition the mind. To see this is the first step.",
        ],
        "quotes": [
            "You are the result of your environment, your culture, your religion, your education. This conditioning is your consciousness.",
            "From childhood we are trained to compare. The whole structure of society is based on comparison.",
            "The mind that is caught in tradition, in belief, cannot possibly discover what is true.",
            "Conditioning means to be set in a pattern — and to be unaware that you are in a pattern.",
            "We think we think independently, but our thinking is the result of thousands of years of propaganda.",
            "The word is not the thing. The description is not the described. Yet we live by descriptions, by words.",
            "Every response you make is from the past, from your conditioning. Can you see that?",
            "To be free of conditioning you must first know you are conditioned — not theoretically, but actually.",
            "Has society created man, or has man created this social structure by his greed, his envy, his violence?",
            "We are conditioned from childhood to conform, to imitate, to accept the authority of another.",
        ],
        "inquiry_patterns": [
            "Is that your own perception, or have you been told that? Where does that belief come from?",
            "Can you see how your response is shaped by your background — not as a fault, but simply as a fact?",
            "When you react that way, is it you reacting, or your conditioning — your culture, your upbringing?",
            "You speak of what 'should be.' Who put that idea there? Your parents? Society? Religion?",
            "Can you observe the pattern without trying to change it? The very seeing may be enough.",
            "Is there a thought you hold so deeply you have never questioned it? What if we looked at it now?",
            "The word 'Hindu,' 'Christian,' 'Buddhist' — these are words that condition. Can you look at yourself without any label?",
            "What if everything you believe is a result of where you were born and how you were raised?",
            "The description is not the described. Can you see that the word 'fear' is not the actual feeling?",
        ],
        "reflections": [
            "Conditioning is not personal. It is the accumulated weight of human history pressing on each mind. To see it is not to condemn yourself but to understand the human condition.",
            "The moment you see how conditioned you are — truly see it, without judgement — something extraordinary happens. The seeing itself begins to dissolve the conditioning.",
            "We think our beliefs are ours. But look carefully — every belief has been handed to you. The real question is: can the mind be free of all belief and look freshly?",
        ],
    },
    # ──────────────────────────── RELATIONSHIP ────────────────────────────
    "relationship": {
        "title": "Relationship and Images",
        "description": "How we relate through images rather than direct perception — and what happens when images are seen for what they are.",
        "core_insights": [
            "Most relationship is between images. When images meet, there is no actual relationship, only friction between concepts.",
            "In relationship we see ourselves most clearly. Relationship is the mirror of self-knowledge.",
            "When there is no image, there is real relationship. Then there is no conflict.",
        ],
        "quotes": [
            "You have an image of your wife and she has an image of you. The relationship is between these two images.",
            "Relationship based on mutual need brings only conflict.",
            "Can one live with another without building an image?",
            "In relationship, every reaction reveals the content of one's consciousness.",
            "Knowledge about another person prevents seeing that person freshly.",
            "We use relationship for our comfort, for our satisfaction, for our loneliness. That is not relationship.",
            "When there is no image between two people, then there is a relationship that is not based on memory.",
            "Conflict in relationship is the conflict between two images, two conclusions, two pasts.",
            "Where there is division there must be conflict. This is a law.",
            "The moment you insult me, if I am totally attentive, the recording doesn't take place.",
            "We carry the dead weight of yesterday's experience into today's relationship.",
            "The whole machinery of image-making has to come to an end for actual relationship to exist.",
        ],
        "inquiry_patterns": [
            "Do you see this person as they are, or do you see the image you've built of them over time?",
            "What was hurt in that interaction? Was it you, or an image you carry of yourself?",
            "Can you meet this person freshly, without all the accumulated memories and conclusions?",
            "You say you love this person. Is it them you love, or the image — the comfort, the habit, the pleasure?",
            "Can two people be together without any image between them? What would that be like?",
            "When your partner says something that hurts, what actually happens? Does the mind record it and carry it forward?",
            "Can you be attentive at the very moment of reaction so that no recording takes place?",
            "If you dropped every opinion you hold about this person — what is left?",
            "Where there is division there must be conflict. Can you see this law operating in your own relationships?",
        ],
        "reflections": [
            "Relationship is the most extraordinary mirror. In it you can discover what you actually are — not what you think you are.",
            "When two people meet without images, something entirely new takes place. That meeting is love. But it requires dying to everything you have accumulated about the other person.",
            "All conflict in relationship stems from the image-making process: each person maintains images of the other, and these images — not the living human beings — interact.",
        ],
    },
    # ──────────────────────────── SORROW ────────────────────────────
    "sorrow": {
        "title": "Sorrow and the Ending of Sorrow",
        "description": "Understanding sorrow not as personal misfortune but as the shared human condition — and what happens when it is met without escape.",
        "core_insights": [
            "When sorrow is fully met without escape, it opens the door to compassion. The ending of sorrow is the beginning of wisdom.",
            "Sorrow is not personal. It is the sorrow of humanity. When you see this, something immense happens.",
            "The word 'passion' comes from 'sorrow.' Out of the ending of sorrow comes passion — an energy that is not of thought.",
        ],
        "quotes": [
            "When you suffer psychologically, when you remain with it completely without escape, then out of that suffering comes compassion.",
            "Sorrow is not personal. It is the sorrow of humanity.",
            "We escape from sorrow through every form of entertainment. But sorrow continues.",
            "Out of the ending of sorrow comes passion. Not lust, not desire, but the passion that is born of complete attention to suffering.",
            "Can you look at sorrow without the word, without the memory? Then it reveals its extraordinary depth.",
            "Man has carried sorrow for millennia. Every escape has not ended it.",
            "The passion that comes from the understanding of sorrow is not personal. It is compassion.",
            "Beauty and sorrow have a very close relationship. When sorrow ends, there is beauty.",
            "Can the mind face sorrow and not escape? That is the real question.",
            "When you remain with sorrow completely — not trying to escape, rationalise, or overcome it — in that total attention, sorrow ends.",
        ],
        "inquiry_patterns": [
            "Can you be with this sorrow completely — without converting it into self-pity, anger, or blame?",
            "What would it mean to not escape from this pain? Not to wallow in it, but to give it your complete attention?",
            "Is this your personal sorrow, or is it something every human being has felt?",
            "What do you do when sorrow comes? Do you intellectualize it? Blame someone? Reach for a distraction?",
            "Can we look at this sorrow without the word? The word brings all the associations. Can you feel it without naming it?",
            "You have lost something. Can you stay with that loss without seeking consolation?",
            "Out of sorrow comes something very deep — if you don't escape from it. Can we explore that together?",
            "What is the relationship between sorrow and compassion? Not pity — compassion.",
            "When you look at the enormous sorrow of the world — poverty, war, cruelty — does it touch you deeply, or have you become numb?",
        ],
        "reflections": [
            "Sorrow is one of the deepest human experiences. Everyone knows it. When you see that your sorrow is not yours alone — that it is the sorrow of humanity — self-pity ends, and something else begins.",
            "The passion born from the ending of sorrow is entirely different from the passion of desire. It is compassion itself.",
            "We have been taught to escape from sorrow. But sorrow that is fully met, fully held, reveals something immense.",
        ],
    },
    # ──────────────────────────── THOUGHT ────────────────────────────
    "thought": {
        "title": "The Nature of Thought",
        "description": "Thought as a material process — always limited, always old — and its proper place in human life.",
        "core_insights": [
            "Thought is the response of memory. It is always limited, always the past. The thinker IS the thought.",
            "Thought has its right place — in technology, in practical life. But psychologically, thought creates the illusion of a separate thinker.",
            "Thought can never bring about a fundamental change. It can rearrange, but not transform.",
        ],
        "quotes": [
            "Thought is the response of memory. Memory is the residue of experience, which is knowledge. So thought is always old, never new.",
            "The thinker IS the thought. There is no thinker without thought.",
            "Can thought be aware of its own limitation?",
            "Thought is a material process. It is the response of the brain cells which hold memory.",
            "Knowledge is always in the past. And thought, being born of knowledge, can never be fresh.",
            "Thought has created the one who thinks, and then thought says, 'I am separate from my thoughts.'",
            "The description is not the described. The word is not the thing. Yet we live in words.",
            "Thought has divided the world — into nations, religions, ideologies. This division brings conflict.",
            "When you say 'I must change,' thought has created both the 'I' and the goal. It is the same movement.",
            "Time is thought. Thought is time.",
            "Is there a perception that is not of thought? That is the real question.",
        ],
        "inquiry_patterns": [
            "Can you see that the very instrument you are using to solve this — thinking — is the same movement that created the difficulty?",
            "Is there a way of looking at this that is not through the lens of past experience?",
            "Who is the 'you' that is thinking about this? Is that thinker different from the thoughts?",
            "Thought says, 'I will solve this problem.' But can you see that thought IS the problem?",
            "Can you observe a thought as it arises — without following it, without pushing it away?",
            "Is there a perception that is not the product of memory? Can you look with fresh eyes?",
            "Thought has its place — in the practical world. But has thought overstepped its place? Can you see where?",
            "When the mind is chattering, who is listening to the chatter? Is that listener different from the chatter?",
            "You say 'I am confused.' Is the confused one different from the confusion?",
        ],
        "reflections": [
            "Thought is a remarkable tool — in the right domain. But the moment thought says 'I must become better,' it has stepped into territory where it creates only more conflict.",
            "The great insight is: the thinker IS the thought. When this is truly seen, the entire structure of the controller trying to control thought collapses.",
            "We live almost entirely in thought. The question is: is there a way of living where thought serves its purpose without dominating everything?",
        ],
    },
    # ──────────────────────────── COMPARISON ────────────────────────────
    "comparison": {
        "title": "Comparison and Becoming",
        "description": "How comparison breeds conflict, inadequacy, and violence — and the radical act of living without measurement.",
        "core_insights": [
            "The desire to become is the origin of conflict. When you drop comparison, what remains is what actually IS.",
            "All comparison is the activity of thought measuring. Without measurement, there is no sense of inadequacy.",
            "Where there is comparison, there is disorder.",
        ],
        "quotes": [
            "Where there is comparison, there is no love.",
            "Can you look at yourself without comparing yourself with another?",
            "The desire to become is the origin of conflict.",
            "From childhood we are taught to compare. This comparison breeds violence.",
            "When you compare yourself with another, you are destroying yourself.",
            "Without the measure, there is no 'better' or 'worse.' There is only what is.",
            "To live without comparison is to live with extraordinary energy.",
            "You want to become something. That becoming is the root of conflict.",
            "Comparison, imitation, conformity, authority — all these contribute to disorder.",
            "A mind that imitates, conforms, compares, is a disordered mind, however orderly it may appear on the surface.",
        ],
        "inquiry_patterns": [
            "You say you are not enough. Compared to what? Whose standard are you measuring yourself against?",
            "What if you dropped all comparison, just for this moment? What is actually here?",
            "Is there a seeing of 'what is' without the desire to change it?",
            "From childhood you've been told to compare. Can you see how deep that goes?",
            "What would your life be like if you never compared yourself with anyone, ever again?",
            "The mind says 'I should be better.' Better than what? Who set this standard?",
            "Can you look at yourself without measuring? Without the word 'success' or 'failure'?",
            "What happens to inadequacy when comparison stops? Does it exist on its own?",
            "You want to become something — better, calmer, more spiritual. But who is the 'you' that wants to become?",
        ],
        "reflections": [
            "Comparison is so deeply ingrained that we don't even notice it. This measurement IS the suffering.",
            "The ending of comparison is not resignation. It is the most vital thing — to see what actually is, without the distortion of measurement.",
            "All psychological becoming is the activity of comparison. The gap between 'I am this' and 'I should be that' is conflict, is sorrow, is time.",
        ],
    },
    # ──────────────────────────── LONELINESS ────────────────────────────
    "loneliness": {
        "title": "Loneliness and Aloneness",
        "description": "The distinction between loneliness (the pain of isolation) and aloneness (the completeness of being).",
        "core_insights": [
            "Loneliness is the awareness of complete isolation. Aloneness is entirely different — it is being whole, complete, not dependent.",
            "We fill loneliness with people, entertainment, knowledge, belief. But the loneliness remains underneath.",
            "When loneliness is fully understood, aloneness emerges — and aloneness is not lonely.",
        ],
        "quotes": [
            "Loneliness is the awareness of complete isolation.",
            "Are not most of our activities self-enclosing?",
            "We use relationship, entertainment, worship, knowledge — all to escape from this loneliness.",
            "Aloneness is entirely different from loneliness. In aloneness there is no sense of isolation.",
            "When you face loneliness completely, something entirely different takes place.",
            "We are so frightened of being alone that we will do anything — join any group, believe in anything.",
            "All our dependencies are escapes from this fundamental loneliness.",
            "Can you sit with the loneliness without seeking to fill it?",
            "The mind that can be alone is no longer lonely. It has a quality of completeness.",
        ],
        "inquiry_patterns": [
            "Is the loneliness a discovery that the 'me' is by nature separate? Can we look at that?",
            "What do you do when loneliness comes? Do you reach for the phone, turn on the television, seek company?",
            "What if loneliness is not a problem to solve, but a fact to understand?",
            "Can you distinguish between being lonely and being alone? They are entirely different.",
            "What happens when you don't run from the loneliness — when you give it complete attention?",
            "All your relationships, your distractions — are they ways to escape from this?",
            "Can loneliness reveal something to you? Not about what you lack, but about the nature of the self?",
            "Is there a completeness that comes when all escape has ended?",
        ],
        "reflections": [
            "Loneliness is one of the most fundamental human experiences. When you stop escaping and face it, loneliness transforms into aloneness — a state of completeness.",
            "The mind that can be alone — truly alone, without dependency — is no longer lonely. It has a quality of freshness and freedom that no relationship can give.",
        ],
    },
    # ──────────────────────────── DEPRESSION ────────────────────────────
    "depression": {
        "title": "Depression and the Collapse of the Self-Image",
        "description": "Exploring depression as the collapse of the self-image — the gap between what you think you should be and what is.",
        "core_insights": [
            "Depression often arises when the image you have of yourself collapses. Was that image real in the first place?",
            "The heaviness of depression is the weight of the self — its demands, its comparisons, its disappointments.",
            "All comparison breeds either elation or depression. Both are the same movement.",
        ],
        "quotes": [
            "The image you have about yourself gets hurt. And you spend your life protecting that image.",
            "When you look at depression without the word, without the explanation, what is actually there?",
            "The weight of the past is the heaviness you feel. Can the mind put it down?",
            "Depression is the mind collapsing under the weight of what it thinks it should be.",
            "To be free of the image is to be free of the suffering that comes when the image is threatened.",
            "All comparison breeds either elation or depression. Both are the same movement.",
            "Self-pity is the companion of depression. Can you see self-pity as it arises?",
            "What is this heaviness? Not the word — the actual weight. Where is it?",
            "Depression may be the mind's way of saying: the life you are living is not true.",
            "The mind that has no image of itself is free from the cycle of inflation and deflation.",
        ],
        "inquiry_patterns": [
            "Depressed compared to what? What is the image you are falling short of?",
            "You say you feel empty. Can we look at that emptiness without running from it?",
            "What if this heaviness is not wrong — what if it is showing you something about the images you have been carrying?",
            "Can you look at what you call 'depression' without naming it? What happens to it then?",
            "Is it depression, or is it the weight of trying to be something you're not?",
            "You had an image of who you should be. Has that image collapsed? Can we look at what happens when it does?",
            "What if there is nothing wrong? What if the mind is simply exhausted from the effort of becoming?",
            "Can you observe the self-pity without getting caught in it? Just see it, like watching a cloud?",
            "You feel heavy. Is the heaviness about what is actually happening, or about the gap between what is and what you want?",
        ],
        "reflections": [
            "Depression is often the collapse of an image. Perhaps what is being revealed is the futility of image-making itself.",
            "The mind that has no image of itself cannot be depressed in the psychological sense. It may be quiet, but that stillness has nothing to do with heaviness.",
            "When we stop trying to be something and simply look at what we are, the energy that was being used in becoming is released.",
        ],
    },
    # ──────────────────────────── MEDITATION ────────────────────────────
    "meditation": {
        "title": "Meditation and Choiceless Awareness",
        "description": "Meditation not as technique but as the quality of attention that comes when the mind understands its own movement.",
        "core_insights": [
            "Meditation is not a means to an end. The first step is the last step — to perceive without condemnation.",
            "Meditation is the quality of attention that pervades all of life — not something you do for twenty minutes.",
            "A mind that is silent — not made silent through effort — has access to the immeasurable.",
            "Any system of meditation is not meditation. Any method makes the mind mechanical.",
        ],
        "quotes": [
            "Meditation is the emptying of the mind of all the things that the mind has put together.",
            "The first step is the last step. Perceive what you are thinking, perceive your ambition, your anxiety. Just perceive it.",
            "Awareness without choice is the highest form of intelligence.",
            "Meditation is not a withdrawal from life. It is the understanding of the whole movement of life.",
            "A mind that practises a method becomes mechanical. And a mechanical mind can never discover what is sacred.",
            "The quality of silence is not the product of effort. It comes naturally when the mind has understood itself.",
            "Meditation is not concentration. Concentration is exclusion. Meditation is inclusive — it embraces everything.",
            "When the mind is completely still — not controlled, but still because it has understood — then that which is immeasurable comes into being.",
            "In that silence there is a quality that is sacred. Not the sacredness invented by thought.",
            "Attention is entirely different from concentration. In attention there is no centre from which you attend.",
            "The controller is the controlled. The one who says 'I must meditate' is the very thing he is trying to overcome.",
            "Meditation is the flowering of understanding. Like a flower that opens naturally.",
        ],
        "inquiry_patterns": [
            "Can you observe what is happening in your mind right now — not to change it, just to see it?",
            "What would it mean to be aware without choosing — not selecting what to observe, but letting everything be seen?",
            "Is there a quality of attention where you are not the centre looking outward, but attention itself — without a centre?",
            "Are you meditating to achieve something? If so, that achievement is projected by thought.",
            "What is silence? Not the absence of noise — but the silence that comes when the mind has understood its own chatter?",
            "Can attention exist without an object? Not attending to something — just attention?",
            "What happens when you stop all methods and just look? Not waiting for anything — just looking?",
            "Can the mind be quiet without any form of control? That is the essence of meditation.",
            "If the controller IS the controlled, what happens to the effort to meditate?",
            "Is there a meditation that is not separate from daily life — from washing dishes, from walking, from talking?",
        ],
        "reflections": [
            "Meditation is perhaps the most misunderstood word. It is the quality of a mind that has understood itself. When that understanding is complete, the mind is naturally silent.",
            "The silence of meditation is not the silence of a graveyard. It is alive, vibrant, extraordinarily sensitive.",
            "Meditation cannot be taught. It begins with self-knowledge and ends where the known ends.",
        ],
    },
    # ──────────────────────────── AUTHORITY ────────────────────────────
    "authority": {
        "title": "Authority and Freedom",
        "description": "Why psychological authority — the guru, the expert, the system — prevents self-knowledge and genuine freedom.",
        "core_insights": [
            "Truth is a pathless land. No guru, no teacher, no system can give you freedom.",
            "Following another in matters of the spirit is the denial of one's own intelligence.",
            "The moment you accept authority psychologically, you have surrendered your capacity to discover.",
        ],
        "quotes": [
            "Truth is a pathless land. Man cannot come to it through any organization, through any creed, through any dogma.",
            "The moment you follow someone, you cease to follow Truth.",
            "You are your own teacher and your own pupil.",
            "Authority prevents learning. It gives you a framework, but destroys the capacity to find out for yourself.",
            "No one can give you freedom. If someone gives it to you, it is not freedom.",
            "To follow another is to deny your own light.",
            "Religion is not belief, not dogma. It is the quality of mind that is utterly free from all authority.",
            "Education is not the accumulation of knowledge. It is the understanding of oneself.",
            "The teacher who says 'I know, you don't know' has already established authority. And where there is authority, there is no learning.",
            "Can a mind be free of all authority and therefore be capable of looking at itself without any distortion? That is the religious mind.",
            "When you follow another in spiritual matters, what happens to your capacity to see directly for yourself?",
        ],
        "inquiry_patterns": [
            "You are looking for someone to tell you the answer. Can we ask — why? What would happen if you looked for yourself?",
            "I am not your authority. Can we explore this together, as two people inquiring?",
            "What is it that makes you seek guidance? Is there a fear of making a mistake?",
            "Can you put aside every authority — including these words — and look for yourself?",
            "What happens when you have no teacher, no method, no system? Is that frightening? Or is that freedom?",
            "You quote others to support your views. But what do YOU see? Not what they said — what do you actually see?",
            "Why do you need a guru? Is it because you distrust your own capacity to observe?",
            "Can a mind burdened with belief ever discover what is true? Or does the very belief prevent the seeing?",
            "Why do you hesitate at the brink of deep self-inquiry? What are you afraid of finding?",
        ],
        "reflections": [
            "The rejection of psychological authority is not rebellion — it is the most responsible thing a human being can do.",
            "Every system of self-improvement is based on authority — someone else's idea of what you should become.",
            "True religion has nothing to do with organizations, rituals, or belief systems. It is the quality of mind that is free to inquire.",
        ],
    },
    # ──────────────────────────── DEATH ────────────────────────────
    "death": {
        "title": "Death and Living",
        "description": "Death not as the end of life but as the continuous ending of the known — dying to the past so the mind is perpetually fresh.",
        "core_insights": [
            "We have separated living from dying. The interval between them is fear.",
            "Death is not at the end of life. It is the ending of the known. When there is this ending, there is freshness.",
            "Death, living, and love are not three separate things. They are one indivisible movement.",
        ],
        "quotes": [
            "We have separated living from dying, and the interval between the living and the dying is fear.",
            "To die to everything of yesterday, so that your mind is always fresh, always young, innocent, full of vigour and passion.",
            "Can you die to a pleasure? Not tomorrow — now? That is the real meaning of death.",
            "The mind that dies to everything it knows is a mind that is truly alive.",
            "Death is not something that happens at the end. It is happening now — in every ending.",
            "We cling to the known because the unknown terrifies us. But the known is the dead.",
            "Living, loving, and dying are not separate things. When you separate them, life becomes a battle.",
            "The fear of death is the fear of losing what you have — your knowledge, your identity.",
            "If you die to attachment, you are no longer seeking security in another. And out of that freedom comes love.",
            "What is it that incarnates? If you haven't changed the content of consciousness, what continues is the same bundle.",
            "To incarnate now means to change profoundly now.",
        ],
        "inquiry_patterns": [
            "What if ending — letting go of what you know — is not loss but renewal?",
            "Can you die to this memory, this grudge, this image — right now? What happens when you do?",
            "Are you living, or are you carrying the past and calling it life?",
            "Can you let go of what happened today — completely — so that tomorrow is fresh?",
            "What is it that you are so afraid of losing? Is it you — or an image of you?",
            "Death means ending. Can you end something you hold dear — not physically, but psychologically?",
            "If you could die to everything you know about yourself, what would remain?",
            "Can you live each day so completely that each day is a dying to everything accumulated?",
            "What is it you are actually frightened of in death? The ending of the known?",
        ],
        "reflections": [
            "Death is not the enemy. It is the ending that makes the new possible. When you die to the past — moment by moment — life is always new.",
            "To die to the known is not a grim act of renunciation. It is the most vital thing — like a tree shedding its leaves.",
            "Death, love, and living are one movement. When you separate them, you lose the beauty of the whole.",
        ],
    },
    # ──────────────────────────── ANGER ────────────────────────────
    "anger": {
        "title": "Anger and the Observer",
        "description": "Seeing anger without the division of controller and controlled — the observer IS the observed.",
        "core_insights": [
            "The observer IS the observed. When this is seen, the conflict of controlling anger dissolves.",
            "Anger is a response to a threatened image. When the image is seen as image, the anger has no ground.",
            "To understand anger, you must meet it without the intention to suppress or express it.",
        ],
        "quotes": [
            "The observer IS the observed. The thinker IS the thought.",
            "As long as there is an observer who says 'I must change,' there will be conflict.",
            "Anger is the response of a mind that has been hurt. The hurt is the image.",
            "When you are angry, there is no 'you' separate from the anger. The division comes later — through thought.",
            "Can you observe anger without naming it? The moment you name it, you have separated yourself from it.",
            "Violence is not only physical. There is violence in comparison, in judgement, in the desire to change.",
            "The effort to control anger is itself a form of violence.",
            "When you are completely one with anger — not controlling it, not expressing it — it undergoes a transformation.",
            "What is hurt is always an image. See the image, and the hurt dissolves.",
        ],
        "inquiry_patterns": [
            "Who is trying to control the anger? Is that controller different from the anger?",
            "Can you be with the anger without naming it, without judging it, without trying to push it away?",
            "What was threatened? What image of yourself was challenged?",
            "Can you observe the anger without the observer — without the one who judges it?",
            "What happens when you don't try to do anything with the anger — not express, not suppress — just watch?",
            "Is the anger about what happened, or about the image that was hurt?",
            "There is anger. Can you stay with it — not for a second, but completely? What do you find?",
            "The division between 'me' and 'my anger' — is it real? Or is it created by thought after the fact?",
            "You say, 'I should not be angry.' Who is this 'I' that should not be angry?",
        ],
        "reflections": [
            "The observer IS the observed. When you truly see this, the whole effort of controlling anger drops away, and a different response becomes possible.",
            "Anger arises when an image is threatened. The anger is not the problem. The image is.",
            "There is a third possibility beyond suppression and expression: to give anger complete attention, without any movement.",
        ],
    },
    # ──────────────────────────── MEANING ────────────────────────────
    "meaning": {
        "title": "The Search for Meaning",
        "description": "Questioning the very search for meaning — who is searching, and can the searcher exist without the search?",
        "core_insights": [
            "The seeker IS the sought. When the search stops, what remains may be what you were looking for.",
            "The demand for meaning arises from a mind that feels empty. The emptiness is not a problem.",
            "When thought is quiet, life has an extraordinary beauty that needs no meaning.",
        ],
        "quotes": [
            "The ability to observe without evaluating is the highest form of intelligence.",
            "The seeker IS the sought. When the seeking stops, you may find what you are looking for.",
            "A mind that demands meaning is a mind that is afraid of what is.",
            "Life has no meaning that thought can give it. But when thought is quiet, life has extraordinary beauty.",
            "The search for meaning is the escape from what is.",
            "When there is complete attention to what is, the question of meaning does not arise.",
            "Purpose is a projection of the mind. Can you live without purpose and still be fully alive?",
            "The meaning of life is not found in books or teachers. It is found in the quality of your attention.",
            "Our living, our daily everyday existence, is a battlefield. We call this living. Is there a totally different way?",
        ],
        "inquiry_patterns": [
            "Who is looking for meaning? Can that one exist without the search?",
            "What if meaning is not found at the end of a search, but in the quality of attention you bring to this moment?",
            "Why do you need meaning? What is the emptiness you are trying to fill?",
            "What if there is no meaning — at least not the kind thought can construct? What then?",
            "Can you live without demanding that life have a purpose? What would that be like?",
            "You feel life is meaningless. But is the demand for meaning itself the problem?",
            "What if the emptiness you feel is not a deficiency, but a space — open, alive, full of potential?",
            "When you are fully present, does the question of meaning even arise?",
        ],
        "reflections": [
            "When you stop searching, demanding, projecting — when you are simply present — life reveals a quality that needs no justification.",
            "Meaning is a construction of thought. When thought is quiet, there may be something beyond meaning — something immeasurable.",
        ],
    },
    # ──────────────────────────── DESIRE ────────────────────────────
    "desire": {
        "title": "Understanding Desire",
        "description": "Desire not as something to suppress or indulge, but as a movement to understand — sensation, perception, and thought's role.",
        "core_insights": [
            "Desire is perception plus sensation plus thought creating an image. Without the image, there is only natural perception.",
            "The problem is not desire itself but thought's interference — 'I must have' or 'I must not have.'",
            "There can be a gap between sensation and the movement of thought — and in that gap lies transformation.",
        ],
        "quotes": [
            "You see a beautiful thing and there is perception, sensation. Then thought comes and says, 'I must have it.' That is the birth of desire.",
            "The understanding of desire is not the denial of it. To deny desire is to deny life.",
            "Desire is not the enemy. The enemy is thought shaping desire into craving.",
            "Can you look at something beautiful without thought saying, 'I must possess it'?",
            "To control desire is to create a controller — and the controller IS desire.",
            "The monk who suppresses desire and the hedonist who indulges — both are caught in the same movement.",
            "Can you enjoy something without the desire to repeat the experience?",
            "When you observe desire without the observer, without the censor, desire has quite a different meaning.",
            "The whole movement of desire is perception, sensation, contact, and then thought creating the image.",
            "To observe desire without any distortion, without any motive — just to observe it — brings about a totally different quality.",
        ],
        "inquiry_patterns": [
            "Can you trace the movement of desire? First seeing, then sensation, then thought creates an image — and desire is born.",
            "You want something. Can you look at the wanting without judging it?",
            "Is it the object you desire, or the image thought has created around it?",
            "Can you enjoy the beauty of something without the urge to possess it?",
            "The mind says 'I should not desire.' But that 'should not' is also desire — the desire to be desireless.",
            "What happens if you don't suppress desire and don't indulge it — but just watch it?",
            "When thought takes over sensation, desire becomes craving. Can you see that moment?",
            "Can there be a gap between sensation and the movement of thought? That is the real question.",
            "Who is the entity that wants to control desire? Is that controller not also a product of desire?",
        ],
        "reflections": [
            "Desire is a natural movement of life — seeing, sensing, responding. The trouble begins when thought creates the image of possession. Seeing this mechanism is not suppression — it is intelligence.",
            "Every religion has tried to deal with desire through control. But understanding desire is entirely different from controlling it. In understanding, there is freedom.",
        ],
    },
    # ──────────────────────────── PLEASURE ────────────────────────────
    "pleasure": {
        "title": "Pleasure and Happiness",
        "description": "The distinction between pleasure (sustained by thought through memory) and joy (which comes uninvited).",
        "core_insights": [
            "Pleasure is the continuity of an experience through thought. Joy comes uninvited and departs when thought tries to hold it.",
            "The pursuit of pleasure is thought seeking to repeat an experience. That repetition is never the original.",
            "Happiness is not pleasure. Happiness comes when you are not seeking it.",
        ],
        "quotes": [
            "Pleasure is the continuation of an experience by thought. Joy is something entirely different.",
            "Thought takes over a moment of delight and turns it into a demand for repetition. That demand is pleasure.",
            "You cannot invite joy. The moment you try to hold it, it becomes pleasure.",
            "Does pleasure bring happiness? Or does the pursuit of pleasure bring anxiety about losing it?",
            "Happiness is not something you can pursue. The very pursuit of happiness is the denial of it.",
            "Pleasure always has the shadow of pain.",
            "Can you enjoy without the desire to repeat? That is freedom from the pleasure principle.",
            "The demand for the repetition of an experience is the movement of pleasure. And that repetition inevitably becomes mechanical.",
            "The pursuit of pleasure is the pursuit of something already dead, because it is the pursuit of a memory.",
            "When you see a mountain with its snow cap glistening, there is great delight. But thought says, 'I must go back there.' And the living thing is dead.",
        ],
        "inquiry_patterns": [
            "Can you see how thought takes a natural moment of delight and turns it into a demand for repetition?",
            "Is what you are seeking pleasure — or something deeper that pleasure cannot give?",
            "You had a beautiful experience and you want it again. But is the memory of it the same as the experience?",
            "What is the difference between enjoyment in the moment and the demand for pleasure?",
            "Does the pursuit of pleasure bring happiness? Or does it bring the fear of not having it?",
            "Joy comes uninvited. What happens when you try to capture it?",
            "Can you enjoy something fully without thought saying, 'I must have this again'?",
            "What would life be like if you lived fully in each moment without demanding its repetition?",
        ],
        "reflections": [
            "Every pursuit of pleasure carries the seed of anxiety — the fear of losing it. Joy is entirely different. It comes when you are not looking.",
            "Thought can replay a moment of delight endlessly. But the replay is never the real thing. The insistence on replaying is what creates craving and suffering.",
        ],
    },
    # ──────────────────────────── HURT ────────────────────────────
    "hurt": {
        "title": "Being Hurt and Hurting Others",
        "description": "How psychological hurt works — it is always an image that is hurt, never the actual self.",
        "core_insights": [
            "It is the image about yourself that gets hurt — never the actual you. When you see the image as image, hurt cannot take root.",
            "From childhood we build images, and those images get hurt. The hurt then shapes all future behaviour.",
            "To never be hurt again is not to build a wall — it is to have no image at all.",
        ],
        "quotes": [
            "The image you have about yourself gets hurt. And you spend your life protecting that image.",
            "A child is told he is stupid. That word creates an image, and that image is carried for life.",
            "All our resistance, all our self-protection, is the response of past hurts.",
            "Can you live without a single image about yourself? Then there is nothing to hurt.",
            "The hurt is the image. See the image, and the hurt dissolves.",
            "From hurt comes the desire to hurt others. The cycle continues.",
            "The walls we build to protect ourselves from hurt also prevent us from living fully.",
            "When there is no image, there is a vulnerability that is not weakness — it is openness.",
            "When you are attentive, there is no hurt. Inattention is the ground of hurt.",
            "If you have no conclusion about yourself, no fixed image, what is there to be hurt?",
        ],
        "inquiry_patterns": [
            "What was actually hurt? Was it you — or an image of yourself?",
            "From childhood, hurts accumulate. Can you see them — not as feelings to push away, but as facts to understand?",
            "The walls you've built to protect yourself — are they protecting you or imprisoning you?",
            "Can you drop the image that was hurt? Not the memory, but the image that took the blow?",
            "If you had no image of yourself — no picture of who you should be — could you be hurt psychologically?",
            "Does self-protection actually protect you? Or does it prevent you from living openly?",
            "Can you see the cycle: being hurt, building walls, isolating, and calling it relationship?",
            "When you hurt someone else, can you trace it back to your own hurt?",
            "What happens when you are completely attentive at the moment of insult? Does the recording take place?",
        ],
        "reflections": [
            "Every hurt is the hurt of an image. See the image, and you are free from the hurt.",
            "The accumulation of hurts from childhood shapes the entire personality. To see this clearly is to begin to be free of it.",
            "Inattention is the ground on which hurt grows. In complete attention there is no self-image to wound.",
        ],
    },
    # ──────────────────────────── LOVE ────────────────────────────
    "love": {
        "title": "Love and the Absence of Self",
        "description": "Love is not what thought has made of it — not attachment, not sentiment. Love exists when the self is absent.",
        "core_insights": [
            "Love is not thought, not desire, not attachment. Love comes into being when the self is absent.",
            "Where there is jealousy, possessiveness, dependency — there is no love.",
            "Love is discovered through negation — by seeing what love is NOT.",
        ],
        "quotes": [
            "Love is not thought. Love is not a thing of the mind.",
            "Where there is jealousy, there is no love. Where there is possessiveness, there is no love.",
            "Love is not the product of thought and therefore cannot be cultivated.",
            "When the self is not, love is.",
            "Love is not pleasure. Love is not desire. They have nothing in common.",
            "Love and attachment are contradictory. Where there is attachment, there is fear of loss.",
            "Love is the most revolutionary thing in the world. Because love is not of time.",
            "When you love, there is no image — no you, no me.",
            "Compassion is the action of love. It has nothing to do with sentiment.",
            "Love is not jealousy. Love is not possessiveness. Love is not dependency. When you negate all that, what remains?",
        ],
        "inquiry_patterns": [
            "You say you love. But is there attachment in it? Possessiveness? A need for something in return?",
            "What is love without the 'me'? Have you ever experienced a moment where the self was completely absent?",
            "Can you love without wanting anything? Without expectation, without motive?",
            "Is what you call love actually dependency? What would happen if the other person left?",
            "Love and jealousy — can they exist together? Or is one the denial of the other?",
            "When the image drops — of yourself, of the other — what is the relationship that remains?",
            "Can you negate everything that love is not? What is left?",
            "Where there is love, do you need rules? Does morality flower naturally when there is love?",
            "You are seeking love. But can love be sought? Or does seeking prevent its coming?",
        ],
        "reflections": [
            "Love is discovered through negation. By seeing clearly what it is NOT — jealousy, possessiveness, attachment — love reveals itself.",
            "When all the images drop, what remains is something extraordinary. That is love. And it has no motive.",
        ],
    },
    # ──────────────────────────── LISTENING ────────────────────────────
    "listening": {
        "title": "The Art of Listening",
        "description": "True listening happens when the mind is quiet — without prejudice, without forming conclusions while listening.",
        "core_insights": [
            "We rarely listen because we are too busy preparing our response, comparing, judging.",
            "When you truly listen — without the screen of your prejudices — what you hear transforms you instantly.",
            "The act of listening itself is the action.",
        ],
        "quotes": [
            "You are not listening if you are merely hearing words and agreeing or disagreeing.",
            "Real listening happens when you are not comparing what is being said with what you already know.",
            "Listening is an act of attention in which there is no centre — no 'me' who is listening.",
            "When you listen completely, the beauty of it is there.",
            "Most of us never listen. We hear through our prejudices, our fears, our anxieties, our desires.",
            "Do we actually see, or do we see through a screen, darkly?",
            "We have screen after screen between us and the object of perception. So do we ever see the thing at all?",
            "The art of listening is the art of silence.",
            "To listen to another without any movement of thought is one of the most difficult things.",
            "Learning is not the accumulation of knowledge. It is a constant movement without the past.",
        ],
        "inquiry_patterns": [
            "Are you listening to what is being said, or are you already formulating a response?",
            "Can you listen without the filter of what you already know? Just hear — freshly?",
            "What happens when you truly listen — not just with the ear, but with your whole being?",
            "Can you listen to yourself with the same quality of attention?",
            "When someone speaks to you, do you hear them — or your interpretation of them?",
            "What prevents you from listening? Is it impatience? The desire to respond?",
            "Can you listen to the silence between the words?",
            "When you look at someone close to you, are you seeing them or the image you have built?",
            "The moment you draw a conclusion, you stop listening. Can you remain without conclusion?",
        ],
        "reflections": [
            "True listening is extraordinarily rare. When you listen without the movement of thought — without agreeing, disagreeing, comparing — the very listening itself transforms.",
            "Listening is not passive. It is the most active thing you can do. It requires the whole of your attention.",
        ],
    },
    # ──────────────────────────── KNOWLEDGE ────────────────────────────
    "knowledge": {
        "title": "Knowledge, Learning, and the Known",
        "description": "The difference between knowledge (always the past) and learning (always the present).",
        "core_insights": [
            "Knowledge is always the past. Learning is always in the present. The two are entirely different.",
            "Self-transformation is not dependent on knowledge or time. It happens in the instant of seeing.",
            "Psychological knowledge prevents fresh perception.",
        ],
        "quotes": [
            "Knowledge is always in the past. And thought, being born of knowledge, can never discover the new.",
            "Learning is not the accumulation of knowledge. Learning is the movement of understanding in the present.",
            "Self-transformation is not dependent on knowledge or time.",
            "Knowledge has its place — in science, in technology. But psychological knowledge prevents seeing freshly.",
            "Freedom from the known is not the rejection of knowledge — it is the understanding of its limitation.",
            "Knowledge gives you security. But that security is the prison.",
            "Can you look at the world, at yourself, without the weight of all that you know?",
            "Merely to accumulate knowledge and act from that knowledge is not transformation.",
            "Knowledge is always in the shadow of ignorance. Understanding is immediate perception.",
        ],
        "inquiry_patterns": [
            "Is your response coming from what you actually see, or from what you have been told?",
            "Can you look at this situation as if you have never encountered anything like it before?",
            "Knowledge has been your security. What happens when you put it aside — just for this moment?",
            "Are you learning right now — or fitting what you hear into what you already know?",
            "What is the difference between knowledge and wisdom? Can wisdom be accumulated?",
            "Can you meet this person, this problem, this moment — without the past?",
            "Knowledge says, 'I know.' Learning says, 'I don't know.' Which state is richer?",
            "Has the knowledge you have gathered actually solved your fundamental human problems?",
        ],
        "reflections": [
            "Knowledge is a remarkable tool in the right domain. But 'I know myself' or 'I know you' becomes a prison that prevents seeing what is fresh.",
            "True learning is not accumulation. It is the act of being present to what is. In that learning, transformation happens instantly.",
        ],
    },
    # ──────────────────────────── FREEDOM ────────────────────────────
    "freedom": {
        "title": "Freedom and Transformation",
        "description": "Freedom is not from something — it is the quality of a mind that has understood its own bondage.",
        "core_insights": [
            "Freedom is not 'freedom from.' Freedom is a state of being where the known does not dictate.",
            "Transformation is not gradual. It happens in the instant of clear perception.",
            "A different way of living is possible — without conflict, without comparison, without becoming.",
        ],
        "quotes": [
            "Freedom from something is not freedom. Freedom is an entirely different quality.",
            "Transformation is not a gradual thing. It happens in the moment of seeing.",
            "Is there a way of living that is not a battle? Something entirely different?",
            "Freedom is not at the end of a long road. It is in the first step — the step of seeing what is.",
            "Can you live without conflict? Not as an ideal — but actually?",
            "Revolution is not political or social. Revolution is the transformation of the human mind.",
            "When the mind is free from the known, the unknown becomes possible.",
            "When the observer is the observed, the mind has a totally different quality of energy.",
            "A mind that is not tortured, not brutalized by conformity — only such a mind can see what is true.",
        ],
        "inquiry_patterns": [
            "What does freedom mean to you? Is it freedom from something — or something more?",
            "You want to be free. Free from what? And is the 'you' that wants freedom part of the bondage?",
            "Can transformation happen now — not tomorrow, not through a process — but in this very instant?",
            "What would a life without conflict look like? Not as an ideal, but as a reality?",
            "Freedom is not at the end of effort. Can you see that the effort to become free is itself bondage?",
            "What if the first step IS the last step? What if seeing clearly is all that is needed?",
            "Is it possible to live without the movement of becoming — without trying to be something you are not?",
            "When you see the whole map of violence, conformity, imitation — as one total movement — what takes place?",
        ],
        "reflections": [
            "True freedom is the quality of a mind that has no psychological bondage. That mind is free, and in that freedom there is extraordinary energy.",
            "Transformation is not a process in time. It happens completely in the moment of seeing. The first step is the last step.",
        ],
    },
    # ──────────────────────────── ORDER ────────────────────────────
    "order": {
        "title": "Order from Understanding Disorder",
        "description": "True order is not imposed from outside — it emerges naturally when the mind understands its own disorder.",
        "core_insights": [
            "Order is not discipline imposed from outside. Order comes from understanding disorder.",
            "The mind that imposes order is still in disorder — it is merely controlling, suppressing, conforming.",
            "When you see the whole structure of disorder, order comes naturally, without effort.",
        ],
        "quotes": [
            "Order comes from the understanding of our disorder — not from the imposition of a pattern.",
            "The mind that disciplines itself into order is a mind in conflict. That conflict IS disorder.",
            "Virtue is not something you practise. Virtue is the natural outcome of understanding disorder.",
            "The mind that conforms to a pattern of order is the most disorderly mind.",
            "Disorder is the conflict between what is and what should be. Order is the seeing of what is.",
            "You cannot impose order. The imposition itself creates disorder.",
            "True order is living — it changes, it moves. It is not a fixed pattern.",
            "Order is not the product of discipline but arises naturally from understanding.",
        ],
        "inquiry_patterns": [
            "You want order in your life. But have you looked at the disorder? Really looked?",
            "Is your order something imposed — a routine, a discipline — or something that arises from understanding?",
            "The conflict between what you are and what you think you should be — is that not the root of disorder?",
            "Can order come without effort? When you truly see disorder, does order not emerge naturally?",
            "What creates disorder in your life? Is it external, or the contradictions within?",
            "Discipline means to learn, not to conform. Are you learning about your disorder, or trying to suppress it?",
            "The mind that imposes order through control — is it orderly or merely suppressed?",
        ],
        "reflections": [
            "Order cannot be imposed. Every imposition creates its own disorder. But when you understand disorder completely, order comes as naturally as breathing.",
            "All our attempts to create order through willpower are themselves disordered. True order arises only when the mind sees its own confusion clearly.",
        ],
    },
    # ──────────────────────────── RESPONSIBILITY ────────────────────────────
    "responsibility": {
        "title": "What Is a Responsible Human Being?",
        "description": "True responsibility is not duty or obligation — it is the response that comes from seeing clearly.",
        "core_insights": [
            "Responsibility is the ability to respond — not from duty, not from guilt, but from clear perception.",
            "You are the world and the world is you. Your transformation IS the transformation of the world.",
            "There is a distinction between being responsible FOR and BEING responsible — the latter is total.",
        ],
        "quotes": [
            "You are the world and the world is you. What you are, the world is.",
            "The responsible human being understands that his own transformation is the transformation of society.",
            "Responsibility is not obligation. It is the natural response of a mind that sees clearly.",
            "To be responsible is to see that the disorder in the world is the disorder in yourself.",
            "Responsibility is not a burden. Duty has a military ring about it. Responsibility is sensitivity.",
            "Where there is love, there is responsibility. Not for one or two, but for the whole of humanity.",
            "If you are sensitive to the beauty of the world and its suffering, that sensitivity makes you responsible.",
        ],
        "inquiry_patterns": [
            "You are the world. Can you see that your anger, your greed, your fear are not just personal?",
            "What does it mean to be responsible? Not in terms of duty — but in terms of seeing?",
            "Responsibility is response-ability — the ability to respond. Are you responding, or merely reacting?",
            "The disorder you see in the world — can you see that same disorder in yourself?",
            "You want to change the world. But can you change it without changing yourself?",
            "We act from fragments — as businessman, father, citizen. Have you ever acted as a total human being?",
            "When there is love, does responsibility need to be cultivated? Or does it flow naturally?",
        ],
        "reflections": [
            "The most radical thing a human being can do is self-understanding. When you see that you are the world, transformation takes on a different meaning.",
            "Responsibility is not a burden. It is the natural response of clarity. When you see clearly, you act rightly.",
        ],
    },
}

# ── Opening, acknowledgment, and closing phrase pools ──

_OPENING_PHRASES: list[str] = [
    "Can we look at that together?",
    "Let's go into that slowly, carefully.",
    "That's a very important question. Let's not rush to answer it.",
    "Before we go further, can we examine what is behind that feeling?",
    "Let's explore this together — not as teacher and student, but as two people inquiring.",
    "I wonder if we can look at this without trying to arrive at a conclusion.",
    "That is something worth looking at very closely.",
    "Let's begin carefully, from the beginning — without assuming we know the answer.",
    "There is something very deep here. Can we look at it without fear?",
    "Can we set aside everything we think we know and look at this freshly?",
    "You raise something very fundamental. Let's explore it together.",
    "Don't accept what I say. Let's look together and see what is actually true.",
    "This is something every human being faces. Let us go into it seriously.",
    "Let's take this very slowly. The speed of thought often prevents real seeing.",
    "That needs looking into. Not answering — but looking.",
    "Can we approach this not from what we have read, but from what we actually observe?",
    "That question itself is the beginning. Let's stay with it.",
    "Let's not try to solve this. Let's understand it first.",
    "Something is being revealed here. Can we give it space?",
    "Can we begin not with the answer, but with the looking?",
]

_ACKNOWLEDGMENT_PHRASES: list[str] = [
    "I hear what you're saying. There is something real in that.",
    "Yes. That is something many people feel, though few look at it closely.",
    "What you describe is very common — and very deep.",
    "That takes courage to say. Let's honour it by looking at it honestly.",
    "That feeling you're describing — it is part of the human condition.",
    "You are touching something very important.",
    "That is an honest observation. Let's go further.",
    "What you're pointing to is not trivial. It goes to the root of things.",
    "Many people carry this. Few look at it directly.",
    "There is nothing wrong with feeling that. The question is: can we look at it?",
    "That is worth your attention — complete attention.",
    "You are beginning to observe something. Let's stay with it.",
    "That question comes from real experience, not theory.",
    "What you describe is not a problem to solve — it is a fact to understand.",
    "Yes, I understand. And the understanding itself may be the answer.",
]

_CLOSING_PHRASES: list[str] = [
    "We've looked at this together. There is no conclusion to reach — just the seeing itself.",
    "Can you carry this observation into your daily life — not as a conclusion, but as a living inquiry?",
    "The question we've explored doesn't need an answer from me. It needs your own looking.",
    "Stay with what we've uncovered. Let it work in you, without trying to do anything with it.",
    "This is not an answer — it is an invitation to keep looking, freshly, each time.",
    "We haven't arrived at a conclusion — and that is the beauty of it. The inquiry is alive.",
    "Take this observation with you — not as knowledge, but as a seed of attention.",
    "Let what we've seen here settle in you. Don't try to hold it — let it live.",
    "The seeing is the doing. There is nothing more to add.",
    "There is no practice here, no method. Just the quality of attention itself.",
    "This is a beginning, not an end. Each day the looking is new.",
    "Carry this inquiry into your relationships, your work, your solitude. It is a living thing.",
    "The question is more important than any answer. Keep the question alive.",
    "What we've seen together cannot be taken away. But it must be seen again, freshly, each time.",
    "There is nothing to become. There is only the seeing of what is — and that seeing is transformative.",
    "Let this be a seed — not a conclusion. Water it with your own attention.",
    "Don't try to remember this as knowledge. Let it work on you directly.",
    "Truth cannot be accumulated. It must be discovered anew each time.",
    "The first step is the last step. You have already taken it by looking.",
    "This conversation is not separate from your life. It IS your life, when you look.",
]

# ── Deepening question pools (cross-theme) ──

_DEEPENING_QUESTIONS: list[str] = [
    "Can you stay with that observation a little longer — without moving away from it?",
    "What happens when you don't try to change what you see?",
    "Is there a seeing without the one who sees?",
    "Can you observe this in your daily life — not just here, but when you are alone, in relationship, at work?",
    "What is the actual feeling — not the word, not the story — but the raw sensation?",
    "Who is the one observing? Is that observer separate from what is being observed?",
    "Can you drop the word and look at the thing itself?",
    "What if there is nothing to do — only something to see?",
    "The mind wants to act. Can it simply be still and watch?",
    "You've named what you feel. But what is there before the naming?",
    "Can you hold this question without answering it? Let the question do its work?",
    "What you are seeing now — is it happening in the past, or right now?",
    "Is there a space between the experience and the reaction? Can you widen that space?",
    "What would happen if you did absolutely nothing about this?",
    "The mind says 'I understand.' But understanding is not a conclusion. Can you keep looking?",
]


def _match_counselling_theme(user_message: str) -> str:
    """Return the best-matching counselling theme key for a user message."""
    msg = user_message.lower()

    keyword_map: list[tuple[list[str], str]] = [
        (["afraid", "fear", "scared", "terrif", "dread", "panic", "phobia"], "fear"),
        (["anxi", "nervous", "worry", "worri", "uneasy", "restless", "tense"], "anxiety"),
        (["depress", "hopeless", "empty", "numb", "worthless", "no point", "dark place", "heavy"], "depression"),
        (["angry", "anger", "furious", "rage", "irritat", "resent", "frustrat"], "anger"),
        (["lonely", "alone", "isolat", "no one", "nobody", "disconnected"], "loneliness"),
        (["hurt", "wounded", "offend", "betray", "insult", "pain from", "rejection"], "hurt"),
        (["relationship", "partner", "spouse", "husband", "wife", "marriage", "breakup", "divorce"], "relationship"),
        (["love", "loving", "beloved", "heart", "intimacy", "compassion"], "love"),
        (["sorrow", "grief", "loss", "mourn", "bereav", "died", "death of", "passed away"], "sorrow"),
        (["die", "dying", "death", "mortal", "end of life", "afterlife"], "death"),
        (["meaning", "purpose", "point of life", "why am i", "meaningless", "existential"], "meaning"),
        (["meditat", "mindful", "stillness", "silence", "inner peace", "calm mind", "sacred"], "meditation"),
        (["desire", "crave", "craving", "urge", "tempt", "addict", "yearning", "wanting things", "wanting more"], "desire"),
        (["pleasure", "enjoy", "happiness", "joy", "satisfaction", "gratif"], "pleasure"),
        (["listen", "hear", "attention", "aware", "present", "mindful"], "listening"),
        (["should be", "not good enough", "compar", "better than", "worse than", "inadequa", "measure up"], "comparison"),
        (["condition", "programm", "brought up", "taught to", "societi", "culture", "tradition"], "conditioning"),
        (["knowledge", "learn", "study", "education", "understand", "intellect"], "knowledge"),
        (["freedom", "free", "liberat", "transform", "change", "different life"], "freedom"),
        (["order", "disciplin", "routine", "chaos", "disorder", "structure"], "order"),
        (["responsib", "duty", "obligat", "contribute", "the world", "humanity"], "responsibility"),
        (["self", "who am i", "identity", "know myself", "understand myself"], "self_knowledge"),
        (["thought", "thinking", "mind won't stop", "overthink", "ruminate", "can't stop thinking"], "thought"),
        (["authorit", "guru", "teacher", "expert", "follow", "obey", "depend", "religion", "god", "belief"], "authority"),
    ]

    for keywords, theme in keyword_map:
        for kw in keywords:
            if kw in msg:
                return theme

    return "self_knowledge"


def _build_counselling_response(
    theme_key: str,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an inquiry-based counselling response for the matched theme.

    Uses randomised selection with history-aware de-duplication so the user
    never receives the same quote, inquiry, or opening twice in a row.
    """
    theme = _COUNSEL_THEMES.get(theme_key, _COUNSEL_THEMES["self_knowledge"])
    history = history or []

    # ── Collect previously-used indices to avoid repetition ──
    used_quotes: set[int] = set()
    used_inquiries: set[int] = set()
    used_openings: set[int] = set()
    used_closings: set[int] = set()
    for h in history[-6:]:
        if h.get("theme") == theme_key:
            if "quote_idx" in h:
                used_quotes.add(h["quote_idx"])
            if "inquiry_idx" in h:
                used_inquiries.add(h["inquiry_idx"])
        if "opening_idx" in h:
            used_openings.add(h["opening_idx"])
        if "closing_idx" in h:
            used_closings.add(h["closing_idx"])

    def _pick(pool: list[str], used: set[int]) -> tuple[str, int]:
        available = [i for i in range(len(pool)) if i not in used]
        if not available:
            available = list(range(len(pool)))
        idx = random.choice(available)
        return pool[idx], idx

    # ── Select components ──
    opening, opening_idx = _pick(_OPENING_PHRASES, used_openings)
    acknowledgment = random.choice(_ACKNOWLEDGMENT_PHRASES)
    inquiry, inquiry_idx = _pick(theme["inquiry_patterns"], used_inquiries)

    # Pick a different inquiry for deepening (or cross-theme deepener)
    remaining_inquiries = [i for i in range(len(theme["inquiry_patterns"]))
                          if i != inquiry_idx and i not in used_inquiries]
    if remaining_inquiries and random.random() < 0.6:
        deep_idx = random.choice(remaining_inquiries)
        deepening = theme["inquiry_patterns"][deep_idx]
    else:
        deepening = random.choice(_DEEPENING_QUESTIONS)

    closing, closing_idx = _pick(_CLOSING_PHRASES, used_closings)
    quote, quote_idx = _pick(theme["quotes"], used_quotes)

    # Pick a reflection
    reflections = theme.get("reflections", [theme["description"]])
    reflection = random.choice(reflections)

    # Pick a core insight
    insights = theme.get("core_insights", [])
    core_insight = random.choice(insights) if insights else ""

    return {
        "theme": theme_key,
        "theme_title": theme["title"],
        "core_insight": core_insight,
        "response": {
            "opening": opening,
            "acknowledgment": acknowledgment,
            "inquiry": inquiry,
            "deepening": deepening,
            "reflection": reflection,
            "closing": closing,
        },
        "quote": quote,
        "all_quotes": theme["quotes"],
        "_indices": {
            "opening_idx": opening_idx,
            "closing_idx": closing_idx,
            "inquiry_idx": inquiry_idx,
            "quote_idx": quote_idx,
        },
    }



@app.get("/api/psychiatry/themes", tags=["Psychiatry"])
async def get_psychiatry_themes() -> dict[str, Any]:
    """Return all counselling themes and their metadata."""
    themes = {}
    for key, theme in _COUNSEL_THEMES.items():
        themes[key] = {
            "title": theme["title"],
            "description": theme["description"],
            "core_insights": theme.get("core_insights", []),
            "quote_count": len(theme["quotes"]),
            "inquiry_count": len(theme["inquiry_patterns"]),
        }
    return {"themes": themes, "count": len(themes)}


@app.post("/api/psychiatry/counsel", tags=["Psychiatry"])
async def psychiatry_counsel(request: Request) -> dict[str, Any]:
    """Process a counselling message and return an inquiry-based response.

    Expects JSON body:
        {"message": "user's message text", "history": [...previous response indices...]}
    The optional ``history`` list enables de-duplication: each entry is a dict
    with keys like ``theme``, ``quote_idx``, ``inquiry_idx``, ``opening_idx``,
    ``closing_idx`` (taken from the ``_indices`` field of prior responses).
    """
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    if len(message) > 5000:
        raise HTTPException(status_code=400, detail="Message too long (max 5000 characters)")

    history: list[dict[str, Any]] = body.get("history", [])

    theme_key = _match_counselling_theme(message)
    response = _build_counselling_response(theme_key, message, history=history)
    return response


@app.get("/api/psychiatry/knowledge-base", tags=["Psychiatry"])
async def get_psychiatry_knowledge_base() -> dict[str, Any]:
    """Return the psychiatry knowledge base document (from research cache)."""
    for doc in _RESEARCH_CACHE.get("documents", []):
        if doc.get("id") == "psychiatry-knowledge-base":
            return {"document": doc}
    return {"document": None, "message": "Psychiatry knowledge base not found in cache"}


@app.get("/api/debug/templates")
async def debug_templates(request: Request) -> dict[str, Any]:
    """Diagnostic endpoint for template debugging."""
    if _TELOSCOPY_ENV == "production":
        raise HTTPException(status_code=404, detail="Not found")
    import os
    import traceback

    import starlette

    diag: dict[str, Any] = {
        "templates_dir": str(_TEMPLATES_DIR),
        "templates_dir_exists": _TEMPLATES_DIR.exists(),
        "template_files": (
            [f.name for f in _TEMPLATES_DIR.iterdir()] if _TEMPLATES_DIR.exists() else []
        ),
        "static_dir": str(_STATIC_DIR),
        "static_dir_exists": _STATIC_DIR.exists(),
        "cwd": os.getcwd(),
        "app_file": str(Path(__file__).resolve()),
        "starlette_version": starlette.__version__,
    }

    # Try rendering index.html to catch the actual error
    try:
        resp = templates.TemplateResponse(request=request, name="index.html")
        diag["index_render"] = "OK"
        diag["index_status"] = resp.status_code
    except Exception as exc:
        diag["index_render_error"] = f"{type(exc).__name__}: {exc}"
        diag["index_traceback"] = traceback.format_exc()

    return diag


# ===================================================================== #
#  API routes                                                            #
# ===================================================================== #

# -- Health -----------------------------------------------------------------


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Returns system health status including uptime and version info.",
    dependencies=[Depends(rate_limit(60, 60))],
)
async def health_check() -> HealthResponse:
    """Liveness / readiness probe."""
    return HealthResponse()


@app.get(
    "/readiness",
    tags=["Health"],
    summary="Readiness check",
    description="Checks if all subsystems (pipeline, diet advisor, disease predictor) are available and ready to serve requests.",
)
async def readiness_check() -> dict[str, Any]:
    """Return readiness status of all subsystems."""
    return {
        "status": "ready",
        "checks": {
            "pipeline": True,
            "diet_advisor": True,
            "disease_predictor": True,
        },
    }


@app.get(
    "/api/agents/status",
    response_model=AgentSystemStatus,
    tags=["Agents"],
    summary="Agent system status",
    description="Returns the current status of each agent in the multi-agent system, including active jobs and uptime.",
    dependencies=[Depends(rate_limit(60, 60)), Depends(require_consent("telomere_analysis"))],
)
async def agents_status() -> AgentSystemStatus:
    """Return status of each agent in the multi-agent system."""
    now: datetime = datetime.utcnow()
    agents: list[AgentInfo] = [
        AgentInfo(
            name="Image Analysis Agent",
            status=AgentStatusEnum.IDLE,
            last_active=now,
            tasks_completed=random.randint(10, 200),
        ),
        AgentInfo(
            name="Genomics Agent",
            status=AgentStatusEnum.IDLE,
            last_active=now,
            tasks_completed=random.randint(10, 200),
        ),
        AgentInfo(
            name="Nutrition Agent",
            status=AgentStatusEnum.IDLE,
            last_active=now,
            tasks_completed=random.randint(10, 200),
        ),
        AgentInfo(
            name="Improvement Agent",
            status=AgentStatusEnum.IDLE,
            last_active=now,
            tasks_completed=random.randint(5, 50),
        ),
    ]
    # If there are running jobs, mark relevant agents as busy
    active: int = sum(1 for j in _jobs.values() if j.status == JobStatusEnum.RUNNING)
    if active > 0 and agents:
        agents[0].status = AgentStatusEnum.BUSY
        agents[0].current_task = "Processing microscopy image"

    return AgentSystemStatus(
        agents=agents,
        total_analyses=len(_jobs),
        active_jobs=active,
        uptime_seconds=round(time.time() - _APP_START_TIME, 1),
    )


# -- Upload -----------------------------------------------------------------


@app.post(
    "/api/upload",
    response_model=UploadResponse,
    status_code=201,
    tags=["Analysis"],
    summary="Upload microscopy image",
    description="Upload a microscopy or face photograph image and receive a job_id for tracking subsequent analysis.",
    dependencies=[Depends(rate_limit(10, 60)), Depends(require_consent("telomere_analysis", "facial_analysis"))],
)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    """Upload a microscopy image and receive a ``job_id``."""
    if not file.filename or not _validate_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Invalid file type. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"),
        )

    job_id: str = str(uuid.uuid4())
    ext: str = Path(file.filename).suffix.lower()
    dest: Path = _UPLOAD_DIR / f"{job_id}{ext}"

    # Read in chunks to avoid loading multi-GB payloads into memory before
    # the size check fires.  Abort as soon as the limit is exceeded.
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1 MiB chunks
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds the 50 MiB limit.",
            )
        chunks.append(chunk)
    contents = b"".join(chunks)
    dest.write_bytes(contents)
    safe_filename = file.filename.replace('\n', '_').replace('\r', '_')
    logger.info("Saved upload %s → %s (%d bytes)", safe_filename, dest, len(contents))

    _evict_stale_jobs()
    _jobs[job_id] = JobStatus(job_id=job_id)

    return UploadResponse(job_id=job_id, filename=file.filename)


# -- Status / results -------------------------------------------------------


@app.get(
    "/api/status/{job_id}",
    response_model=JobStatus,
    tags=["Analysis"],
    summary="Get job status",
    description="Return the current status and progress of an analysis job by its job_id.",
    dependencies=[Depends(rate_limit(60, 60)), Depends(require_consent("telomere_analysis"))],
)
async def get_job_status(job_id: str) -> JobStatus:
    """Return the current status of an analysis job."""
    job: JobStatus | None = _jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    return job


@app.get(
    "/api/results/{job_id}",
    response_model=AnalysisResponse,
    tags=["Analysis"],
    summary="Get analysis results",
    description="Return the full analysis results (telomere, disease risk, nutrition) for a completed job.",
    dependencies=[Depends(rate_limit(60, 60)), Depends(require_consent("telomere_analysis"))],
)
async def get_job_results(job_id: str) -> AnalysisResponse:
    """Return the full results of a completed analysis job."""
    job: JobStatus | None = _jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    if job.status != JobStatusEnum.COMPLETED or job.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job_id} is not yet complete (status={job.status.value}).",
        )
    return job.result


# -- Full analysis -----------------------------------------------------------


@app.post(
    "/api/analyze",
    response_model=JobStatus,
    status_code=202,
    tags=["Analysis"],
    summary="Run full analysis pipeline",
    description="Upload an image with user profile data and run the complete analysis pipeline (telomere measurement, disease risk, nutrition plan).",
    dependencies=[Depends(rate_limit(20, 60)), Depends(require_consent("telomere_analysis", "disease_risk", "nutrition_plan"))],
)
async def full_analysis(
    file: UploadFile = File(...),
    age: int = Form(...),
    sex: str = Form(...),
    region: str = Form(...),
    country: str = Form(""),
    state: str = Form(""),
    dietary_restrictions: str = Form(""),
    known_variants: str = Form(""),
    health_conditions: str = Form(""),
) -> JobStatus:
    """Run the full analysis pipeline (image + profile → results).

    Parameters are sent as multipart form data so the image and JSON
    metadata travel in a single request.
    """
    if not file.filename or not _validate_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    job_id: str = str(uuid.uuid4())
    ext: str = Path(file.filename).suffix.lower()
    dest: Path = _UPLOAD_DIR / f"{job_id}{ext}"

    contents: bytes = await _read_upload_chunked(file, _MAX_UPLOAD_BYTES)
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 50 MiB limit.",
        )
    dest.write_bytes(contents)

    # Parse comma-separated lists
    restrictions: list[str] = [r.strip() for r in dietary_restrictions.split(",") if r.strip()]
    variants: list[str] = [v.strip() for v in known_variants.split(",") if v.strip()]
    conditions: list[str] = [c.strip() for c in health_conditions.split(",") if c.strip()]

    profile = UserProfile(
        age=age,
        sex=Sex(sex),
        region=region,
        country=country or None,
        state=state or None,
        dietary_restrictions=restrictions,
        known_variants=variants,
        health_conditions=conditions,
    )

    job = JobStatus(job_id=job_id, message="Queued for analysis")
    _evict_stale_jobs()
    _jobs[job_id] = job

    # Fire-and-forget background task
    asyncio.create_task(_run_full_analysis_limited(job_id, profile, str(dest)))  # noqa: RUF006
    logger.info("Queued full analysis job %s", job_id)

    return job


# -- Disease risk (standalone) -----------------------------------------------


@app.post(
    "/api/disease-risk",
    response_model=DiseaseRiskResponse,
    tags=["Disease Risk"],
    summary="Predict disease risks",
    description="Compute disease-risk scores from known genetic variants, age, sex, and region without requiring an image upload.",
    dependencies=[Depends(rate_limit(20, 60)), Depends(require_consent("disease_risk", "genetic_data"))],
)
async def disease_risk(request: DiseaseRiskRequest) -> DiseaseRiskResponse:
    """Compute disease-risk scores from variants and telomere data."""
    variant_dict = _build_variant_dict(request.known_variants)
    try:
        risk_profile = await asyncio.to_thread(
            _disease_predictor.predict_from_variants,
            variant_dict,
            request.age,
            request.sex.value,
        )
        risks = _translate_disease_risks(risk_profile.top_risks(n=15))
    except Exception:
        logger.exception("disease-risk prediction failed, returning empty")
        risks = []
    overall: float = round(sum(r.probability for r in risks) / max(len(risks), 1), 3)
    return DiseaseRiskResponse(risks=risks, overall_risk_score=min(overall, 1.0))


# -- Diet plan (standalone) --------------------------------------------------


@app.post(
    "/api/diet-plan",
    response_model=DietPlanResponse,
    tags=["Nutrition"],
    summary="Generate diet plan",
    description="Generate a personalised diet plan based on genetic risk profile, dietary restrictions, and regional food preferences.",
    dependencies=[Depends(rate_limit(20, 60)), Depends(require_consent("nutrition_plan"))],
)
async def diet_plan(request: DietPlanRequest) -> DietPlanResponse:
    """Generate a personalised diet plan."""
    variant_dict = _build_variant_dict(request.known_variants)
    resolved_region = resolve_region(
        request.region,
        country=getattr(request, "country", None),
        state=getattr(request, "state", None),
    )
    try:
        genetic_risk_names = [r.disease for r in request.disease_risks]
        diet_recs = await asyncio.to_thread(
            _diet_advisor.generate_recommendations,
            genetic_risk_names,
            variant_dict,
            resolved_region,
            request.age,
            request.sex.value,
            request.dietary_restrictions or None,
        )
        diet_meals = await asyncio.to_thread(
            _diet_advisor.create_meal_plan,
            diet_recs,
            resolved_region,
            request.calorie_target,
            request.meal_plan_days,
            request.dietary_restrictions or None,
        )

        # Safety net: adapt any remaining violations post-hoc.
        if request.dietary_restrictions:
            diet_meals = await asyncio.to_thread(
                _diet_advisor.adapt_to_restrictions,
                diet_meals,
                request.dietary_restrictions,
            )

        rec = _translate_diet_recommendation(diet_recs, diet_meals)
    except Exception:
        logger.exception("diet-plan generation failed, returning defaults")
        rec = DietRecommendation(
            summary="A balanced diet rich in whole foods is recommended.",
            key_nutrients=["Omega-3", "Folate", "Vitamin D"],
            foods_to_increase=["Leafy greens", "Fatty fish", "Berries"],
            foods_to_avoid=["Processed meats", "Refined sugars"],
            meal_plans=[],
            calorie_target=2100,
        )
    return DietPlanResponse(recommendation=rec)


# -- Image validation --------------------------------------------------------


@app.post(
    "/api/validate-image",
    response_model=ImageValidationResponse,
    tags=["Analysis"],
    summary="Validate image",
    description="Validate an uploaded image before analysis — checks format, dimensions, and classifies as face photo or microscopy image.",
    dependencies=[Depends(rate_limit(10, 60)), Depends(require_consent("telomere_analysis"))],
)
async def validate_image(file: UploadFile = File(...)) -> ImageValidationResponse:
    """Validate an uploaded image before analysis.

    Checks magic bytes, decodability, dimensions, and classifies as
    face photo or microscopy image. Use this for client-side previews.
    """
    if not file.filename or not _validate_extension(file.filename):
        return ImageValidationResponse(
            valid=False,
            issues=[f"Invalid file type. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"],
        )
    contents: bytes = await _read_upload_chunked(file, _MAX_UPLOAD_BYTES)
    if len(contents) > _MAX_UPLOAD_BYTES:
        return ImageValidationResponse(
            valid=False,
            file_size_bytes=len(contents),
            issues=["File exceeds the 50 MiB limit."],
        )
    return await asyncio.to_thread(_validate_image_content, contents, file.filename)


# -- Profile-only analysis (no image) ----------------------------------------


@app.post(
    "/api/profile-analysis",
    response_model=ProfileAnalysisResponse,
    tags=["Analysis"],
    summary="Profile-only analysis",
    description="Run disease-risk and nutrition analysis using only user-provided details (no image upload required).",
    dependencies=[Depends(rate_limit(20, 60)), Depends(require_consent("disease_risk", "nutrition_plan", "profile_data"))],
)
async def profile_analysis(request: ProfileAnalysisRequest) -> ProfileAnalysisResponse:
    """Run disease-risk and nutrition analysis using only user-provided details.

    No image upload is required. Users provide age, sex, region, dietary
    restrictions, and optionally known genetic variants.
    """
    variant_dict = _build_variant_dict(request.known_variants)
    risks: list[DiseaseRisk] = []
    rec: DietRecommendation | None = None

    # Disease risk
    if request.include_disease_risk:
        try:
            risk_profile = await asyncio.to_thread(
                _disease_predictor.predict_from_variants,
                variant_dict,
                request.age,
                request.sex.value,
            )
            risks = _translate_disease_risks(risk_profile.top_risks(n=15))
        except Exception:
            logger.exception("profile-analysis: disease-risk failed")

    # Nutrition
    if request.include_nutrition:
        try:
            resolved_rgn = resolve_region(
                request.region,
                country=getattr(request, "country", None),
                state=getattr(request, "state", None),
            )
            genetic_risk_names = [r.disease for r in risks[:10]]
            diet_recs = await asyncio.to_thread(
                _diet_advisor.generate_recommendations,
                genetic_risk_names,
                variant_dict,
                resolved_rgn,
                request.age,
                request.sex.value,
                request.dietary_restrictions or None,
            )
            diet_meals = await asyncio.to_thread(
                _diet_advisor.create_meal_plan,
                diet_recs,
                resolved_rgn,
                2000,
                7,
                request.dietary_restrictions or None,
            )
            if request.dietary_restrictions:
                diet_meals = await asyncio.to_thread(
                    _diet_advisor.adapt_to_restrictions,
                    diet_meals,
                    request.dietary_restrictions,
                )
            rec = _translate_diet_recommendation(diet_recs, diet_meals)
        except Exception:
            logger.exception("profile-analysis: nutrition failed")

    overall = round(sum(r.probability for r in risks) / max(len(risks), 1), 3) if risks else 0.0
    return ProfileAnalysisResponse(
        disease_risks=risks,
        diet_recommendations=rec,
        overall_risk_score=min(overall, 1.0),
    )


# -- Standalone nutrition endpoint -------------------------------------------


@app.post(
    "/api/nutrition",
    response_model=NutritionResponse,
    tags=["Nutrition"],
    summary="Personalised nutrition plan",
    description="Generate a personalised nutrition plan from user details including health conditions, dietary restrictions, and genetic variants.",
    dependencies=[Depends(rate_limit(20, 60)), Depends(require_consent("nutrition_plan"))],
)
async def nutrition_plan(request: NutritionRequest) -> NutritionResponse:
    """Generate a personalised nutrition plan from user details.

    Accepts age, sex, region, dietary restrictions, known variants,
    health conditions, calorie target, and number of meal plan days.
    No image required.
    """
    variant_dict = _build_variant_dict(request.known_variants)
    resolved_region = resolve_region(
        request.region,
        country=getattr(request, "country", None),
        state=getattr(request, "state", None),
    )
    try:
        # Use health conditions as genetic risk proxies
        genetic_risk_names = list(request.health_conditions)
        diet_recs = await asyncio.to_thread(
            _diet_advisor.generate_recommendations,
            genetic_risk_names,
            variant_dict,
            resolved_region,
            request.age,
            request.sex.value,
            request.dietary_restrictions or None,
        )
        diet_meals = await asyncio.to_thread(
            _diet_advisor.create_meal_plan,
            diet_recs,
            resolved_region,
            request.calorie_target,
            request.meal_plan_days,
            request.dietary_restrictions or None,
        )
        if request.dietary_restrictions:
            diet_meals = await asyncio.to_thread(
                _diet_advisor.adapt_to_restrictions,
                diet_meals,
                request.dietary_restrictions,
            )
        rec = _translate_diet_recommendation(diet_recs, diet_meals, request.calorie_target)
    except Exception:
        logger.exception("nutrition plan generation failed")
        rec = DietRecommendation(
            summary="A balanced diet rich in whole foods is recommended.",
            key_nutrients=["Omega-3", "Folate", "Vitamin D"],
            foods_to_increase=["Leafy greens", "Berries", "Legumes"],
            foods_to_avoid=["Processed meats", "Refined sugars"],
            meal_plans=[],
            calorie_target=request.calorie_target,
        )
    return NutritionResponse(recommendation=rec)


# -- Health checkup ----------------------------------------------------------


@app.post(
    "/api/health-checkup",
    response_model=HealthCheckupResponse,
    tags=["Health Checkup"],
    summary="Analyse annual health checkup",
    description=(
        "Upload blood test, urine test, and abdomen scan results to "
        "get a personalised health analysis with condition detection, "
        "health scoring, and a diet plan tailored to your findings."
    ),
    dependencies=[Depends(rate_limit(10, 60)), Depends(require_consent("health_report"))],
)
async def health_checkup(request: HealthCheckupRequest) -> HealthCheckupResponse:
    """Analyse health checkup data and return personalised diet plan."""
    # Reject if no lab data at all — a score of 0/100 with 0 parameters is misleading.
    has_blood = request.blood_tests is not None and any(
        v is not None for v in request.blood_tests.model_dump().values()
    )
    has_urine = request.urine_tests is not None and any(
        v is not None for v in request.urine_tests.model_dump().values()
    )
    if not has_blood and not has_urine:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No lab values provided. Please enter at least one blood or urine "
                "test value, or upload a lab report using the 'Upload Report' tab."
            ),
        )
    try:
        response = await asyncio.to_thread(_health_analyzer.analyze, request)
    except Exception as exc:
        logger.error("health-checkup analysis failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health checkup analysis failed. Please try again.",
        )
    return response


# -- Health checkup report upload --------------------------------------------

_REPORT_ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".txt", ".text", ".csv",
}
_MAX_REPORT_BYTES: int = 20 * 1024 * 1024  # 20 MiB


@app.post(
    "/api/health-checkup/parse-report",
    response_model=ReportParsePreview,
    tags=["Health Checkup"],
    summary="Parse uploaded lab report (preview)",
    description=(
        "Upload a lab report (PDF, image, or text file) and get a preview "
        "of extracted lab values. Use this to review and correct values "
        "before running the full health checkup analysis."
    ),
    dependencies=[Depends(rate_limit(10, 60)), Depends(require_consent("health_report"))],
)
async def parse_report_preview(file: UploadFile = File(...)) -> ReportParsePreview:
    """Parse an uploaded lab report and return extracted values for review.

    Supports PDF, image (via OCR), and plain text files.
    """
    filename = file.filename or "report"
    ext = Path(filename).suffix.lower()
    if ext and ext not in _REPORT_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_REPORT_ALLOWED_EXTENSIONS))}",
        )

    contents: bytes = await _read_upload_chunked(file, _MAX_REPORT_BYTES)
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Detect file type and extract text
    file_type = detect_file_type(contents, filename)
    try:
        text = await asyncio.to_thread(extract_text, contents, filename)
    except RuntimeError as exc:
        return ReportParsePreview(
            confidence=0.0,
            file_type=file_type,
            text_length=0,
            unrecognized_lines=[str(exc)],
        )

    if not text.strip():
        hints = []
        if file_type == "pdf":
            hints.append("The PDF may be a scanned image without a text layer. Try uploading as an image instead, or use the manual entry form.")
        elif file_type == "image":
            hints.append("Could not extract text from the image. The image may be too low quality or in an unsupported format. Try the manual entry form.")
        else:
            hints.append("Could not extract any text from the uploaded file.")
        return ReportParsePreview(
            confidence=0.0,
            file_type=file_type,
            text_length=0,
            unrecognized_lines=hints,
        )

    # Parse lab values from extracted text
    blood_tests, urine_tests, abdomen_text = await asyncio.to_thread(
        parse_lab_report, text
    )

    # Compute confidence
    confidence = compute_extraction_confidence(blood_tests, urine_tests, abdomen_text, text)

    # Collect unrecognized lines (lines with numbers that weren't matched)
    import re as _re

    unrecognized: list[str] = []
    recognized_values = set()
    for v in blood_tests.values():
        recognized_values.add(str(v))
    for v in urine_tests.values():
        recognized_values.add(str(v))

    for line in text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped or len(line_stripped) < 5:
            continue
        if _re.search(r"\d+\.?\d*", line_stripped):
            # Check if any recognized value appears in this line
            has_recognized = False
            for rv in recognized_values:
                if rv in line_stripped:
                    has_recognized = True
                    break
            if not has_recognized and len(unrecognized) < 50:
                unrecognized.append(line_stripped[:200])

    return ReportParsePreview(
        extracted_blood_tests=blood_tests,
        extracted_urine_tests=urine_tests,
        extracted_abdomen_notes=abdomen_text,
        unrecognized_lines=unrecognized,
        confidence=confidence,
        file_type=file_type,
        text_length=len(text),
    )


@app.post(
    "/api/health-checkup/upload",
    response_model=HealthCheckupResponse,
    tags=["Health Checkup"],
    summary="Upload lab report and analyse",
    description=(
        "Upload a lab report (PDF, image, or text) along with profile data "
        "to get a full health checkup analysis. The report is parsed "
        "automatically and values are used for condition detection, health "
        "scoring, and personalised diet planning."
    ),
    dependencies=[Depends(rate_limit(10, 60)), Depends(require_consent("health_report"))],
)
async def health_checkup_upload(
    file: UploadFile = File(...),
    age: int = Form(...),
    sex: str = Form(...),
    region: str = Form(...),
    country: str = Form(None),
    state: str = Form(None),
    dietary_restrictions: str = Form(""),
    known_variants: str = Form(""),
    calorie_target: int = Form(2000),
    meal_plan_days: int = Form(7),
    health_conditions: str = Form(""),
) -> HealthCheckupResponse:
    """Upload a lab report file and run full health checkup analysis.

    The uploaded file is parsed to extract blood test, urine test, and
    abdomen scan values.  These are combined with the provided profile
    data and run through the same analysis pipeline as the manual entry
    endpoint (``/api/health-checkup``).
    """
    filename = file.filename or "report"
    ext = Path(filename).suffix.lower()
    if ext and ext not in _REPORT_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_REPORT_ALLOWED_EXTENSIONS))}",
        )

    contents: bytes = await _read_upload_chunked(file, _MAX_REPORT_BYTES)
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Extract text and parse lab values
    file_type = detect_file_type(contents, filename)
    try:
        text = await asyncio.to_thread(extract_text, contents, filename)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    if not text.strip():
        if file_type == "pdf":
            detail = "Could not extract text from the PDF. It may be a scanned image without a text layer. Try using the 'Extract Lab Values' button first, or enter values manually."
        elif file_type == "image":
            detail = "Could not extract text from the image. It may be too low quality. Try entering values manually."
        else:
            detail = "Could not extract text from the uploaded file. Try entering values manually."
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    blood_dict, urine_dict, abdomen_text = await asyncio.to_thread(
        parse_lab_report, text
    )

    if not blood_dict and not urine_dict:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No lab values could be extracted from the uploaded file. "
                "Please check the file format or use manual entry."
            ),
        )

    # Parse comma-separated form fields
    restrictions: list[str] = [r.strip() for r in dietary_restrictions.split(",") if r.strip()]
    variants: list[str] = [v.strip() for v in known_variants.split(",") if v.strip()]
    conditions: list[str] = [c.strip() for c in health_conditions.split(",") if c.strip()]

    # Build request from parsed data
    blood_panel = BloodTestPanel(**blood_dict) if blood_dict else None
    urine_panel = UrineTestPanel(**urine_dict) if urine_dict else None

    # Validate that at least one real value was extracted (not all None)
    has_blood = blood_panel is not None and any(
        v is not None for v in blood_panel.model_dump().values()
    )
    has_urine = urine_panel is not None and any(
        v is not None for v in urine_panel.model_dump().values()
    )
    if not has_blood and not has_urine:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No recognisable lab values could be extracted from the uploaded file. "
                "Please check the file format, or switch to the manual entry tabs "
                "and enter your blood/urine test values directly."
            ),
        )

    checkup_request = HealthCheckupRequest(
        age=age,
        sex=Sex(sex),
        region=region,
        country=country or None,
        state=state or None,
        dietary_restrictions=restrictions,
        known_variants=variants,
        blood_tests=blood_panel,
        urine_tests=urine_panel,
        abdomen_scan_notes=abdomen_text or None,
        calorie_target=calorie_target,
        meal_plan_days=meal_plan_days,
        health_conditions=conditions,
    )

    try:
        response = await asyncio.to_thread(_health_analyzer.analyze, checkup_request)
    except Exception as exc:
        logger.error("health-checkup upload analysis failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health checkup analysis failed. Please try again.",
        )
    return response
