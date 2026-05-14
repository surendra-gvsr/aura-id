# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging import configure_structlog


def _sentry_before_send(event, hint):
    """Strip PII fields from Sentry events before transmission."""
    for key in ("first_name", "last_name", "dob", "doc_number", "email", "phone", "address"):
        event.get("extra", {}).pop(key, None)
        event.get("contexts", {}).pop(key, None)
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

    @application.get("/health", tags=["ops"])
    async def health():
        # Simple liveness check — no DB ping, no secrets exposed
        return {"status": "ok"}

    return application


app = create_app()
