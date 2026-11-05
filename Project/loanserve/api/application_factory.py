"""Build one independently configured FastAPI application per call."""

from time import monotonic

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from loanserve.api.orm_models import create_session_factory
from loanserve.api.access_control import AccessControl
from loanserve.api.middleware import RequestLogger, SlidingWindowRateLimiter
from loanserve.api.password_hashing import PasswordVault
from loanserve.api.repository import InMemoryApplicationRepository, SqlApplicationRepository
from loanserve.api.routers.loan_applications import router as applications_router
from loanserve.api.routers.user_accounts import router as accounts_router
from loanserve.api.routers.assistant import router as assistant_router
from loanserve.api.routers.policy import router as policy_router
from loanserve.core.exceptions import LoanServeError
from config.constants import ALLOWED_ORIGINS, MAXIMUM_REQUESTS_PER_MINUTE


def create_application(database_url=None, maximum_requests_per_minute=None, request_log_path=None):
    application = FastAPI(
        title="LoanServe",
        version="1.0",
        docs_url=None,
        servers=[{"url": "."}],
    )
    if database_url is None:
        application.state.application_repository = InMemoryApplicationRepository()
    else:
        application.state.application_repository = SqlApplicationRepository(create_session_factory(database_url))
    application.state.access_control = AccessControl()
    application.state.password_vault = PasswordVault()
    application.state.user_accounts = {}
    limiter = SlidingWindowRateLimiter(maximum_requests_per_minute or MAXIMUM_REQUESTS_PER_MINUTE, 60)
    application.add_middleware(
        CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"],
    )

    @application.middleware("http")
    async def refuse_when_over_the_limit(request: Request, call_next):
        client_key = request.client.host if request.client else "unknown"
        if not limiter.is_allowed(client_key, monotonic()):
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        return await call_next(request)

    if request_log_path is not None:
        application.middleware("http")(RequestLogger(request_log_path))

    @application.exception_handler(LoanServeError)
    async def report_domain_error(_request, raised_error):
        return JSONResponse(status_code=400, content={"detail": str(raised_error)})

    @application.get("/health", tags=["service"])
    def read_health():
        _, total = application.state.application_repository.list_applications(None, 1, 0)
        return {"status": "ok", "applications": total}

    @application.get("/docs", include_in_schema=False, response_class=HTMLResponse)
    async def read_docs():
        return get_swagger_ui_html(
            openapi_url="openapi.json",
            title=f"{application.title} - Swagger UI",
        )

    application.include_router(accounts_router, prefix="/api/v1")
    dependencies = [] if application.state.access_control.open_mode else [Depends(application.state.access_control.authorise)]
    application.include_router(applications_router, prefix="/api/v1", dependencies=dependencies)
    application.include_router(assistant_router, prefix="/api/v1", dependencies=dependencies)
    application.include_router(policy_router, prefix="/api/v1", dependencies=dependencies)
    return application


if __name__ == "__main__":
    from fastapi.testclient import TestClient
    print(TestClient(create_application()).get("/health").json())
