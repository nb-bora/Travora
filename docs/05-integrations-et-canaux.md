# 05 — Intégrations, paiements et canaux

Version 2, mise à jour le 27 octobre 2026 après vérification sur sources primaires. Citations et verdicts : [08-verifications-primaires-2026-10-27.md](08-verifications-primaires-2026-10-27.md), identifiants M-, N-, C-, O-, W-, B-.

Légende : **V** vérifié sur source primaire ; **◐** partiel ; **S** secondaire seulement ; **?** non établi.

## 1. Entrée des données de réservation

### 1.1 Options classées pour un éditeur sans accord GDS

| Rang | Option | Faisabilité | Remarques |
|---|---|---|---|
| 1 | **Collage de texte** (PNR ou reçu d'itinéraire) | La plus faisable : aucune autorisation | Parseur à écrire ; validation humaine ; formats hétérogènes ; dates sans année (« 18JUL ») à inférer |
| 2 | **E-ticket transféré** (PDF ou e-mail vers une adresse dédiée de l'agence) | Très faisable ; fiabilité moindre | Mise en page propre à chaque compagnie ; sert à compléter : numéro de billet, tarif, taxes |
| 3 | **Fichier d'interface comptable du GDS** (Amadeus AIR, Travelport MIR, Sabre IUR) | Faisable seulement avec l'agence | Activation par le représentant du GDS sur le profil de l'agence ; spécification non publique ; droit d'usage du format à clarifier |
| 4 | **API Amadeus Enterprise** | La moins faisable sans accord | Contrat et droits par API, liés à l'identifiant de bureau de l'agence ; lecture de dossiers existants non acquise ; partenariat plutôt que prérequis |

**Amadeus Self-Service** : fermeture annoncée, clés désactivées le 17 juillet 2026 (A-01, source secondaire concordante ; courrier officiel non trouvé). Ce n'est plus une option.

### 1.2 Remise BSP (vérifié, IATA)

- Depuis l'amendement de novembre 2025 à la Résolution 812, les marchés hebdomadaires versent « five working days or seven calendar days after the close of the sales/billing period » (B-01).
- 134 marchés sont hebdomadaires, dont 108 déjà alignés ; 26 devaient l'être avant juin 2026 (B-02). 42 marchés sont bimensuels (B-03).
- **Le Cameroun n'apparaît pas dans ce document** (B-04) : son calendrier et sa banque de compensation restent inconnus. À demander à l'IATA locale ou à une agence accréditée.
- **Mon hypothèse initiale « mensuel ou bimensuel » est fausse pour la majorité des marchés** (B-05) : elle est retirée.
- Easy Pay est lancé au Cameroun depuis le 30 août 2023 (S : publication IATA, résumé).
- ADM et ACM : débits et crédits émis par la compagnie après audit, consultables dans BSPlink (S). Le format des fichiers HOT n'a pas été confirmé.

### 1.3 Autres modes de transport

Aucun format de billet de bus, de train ou de bateau n'a été vérifié au Cameroun. À établir en entretien (voir [06](06-validation-terrain-et-demarrage-a-chaud.md)) avant d'écrire un parseur.

1. **MVP** : saisie guidée par schéma de champs par mode (voir [03](03-modele-de-donnees-et-invariants.md) §3.1), avec modèles prédéfinis.
2. **Phase 2** : lecture de billets de bus ou de train sur PDF ou image, si les pilotes en fournissent des exemples.
3. Pas de rapprochement BSP hors aérien ; le rapprochement se fait sur le relevé du transporteur concerné, saisi ou importé.

### 1.4 Principes

1. Le parseur **pré-remplit** ; l'humain confirme. Aucune écriture financière n'est créée automatiquement à partir d'un texte analysé.
2. Le texte brut d'origine est conservé avec le dossier.
3. Chaque source passe par le même port d'ingestion : un changement de source ne touche pas le métier.
4. Analyse déterministe d'abord ; repli par modèle de langage seulement avec masquage des données personnelles ou hébergement local (voir [04](04-conformite-et-risques.md) §1).
5. Le rapprochement se fait sur le **numéro de billet**, clé commune avec le BSP.

## 2. Paiements

### 2.1 Position de principe

Travora **enregistre** les paiements ; il ne détient jamais les fonds des voyageurs ni ceux de l'agence. Les fonds vont au compte de l'agence (ou du prestataire qu'elle choisit). Le cadre BEAC/COBAC reste à faire trancher par un juriste (voir [04](04-conformite-et-risques.md) §3).

| Flux | Qui encaisse | Rôle de Travora |
|---|---|---|
| Paiement d'un voyageur à l'agence | L'agence, sur son compte marchand ou via un agrégateur | Lit les statuts, rapproche avec le dossier |
| Abonnement de l'agence à Travora | Travora, via un compte marchand chez un agrégateur | Aucun fonds d'agence détenu |
| Répartition des fonds entre agences par Travora | — | **À éviter** : aucune preuve qu'un fournisseur camerounais l'offre ; risque réglementaire |

### 2.2 Opérateurs et agrégateurs (ce qui est vérifié)

| Fournisseur | Ce qui est vérifié | Non établi |
|---|---|---|
| **MTN MoMo, Collections Cameroun** (V, M-01 à M-05) | Paiement initié par le client (USSD, application, web) ou par le marchand (demande de débit). Frais « between 1% » par transaction (◐ : borne supérieure non lisible dans l'extraction). Prélevés à la liquidation, négociables. Pas de coût par appel API. Fonds conservés sur un compte Collections créé par MTN. Plafonds fixés par la BEAC | Délai de règlement (M-06) ; devise de la page ; environnements |
| **MTN, portail développeur** (V, M-07, M-08) | Familles d'API « Get Paid » (Request Payment, Refund, Notify, Payment Status, Account Balance) et « Pay » (Transfer, Transfer Status). Bac à sable à `/API-collections` | Cameroun et XAF non mentionnés sur la page ; procédure d'accès et KYC non visibles |
| **MTN, requête de paiement** (S, M-09) | Selon des guides tiers : POST `/collection/v1_0/requesttopay`, succès 202, statut en GET, callbacks en PUT, identifiant UUID v4 | **À valider** sur la documentation d'accès après inscription |
| **Orange Money Web Payment** (V, O-01 à O-03) | Disponible au Cameroun pour les marchands. Inscription en boutique Orange dans le pays. **Approbation par la banque centrale** exigée. Paiement validé par OTP USSD | Frais, délais de validation, remboursement, signature des notifications (O-04) |
| **Campay** (V pour le site du fournisseur, C-01 à C-04) | Encaissement MTN et Orange à **2 %** (« flat 2% fee »). Retrait à 1 %. Virement bancaire : 5 000 FCFA forfaitaires. Présent au Cameroun | Webhooks et notifications absents du site (C-05) ; documentation API non lisible ici ; flux « lien de paiement » avec statuts SUCCESSFUL et FAILED (S, C-06) |
| **Notch Pay** (V, N-01 à N-05) | Pas de frais d'installation ni mensuels. Frais variables selon le moyen et le volume, **non publiés en chiffres**. Vérification de compte 1 à 2 jours ouvrés. Remboursement total ou partiel en 5 à 7 jours ouvrés. Cameroun listé | Disponibilité MTN et Orange par pays (« varies by country ») ; mécanisme de signature des webhooks (N-06) ; politique de nouvelle tentative |
| **MoPay** (utilisé par FairFare, vérifié par l'équipe contre sa sandbox le 28/09/2026) | Authentification par clé d'API ; pas d'en-tête d'idempotence ; type d'encaissement `deposit` ; réponse 202 avec statut `pending` ; webhook signé HMAC-SHA256 sur le corps brut | Frais ; API de remboursement non vérifiée |
| PawaPay, Fapshi, Flutterwave, CinetPay, Monetbil | Existent ; tarifs et conditions non relus ici | Tout le reste : à vérifier avant toute décision |

**Mise en garde** : le SDK PHP « camerpay/php-sdk » appartient à un autre fournisseur (CamerPay), pas à Campay (C-08).

### 2.3 Modèle de rapprochement

1. **Tentative de paiement** : clé d'idempotence Travora, référence fournisseur unique par agence et par fournisseur, montant en XAF entier, numéro masqué, statut interne et statut brut, expiration.
2. **Statuts** : initié → en attente → réussi | échoué | expiré ; puis remboursé, partiellement remboursé, litigieux. Un statut terminal ne revient jamais en arrière sans action explicite.
3. **Journal brut des événements du fournisseur** : charge utile, validité de la signature, horodatage ; unicité par fournisseur et identifiant d'événement : un rejeu est sans effet.
4. **Le webhook est un signal** : après réception, appel de l'API de statut ; passage à « réussi » seulement après cette confirmation. Une tâche planifiée relance les tentatives en attente avec délai croissant, puis fait un balayage quotidien.
5. **Journal comptable** : voir [03](03-modele-de-donnees-et-invariants.md) §4. Espèces, virement et Mobile Money partagent le même journal, avec pièce justificative.
6. **Doublons** : unicité de la référence externe (identifiant de transaction du SMS de confirmation), y compris en saisie manuelle ; alerte si même payeur, même montant et même dossier dans une courte fenêtre.
7. **Import de relevés opérateur** (CSV) : appariement, écart de montant, doublon, non rapproché.
8. **Litiges** : ouverture, motif, preuves, résolution ; un litige gèle l'écriture concernée.
9. **Remboursement automatique** : non automatisé tant qu'aucune API de remboursement n'est vérifiée en bac à sable. Alerte et tâche manuelle tracée (même décision que dans FairFare).

### 2.4 Abonnements Travora

- Le Mobile Money est « push » : le payeur valide en USSD. Prévoir un lien ou une demande mensuelle avec relances, pas un prélèvement automatique.
- Au MVP : lien créé à la main chez un agrégateur, ou virement.
- Ensuite : agrégateur avec webhook et appel de statut.
- Coût d'encaissement de référence : 2 % chez Campay (C-02). Chez Notch Pay, non publié.

## 3. Communications

### 3.1 WhatsApp Business Platform (vérifié, Meta)

- **Messages de service** : gratuits jusqu'à 1 000 messages livrés par mois et par numéro, puis payants (W-01).
- **Changement du 1er octobre 2026** : « Meta resumed charging, on a per-message basis, for messages that were previously free » ; 40 tarifs mis à jour (W-02).
- **Régions** : « Rest of Africa » existe avec 40 marchés (W-03). Le Maroc en est sorti au 1er octobre 2026 (W-03).
- **Cameroun dans cette région** : **non établi** (W-04). **Montants pour le Cameroun** : **non établis** (W-05). La grille n'est pas lisible en texte ; elle se consulte par marché et par devise.
- **Messages utilitaires envoyés en réponse** : formulation ambiguë dans l'extraction (W-06, ◐) ; à relire sur la page avant tout chiffrage.
- **Montants 0,0259 USD et 0,0046 USD** (revendeur Gallabox) : **retirés**, faute de source primaire (W-07).

Conséquence : aucun coût WhatsApp n'est chiffré dans ce document tant que la grille du Cameroun n'a pas été lue.

### 3.2 Autres canaux

| Canal | Statut | Recommandation |
|---|---|---|
| Lien `wa.me` | Principe connu (inféré) : `https://wa.me/<numéro international sans +>?text=<texte encodé>` ; gratuit, sans API ; l'utilisateur envoie lui-même le message | **MVP** : devis et relances depuis le WhatsApp de l'agence |
| SMS | Tarifs de sources tierces contradictoires ; identifiant d'expéditeur à enregistrer chez l'opérateur | Secours seulement ; devis à obtenir |
| E-mail transactionnel | Paliers gratuits chez plusieurs prestataires (S) ; coût négligeable | **MVP** |
| Notifications dans l'application | Gratuit | **MVP** : alertes internes |

## 4. Coûts d'encaissement indicatifs

| Élément | Valeur | Statut |
|---|---|---|
| Encaissement d'un abonnement chez Campay (2 %) | 300 FCFA pour 15 000 ; 700 FCFA pour 35 000 | **V** (tarif affiché par le fournisseur) |
| Encaissement chez MTN | « between 1% » ; borne supérieure à relire | **◐** |
| Encaissement chez Notch Pay | Non publié | **?** |
| Encaissement chez Orange | Non publié sur la page lue | **?** |
| WhatsApp (phase 2) | Montant du Cameroun à lire sur la grille | **?** |

## 5. À confirmer en priorité

1. **Documentation d'accès MTN** après inscription : requête de paiement, statuts, callbacks, devise, délai de règlement (M-06, M-09).
2. **Borne supérieure des frais MTN** sur la page Collections (M-02).
3. **Orange Money** : frais, délai d'approbation par la banque centrale, notifications, remboursement (O-04).
4. **Notch Pay** : tarif par moyen de paiement et par volume, signature des webhooks, disponibilité MTN et Orange au Cameroun (N-05, N-06).
5. **Campay** : documentation API lisible, webhooks et statuts (C-05).
6. **WhatsApp** : grille du Cameroun et appartenance à « Rest of Africa » (W-04, W-05, W-06).
7. **BSP** : calendrier de remise du Cameroun (B-04).
8. **Cadre BEAC/COBAC** avant toute répartition de fonds (voir [04](04-conformite-et-risques.md) §3).
