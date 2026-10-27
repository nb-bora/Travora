# Travora

Gestion opérationnelle et financière pour agences de voyages : dossiers, devis, paiements, soldes et marges, sans double saisie. Monolithe modulaire Django 6.1 sur PostgreSQL, multi-tenant avec isolation forcée par la base (RLS).

État : le socle métier est complet et testé (agences, comptes, clients, dossiers, journal comptable, paiements, devis, tableau de bord, commandes du concierge). **L'interface web n'est pas encore construite** : le concierge utilise les commandes de gestion décrites plus bas. Voir [docs/architecture.md](docs/architecture.md).

## Prérequis

- Python 3.14 (le projet utilise `uuid.uuid7`)
- [Poetry](https://python-poetry.org/) 2.4 ou plus
- Docker (PostgreSQL local et image de production)

## Démarrer

```powershell
poetry install
docker compose up -d db          # PostgreSQL 17 sur le port 5433, avec les rôles de développement
```

Les migrations s'exécutent avec le rôle **propriétaire** ; l'application s'exécute avec le rôle **d'exécution**, qui ne possède aucune table et ne contourne pas la RLS.

```powershell
$env:DB_USER = "travora_owner"; $env:DB_PASSWORD = "travora_owner"
poetry run python manage.py migrate
Remove-Item Env:DB_USER, Env:DB_PASSWORD      # retour au rôle d'exécution (valeurs par défaut)
```

Sous bash : `DB_USER=travora_owner DB_PASSWORD=travora_owner poetry run python manage.py migrate`.

## Commandes du concierge

L'agence d'un utilisateur se déduit de son identifiant (`--as`) : on ne saisit jamais d'identifiant d'agence. Les mots de passe se lisent dans la variable `TRAVORA_PASSWORD`, ou sont demandés sans écho.

```powershell
$env:TRAVORA_PASSWORD = "un-mot-de-passe-solide"
poetry run python manage.py create_agency --name "Voyages Essai" --slug essai --manager marie
poetry run python manage.py add_member --as marie --username paul           # agent par défaut

# Reprise des dossiers ouverts d'une agence : essai à blanc, puis enregistrement
poetry run python manage.py import_cases --as marie --file docs/examples/dossiers.csv
poetry run python manage.py import_cases --as marie --file docs/examples/dossiers.csv --commit

poetry run python manage.py show_balances --as marie     # prix, solde dû, marge reconnue
poetry run python manage.py show_balances --as paul      # idem sans la marge
```

L'import est rejouable (un dossier déjà présent est ignoré) et tout-ou-rien (une ligne invalide annule tout). Le format du CSV est dans [docs/examples/dossiers.csv](docs/examples/dossiers.csv). Les numéros de téléphone doivent être au format international ; `--default-country-code +237` complète explicitement les numéros locaux.

## Qualité et tests

```powershell
poetry run ruff check .            # lint
poetry run ruff format --check .   # format
poetry run mypy apps config        # typage
poetry run lint-imports            # frontières entre applications
poetry run pytest                  # tests (PostgreSQL requis : docker compose up -d db)
poetry run pytest --cov            # avec couverture (seuil de la CI : 94 %)
```

### Tests d'isolation entre agences

Ils prouvent qu'une agence ne lit, n'écrit ni ne modifie jamais les données d'une autre, et que le journal est inaltérable :

```powershell
poetry run pytest tests/test_isolation.py tests/test_isolation_all_tables.py tests/test_append_only.py tests/test_ledger.py -v
```

Le super-utilisateur qui crée la base de test contourne toujours la RLS : ces tests endossent donc explicitement le rôle d'exécution (`SET LOCAL ROLE travora_app`). `test_isolation_all_tables.py` alimente **toutes** les tables pour deux agences et échoue si une table est ajoutée sans données de test.

Le rendu PDF des devis exige les bibliothèques Pango : le test correspondant est ignoré sous Windows et exécuté dans la CI (Linux) et dans l'image Docker.

## Image de production

```powershell
docker build -t travora .
docker run --rm -e DJANGO_SECRET_KEY=... -e DJANGO_ALLOWED_HOSTS=... `
  -e DB_HOST=... -e DB_USER=travora_app -e DB_PASSWORD=... travora python tools/smoke_image.py
```

L'image s'exécute sans privilèges (utilisateur 10001), avec Gunicorn. Le point de santé est `/healthz`. L'hébergement n'est pas décidé : aucun déploiement automatique n'est configuré (voir [docs/04-conformite-et-risques.md](docs/04-conformite-et-risques.md)).

## Flux de travail Git

- `main` est toujours dans un état qui passe la CI et se publie.
- Une branche par fonctionnalité (`feat/…`, `fix/…`, `chore/…`, `ci/…`, `docs/…`), avec ses tests ; fusion dans `main` avec un commit de fusion, seulement si tout est vert.
- Une étiquette `vX.Y.Z` déclenche la publication : la CI complète est rejouée, puis l'image est publiée sur le registre de conteneurs GitHub et une version est créée.
- Recommandé sur GitHub : protéger `main` (CI obligatoire avant fusion). Ce réglage ne se fait pas depuis le dépôt.

## Documentation

- [docs/README.md](docs/README.md) : index de la documentation de conception
- [docs/architecture.md](docs/architecture.md) : architecture implémentée
- [docs/adr/](docs/adr/) : décisions d'architecture
