import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ContextVar : contrairement à une simple variable globale, elle isole
# proprement chaque requête même avec plusieurs requêtes traitées en
# parallèle (async) - chacune a sa propre valeur, pas de mélange possible.
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDLogFilter(logging.Filter):
    """À attacher à un logger pour que CHAQUE ligne de log affiche le
    request_id de la requête en cours - sans avoir à le passer explicitement
    en paramètre à chaque appel de logger.info(...) dans tout le code."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Génère un identifiant unique par requête HTTP, l'expose :
    - dans les logs, via request_id_ctx_var (lu par RequestIDLogFilter)
    - dans la réponse, via le header X-Request-ID (utile pour corréler un
      ticket support/bug avec une ligne précise dans les logs serveur)
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_ctx_var.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response