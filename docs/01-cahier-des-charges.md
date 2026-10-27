# 01 — Cahier des charges de Travora

Plateforme SaaS de gestion opérationnelle et financière pour agences de voyages, d'abord les agences de billetterie aérienne indépendantes de Douala et Yaoundé.

Statut : version 0.1, hypothèses à valider (voir `06-validation-terrain-et-demarrage-a-chaud.md`). Les exigences portent un identifiant (F = fonctionnelle, N = non fonctionnelle, C = conformité) et une priorité : **M** (MVP), **P2** (phase 2), **P3** (phase 3). Le nom « Travora » est un nom de travail (voir `04-conformite-et-risques.md`).

## 1. Vision et périmètre

**Problème** : une agence suit ses dossiers dans Amadeus, WhatsApp, un tableur et un cahier. Elle ne sait pas, à tout moment, quels dossiers sont en cours, combien les clients doivent encore, combien elle a réellement gagné, quelles opérations risquent de poser problème.

**Promesse** : transformer une demande en dossier suivi, payé, avec marge visible, sans obliger l'agence à quitter ses outils de réservation.

**Modes de transport couverts** (décision du fondateur) : avion, bus, train, bateau et tout autre titre de transport, plus hôtel, transfert, location de voiture, assurance. Dans cette version, Travora **enregistre et suit** les titres vendus par l'agence ; il n'émet pas de titres lui-même.

**Hors périmètre initial** : moteur de réservation et d'émission, **gestion d'inventaire et de places d'une compagnie de transport** (plans de sièges, départs, manifestes, embarquement : produit différent, voir D7), marketplace, application mobile native, portail client public, détention de fonds, comptabilité légale complète.

## 2. Personas

| Persona | Besoin | Ce qui le fait adopter |
|---|---|---|
| Gérant | Voir dossiers, soldes, marge, risques | Un tableau de bord fiable, un rapport mensuel de valeur récupérée |
| Agent | Faire un devis vite, encaisser, ne pas ressaisir | Devis PDF en 30 secondes, collage de PNR, reçus automatiques, relevé de commission personnel |
| Comptable (interne ou externe) | Pièces et exports cohérents | Journal immuable, export, périodes verrouillées |
| Fondateur de Travora | Support et exploitation | Outils d'administration, supervision, runbook |

## 3. Décisions à prendre (avec ma recommandation)

| # | Décision | Recommandation | Raison |
|---|---|---|---|
| D1 | Pile technique | Django 6.1 + PostgreSQL, interface serveur + htmx, monolithe modulaire | Une base de code, mêmes conventions que le monolithe FairFare déjà maîtrisé, HTML léger sur réseau lent ; le texte initial supposait FastAPI et Next.js sans lien avec ton expérience documentée. Version vérifiée le 27/10/2026 : Django 5.2 LTS n'a plus de support régulier depuis le 3 décembre 2025 (sécurité seule jusqu'en avril 2028) ; Django 6.1 a un support régulier jusqu'en avril 2027. Recommandation : 6.1, avec migration vers la prochaine LTS avant avril 2027 (date à confirmer sur djangoproject.com) ; le monolithe FairFare est encore en 5.2 |
| D2 | Hébergement | À décider avec un juriste avant le premier pilote ; Travora rendu portable | Transferts hors du Cameroun soumis à autorisation |
| D3 | Réutilisation de code FairFare | Réimplémenter à partir des principes, sauf autorisation écrite de FairFareHQ | Propriété intellectuelle partagée, plusieurs contributeurs |
| D4 | Segment initial | Agences indépendantes de 1 à 5 agents, 30 à 150 dossiers par mois, émission directe ou via consolidateur ; consolidateurs en piste parallèle | Hypothèse à trancher par les entretiens |
| D5 | Traitement fiscal des billets | Paramètre par ligne ; commission taxable et débours exclu de la base (guide de la DGI, vérifié le 27/10/2026) ; traitement des billets à fixer avec un comptable | La règle propre aux billets d'avion n'est pas dans le guide de la DGI |
| D6 | Nom | Garder « Travora » comme nom de travail, tester trois alternatives auprès de l'OAPI | Conflits de marque trouvés ailleurs |
| D7 | Modes de transport | Modèle **multimodal** dès le départ (avion, bus, train, bateau…), analyse automatique de l'aérien seulement au MVP, saisie guidée pour les autres modes ; l'inventaire de places d'une compagnie de transport reste hors périmètre (phase 3, module séparé) | Le journal financier est indépendant du mode ; le coût est dans la saisie et les parseurs, pas dans le modèle. Piège : une compagnie de bus qui vend ses propres places a besoin de sièges, de départs et de manifestes, ce qui est un autre produit |

