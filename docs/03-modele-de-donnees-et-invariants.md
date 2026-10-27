# 03 — Modèle de données et invariants financiers

Statut : proposition de conception, à valider. Les montants, taux et règles fiscales cités ici sont des paramètres, pas des vérités légales (voir `04-conformite-et-risques.md`).

## 0. Conventions retenues

| Sujet | Convention | Raison |
|---|---|---|
| Pile (hypothèse D1, à confirmer) | Monolithe modulaire Django 6.1 (voir [01](01-cahier-des-charges.md), D1), PostgreSQL, interface serveur + htmx, Celery seulement quand un traitement asynchrone devient nécessaire | Une seule base de code pour un développeur seul ; HTML léger sur réseau lent ; mêmes conventions que le monolithe FairFare déjà maîtrisé |
| Identifiants | UUIDv7 | Ordonnés dans le temps, sûrs à exposer |
| Montants | Entiers en unité mineure de la devise (XAF : exposant 0). Une ligne porte `montant`, `devise`, et, si la devise n'est pas XAF, `taux_vers_xaf` figé à la saisie | Pas d'erreur d'arrondi flottant ; une ligne reste explicable des années après |
| Suppressions | `PROTECT` entre modules, jamais `CASCADE` ; désactivation douce pour les référentiels | Aucun paiement ne perd sa trace parce qu'un client a été supprimé |
| Photos (snapshots) | Prix, frais, taux, libellé du moyen de paiement sont copiés sur la ligne au moment du fait | Une modification ultérieure de la grille ne réécrit pas l'histoire |
| Dates | UTC en base, fuseau `Africa/Douala` à l'affichage | Alertes fiables |

## 1. Isolation entre agences

Une base, un schéma, `tenant_id` sur toute table du plan de données, et cloisonnement appliqué par PostgreSQL (Row Level Security), pas par l'application.

