# AUDIT-01 — État, modèle du domaine, lacunes et plan

Date : 27 octobre 2026. Périmètre : Travora v0.1 (socle backend, sans interface). Responsable : fondateur. Statut : première revue, à valider.

Convention : **[C]** constaté (code lu, test ou sonde exécuté), **[R]** règle métier ou décision de conception, **[L]** exigence légale (source indiquée, niveau de preuve dans [08](../08-verifications-primaires-2026-10-27.md)), **[H]** hypothèse, **[?]** à confirmer.

## A. État constaté

- **[C]** 132 tests (131 passent, 1 ignoré : rendu PDF, impossible sous Windows, vérifié dans l'image Docker) ; couverture 96,49 % ; lint, format, typage et 12 contrats d'architecture au vert ; `pip-audit` sans vulnérabilité ; 21 dépendances de production sans licence interdite.
- **[C]** Parcours complet exécuté avec le rôle d'exécution PostgreSQL (sans privilèges) dans l'image de production : création d'agence, import CSV, soldes. Isolation et ajout seul prouvés directement en base.
- **[C]** Quatre sondes jetables, exécutées pour cet audit (puis supprimées), ont **confirmé quatre défauts d'invariants** (section C).
- **Non vérifié** : exécution des workflows sur GitHub (push bloqué), interface (inexistante), charge, reprise après sinistre, restauration de sauvegarde, concurrence réelle entre deux sessions.

## 1. Synthèse du domaine et de ses limites

Travora représente l'activité financière et opérationnelle d'une **agence de voyages** : un client demande des prestations, l'agence les vend (billets d'avion, prestations libres), encaisse en plusieurs fois, supporte un coût fournisseur et dégage une marge. Le système représente **ce que l'agence a vendu et encaissé**, pas la réalité du voyage (émission, vol, annulation par le transporteur), qui reste chez le fournisseur.

Limites assumées : un seul pays d'usage visé (Cameroun, devise XAF), une agence par utilisateur, aucune intégration externe, saisie manuelle. Ce périmètre est **[R]** (plan [12](../12-plan-recentre-60-jours.md)).

## 2. Cartographie des concepts

| Concept | Statut dans le code | Remarque |
|---|---|---|
| Agence (locataire) | Modélisé (`Agency`) | `is_active` existe mais n'est pas appliqué (V3) |
| Utilisateur, appartenance, rôle | Modélisés | Un utilisateur = une agence |
| Client payeur | Modélisé (`Customer`) | Pas de consentement ni de finalité enregistrés |
| **Passager** | **Absent** : simple texte sur la ligne | Distinct du client dans le réel ; non identifiable, non effaçable individuellement |
| Dossier | Modélisé (`Case`) | Statuts ouvert, clos, annulé |
| Ligne vendue | Modélisée (`CaseLine`) | Billet d'avion ou prestation libre |
| **Fournisseur** | **Absent** | Le coût n'est rattaché à aucun tiers ; aucune dette fournisseur identifiable |
| **Itinéraire, segment, titre émis** | **Absents** | Voulu pour le MVP ; le numéro de billet est un texte |
| Devis et version | Modélisés (`Quote`) | Instantané des prix sans coût |
| Encaissement | Modélisé (`Payment`) | Espèces, virement, Mobile Money |
| **Remboursement au client** | **Absent** comme concept | Représenté seulement par une annulation de paiement ; pas de pénalité, pas de motif |
| Écriture comptable | Modélisée (`LedgerTransaction`, `LedgerPosting`) | Ajout seul |
| **Période comptable, clôture** | **Absentes** | Voir V4 |
| Événement d'audit | Modélisé | Pas d'audit des lectures |
| **Taux de change, devise** | **Absents** | XAF seul |
| **Commission, frais de service** | **Absents** comme concepts | Fondus dans la marge |
| **Abonnement de l'agence** | **Absent** | Pas d'état « impayé », ni de lecture seule |
| **Demande d'une personne concernée, conservation** | **Absentes** | Voir L1 |
| **Taxe (TVA)** | **Absente** | Voulu : proforma seulement |

## 3. Modèle conceptuel : entités, cardinalités, cycles de vie

