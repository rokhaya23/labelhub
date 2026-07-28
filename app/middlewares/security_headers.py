from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute les en-têtes de sécurité minimaux exigés par le sujet :
    - X-Content-Type-Options: empêche le navigateur de "deviner" un type de
      contenu différent de celui déclaré (protection contre certaines
      attaques XSS basées sur le MIME-sniffing)
    - X-Frame-Options: empêche que l'API soit chargée dans une <iframe>
      (protection contre le clickjacking)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response