1. **Quatre catégories de tables.** Identité globale (utilisateur), plan de contrôle (agence, domaines, routage des webhooks), référence partagée (aéroports, devises), plan de données (tout le reste). Toute nouvelle table est classée avant d'être écrite ; en cas de doute, c'est du plan de données.
2. **Rôles de base de données.** Un rôle propriétaire qui ne se connecte jamais, un rôle de migration, un rôle applicatif sans `BYPASSRLS`, ni DDL, ni `TRUNCATE`. Les policies visent explicitement le rôle applicatif, jamais `PUBLIC`. `FORCE ROW LEVEL SECURITY` sur chaque table.
3. **Contexte.** L'identité authentifiée détermine l'agence ; la valeur est posée dans la transaction (`SET LOCAL`). Sans contexte, une requête du plan de données lève une erreur au lieu de renvoyer zéro ligne.
4. **Clés étrangères composites** `(parent_id, tenant_id)` entre tables d'un même tenant : un identifiant globalement unique empêche de pointer vers un objet inexistant, pas vers un objet d'une autre agence.
5. **Unicités métier toujours préfixées par le tenant** (numéro de dossier, numéro de billet, code fournisseur).
6. **Webhooks.** Un paiement Mobile Money arrive sans contexte d'agence. Une table de routage du plan de contrôle (identifiant fournisseur → tenant, deux UUID, aucune donnée personnelle, écriture unique) rouvre le contexte avant toute lecture.
7. **Tâches de fond** (Celery ou planifiées) : elles posent le contexte d'agence explicitement, une agence à la fois.
8. **Ce que la RLS ne protège pas** : une résolution de tenant erronée, un processus applicatif compromis, un SQL arbitraire exécuté par le rôle applicatif. Pour un client institutionnel exigeant, la réponse est une base dédiée avec identifiants séparés (niveau d'isolation supérieur), à prévoir comme option sans l'imposer à tous.
9. **Tests de CI obligatoires** : (a) toute table du plan de données a une policy ; (b) toute relation interne porte une FK composite ; (c) un test d'intrusion automatisé lit, écrit et met à jour avec le contexte de l'agence A les lignes de l'agence B et doit échouer à chaque fois.

## 2. Entités

| Module | Entité | Rôle | Remarques |
|---|---|---|---|
| tenancy | `Agency` | Tenant, plan, pays, devise de base, fuseau, région d'hébergement | `region_donnees` prévu dès le départ (voir conformité) |
| tenancy | `Branch` | Succursale | Rattachement principal, jamais une autorisation |
| accounts | `User`, `Membership` | Identité globale ; accès à une agence avec un rôle | Un utilisateur peut appartenir à plusieurs agences (agent indépendant, expert-comptable) |
| crm | `Customer` | Payeur (particulier ou entreprise) | Numéro de téléphone normalisé E.164, canal préféré |
| crm | `Passenger` | Voyageur, distinct du payeur | Nom tel qu'il figure sur le document de voyage ; date de naissance ; date d'expiration du document (pas de scan au MVP) |
| catalog | `Supplier` | Compagnie aérienne, consolidateur, compagnie de bus, opérateur ferroviaire, armateur, hôtel, assureur, loueur | `type_approvisionnement` : BSP direct, consolidateur, compagnie directe, guichet, autre ; règles d'annulation et de remboursement par fournisseur |
| catalog | `FeeRule` | Règle de frais de service | Fixe, pourcentage, par fournisseur, par classe, par type de dossier ; dates de validité |
| catalog | `TaxProfile` | Régime de TVA et mentions | Versionné par date d'effet |
| quotes | `Quote`, `QuoteVersion`, `QuoteLine` | Devis, versions, lignes | Chaque version est figée à l'envoi ; marge interne séparée du prix présenté |
| cases | `TravelCase` | Dossier commercial central | Contient 1..N réservations ; porte les échéances |
| bookings | `Booking` | Réservation fournisseur, avec un **mode** (avion, bus, train, bateau, hôtel, transfert, location, assurance, autre) | Références externes (PNR pour l'aérien, code de réservation pour les autres), délai d'émission lorsqu'il existe, statut |
| bookings | `TravelDocument` | Titre de transport ou document émis (billet aérien, billet de bus ou de train, voucher d'hôtel, EMD) | Passager, numéro du titre, montants, statut (émis, annulé, remboursé, échangé) ; attributs propres au mode dans un champ validé par un schéma |
| bookings | `Segment` | Tronçon d'un titre : origine, destination, départ, arrivée, transporteur, numéro de service, classe, place | 1..N par titre ; couvre aller simple, aller-retour, correspondances, multi-destinations |
| bookings | `ModeSchema` | Définition des champs propres à un mode et de leurs validations | Plan de contrôle configurable ; ajouter un mode ne demande pas de migration |
| ledger | `LedgerTransaction`, `LedgerPosting` | Écriture équilibrée et ses lignes | Immuables (voir §4) |
| ledger | `Payment`, `Refund` | Faits d'encaissement et de remboursement | Génèrent des écritures ; statuts Mobile Money |
| ledger | `SupplierStatement` | Relevé fournisseur (remise BSP, relevé consolidateur) | Sert au rapprochement |
| documents | `Document` | Pièce jointe ou PDF généré | Chiffrement par agence, durée de conservation |
| alerts | `Alert` | Alerte calculée à partir de dates et statuts | Pas de rappel générique |
| ingestion | `ImportBatch`, `IngestedMessage` | Lot d'import, e-mail ou texte reçu | Idempotent, annulable, texte brut conservé |
| audit | `AuditEvent` | Journal d'actions sensibles | Ajout seul (interdit de modifier ou supprimer au niveau modèle) |

## 3. Machines d'état

- **Devis** : brouillon → envoyé → accepté | refusé | expiré ; un devis accepté est converti en dossier. Un nouveau devis remplace une version, il ne la modifie pas.
- **Dossier** : ouvert → confirmé (au moins une réservation confirmée) → en cours de voyage → terminé → clôturé ; ou annulé. Le **statut financier est dérivé du journal**, jamais saisi : non payé, partiellement payé, soldé, trop-perçu, remboursement dû.
- **Réservation** : demandée → retenue (PNR créé, délai d'émission connu) → confirmée → émise → échangée ou réémise ; ou annulée, expirée (délai dépassé), remboursée. Un devis payé n'est jamais assimilé à un billet émis.
- **Paiement** : en attente (Mobile Money initié) → confirmé | échoué | à revoir (réponse ambiguë) ; un paiement saisi manuellement est confirmé à la saisie, avec auteur et justificatif facultatif. Une erreur se corrige par une contre-écriture, jamais par une modification.

### 3.1 Multimodalité

Le journal financier (§4) ne dépend pas du mode : une vente reconnue, un encaissement, un règlement fournisseur et un remboursement s'écrivent de la même façon pour un billet d'avion, de bus ou de train. Seuls changent :

- les **attributs du titre** (schéma par mode) ;
- les **règles d'annulation et de remboursement** (par fournisseur et par mode) ;
- le **moment d'émission** : l'aérien a un délai d'émission et une remise BSP ou consolidateur ; un billet de bus ou de train est souvent émis et payé au guichet, sans délai ; la machine d'état de la réservation s'adapte par mode (états optionnels : « retenue », « émise ») ;
- le **parseur** disponible (aérien d'abord) ; les autres modes passent par une saisie guidée.

Ce qui n'est pas couvert : l'inventaire de places d'une compagnie de transport (plan de sièges, départs, manifestes, embarquement). Si l'agence est elle-même le transporteur, il faut un module séparé.

## 4. Journal financier

### 4.1 Principes

- Journal à partie double **opérationnel** (suivi interne de l'agence), pas la comptabilité légale SYSCOHADA. Un export doit permettre à l'expert-comptable de reprendre les données.
- Une `LedgerTransaction` regroupe des `LedgerPosting` (débit ou crédit) dont **la somme des débits égale la somme des crédits**. Elle est immuable. Une correction est une transaction de contre-passation qui référence l'originale.
- Les soldes (client, fournisseur, caisse) sont **calculés** à partir des écritures, jamais stockés comme valeurs modifiables. Des vues matérialisées servent le tableau de bord.
- Chaque écriture porte : agence, date de valeur, date de saisie, auteur, source (saisie manuelle, Mobile Money, import), clé d'idempotence, référence du dossier.

### 4.2 Comptes

| Compte | Sens |
|---|---|
| `CAISSE`, `BANQUE`, `MOMO_MTN`, `MOMO_ORANGE`… | Trésorerie par moyen |
| `CLIENT:<id>` | Compte client : solde positif = le client doit ; négatif = avance reçue |
| `FOURNISSEUR:<id>` | Compte fournisseur : ce que l'agence doit |
| `PRODUIT_FRAIS` | Frais de service |
| `PRODUIT_MARGE` | Marge commerciale sur le billet |
| `PRODUIT_COMMISSION` | Commissions reçues des fournisseurs |
| `TVA_COLLECTEE` | Si applicable selon le profil fiscal |
| `CHARGE_FRAIS_PAIEMENT` | Frais prélevés par l'opérateur ou l'agrégateur |
| `PERTE_CREANCE` | Créances radiées |

### 4.3 Écritures types

| Fait | Débit | Crédit |
|---|---|---|
| Encaissement client (acompte ou solde) | `MOMO_*` / `CAISSE` / `BANQUE` (net), `CHARGE_FRAIS_PAIEMENT` (frais) | `CLIENT` (brut) |
| Vente reconnue (billet émis) | `CLIENT` (prix de vente total) | `FOURNISSEUR` (coût), `PRODUIT_FRAIS`, `PRODUIT_MARGE`, `TVA_COLLECTEE` |
| Règlement fournisseur | `FOURNISSEUR` | Trésorerie |
| Commission fournisseur | `FOURNISSEUR` | `PRODUIT_COMMISSION` |
| Remboursement au client | `CLIENT` | Trésorerie |
| Annulation après émission | Contre-passation partielle de la vente + ligne de frais d'annulation | selon le cas |
| Échange / réémission | Contre-passation de la part remplacée + nouvelle vente de la différence | selon le cas |
| Radiation de créance (approbation du gérant) | `PERTE_CREANCE` | `CLIENT` |

Le moment de la reconnaissance du revenu (à l'émission ou au départ) est un **paramètre d'agence**, par défaut à l'émission. Le traitement exact est à valider avec un comptable.

### 4.4 Invariants (testés automatiquement)

1. Toute transaction est équilibrée.
2. Aucune écriture n'est modifiée ni supprimée ; une correction est une contre-passation.
3. Le solde d'un client est la somme de ses lignes ; trésorerie, créances et dettes se réconcilient au franc près avec le journal.
4. Une même clé d'idempotence ne crée jamais deux transactions pour une agence (contrainte en base).
5. Un identifiant de transaction fournisseur (Mobile Money) est unique ; un deuxième webhook identique ne crée rien.
6. Un seul paiement « vivant » (en attente, confirmé, à revoir) par fait générateur lorsque le métier l'exige (contrainte conditionnelle en base, pas un simple `exists()`).
7. Une réservation « émise » exige un coût fournisseur renseigné et au moins un billet.
8. Un dossier ne se clôture qu'à solde nul ou après radiation approuvée.
9. **Période verrouillée** : après clôture d'un mois, aucune écriture n'est datée dans ce mois ; les corrections s'imputent sur la période courante avec référence.
10. Devise étrangère : montant d'origine, taux et montant en XAF sont figés ; la règle d'arrondi est unique et documentée.
11. Le prix de vente est toujours `coût + frais + marge (+ taxes)` ; l'identité est vérifiée à chaque enregistrement.

## 5. Prix, marge et visibilité

- Trois montants internes par ligne : coût fournisseur, frais de service, marge. Seul le **prix de vente** figure sur les documents du client.
- Les frais viennent d'une règle versionnée ; un changement de grille s'applique aux nouveaux devis, pas aux anciens.
- Permissions par champ : le coût et la marge sont visibles du gérant, du responsable et du comptable ; l'agent les voit seulement si l'agence l'active.
- Une classe tarifaire sans règle de frais fait échouer la création du devis avec un message clair : on ne laisse jamais passer un frais omis par défaut.
- Chaque ligne de devis ou de dossier a un **type** : commission, débours (montant avancé au nom et pour le compte du client, exclu de la base de TVA selon le guide de la DGI, voir [04](04-conformite-et-risques.md) §2), ou vente en nom propre. Le type porte le traitement fiscal ; il n'est jamais déduit du libellé.

## 6. Configuration par agence (« tout est paramètre »)

Pour absorber les situations imprévues sans modifier le code :

- Devises actives, règle d'arrondi, taux de change (saisis ou importés).
- Grilles de frais et de commissions, profils fiscaux avec dates d'effet.
- Mode de reconnaissance du revenu ; acompte minimal avant émission ; durée de validité par défaut d'un devis.
- Seuils d'alerte (jours avant départ, jours avant expiration d'un délai d'émission, solde impayé).
- Seuils d'approbation (remboursement ou remise au-delà de X : validation du gérant).
- Modèles de documents (logo, mentions légales, langue, numérotation).
- Types de fournisseur et leurs champs obligatoires.
- Drapeaux de fonctions par plan (interrupteurs côté serveur, jamais côté navigateur).

## 7. Ports et adaptateurs (extension sans réécriture)

Chaque dépendance externe se branche derrière une interface ; le métier ne connaît jamais le fournisseur.

| Port | Adaptateurs prévus | Remplaçable si… |
|---|---|---|
| `IngestionPort` | collage de texte, transfert d'e-mail, PDF, fichier GDS, API GDS | l'accès GDS est refusé ou change |
| `PaymentProviderPort` | saisie manuelle ; agrégateurs Mobile Money | un opérateur ou agrégateur ferme ou renchérit |
| `NotificationChannelPort` | e-mail, notification dans l'application, lien WhatsApp, API WhatsApp, SMS | un canal change de tarif ou de règles |
| `StoragePort` | stockage compatible S3 | l'hébergement change |
| `PdfRendererPort` | moteur HTML vers PDF | une licence ou une police pose problème |
| `ParserPort` | analyseur déterministe, repli assisté par IA (avec masquage des données personnelles) | un transfert de données hors du pays n'est pas autorisé |

## 8. Tests obligatoires avant le premier pilote

1. Intrusion inter-agences (lecture, écriture, mise à jour) sur chaque table du plan de données.
2. Propriétés du journal : transactions équilibrées ; solde client égal à la somme de ses écritures ; réconciliation trésorerie.
3. Idempotence : rejouer dix fois le même webhook, le même import, le même envoi de formulaire.
4. Parseur : corpus de textes réels anonymisés, avec taux de correction manuelle mesuré par champ.
5. Restauration complète d'une sauvegarde sur un environnement vierge, chronométrée.
6. Période verrouillée : tentative d'écriture rétroactive refusée.
