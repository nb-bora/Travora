# 02 — Solutions existantes, cahiers des charges types et réutilisation

Légende : **[LU]** page lue en entier ; **[RECH]** résumé de résultat de recherche seulement ; **[I]** inférence. Les prix sont publics, mensuels et non comparables entre eux. Recherche arrêtée au 26 octobre 2026 ; Capterra, G2 et Reddit n'ont pas pu être exploités (accès refusé ou rien de pertinent).

## 1. Solutions existantes

| Solution | Cible | Ce qu'elle couvre | Prix repère | Enseignement pour Travora |
|---|---|---|---|---|
| Amadeus Agency Manager [LU] | Agences avec Amadeus, 20+ pays | Facturation juste après l'émission, frais de service automatiques, contrôle de marge prévue et réelle par dossier, dossier consolidé, TVA | Sur devis | Le modèle « marge prévue vs réelle par dossier » est la référence ; il est lié à un contrat Amadeus et à des pays précis |
| Savanna Sync (Nairobi) [LU] | Consultants et agences africaines, plutôt safari et circuits | Devis, itinéraires, CRM, M-Pesa, multi-devise | 115 USD (1 utilisateur), 270 USD (jusqu'à 10) | Existe bel et bien ; ne mentionne ni PNR, ni GDS, ni billetterie ; statut de lancement incertain |
| TourismOS | — | — | — | **Introuvable** en deux recherches ; ne pas s'y référer |
| Travelife [LU] | « Agences B2B et B2C au Maroc et en Afrique » | Réservations, comptabilité, GDS, CRM, documents | Sur demande ; « dès 199 € » selon Capterra [RECH] | Concurrent le plus proche de la cible, peu documenté (éditeur et clients inconnus) |
| TravelOS (Maroc) [RECH] | Agences marocaines | Dossiers, devis, statuts de paiement, liaison aux contrats GDS de l'agence, support WhatsApp, environnement isolé, ne détient pas les fonds | Inconnu | Même philosophie que Travora ; source unique (offre d'emploi) |
| Ezus [RECH] | Agences sur mesure | Back-office généraliste | Dès 75 € | Reconnaît ne pas viser l'accès aux stocks GDS |
| Tramada / TRAMS | Agences australiennes et nord-américaines | Post-réservation, comptabilité | 92 AUD, 3 licences minimum [RECH] | Minimums de licences et courbe d'apprentissage : pas adaptés à une agence de 1 à 5 postes |
| TravelWorks, Travefy, TravelOperations | Amérique du Nord | Comptabilité GDS, itinéraires, ERP | 25–39 USD par utilisateur (Travefy) à 500 USD et plus (TravelWorks) | Interfaces jugées datées ; ERP excessif pour les petites agences |
| Odoo « Tours & Travels CRM » (AGPL-3), PHPTravels CRM, iCaro (GPLv2) | Agences, bricolage | CRM de réservation | Gratuit / Pro | Voir §4 : inspiration d'écrans seulement |

Aucun éditeur trouvé ne cite MTN MoMo ou Orange Money. Seul Savanna Sync cite M-Pesa. [I] La recherche était limitée ; l'absence n'est pas une preuve.

## 2. Plaintes récurrentes (confiance moyenne à faible)

Aucune étude sérieuse sur l'échec d'adoption n'a été trouvée. Les points viennent de comparatifs d'éditeurs et de listicles :