| Entité | Identité et unicité | Cycle de vie | États interdits à garantir |
|---|---|---|---|
| Agency | UUID ; `slug` unique | créée → active → inactive | Écrire pour une agence inactive (V3) |
| Membership | UUID ; un par utilisateur | active ↔ inactive | Deux agences pour un utilisateur (garanti) |
| Customer | UUID ; téléphone unique par agence si renseigné | créé | Doublon par téléphone (garanti) |
| Case | UUID ; référence unique par agence | ouvert → clos ou annulé | Clos avec solde ≠ 0 (V1, V2) |
| CaseLine | UUID ; billet unique parmi les lignes actives | brouillon → émise → annulée | Émise sans coût (garanti) ; modifiée après émission (garanti) |
| Quote | UUID ; (dossier, version) unique | brouillon → envoyé → accepté ou refusé | Modifié après envoi (garanti) |
| Payment | UUID ; référence unique par agence ; clé d'idempotence | saisi → annulé | Paiement sur dossier non ouvert (garanti à la saisie) |
| LedgerTransaction/Posting | UUID ; clé d'idempotence ; une contre-passation par écriture | créée (immuable) | Déséquilibre, modification, suppression (garantis par trois mécanismes) |

### Relations (catalogue initial)

| Relation | Cardinalité | Obligatoire | Garantie |
|---|---|---|---|
| Agency — Membership | 1 — 0..n | oui (appartenance) | FK, RLS |
| User — Membership | 1 — 0..1 | non | unicité |
| Customer — Case | 1 — 0..n | oui (un dossier a un client) | FK `PROTECT` |
| Case — CaseLine | 1 — 0..n | non | FK `PROTECT` |
| Case — Quote | 1 — 0..n | non | FK, unicité de version |
| Case — Payment | 1 — 0..n | non | FK |
| Case — LedgerTransaction | 1 — 0..n | oui | **valeur UUID sans clé étrangère** : l'existence du dossier n'est garantie que par les services (écart, voir C4) |
| CaseLine — vente comptable | 1 — 0..1 | si émise | `sale_transaction_id`, **sans clé étrangère** (même écart) |
| LedgerTransaction — contre-passation | 1 — 0..1 | non | unicité |
| Payment — LedgerTransaction | 1 — 0..1 | oui | **valeur UUID sans clé étrangère** |

Relations **manquantes** à instruire : Customer — Passenger (porteur ou bénéficiaire), CaseLine — Passenger, CaseLine — Supplier (coût dû à), Payment — Refund, Agency — Subscription.

## 4. Invariants

### Garantis et testés [C]

Isolation entre agences (RLS forcée, rôle sans privilège, ORM) ; journal en ajout seul et équilibré ; montants positifs ; idempotence des écritures et des paiements ; unicité des références ; ligne émise non modifiable ; devis envoyé figé ; coût et marge absents des vues d'un agent ; clôture à solde nul.

### Violés, confirmés par exécution [C]

- **V1 — Annuler une ligne émise sur un dossier clos** réussit : le dossier reste « clos » avec un solde de −100 000 XAF (sonde 1).
- **V2 — Annuler un paiement sur un dossier clos** réussit : le dossier reste « clos » avec un solde de +100 000 XAF (sonde 2). L'invariant « un dossier clos a un solde nul » n'est donc vérifié qu'à l'instant de la clôture.
- **V3 — Une agence désactivée** (`is_active = False`) résout toujours ses utilisateurs en acteurs valides (sonde 3). Le « mode lecture seule après impayé » prévu ne peut pas exister.
- **V4 — Une écriture datée de 2099** est acceptée (sonde 4). Aucune borne de date ni verrouillage de période n'existe, alors que le modèle cible le prévoit.

### Constatés à la lecture du code, non exécutés

- **V5** : la date d'import par défaut de `import_cases` utilise `date.today()` (fuseau du serveur, UTC dans le conteneur) et non `Africa/Douala` : décalage possible d'un jour près de minuit.
- **V6 [H]** : aucune fonction ne verrouille la ligne du dossier entre `close_case` et un paiement simultané : un paiement concurrent pourrait s'intercaler. À prouver par un test de concurrence avant de corriger.
- **V7** : aucune suppression, anonymisation, export ni durée de conservation des données personnelles (L1).

## 5. Hypothèses, ambiguïtés, informations manquantes

