# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.subscription_gate import SubscriptionGateMiddleware
from app.utils.logging import configure_structlog


_PII_KEYS = ("first_name", "last_name", "dob", "doc_number", "email", "phone", "address", "username")


def _sentry_before_send(event, hint):
    """Strip PII fields from Sentry events before transmission."""
    if event is None:
        return None
    for key in _PII_KEYS:
        event.get("extra", {}).pop(key, None)
    # Sentry user context — clear entirely rather than scrub selectively
    if "user" in event:
        event["user"] = {}
    # contexts["user"] sub-dict
    contexts = event.get("contexts", {})
    if isinstance(contexts.get("user"), dict):
        contexts["user"] = {}
    return event


def create_app() -> FastAPI:
    configure_structlog(environment=settings.environment)

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            before_send=_sentry_before_send,
            send_default_pii=False,
            environment=settings.environment,
        )

    application = FastAPI(
        title="Aura ID Backend",
        version="1.0.0",
        # Hide API docs in production to prevent schema exposure
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(AuditMiddleware)
    application.add_middleware(SubscriptionGateMiddleware)

    @application.get("/health", tags=["ops"])
    async def health():
        # Simple liveness check — no DB ping, no secrets exposed
        return {"status": "ok"}

    import atexit
    from app.services.retention import start_retention_scheduler
    _scheduler = start_retention_scheduler()
    atexit.register(_scheduler.shutdown)

    return application


app = create_app()