1. Courbe d'apprentissage raide (Trams, TravelWorks, Tourplan).
2. Interfaces datées.
3. Prix opaques, mise en place longue, minimums d'utilisateurs.
4. Limites hors connexion.
5. Outils fragmentés sans référence commune de réservation, de passager et de paiement.
6. Export de données difficile (accusation d'un concurrent, à prendre avec précaution).

[I] Causes d'échec probables pour une petite agence camerounaise : double saisie, temps de paramétrage, prix en devises fortes, manque de formation.

## 3. Exigences récurrentes dans les cahiers des charges types

Sources : guide d'achat du régulateur singapourien IMDA pour les systèmes de gestion de voyages [LU], modèles de RFP d'éditeurs [RECH]. Aucun appel d'offres public pour un back-office d'agence n'a été trouvé.

**Structure à reprendre** : périmètre par module → intégrations → sécurité et données → mise en œuvre et formation → support → reporting → coût total ; chaque exigence classée « obligatoire » ou « souhaitée ».

**Fonctions présentes dans au moins trois sources** (comptage fait à partir des sources lues) :

1. Devis avec coût et marge visibles.
2. Dossier de voyage centralisé et génération de documents.
3. CRM clients.
4. Facturation et suivi des paiements.
5. Rapports et tableaux de bord exportables.
6. Gestion des fournisseurs.
7. Suivi des commissions, mark-ups et frais de service.
8. Export ou intégration comptable.
9. Multi-devise.
10. Rôles et accès multi-utilisateurs.
11. Connexion GDS (à nuancer : voir `05-integrations-et-canaux.md`).

Exigences transverses du guide IMDA : accès cloud et mobile, export de données (CSV, XLSX, XML), protection des données personnelles, test d'intrusion, calcul des pénalités et remboursements à l'annulation, contrôle de crédit pour les agents B2B.

## 4. Pistes de différenciation pour Travora

| Piste | Statut de la preuve |
|---|---|
| Mobile Money (MTN, Orange) comme moyen de paiement de première classe | Aucun concurrent trouvé qui le cite |
| Encaissements partiels avec échéancier, reçus et solde par dossier, espèces comprises | Non détaillé par les sources |
| Billetterie aérienne indépendante : PNR et billet rattachés au dossier, marge par billet, remise BSP | Les sources ne la mettent pas en avant |
| Alertes sur dates fiables : délai d'émission, échéance de paiement, expiration de document de voyage | Aucune source ne les décrit : à valider en entretien |
| WhatsApp comme canal | Cité par TravelOS et par la presse sectorielle |
| Tolérance aux connexions faibles | Lacune relevée chez un concurrent [RECH] |
| Prix en FCFA, sans minimum d'utilisateurs, pour 1 à 5 postes | Face à des minimums de 3 ou 10 licences |
| Export libre des données | Exigé par IMDA, argument contre le verrouillage |

**Repère de prix** : les outils publiés pour petites équipes se situent entre environ 25 et 270 USD par mois. Aucune donnée camerounaise de disposition à payer : à établir par entretiens.

## 5. Ce qui existe déjà chez toi : le monolithe FairFare (FF-Modulith)

Dossier local `D:\MITS\Projets\FaiFaire\FF-Modulith`, dépôt GitHub de l'organisation FairFareHQ, 366 commits, Django 5.2 et DRF, PostgreSQL avec RLS, Celery et Redis, applications `tenancy`, `audit`, `payments`, `ingestion`, `notification`, `expenses`, `booking`, `amadeus`, `shared_kernel`, ADR et SPEC documentés.

### 5.1 Avertissement de propriété (à lever avant toute copie de code)

- Le dépôt appartient à une organisation GitHub et a plusieurs contributeurs (huit auteurs ou plus dans l'historique git). Le champ de licence du fichier `pyproject.toml` indique « MIT », mais cela ne vaut pas autorisation de réutilisation tant que les titulaires des droits ne l'ont pas confirmée.
- Tu travailles aussi pour une société cliente de ce projet (adresse professionnelle et références à une passerelle back-office dans les documents). Vérifie ton contrat de travail et les clauses de propriété intellectuelle et de non-concurrence.
- Recommandation : obtenir une autorisation écrite de FairFareHQ pour réutiliser des modules précis, ou réimplémenter à partir des **principes** (les patterns de tenancy, d'idempotence et d'audit sont des pratiques standard), sans copier le code ni les documents.
- Je n'ai utilisé aucun contenu du dossier `TourVest` (plan d'intégration d'un autre client) pour Travora.

### 5.2 Carte de réutilisation (sous réserve du §5.1)

| Besoin Travora | Existant FairFare | Adaptation |
|---|---|---|
| Isolation par agence | Tenancy `tenant_id` + RLS, FK composites, plan de contrôle, tests de catalogue en CI | Reprendre le modèle ; remplacer « entreprise cliente » par « agence » et « société » par « succursale » |
| Journal d'audit | Table en ajout seul, modification et suppression interdites | À reprendre presque tel quel |
| Paiements Mobile Money | Client MoPay (Orange Money Cameroun), webhook HMAC-SHA256, idempotence, anti double débit en base, route de webhook hors RLS | Voir `05-integrations-et-canaux.md` ; inverse du besoin Travora (ici l'agence encaisse, Travora enregistre) |
| Ingestion d'e-mails | Écouteur IMAP, analyse par modèle de langage | À reprendre avec correctifs (§5.3) |
| Frais de service | Prix en trois montants (net, frais, total), frais figés à la réservation, grille obligatoire | Même logique pour les devis de Travora |
| Amadeus | Accès Enterprise sandbox pour l'OID du Cameroun : recherche, tarification, commande et annulation fonctionnent ; mise en queue en échec ; API hôtels non autorisées | Peut servir de preuve de faisabilité pour la phase 2, pas pour le MVP |
| Notifications | Rappels avant échéance, envois au mieux sans jamais annuler un fait métier | À reprendre comme principe |
| Reçus de dépenses | Lecture de PDF et d'images par OCR | Possible pour justificatifs de dépenses de l'agence |

### 5.3 Points d'attention relevés dans le code et les docs

1. **Jeton exposé** : le fichier `README.md` du dépôt contient, dans l'URL d'un badge, un jeton SonarQube (préfixe `sqb_`). À révoquer et remplacer par un badge sans jeton, surtout si le dépôt est public ou le devient.
2. **Transfert de données personnelles hors du Cameroun** : l'ingestion d'e-mails envoie le contenu des messages à OpenAI. Sous la loi 2024/017, un transfert hors du Cameroun exige une autorisation préalable de l'autorité. Pour Travora : analyseur déterministe d'abord, repli par modèle de langage avec masquage des données personnelles ou modèle hébergé localement.
3. **Écouteur IMAP lancé dans un thread au démarrage de l'application** : fragile en production ; préférer une tâche planifiée ou un worker dédié.
4. **Pile** : le texte initial supposait FastAPI et SQLAlchemy ; l'expérience réelle documentée est Django. Je recommande Django pour Travora (décision D1 du cahier des charges).

## 6. Briques open source et licences

Légende : **[V]** vérifié dans la source (API GitHub, fichier de licence, documentation) ; **[I]** inféré. Les licences marquées [I] sont à confirmer dans le dépôt avant adoption. Date de référence : 26 octobre 2026.

### 6.1 Grand livre

| Brique | Licence | Maturité | Verdict |
|---|---|---|---|
| pgledger (SQL pur PostgreSQL) | MIT [V] | Créé en mars 2025, ~500 étoiles, jeune | S'inspirer fortement (schéma, soldes recalculés à partir d'un historique en ajout seul) ; reprise du SQL possible après audit |
| django-hordak | MIT (selon la recherche) | v2.0.0 (nov. 2024) ; testé Django 4.2/5.0 ; contrainte « les jambes somment à zéro » ; **compatibilité Django 5.2 non vérifiée** | Évaluer ; vérifier immutabilité et multi-tenant |
| Formance Ledger v2.4 | MIT [V] | Service Go séparé, avec son propre modèle | S'inspirer (redondant avec un module Django) |
| Formance Ledger `main` (« v3 ») | Aucun fichier de licence ; stockage sans PostgreSQL [V] | Expérimental | Éviter |
| TigerBeetle | Apache-2.0 [V] | Cluster dédié | S'inspirer (débit/crédit, identifiants, idempotence) ; ne pas ajouter comme second système |
| Medici | MIT [V] | Node.js + MongoDB | S'inspirer seulement |
| django-ledger | **GPL-3.0** [V] | Actif | **Éviter** |

Recommandation : tables en ajout seul (écritures et jambes dont la somme est nulle) ; soldes dérivés ou matérialisés ; immutabilité imposée en base (retrait des droits de mise à jour et suppression au rôle applicatif, plus déclencheurs) ; corrections par extourne.

### 6.2 Multi-tenant avec RLS

- Faits PostgreSQL vérifiés : superutilisateurs et rôles `BYPASSRLS` contournent toujours la RLS ; le propriétaire de table aussi sauf avec `FORCE ROW LEVEL SECURITY` ; `TRUNCATE` et `REFERENCES` ne sont pas soumis à la RLS ; les contraintes d'unicité et de clé étrangère peuvent révéler l'existence de lignes (canaux cachés).
- Pièges Django (à tester) : rôle applicatif non propriétaire ; contexte posé par `SET LOCAL` **dans** la transaction (`ATOMIC_REQUESTS`) ; un `SET` simple avec `CONN_MAX_AGE` fuirait entre requêtes ; PgBouncer en mode transaction convient avec `SET LOCAL` seulement ; Celery et commandes de gestion posent le contexte explicitement ; tests au niveau base avec le rôle applicatif.
- `django-rls-tenants` (MIT annoncé, récent) : à évaluer ; le mécanisme tient en peu de code.

### 6.3 Idempotence, audit, tâches

| Brique | Licence | Verdict |
|---|---|---|
| Procrastinate (file de tâches sur PostgreSQL) | MIT [V, vérifié le 27/10/2026 : API GitHub, non archivé, 1 435 étoiles] | **Utiliser** : pas de Redis, mise en file dans la même transaction que les données ; intégration Django à vérifier |
| Celery + Redis | BSD [I] | Seulement si le besoin le justifie |
| Dramatiq | LGPL-3.0 [V] | Éviter par prudence |
| django-simple-history | BSD-3-Clause [V] | Utiliser pour l'audit des modèles non financiers |
| django-pgtrigger | BSD-3-Clause [V] | Utiliser (déclencheurs anti-mise à jour du journal) ou SQL brut dans les migrations |

Modèle d'idempotence : table (tenant, clé, empreinte de requête, réponse, statut) avec unicité ; pour webhooks et imports, unicité (fournisseur, identifiant d'événement) ou empreinte de fichier ; webhooks écrits d'abord dans une table d'arrivée puis traités par la file.

### 6.4 PDF et analyse de PNR

| Brique | Licence | Verdict |
|---|---|---|
| WeasyPrint | BSD-3-Clause [V, vérifié le 27/10/2026 : API GitHub, non archivé, 9 736 étoiles] | **Utiliser** pour devis, reçus, factures ; polices embarquées via `@font-face` (licence à vérifier) ; génération en tâche de fond |
| PyMuPDF | AGPL-3.0 [V] | Éviter |
| wkhtmltopdf | LGPL, projet archivé [I] | Éviter |
| Chromium headless | Apache-2.0 [I] | Repli si le CSS dépasse WeasyPrint |
| open-pnr, pnr-parser (TypeScript) | MIT [V] | S'inspirer, ne pas dépendre |
| PnrParse (Python, 2017), pnr-parser (Yacc) | MIT, LGPL-2.1 [V] | Éviter (abandonnés ou copyleft) |

### 6.5 Application à connexion faible

Rien de spécifique à htmx et Django n'a été trouvé sur le hors-ligne. Motif proposé [I] : service worker pour la coquille et les statiques (Serwist, MIT, ou service worker minimal) ; brouillons de formulaires dans IndexedDB ; envoi différé avec clé d'idempotence ; le serveur reste l'arbitre, seuls les brouillons se synchronisent, jamais le journal financier ; ne pas compter sur Background Sync (support Safari et Firefox à vérifier) ; fragments htmx courts, compression Brotli, polices sous-ensemblées, pas de gros bundle JavaScript. Safari iOS : pas de `beforeinstallprompt` ; Web Push à partir de iOS 16.4 pour les applications installées.

### 6.6 Chiffrement, stockage, sauvegardes

- Aucune bibliothèque Django trouvée qui combine chiffrement par enveloppe, clés par agence et stockage objet. Motif [I] : une clé de chiffrement de clés (KEK) par agence enveloppée par une clé maître (KMS ou secret hors base) ; une clé de données (DEK) aléatoire par document, AES-256-GCM ; DEK enveloppées en base, texte chiffré dans l'objet, agence dans les données authentifiées (AAD) ; rotation par ré-enveloppement. Bibliothèques : `cryptography` ou Tink.
- Éviter HashiCorp Vault (BSL depuis 2023 [I]) ; OpenBao (MPL-2.0, fork) est une alternative [I].
- **MinIO** : AGPL-3.0, édition communautaire en mode maintenance [V] : éviter pour un nouveau projet ; stockage S3 géré compatible, ou SeaweedFS, Garage, Ceph à évaluer.
- **pgBackRest** : sauvegardes et restauration à un instant donné (WAL), licence à confirmer (affichage GitHub ambigu) ; restauration vers une base vierge **testée régulièrement**, avec mesure du temps de reprise. Une sauvegarde jamais restaurée ne compte pas.

### 6.7 Licences à éviter dans un SaaS fermé

| Licence | Raison |
|---|---|
| AGPL-3.0 | Clause « interaction réseau » : si le programme est modifié et exposé aux utilisateurs, le code doit être offert ; un composant lié contamine ; un service non modifié et isolé est en pratique toléré (texte du §13 non vérifié ici, 429) |
| GPL-3.0 | Copyleft à la distribution ; l'exigence d'hébergement portable peut mener à livrer des conteneurs, donc à distribuer |
| LGPL | Friction inutile (acceptable en dépendance non modifiée) |
| SSPL, BSL 1.1, Elastic License 2.0, Commons Clause, Polyform | Non open source ou restrictions sur l'offre en service |

Licences sûres : MIT, BSD, Apache-2.0, ISC, MPL-2.0. Mettre en CI un inventaire des licences des dépendances Python et JavaScript.