- **[H]** Un dossier clos peut-il être rouvert ? Par qui ? Avec quelle trace ? (décision métier, conditionne V1 et V2.)
- **[?]** Comportement attendu d'une agence inactive : refus total, lecture seule, ou export seul ?
- **[?]** Tolérance de date d'une écriture (saisie rétroactive acceptable sur combien de jours ?) et périodicité de la clôture.
- **[?]** Le passager est-il toujours le client ? (dans le réel, non ; impact sur les droits des personnes.)
- **[?]** Un coût peut-il être payé en plusieurs fois à un fournisseur ? (dette fournisseur : hors MVP, à décider.)
- **[H]** Un billet = 13 chiffres (source secondaire), numéro non validé par chiffre de contrôle.
- **[?]** Durées de conservation applicables (comptables, fiscales, données personnelles) : non trouvées.
- **[?]** Texte officiel de la loi 2024/017 et décret : introuvables.

## 6. Matrice de traçabilité initiale (extrait)

| Exigence | Règle | Code | Test |
|---|---|---|---|
| Isolation entre agences | RLS forcée, rôle sans privilège | `shared_kernel/rls.py`, `tenant_context.py`, migrations `…_rls.py` | `test_isolation.py`, `test_isolation_all_tables.py` |
| Journal inaltérable | Ajout seul à trois niveaux | `shared_kernel/append_only.py`, `tenancy/privileges.py` | `test_append_only.py`, `test_ledger.py` |
| Écritures équilibrées | Débits = crédits | `ledger/services/commands.py`, déclencheur | `test_ledger.py` |
| Aucun coût visible pour un agent | Filtrage serveur | `cases/selectors.py`, `ledger/services/public.py` | `test_cases.py`, `test_dashboard.py`, `test_concierge.py` |
| Ligne émise immuable | `LineLocked` | `cases/services/commands.py` | `test_cases.py` |
| Devis figé | `QuoteFrozen` | `quotes/models.py` | `test_quotes.py` |
| Paiement idempotent | clé unique | `payments/services/commands.py` | `test_payments.py` |
| Dossier clos à solde nul | `BalanceNotSettled` | `cases/services/commands.py` | `test_cases.py` (à la clôture seulement : **V1, V2 sans test**) |
| Agence inactive refusée | — | — | **aucun** (V3) |
| Droits des personnes | — | — | **aucun** (V7) |

## 7. Diagnostic de l'architecture et de la qualité des données

- **Forces [C]** : trois niveaux d'isolation indépendants, frontières imposées par l'outil, invariants financiers en base, tests de non-régression d'isolation qui échouent si une table échappe à la couverture.
- **Faiblesses** : trois références croisées par valeur UUID sans clé étrangère (écart C4) ; absence de verrous de concurrence ; invariants du dossier vérifiés à la clôture seulement ; modèle sans fournisseur, passager, remboursement, période.
- **Qualité des données** : un coût **inconnu** est représenté par `NULL` et bloque l'émission (bonne pratique) ; en revanche, l'état « non vérifié » d'un numéro de billet n'existe pas, et `raw_text` conserve le texte collé tel quel (données personnelles possibles, sans durée de conservation).

## 8. Plan d'analyse réglementaire

| Obligation | Juridiction | Source | Niveau de preuve | Statut |
|---|---|---|---|---|
| L1 Protection des données (loi 2024/017) : autorisation ou déclaration, registre, droits, violation, transferts | Cameroun | commentaires et cabinets | secondaire, texte officiel introuvable | applicable, **non conforme** (V7), décret inconnu |
| L2 TVA : taux, exigibilité, débours, factures | Cameroun | guide DGI, lu en entier | primaire | partiellement traitée (proforma seulement, pas de TVA calculée) |
| L3 Facture conforme et e-facturation | Cameroun | blog d'éditeur | secondaire | à analyser ; hors MVP |
| L4 Services de paiement (BEAC, COBAC) | CEMAC | source secondaire | secondaire | conforme par conception (aucun fonds détenu), **à faire valider** |
| L5 Conservation des documents comptables (OHADA) | OHADA | non trouvé | — | applicabilité indéterminée |
| L6 Cybersécurité (loi 2010/012) | Cameroun | profil du Conseil de l'Europe | secondaire | à analyser |
| L7 Protection du consommateur (loi 2011/012) | Cameroun | non consultée | — | à analyser |
| Normes de référence (ISO 27001, 27701, OWASP ASVS, NIST SSDF) | — | volontaires | non vérifiées ici | références, aucune certification visée |
| PCI DSS | — | — | — | **non applicable par conception** : aucun numéro de carte n'est stocké (**[H]** à reconfirmer à chaque ajout de paiement) |
| Accessibilité (WCAG 2.2) | — | — | — | sans objet tant qu'il n'y a pas d'interface |

