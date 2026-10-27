# 00 — Glossaire et conventions

Langage commun du projet. Les termes de ce glossaire font foi ; en cas de conflit avec un autre document, ce glossaire s'applique et le document est corrigé. Le code utilise les noms anglais de la colonne « Code ».

## 1. Termes métier

| Terme (français) | Code | Définition | Remarques |
|---|---|---|---|
| Agence | `Agency` | Locataire (tenant) : entreprise cliente de Travora | Frontière d'isolation et de facturation |
| Succursale | `Branch` | Point de vente d'une agence | Rattachement, jamais une autorisation |
| Membre | `Membership` | Accès d'un utilisateur à une agence avec un rôle | Un utilisateur peut avoir plusieurs agences |
| Client | `Customer` | Payeur du dossier (personne ou entreprise) | Distinct du voyageur |
| Passager | `Passenger` | Voyageur | Nom tel qu'il figure sur le document de voyage |
| Dossier | `TravelCase` | Dossier commercial central | Contient 0..N réservations ; ≠ réservation |
| Devis | `Quote` | Proposition chiffrée | Versions figées à l'envoi (`QuoteVersion`, `QuoteLine`) |
| Réservation | `Booking` | Réservation auprès d'un fournisseur, avec un **mode** | Le PNR n'est jamais l'identifiant universel |
| Mode | `mode` | Avion, bus, train, bateau, hôtel, transfert, location, assurance, autre | Liste configurable ; champs propres au mode dans un schéma (`ModeSchema`) |
| Titre de transport | `TravelDocument` | Document émis par le fournisseur : billet aérien, billet de bus, de train, de bateau, bon d'hôtel, EMD | « Billet » dans le langage courant ; nom de code unique `TravelDocument` |
| Segment | `Segment` | Tronçon d'un titre (vol, trajet de car, voyage en train) : origine, destination, départ, arrivée, transporteur, service, classe, place | **Décision de nommage** : `Segment` (terme des PNR) ; l'alias `Leg` n'est pas utilisé. À confirmer par le fondateur |
| Fournisseur | `Supplier` | Compagnie, consolidateur, hôtel, assureur, loueur, transporteur | Typé ; porte les règles d'annulation |
| Connecteur | `Connector` | Adaptateur technique vers un fournisseur, un agrégateur ou un canal | Derrière un port ; activé par agence, seulement si droits et contrats l'autorisent |
| Agrégateur | `Aggregator` | Intermédiaire qui donne accès à plusieurs opérateurs ou fournisseurs : agrégateur de paiement (Mobile Money) ou de contenu (NDC, bus, hôtels) | Distinct d'un fournisseur final |
| Prestataire de paiement | `PaymentProvider` | Agrégateur ou opérateur par lequel le client paie l'agence | Travora ne détient jamais les fonds |
| Journal | `Ledger` | Journal comptable opérationnel en ajout seul | Pas la comptabilité légale |
| Transaction comptable | `LedgerTransaction` | Écriture équilibrée regroupant des lignes | Immuable |
| Ligne d'écriture | `LedgerPosting` | Débit ou crédit sur un compte | |
| Contre-passation | reversal | Écriture qui annule en tout ou en partie une écriture antérieure | Seul moyen de corriger |
| Période verrouillée | `PeriodLock` | Mois clos : plus d'écriture datée dans la période | Corrections sur la période courante avec référence |
| Paiement | `Payment` | Fait d'encaissement d'un client | Génère une écriture |
| Tentative de paiement | `PaymentAttempt` | Demande de paiement auprès d'un prestataire, avec statut | Un paiement peut avoir plusieurs tentatives |
| Remboursement | `Refund` | Restitution au client | Contre-écriture |
| Coût fournisseur | cost | Prix payé ou dû au fournisseur | Interne |
| Frais de service | service fee | Rémunération de l'agence facturée au client | Interne et visible sur le prix de vente |
| Débours | disbursement | Montant avancé par l'agence au nom et pour le compte du client (par exemple un billet payé à la compagnie) | Exclu de la base de TVA selon le guide de la DGI ; à distinguer de la commission (voir [04](04-conformite-et-risques.md) §2) |
| Marge | markup / margin | Écart commercial sur la vente | Interne |
| Prix de vente | sale price | Coût + frais + marge (+ taxes) | Seul montant présenté au client |
| Trésorerie, chiffre d'affaires reconnu, marge | — | Trois mesures distinctes, jamais confondues | Voir `03` §4 |
| Démarrage à chaud | hot start | Import des dossiers ouverts et des soldes d'ouverture, sans l'historique | Voir `06` §3 |
| Lot d'import | `ImportBatch` | Import identifié, idempotent, annulable | |
| Clé d'idempotence | `idempotency_key` | Identifiant qui garantit qu'un rejeu ne crée pas de doublon | |
| Boîte de réception / d'envoi | inbox / outbox | Tables qui reçoivent les événements externes et publient les messages sortants de façon fiable | |

## 2. Conventions techniques

| Sujet | Convention |
|---|---|
| Identifiants | UUIDv7 |
| Montants | Entiers en unité mineure ; XAF : exposant 0 ; devise étrangère : montant d'origine, devise, taux figé, montant en XAF |
| Dates | UTC en base (ISO 8601), fuseau `Africa/Douala` à l'affichage |
| Téléphones | Format E.164 |
| Pays, devises | ISO 3166-1 alpha-2, ISO 4217 |
| Langues | Interface en français et en anglais ; documents de projet en français ; code, commentaires techniques et noms de tables en anglais |
| Suppression | Désactivation douce ; jamais `CASCADE` entre modules |
| Photos (snapshots) | Prix, frais, taux et libellés copiés au moment du fait |
| Modules | Un module par domaine ; appel entre modules par une façade publique ; accès externes derrière des ports |

## 3. Conventions documentaires

- **Niveaux de preuve** : [V] vérifié sur une source officielle ou primaire ; [T] source tierce ; [I] inféré. Statut de vérification d'une affirmation sourcée : ✔ vérifiée par deux vérifications indépendantes ; ◐ partiellement ; ? invérifiable ; ✘ contredite ; · non contrôlée (non critique).
- **Confiance** : H haute, M moyenne, B basse.
- **Priorités** : M (MVP), P2 (phase 2), P3 (phase 3).
- **Identifiants d'exigences** : F-… (fonctionnelles), N-… (non fonctionnelles), C-… (conformité) ; **risques** R… ; **décisions** D… ; **ADR** `adr/ADR-NNNN-titre.md`.
- **Sources** : chaque affirmation factuelle importante renvoie à un identifiant de source du registre (`08-verifications-primaires-2026-10-27.md`), de la forme `AXE-NNN`. Aucune règle légale, aucun chiffre, aucun format de fichier et aucune API n'est affirmé sans source ou sans mention « à confirmer ».
- **Versions des documents** : version et date en tête ; toute décision structurante passe par un ADR (contexte, décision, conséquences).
- **Avertissement permanent** : ces documents ne sont ni un avis juridique ni un avis comptable.