## 4. Périmètre du MVP

Le MVP tient dans un écran central : **dossier → devis → paiements partiels → coût fournisseur → marge réelle → solde**. Tout le reste le soutient.

| Domaine | MVP | Phase 2 | Phase 3 |
|---|---|---|---|
| Authentification, agences, rôles | ✔ | SSO, MFA obligatoire | Réseaux multi-agences |
| Clients et passagers | ✔ | Documents (scans chiffrés) | — |
| Devis PDF avec marge interne | ✔ | Options multiples, multi-devises avancé | — |
| Dossiers et réservations multimodales (avion, bus, train, bateau, hôtel…) | ✔ saisie guidée pour tous les modes ; collage de PNR et e-ticket transféré pour l'aérien | Import fichier AIR ; analyse de billets de bus et de train | API GDS si accord ; module d'inventaire pour compagnies de transport |
| Paiements et soldes | ✔ saisie manuelle avec identifiant de transaction | Agrégateur Mobile Money, rapprochement | Comptes marchands par agence |
| Journal financier, marges, commissions | ✔ | Remise BSP et relevés fournisseurs | Export comptable avancé |
| Alertes et tableau de bord | ✔ dates et statuts fiables | WhatsApp automatisé | — |
| Import de démarrage à chaud | ✔ Excel/CSV + texte collé | PDF, WhatsApp | — |
| Facturation fiscale | Proforma et reçus | Facture conforme, e-facturation | — |
| Abonnements Travora | Lien ou virement | Automatisé | — |

## 5. Exigences fonctionnelles

### 5.1 Clients et passagers (CRM)

- **F-CRM-1 (M)** Fiche client (payeur) : nom, téléphone normalisé, e-mail, canal préféré.
- **F-CRM-2 (M)** Fiche passager distincte du client : nom tel qu'il figure sur le document, date de naissance, date d'expiration du document de voyage.
- **F-CRM-3 (M)** Historique des demandes, devis, dossiers et paiements par client.
- **F-CRM-4 (M)** Détection de doublons à la création (téléphone, nom).
- **F-CRM-5 (P2)** Affectation de prospects aux agents ; relances de devis non acceptés.

### 5.2 Devis et tarification

- **F-DEV-1 (M)** Un devis a des lignes (vol, hôtel, assurance, transfert) avec coût fournisseur, frais de service, marge, taxes, prix de vente.
- **F-DEV-2 (M)** Seul le prix de vente figure sur le PDF du client ; coût et marge restent internes.
- **F-DEV-3 (M)** Les frais de service viennent d'une règle versionnée ; une classe sans règle bloque la création du devis avec un message clair.
- **F-DEV-4 (M)** Versions : un devis envoyé est figé ; une modification crée une nouvelle version.
- **F-DEV-5 (M)** Date d'expiration, statut (brouillon, envoyé, accepté, refusé, expiré) ; alerte avant expiration.
- **F-DEV-6 (M)** PDF avec logo et mentions de l'agence ; envoi par lien WhatsApp (`wa.me`) ou e-mail.
- **F-DEV-7 (M)** Devises XAF, EUR, USD avec taux figé à la saisie.
- **F-DEV-8 (P2)** Options multiples dans un même devis.

### 5.3 Dossiers et réservations

