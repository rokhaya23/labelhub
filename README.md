# LabelHub API

API de plateforme d'annotation de données - Master 1 DSIA (Sujet 2)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Lancement local

```bash
uvicorn app.main:app --reload
```

## Lancement avec Docker

```bash
docker compose up --build
```

## Tests

```bash
pytest --cov=app
```

## Rôles

- data_manager : crée dataset, importe des items, crée campagne, assigne des annotateurs
- annotator : voit ses tâches assignées, soumet/modifie une annotation tant que la campagne est ouverte
- reviewer : voit les annotations soumises de sa campagne, approuve ou demande correction
- admin : gère utilisateurs, rôles, activation/désactivation de compte
