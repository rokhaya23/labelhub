import enum


class RoleEnum(str, enum.Enum):
    """Rôles applicatifs de LabelHub.

    - data_manager : crée dataset, importe des items, crée campagne, assigne des annotateurs
    - annotator    : voit ses tâches assignées, soumet/modifie une annotation (campagne ouverte)
    - reviewer     : contrôle les annotations soumises de sa campagne, approuve ou rejette
    - admin        : gère utilisateurs, rôles, activation/désactivation de compte
    """

    DATA_MANAGER = "data_manager"
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    ADMIN = "admin"