- **F-DOS-1 (M)** Un dossier contient 0..N réservations de types différents ; le PNR n'est pas l'identifiant du dossier.
- **F-DOS-2 (M)** Statuts distincts : devis accepté, réservation retenue, confirmée, billet émis, annulé, remboursé, échangé. Un devis payé n'est jamais assimilé à un billet émis.
- **F-DOS-3 (M)** Le délai d'émission (TL), la date de départ et les échéances de paiement sont des champs de première classe.
- **F-DOS-4 (M)** Collage d'un affichage PNR ou d'un reçu d'itinéraire : pré-remplissage des passagers, segments, numéro de billet ; confirmation humaine ; texte brut conservé.
- **F-DOS-5 (M)** Transfert d'un e-mail d'e-ticket à une adresse dédiée de l'agence : création ou rattachement à un dossier, avec confirmation.
- **F-DOS-6 (M)** Numéro de billet unique par agence ; rapprochement sur ce numéro.
- **F-DOS-7 (M)** Pièces jointes chiffrées, durée de conservation configurable.
- **F-DOS-8 (P2)** Import de fichiers AIR ; rapprochement avec le relevé BSP.

### 5.4 Paiements et soldes

- **F-PAI-1 (M)** Paiement intégral ou partiel : espèces, virement, Mobile Money ; identifiant de transaction obligatoire pour Mobile Money et virement ; justificatif facultatif.
- **F-PAI-2 (M)** Solde restant par dossier et par client, calculé à partir du journal.
- **F-PAI-3 (M)** Reçu PDF numéroté pour chaque encaissement.
- **F-PAI-4 (M)** Alerte sur doublon probable (même payeur, même montant, même dossier, courte fenêtre) et sur règlement en espèces supérieur à 100 000 FCFA.
- **F-PAI-5 (M)** Remboursement au client : approbation du gérant au-delà d'un seuil configurable ; contre-écriture.
- **F-PAI-6 (P2)** Paiement Mobile Money initié depuis Travora via un agrégateur ; webhook = signal, confirmation par appel de statut.
- **F-PAI-7 (P2)** Import de relevés opérateur (CSV) et rapprochement.

### 5.5 Finance et rentabilité

- **F-FIN-1 (M)** Journal à partie double opérationnel, immuable (voir `03`).
- **F-FIN-2 (M)** Tableau de bord du gérant : dossiers en cours, créances clients, dettes fournisseurs, trésorerie par moyen, marge par dossier, commissions.
- **F-FIN-3 (M)** Distinction explicite entre trésorerie encaissée, chiffre d'affaires reconnu et marge.
- **F-FIN-4 (M)** Marge prévue et marge réelle par dossier ; alerte sur marge négative.
- **F-FIN-5 (M)** Période verrouillable ; corrections sur la période courante avec référence.
- **F-FIN-6 (M)** Export CSV et Excel des écritures, créances et dettes.
- **F-FIN-7 (M)** Rapport mensuel automatique « valeur récupérée » (soldes relancés, marges négatives évitées, frais de service oubliés).
- **F-FIN-8 (P2)** Remise BSP et relevés de consolidateurs ; TVA collectée par mois.
- **F-FIN-9 (P3)** Facture conforme et e-facturation après validation fiscale.

### 5.6 Alertes et suivi

- **F-ALE-1 (M)** Alertes calculées sur dates et statuts : devis qui expire, délai d'émission proche, départ imminent, solde impayé, document de voyage expirant (moins de six mois avant le voyage), dossier sans action.
- **F-ALE-2 (M)** Canal principal : notifications dans l'application et e-mail ; seuils configurables par agence.
- **F-ALE-3 (P2)** Relances WhatsApp et SMS automatiques, coût refacturé.

### 5.7 Administration et sécurité

- **F-ADM-1 (M)** Agences, succursales, utilisateurs, rôles (gérant, responsable, agent, comptable, lecteur), permissions par champ (coût et marge).
- **F-ADM-2 (M)** Journal d'audit en ajout seul : paiements, remboursements, modifications de prix, annulations, accès aux documents sensibles.
- **F-ADM-3 (M)** Export complet des données d'une agence à tout moment.
- **F-ADM-4 (M)** Lecture seule après 14 jours d'impayé, jamais de suppression.
- **F-ADM-5 (M)** Outils d'administration plateforme : agences, plans, incidents.

