class BusinessRuleError(Exception):
    """Une règle métier est violée (ex: campagne pas assez remplie pour ouvrir).
    À catcher dans les routes et traduire en HTTP 400."""


class ForbiddenActionError(Exception):
    """L'utilisateur est authentifié et a le bon rôle, mais n'a pas le droit sur
    CETTE ressource précise (ex: annoter la tâche de quelqu'un d'autre).
    Complète permissions.py, qui ne vérifie que le rôle, pas la ressource.
    À catcher dans les routes et traduire en HTTP 403."""


class NotFoundError(Exception):
    """La ressource n'existe pas, ou existe mais n'est pas visible par cet
    utilisateur. À traduire en HTTP 404 (pas 403, pour ne pas révéler
    l'existence d'une ressource à quelqu'un qui n'y a pas accès)."""