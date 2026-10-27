# Architecture implémentée

Ce document décrit ce qui est **réellement construit** (MVP, version 0.1). Le modèle cible plus large est dans [03](03-modele-de-donnees-et-invariants.md) ; pour le MVP, ce document fait foi.

## 1. Vue d'ensemble

Un monolithe modulaire Django : une seule application déployable, des modules métier indépendants. Chaque module expose une **façade publique** (`services/public.py`) et n'est jamais importé autrement par les autres. Les frontières sont vérifiées par `import-linter` à chaque exécution de la CI.

```
config/                  réglages (base, dev, test, prod), URL, WSGI, point de santé
apps/
  shared_kernel/         contexte d'agence, modèles de base, ajout seul, RLS, rôles, montants
  audit/                 journal d'actions sensibles (ajout seul)
  accounts/              utilisateurs et appartenances (gérant ou agent)
  tenancy/               agences, résolution de l'agence depuis l'identité, middleware
  crm/                   clients (téléphone E.164)
  ledger/                journal comptable en ajout seul, soldes et marges dérivés
  cases/                 dossiers et lignes (billet d'avion ou prestation libre)
  payments/              encaissements manuels
  quotes/                devis versionnés, lien WhatsApp, PDF
  dashboard/             les quatre chiffres du gérant et trois alertes
  concierge/             commandes de gestion pour l'accompagnement des agences
infra/postgres/          rôles de développement et d'intégration continue
tests/                   tests, y compris l'isolation entre agences
```

### Couches (de haut en bas)

Une application n'importe que des applications situées plus bas : `concierge` → `dashboard` → `quotes` → `payments` → `cases` → `tenancy | ledger | crm` → `accounts` → `audit` → `shared_kernel`. Dans chaque application, on retrouve les mêmes pièces : `models.py`, `selectors.py` (lectures), `services/commands.py` (écritures), `services/public.py` (façade), `dto.py`, `exceptions.py`, `constants.py`.

## 2. Isolation entre agences

Trois niveaux indépendants, dont chacun suffit à lui seul à protéger les données :

1. **PostgreSQL (RLS forcée).** Chaque table du plan de données porte `agency_id` ; une politique `tenant_isolation` compare `agency_id` à la variable de transaction `app.agency_id`. `FORCE ROW LEVEL SECURITY` s'applique aussi au propriétaire des tables. Sans variable, aucune ligne n'est visible.
2. **Rôles de base de données.** `travora_owner` possède les tables et exécute les migrations. `travora_app` s'exécute en production : il ne possède rien, n'a ni `BYPASSRLS` ni droit de superutilisateur.
3. **ORM.** `TenantManager` restreint toute requête à l'agence courante et lève une erreur s'il n'y en a pas ; `TenantScopedModel.save()` refuse d'écrire pour une autre agence. Ce niveau protège même si l'application se connectait par erreur avec un rôle privilégié.

### Cycle d'une requête

1. L'authentification résout l'utilisateur (table d'identité globale, hors RLS).
2. `TenantMiddleware` pose `app.user_id`, lit l'appartenance de cet utilisateur (la politique n'expose que sa propre ligne), puis pose `app.agency_id` et la valeur du rôle.
3. Toute la requête s'exécute dans **une transaction** : les variables sont locales à la transaction et disparaissent au `COMMIT`, même avec des connexions persistantes.
4. À la sortie du contexte, les contraintes différées (équilibre du journal, clés étrangères) sont vérifiées **tant que l'agence est posée** : au `COMMIT`, la RLS masquerait les lignes à contrôler.
5. Une réponse 5xx annule la transaction.

L'agence n'est **jamais** lue dans la requête (paramètre, en-tête, formulaire).

### Tables hors RLS (identité et configuration)

