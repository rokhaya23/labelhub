import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import auth, users, datasets, campaigns, tasks, annotations

from app.core.errors import BusinessRuleError, ForbiddenActionError, NotFoundError
from app.middlewares.request_id import RequestIDLogFilter, RequestIDMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware
 
# Configuration du logging pour que request_id apparaisse sur chaque ligne
logging.basicConfig(format="%(asctime)s [%(request_id)s] %(levelname)s %(name)s: %(message)s")
logging.getLogger().addFilter(RequestIDLogFilter())
logger = logging.getLogger("labelhub")


app = FastAPI(
    title="LabelHub API",
    description="API de plateforme d'annotation de données - Master 1 DSIA",
    version="0.1.0",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(annotations.router, prefix="/annotations", tags=["annotations"])


@app.exception_handler(BusinessRuleError)
def business_rule_error_handler(request: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
 
 
@app.exception_handler(ForbiddenActionError)
def forbidden_action_error_handler(request: Request, exc: ForbiddenActionError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})
 
 
@app.exception_handler(NotFoundError)
def not_found_error_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