### 5.8 Import et démarrage à chaud

- **F-IMP-1 (M)** Import Excel/CSV avec correspondance de colonnes mémorisée par agence.
- **F-IMP-2 (M)** Aperçu, lots annulables, idempotence, rapport de rejets.
- **F-IMP-3 (M)** Soldes d'ouverture sous forme d'écritures du journal.
- **F-IMP-4 (M)** Rapport de réconciliation (totaux Travora vs tableur) avant bascule.

### 5.9 Modes de transport et types de titres

- **F-TRA-1 (M)** Chaque réservation a un **mode** : avion, bus, train, bateau, hôtel, transfert, location de voiture, assurance, circuit, autre. La liste est configurable par agence.
- **F-TRA-2 (M)** Un titre de transport (billet) est rattaché à un passager et à 1..N segments ; un segment a origine, destination, départ, arrivée, transporteur, numéro de service, classe, place éventuelle.
- **F-TRA-3 (M)** Les attributs propres à un mode (numéro de billet aérien, base tarifaire, bagages ; numéro de car, gare ou agence de départ ; numéro de train, voiture, place ; etc.) sont définis par un schéma de champs par mode, validé à la saisie, sans migration de base pour ajouter un mode.
- **F-TRA-4 (M)** Aller simple, aller-retour, avec correspondances, multi-destinations : tous représentables ; saisie manuelle possible pour tous les modes.
- **F-TRA-5 (M)** Fournisseurs typés : compagnie aérienne, consolidateur, compagnie de bus, opérateur ferroviaire, armateur, hôtel, assureur, loueur.
- **F-TRA-6 (M)** Le journal financier, le solde, la marge, les alertes de paiement et les documents sont identiques pour tous les modes.
- **F-TRA-7 (M)** Alertes selon le mode : délai d'émission (aérien), date et heure de départ, échéance de paiement ; les règles propres à un mode se configurent sans code.
- **F-TRA-8 (M)** Annulation, échange et remboursement : règles de pénalité paramétrables par fournisseur et par mode.
- **F-TRA-9 (P2)** Analyse automatique par mode : aérien d'abord (PNR, e-ticket), puis modèles de billets de bus et de train les plus courants (PDF ou image avec code-barres), selon les volumes révélés par les entretiens.
- **F-TRA-10 (P2)** Documents complémentaires aériens (EMD) et réémissions complexes.
- **F-TRA-11 (P3)** Module séparé d'inventaire pour compagnies de transport (départs, places, manifestes, embarquement), si les entretiens montrent ce besoin.

## 6. Exigences non fonctionnelles

| ID | Exigence | Cible |
|---|---|---|
| N-1 | Isolation entre agences appliquée par la base (RLS), clés étrangères composites, tests d'intrusion automatisés en CI | 0 fuite |
| N-2 | Idempotence des webhooks, imports et envois de formulaires | Rejeu sans doublon |
| N-3 | Intégrité financière : transactions équilibrées, réconciliation au franc près | 0 écart |
| N-4 | Disponibilité | ≥ 99,5 % mensuel (cible à valider) |
| N-5 | Sauvegarde quotidienne chiffrée et restauration testée chaque mois | Temps de reprise mesuré |
| N-6 | Performance sur réseau lent : pages légères, fragments htmx, brouillons locaux | Écran principal utilisable en 3G |
| N-7 | Portabilité d'hébergement : conteneurs, PostgreSQL, stockage compatible S3, aucun service propriétaire | Changement de région sans réécriture |
| N-8 | Sécurité : chiffrement en transit et au repos, chiffrement par enveloppe des documents, secrets hors du code, MFA pour gérant et administrateurs | À définir |
| N-9 | Observabilité : journaux structurés, supervision de disponibilité, alertes d'erreurs | — |
| N-10 | Internationalisation : français d'abord, anglais ensuite ; dates et montants localisés | — |
| N-11 | Licences : aucune dépendance AGPL, GPL, SSPL ou BSL ; inventaire en CI | 0 |
| N-12 | Qualité : tests unitaires et d'intégration sur le journal, l'isolation et l'idempotence | Couverture élevée sur ces modules |