`accounts_user` (identité globale, nécessaire avant de connaître l'agence) et les tables de Django (sessions, permissions). `tenancy_agency` et `accounts_membership` ont des politiques particulières (l'agence se voit elle-même ; l'appartenance se lit par `app.user_id`).

## 3. Journal comptable

- Deux tables : `ledger_transaction` (en-tête) et `ledger_posting` (lignes). Montants **entiers en XAF** (unité mineure 0, liste ISO 4217).
- **Ajout seul, appliqué trois fois** : le code refuse `save()` sur une ligne existante, `update()` et `delete()` ; le rôle d'exécution n'a ni `UPDATE`, ni `DELETE`, ni `TRUNCATE` ; des déclencheurs refusent ces opérations même au super-utilisateur.
- **Équilibre** : un déclencheur différé vérifie que débits et crédits d'une écriture sont égaux. Le service le vérifie aussi avant d'écrire.
- **Montants strictement positifs** (contrainte `CHECK`).
- **Contre-passation** : une erreur se corrige en écrivant l'écriture opposée, une seule fois par écriture (contrainte d'unicité) ; on ne contre-passe pas une contre-passation.
- **Idempotence** : clé unique par agence ; rejouer renvoie l'écriture existante, et la réutiliser pour une autre écriture est refusé.
- **Soldes et marges toujours dérivés** par agrégation des lignes, jamais stockés.

### Écritures

| Fait | Débit | Crédit |
|---|---|---|
| Vente (émission d'une ligne) | Client : prix | Fournisseur : coût ; Marge : prix − coût (au débit si négatif) |
| Encaissement | Caisse, Banque ou Mobile Money : montant | Client : montant |
| Contre-passation | Écriture opposée de l'originale | |

### Définitions

- **Solde dû** d'un dossier : débits − crédits du compte client.
- **Marge reconnue** : marge des lignes émises, nette des contre-passations.
- **Marge encaissée** (tableau de bord) : marge reconnue des dossiers entièrement soldés.
- **Créances** : somme des soldes positifs.

## 4. Rôles et confidentialité

Deux rôles seulement : **gérant** et **agent**. Les vues renvoyées par les façades ne contiennent **jamais** le coût ni la marge pour un agent : le filtrage est fait côté serveur, pas par l'interface. Un agent **peut saisir** un coût (il le connaît) mais ne peut jamais le relire. Seul le gérant annule une ligne, un paiement ou un dossier, et consulte l'audit.

## 5. Règles métier retenues

- Un dossier se clôture seulement à **solde nul** ; il s'annule seulement quand ses lignes émises ont été annulées.
- Une ligne dont le **coût est inconnu** ne peut pas être émise : jamais de fausse marge.
- Une ligne **émise ou annulée** ne se modifie plus.
- Un **devis envoyé** est figé (prix, lignes, validité) ; une modification crée une nouvelle version. Un devis ne contient que les prix.
- Un **paiement** hors espèces exige une référence, unique par agence ; un surpaiement est accepté comme crédit.
- Un **numéro de billet** est unique parmi les lignes actives d'une agence. La reconnaissance depuis un texte collé n'est qu'une **proposition** à confirmer (13 chiffres selon des sources secondaires).
- Un utilisateur appartient à **une seule agence** (MVP).

## 6. Pour ajouter une table du plan de données

1. Hériter de `TenantScopedModel` (ou `AppendOnlyModel` pour un journal).
2. Écrire la migration de politique `…_rls.py` avec `tenant_policy("nom_de_table")` (et `append_only_guard` si ajout seul).
3. L'alimenter dans `populate()` de `tests/test_isolation_all_tables.py` : le test échoue sinon.
4. Faire passer `poetry run lint-imports`.

## 7. Limites connues

- **Pas d'interface web** : seules les commandes du concierge existent. L'interface (htmx) est la suite logique.
- **Hébergement non décidé** (décision juridique, voir [04](04-conformite-et-risques.md)) : l'image est prête, aucun déploiement n'est configuré.
- **Lien WhatsApp** : le format `wa.me` n'est confirmé que par des sources tierces ; à vérifier sur la documentation officielle avant la mise en production.
- **Rendu PDF** : vérifié dans l'image Docker, pas sous Windows.
- **Pas de paiement fournisseur** : le compte Fournisseur accumule les coûts, mais aucun règlement n'est encore enregistré.
- **Pas de réinitialisation de mot de passe** ni de gestion des sessions par l'interface.
- **Workflows GitHub Actions** validés par `actionlint` et rejoués localement, mais **pas encore exécutés sur GitHub**.