Aucune conclusion juridique n'est affirmée : L1, L3, L5 à L7 exigent un juriste ou un comptable.

## 9. Registre initial des risques (nouveaux, issus de cet audit)

| # | Risque | Gravité | Preuve | Traitement proposé |
|---|---|---|---|---|
| K1 | Dossier clos au solde non nul après annulation (V1, V2) | Haute | sondes 1 et 2 | C1 |
| K2 | Agence impayée ou résiliée toujours active (V3) | Haute (revenu et conformité) | sonde 3 | C2 |
| K3 | Écritures rétroactives ou futures sans contrôle (V4) | Moyenne | sonde 4 | C3 |
| K4 | Absence de droits des personnes et de conservation (V7) | Haute (légale) | lecture | C6 |
| K5 | Course entre clôture et paiement (V6) | Moyenne [H] | non prouvée | test de concurrence puis C5 |
| K6 | Références sans clé étrangère | Moyenne | lecture du schéma | C4 |
| K7 | Décalage de fuseau à l'import (V5) | Basse | lecture | C7 |
| K8 | Passager et fournisseur non modélisés | Moyenne | cartographie | C8, après entretiens |
| K9 | Aucune restauration de sauvegarde testée | Haute | absence | C9 |

Les risques R1 à R17 de [04](../04-conformite-et-risques.md) restent en vigueur.

## 10. Plan d'action priorisé

| # | Correction | Critère de vérification | Décision préalable |
|---|---|---|---|
| C1 | Refuser l'annulation d'une ligne ou d'un paiement sur un dossier clos ou annulé, sauf réouverture explicite et tracée | Les sondes 1 et 2 deviennent des tests qui passent ; une réouverture écrit un événement d'audit | Qui peut rouvrir ? (gérant seul, proposé) |
| C2 | Refuser la résolution d'un acteur dont l'agence est inactive, selon la politique choisie | Test : agence inactive → accès refusé (ou lecture seule) | Refus total, lecture seule ou export seul |
| C3 | Borner `occurred_on` (pas de date future ; rétroactivité limitée) ; introduire la clôture de période | Test : date 2099 refusée ; période close refusée | Tolérance rétroactive ; périodicité |
| C4 | Remplacer les références par valeur par de vraies clés étrangères (ledger → dossier, ligne → vente, paiement → écriture) | Schéma : clés présentes ; test d'intégrité | Aucune (technique) |
| C5 | Verrouiller le dossier (`SELECT … FOR UPDATE`) dans clôture, paiement, annulation | Test de concurrence à deux connexions | Aucune |
| C6 | Concevoir export, anonymisation, durées de conservation et information des personnes ; nettoyer `raw_text` | Registre L1 mis à jour ; tests d'export et d'anonymisation | Texte officiel de la loi et avis juridique |
| C7 | Utiliser `timezone.localdate()` à l'import | Test avec fuseau simulé | Aucune |
| C8 | Instruire passager, fournisseur, remboursement, commission | Résultats des entretiens | Entretiens terrain |
| C9 | Test de restauration de sauvegarde automatisé | Restauration d'une base vierge et réconciliation des soldes | Hébergement |

Ordre recommandé : **C1, C4, C5, C7** (techniques, sans décision), puis **C2, C3** (après tes décisions), puis **C6, C9** (conformité et exploitation), puis **C8** (après le terrain).

## G. Vérification réellement effectuée

Tests complets, lint, typage, contrats d'architecture, audit des vulnérabilités, contrôle des licences, déploiement de l'image avec rôle d'exécution, sondes jetables pour V1 à V4. **Non exécuté** : charge, concurrence (V6), restauration, workflows sur GitHub.

## H. Risques résiduels

Textes légaux non lus à la source ; modèle tributaire d'entretiens non réalisés ; concurrence non éprouvée.

## I. Décision

**Corriger avant d'étendre.** Ne pas construire d'interface sur un noyau dont V1 et V2 peuvent produire un dossier clos au solde faux. Poursuivre par C1, C4, C5, C7 sur des branches distinctes, après ton accord sur le plan et sur les deux décisions de C1 et C2.