## 7. Exigences de conformité

Voir `04-conformite-et-risques.md` pour le détail. En synthèse :

- **C-1 (M)** Rôles agence = responsable de traitement, Travora = sous-traitant ; contrat de sous-traitance.
- **C-2 (M)** Registre des traitements exportable ; finalité par catégorie de données ; liste des sous-traitants ultérieurs.
- **C-3 (M)** Consentements et mentions paramétrables, horodatés, révocables.
- **C-4 (M)** Droits des personnes : export, anonymisation, journal des demandes.
- **C-5 (M)** Procédure d'incident et alerte de l'agence sans délai (cible interne 72 h).
- **C-6 (M)** Cartographie des flux sortants ; aucun transfert hors du Cameroun sans cadre validé ; masquage avant tout modèle de langage.
- **C-7 (M)** Taux de TVA, régime et mentions paramétrables par ligne et par date d'effet ; aucun traitement fiscal codé en dur.
- **C-8 (M)** Travora ne détient aucun fonds et n'initie aucun ordre de paiement.
- **C-9 (P3)** Facture conforme et connecteur d'e-facturation.
- **C-10 (M)** Statut fiscal de Travora (résident ou non) et TVA sur les abonnements facturés à des clients camerounais : avis écrit d'un fiscaliste avant la première facturation (voir [04](04-conformite-et-risques.md) §2, R16).

## 8. Architecture (résumé)

- Monolithe modulaire par domaines : tenancy, accounts, crm, catalog, quotes, cases, bookings, ledger, documents, alerts, ingestion, audit, integrations, reporting.
- Appels entre modules uniquement par une façade publique ; accès externes derrière des ports et adaptateurs (ingestion, paiements, notifications, stockage, PDF, analyse).
- Détails du modèle, des invariants et de l'isolation : `03-modele-de-donnees-et-invariants.md`.
- Briques et licences : `02-etude-existant-et-reutilisation.md` §6 (Procrastinate ou Celery, WeasyPrint, pgledger ou django-hordak à évaluer, chiffrement maison par enveloppe).

## 9. Intégrations

Voir `05-integrations-et-canaux.md`. Ordre : collage de texte et e-mail transféré (MVP), puis fichier AIR avec une agence pilote, puis agrégateur Mobile Money, puis WhatsApp Cloud API, puis API Amadeus Enterprise par partenariat.

## 10. Critères d'acceptation du MVP

1. Un agent crée un devis avec marge interne et l'envoie par WhatsApp en moins de deux minutes.
2. Un affichage PNR collé pré-remplit passagers, segments et numéro de billet ; l'agent corrige et valide.
3. Un dossier avec trois paiements partiels (espèces, virement, Mobile Money) affiche le bon solde ; un remboursement partiel se corrige par contre-écriture.
4. Le tableau de bord du gérant se réconcilie au franc près avec le journal.
5. Un test automatisé prouve qu'une agence ne peut ni lire, ni écrire, ni modifier les données d'une autre.
6. Une sauvegarde est restaurée sur un environnement vierge et le temps de reprise est mesuré.
7. Un import de démarrage à chaud d'une agence pilote est réconcilié avec son tableur, puis annulé et rejoué sans doublon.
8. L'export complet d'une agence est produit et rechargeable.

## 11. Prix (hypothèses à valider en entretien)

| Plan | Cible | Prix indicatif | Remarque |
|---|---|---|---|
| Pilote | 3 à 5 agences | 10 000 à 15 000 FCFA/mois | Preuve de volonté de payer |
| Agence | 1 à 5 postes | 35 000 FCFA/mois (≈ 53 €) | Plafond de référence : environ 3 % de la marge brute mensuelle de l'agence |
| Réseau | Multi-succursales | Sur devis | Contrôles et workflows personnalisés |

Frais d'installation (reprise de données, formation) et prépaiement annuel proposés. Repère de marché : les outils publiés pour petites équipes se situent entre environ 25 et 270 USD par mois. Un abonnement fixe est préféré à une commission sur les billets.
