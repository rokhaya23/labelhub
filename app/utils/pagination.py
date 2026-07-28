from sqlalchemy.orm import Query


def paginate(query: Query, model, skip: int = 0, limit: int = 50) -> list:
    """Pagination "stable" : trie explicitement par model.id avant d'appliquer
    OFFSET/LIMIT.

    Sans ORDER BY explicite, l'ordre renvoyé par la base n'est PAS garanti
    entre deux appels - si des lignes sont insérées entre le chargement de
    la page 1 et de la page 2, on peut voir une même ligne deux fois, ou en
    sauter une. Trier par id (croissant, jamais modifié après insertion)
    élimine ce problème : la page N renvoie toujours les mêmes lignes tant
    qu'aucune n'est supprimée.
    """
    return query.order_by(model.id).offset(skip).limit(limit).all()