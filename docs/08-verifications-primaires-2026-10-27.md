# 08 — Vérifications sur sources primaires (27 octobre 2026)

Registre des affirmations **lues sur la source** lors de la passe du 27 octobre 2026, avec le verdict. Il porte sur les points qui changent une décision de conception. Il ne remplace pas une revue juridique ou comptable.

## Méthode

- **PDF** : texte extrait localement avec `pdftotext`, lu intégralement (guide TVA de la DGI ; document IATA sur la remise BSP). Les citations sont exactes.
- **Pages web** : lues par un outil d'extraction qui restitue des passages. Les citations sont celles restituées ; elles doivent être recontrôlées sur la page avant tout engagement.
- **Sources secondaires** (presse, cabinets, blogs, plugins, résultats de recherche) : utilisées seulement pour signaler un point, jamais comme preuve.

## Légende

| Symbole | Sens |
|---|---|
| **V** | Vérifié sur source primaire (officielle ; pour un fournisseur, sa propre page tarifaire ou documentation) |
| **◐** | Partiellement vérifié (le passage existe mais une borne ou un détail manque) |
| **S** | Secondaire seulement |
| **?** | Non établi : introuvable ou illisible |
| **C** | Contesté : des sources s'opposent |
| **✘** | Contredit par une source primaire |

## A. Fiscalité (DGI, guide TVA, 1er avril 2025 selon les métadonnées)

Ce document est un **guide de vulgarisation**, pas le Code général des impôts. Les articles qu'il cite (dont l'article 128 pour les exonérations) n'ont pas été lus.

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| T-01 | Taux général de TVA de 19,25 % | **V** | « Taux général : 19,25 % (soit un taux de 17,5 % majoré des centimes additionnels communaux de 10 %) » |
| T-02 | Assujettissement dès 50 millions de FCFA de chiffre d'affaires annuel | **V** | « les personnes réalisant un chiffre d'affaires annuel égal ou supérieur à 50 millions de FCFA » |
| T-03 | Commissions des agences de voyage taxables | **V** | « commissions perçues par les agences de voyage » (liste des opérations taxables) |
| T-04 | TVA exigible à l'encaissement pour les services | **V** | « l'encaissement du prix pour les prestations de services » |
| T-05 | Base des services : rémunération totale ; débours exclus | **V** | « Pour les services : la rémunération totale perçue » ; « Sont exclus : escomptes, remises, débours, indemnisations, etc. » |
| T-06 | Pas de déduction pour un paiement en espèces au-delà de 100 000 FCFA | **V** | « ne pas avoir payé en espèces au-delà de 100 000 FCFA » |
| T-07 | Déclaration mensuelle dans les 15 jours du mois suivant | **V** | « déposer une déclaration mensuelle dans les 15 jours du mois suivant » |
| T-08 | Mentions de facture : parties, prix HT, taux et montant de TVA | **V** | « identification des parties, prix HT, taux et montant de TVA, etc. » (liste non exhaustive) |
| T-09 | Déduction suppose des factures issues du système de facturation de l'administration | **V** | « factures conformes générées à partir du système de facturation de l'administration fiscale » |
| T-10 | TVA sur opérations réalisées au Cameroun même si le prestataire est étranger | **V** | « La TVA s'applique aux opérations réalisées au Cameroun, même si le prestataire est établi à l'étranger. » |
| T-11 | Prestations immatérielles (conseil, télécommunications, internet) taxées au lieu d'établissement du client | **V** | « Les prestations immatérielles (conseil, publicité, télécommunications, internet) sont taxées au lieu d'établissement du client. » |
| T-12 | Règle de TVA pour les billets d'avion | **?** | Le guide ne traite pas des billets |
| T-13 | Le guide cite les plateformes de commerce électronique comme devant s'immatriculer | **V** (texte) / **?** (application à Travora) | « Les plateformes étrangères ou locales doivent s'immatriculer, collecter et reverser la TVA » : application à un SaaS B2B à faire trancher |

## B. Remise BSP (IATA, « Recent changes to BSP remittance rules », date indiquée par le moteur de recherche : 14 janvier 2026)

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| B-01 | Marchés hebdomadaires : versement sous cinq jours ouvrés ou sept jours calendaires après la clôture | **V** | « five working days or seven calendar days after the close of the sales/billing period » (amendement de novembre 2025 à la Résolution 812) |
| B-02 | 134 marchés hebdomadaires, dont 108 alignés ; 26 à aligner avant juin 2026 | **V** | « Of the 134 BSP markets operating on a weekly remittance schedule, 108 have … » ; « the remaining 26 markets by June 2026 » |
| B-03 | 42 marchés en remise bimensuelle | **V** | « the 42 BSP markets that operate on fortnightly remittance » |
| B-04 | Calendrier de remise du Cameroun | **?** | Le mot « Cameroon » n'apparaît pas dans le document. À demander à l'IATA locale ou aux agences accréditées |
| B-05 | Hypothèse initiale « mensuel ou bimensuel » | **✘** pour la majorité des marchés | Les marchés hebdomadaires sont les plus nombreux dans ce document |

## C. Orange Money Web Payment (developer.orange.com)

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| O-01 | Le service est disponible au Cameroun pour les marchands | **V** | « Orange Money Web Payment service is available to merchants starting with Mali, Cameroon, Cote d'Ivoire » |
| O-02 | Le marchand doit être approuvé par la banque centrale | **V** | « It must be approved by the relevant central bank. » |
| O-03 | Inscription en boutique Orange dans le pays d'activité | **V** | « These merchants just have to sign up for our solution in an Orange store in their country of business » |
| O-04 | Frais, délais de validation, remboursement, signature des notifications | **?** | Absents de la page lue |

## D. MTN MoMo : Collections Cameroun (momoapi.mtn.com) et portail développeur (momodeveloper.mtn.com)

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| M-01 | Paiement initié par le client (USSD, application, web) ou par le marchand (demande de débit) | **V** | « Payments can be customer-initiated on USSD/App/Web » ; « Merchant-initiated where a customer is sent a debit request for approval » |
| M-02 | Frais : « between 1% » par transaction | **◐** | « A Fee of between 1% shall be charged per transaction. » La borne supérieure n'apparaît pas dans l'extraction : à relire sur la page |
| M-03 | Pas de coût par appel API | **V** | « There is no cost per API call. » |
| M-04 | Frais prélevés à la liquidation, négociables | **V** | Extraction : frais « prélevés sur le compte Collections du client lors de la liquidation », « peuvent être négociés » |
| M-05 | Fonds conservés sur un compte Collections créé par MTN ; plafonds fixés par la BEAC | **V** | Extraction : « Les fonds collectés sont conservés sur un compte Collections créé par MMC » ; « soumises aux plafonds fixés par la BEAC » |
| M-06 | Délai de règlement, devise, environnements Cameroun | **?** | Absents de la page |
| M-07 | Portail développeur : familles « Get Paid » (Request Payment, Refund, Notify, Payment Status, Account Balance) et « Pay » (Transfer, Transfer Status, Account Balance) | **V** | Page d'accueil lue ; la nomenclature « Collection / Disbursement » des guides tiers n'y figure pas |
| M-08 | Bac à sable accessible à `/API-collections` ; Cameroun et XAF non mentionnés | **V** | Lien « API Sandbox » vers `/API-collections` ; aucune mention du Cameroun ni du XAF |
| M-09 | Requête de paiement : POST `/collection/v1_0/requesttopay`, succès 202, statut en GET, callbacks en PUT, identifiant UUID v4 | **S** | Guides tiers et forum uniquement. **À valider sur la documentation d'accès** (après inscription) |

## E. Notch Pay (developer.notchpay.co/faq.md)

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| N-01 | Frais par transaction variables selon le moyen et le volume, non publiés en chiffres | **V** | « Notch Pay charges a small fee per transaction, which varies depending on the payment method and volume. » |
| N-02 | Pas de frais d'installation ni mensuels | **V** | « There are no setup fees or monthly charges. » |
| N-03 | Vérification du compte en 1 à 2 jours ouvrés | **V** | « Account verification typically takes 1-2 business days » |
| N-04 | Remboursement total ou partiel en 5 à 7 jours ouvrés | **V** | « You can refund the full amount or a partial amount. » ; « Refunds are typically processed within 5-7 business days » |
| N-05 | Cameroun listé ; disponibilité MTN et Orange variable selon le pays | **V** / **?** | « including Cameroon, Côte d'Ivoire, Senegal » ; « The available payment methods vary by country. » : disponibilité exacte par pays non confirmée |
| N-06 | Signature des webhooks vérifiable ; pas de politique de nouvelle tentative décrite | **◐** | « Verify webhook signatures » sans mécanisme ; aucune politique de nouvelle tentative |

## F. Campay

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| C-01 | Encaissement Mobile Money au Cameroun (MTN et Orange) | **V** (site du fournisseur) | « CamPay helps businesses to accept Payments with Mobile Money in Cameroon » |
| C-02 | Encaissement MTN et Orange à 2 % de frais | **V** (site du fournisseur, tarif affiché) | « Collect payments from MTN & Orange with a flat 2% fee. » |
| C-03 | Retrait à 1 % | **V** (site du fournisseur) | « 1%/ Withdrawal » |
| C-04 | Virement bancaire : frais forfaitaire de 5 000 FCFA | **V** (site du fournisseur) | « 5000f/ bank transfer » |
| C-05 | Webhooks et notifications | **?** | Absents du site ; documentation API (Postman) non lisible par l'outil |
| C-06 | Flux « lien de paiement » avec URL de redirection, statuts SUCCESSFUL ou FAILED ; retraits à activer dans les réglages | **S** | SDK et plugins (PyPI, WordPress) |
| C-07 | Société TAKWID GROUP, service lancé en janvier 2021 | **S** | Résultat de recherche |
| C-08 | Le SDK « camerpay/php-sdk » est un autre fournisseur, CamerPay | **S** | Packagist : ne pas réutiliser ses points d'accès pour Campay |

## G. WhatsApp Business Platform (developers.facebook.com/docs/whatsapp/pricing ; whatsappbusiness.com)

| ID | Affirmation | Verdict | Citation |
|---|---|---|---|
| W-01 | Messages de service : 1 000 gratuits par mois et par numéro, puis payants | **V** | « Each business phone number has one free tier of 1,000 delivered service messages per month. » |
| W-02 | Changement au 1er octobre 2026 : reprise de la facturation par message de messages auparavant gratuits ; 40 tarifs mis à jour | **V** | « Meta resumed charging, on a per-message basis, for messages that were previously free » ; « Meta updated 40 rates » |
| W-03 | Région tarifaire « Rest of Africa » (40 marchés) ; le Maroc en sort au 1er octobre 2026 | **V** | « Rest of Africa – 40 markets » ; « Moved out of “Rest of Africa” region » |
| W-04 | Le Cameroun appartient à « Rest of Africa » | **?** | Liste des pays non lue ; la page de tarifs ne l'affiche pas en texte |
| W-05 | Montants pour le Cameroun | **?** | La page affiche : « Sélectionnez le marché, la devise et la catégorie de message pour consulter le détail de notre tarification. » Grille à lire dans l'outil de tarification ou dans les fichiers de tarifs |
| W-06 | Messages utilitaires envoyés en réponse : gratuits depuis le 1er juillet 2025, payants au 1er octobre 2026 | **◐** | Formulation ambiguë dans l'extraction : à relire sur la page |
| W-07 | Montants 0,0259 USD (marketing) et 0,0046 USD (utilitaire) | **✘ non retenu** | Source : un revendeur (Gallabox), non vérifiée. **Retirés de la fiche 05** |

## H. Loi n° 2024/017 (données personnelles)

| ID | Affirmation | Verdict | Note |
|---|---|---|---|
| L-01 | Texte officiel (Journal officiel) | **?** | Introuvable en deux recherches (27/10/2026) |
| L-02 | Promulgation le 23 décembre 2024 ; vote le 26 novembre 2024 | **S** | Plusieurs commentaires concordants |
| L-03 | Création de l'APDP, article 53 | **S** | Commentaire ; l'article n'a pas été lu |
| L-04 | Entrée en vigueur le 23 juin 2026 | **S** | Une source de presse |
| L-05 | Obligation de DPO pour les grandes structures (télécoms, banque, assurance) | **C** | Une source l'affirme ; un rapport précédent cite une source disant qu'elle ne figure pas dans la version finale. Les agences ne sont pas dans ces secteurs |
| L-06 | Décret d'application et liste des pays adéquats | **?** | Aucun trouvé |

## I. Amadeus Self-Service

| ID | Affirmation | Verdict | Note |
|---|---|---|---|
| A-01 | Fermeture du portail Self-Service ; clés désactivées le 17 juillet 2026 | **S** | Presse et résumés concordants (PhocusWire, AirLabs, Ignav) ; **courrier officiel d'Amadeus non trouvé** |
| A-02 | Enterprise non concerné | **S** | Même source |

## J. Briques techniques (vérifiées ce jour)

| ID | Affirmation | Verdict | Citation ou valeur |
|---|---|---|---|
| D-01 | Django 5.2 LTS : support régulier terminé le 3 décembre 2025 ; sécurité jusqu'en avril 2028 | **V** | Page officielle de téléchargement : « December 3, 2025 » ; « April 2028 » |
| D-02 | Dernière version listée : 6.1.2 ; support régulier jusqu'en avril 2027 ; sécurité jusqu'en décembre 2027 | **V** | « The latest official version is 6.1.2. » ; « April 2027 » ; « December 2027 » |
| G-01 | Procrastinate : licence MIT, non archivé, poussé le 26/10/2026 (1 435 étoiles) | **V** | API GitHub |
| G-02 | WeasyPrint : licence BSD-3-Clause, non archivé, poussé le 26/10/2026 (9 736 étoiles) | **V** | API GitHub |

## Bilan de la passe

- **Confirmé sur source primaire** : TVA (taux, seuil, commissions, exigibilité, déclaration, factures, débours, prestataires étrangers) ; BSP (règle hebdomadaire) ; Orange Money (Cameroun, approbation de la banque centrale) ; MTN (frais « between 1% », pas de coût par appel, fonds sur compte Collections) ; Notch Pay (délais, remboursement) ; Campay (tarifs affichés) ; WhatsApp (1 000 messages de service gratuits) ; Django ; Procrastinate ; WeasyPrint.
- **Corrigé** : hypothèse « mensuel ou bimensuel » pour le BSP ; frais MTN « ~1,5 % » (non vérifié) ; Cameroun « dans Rest of Africa » (non vérifié) ; montants WhatsApp du revendeur (retirés).
- **Toujours non établi** : texte officiel de la loi 2024/017 et décret ; calendrier BSP du Cameroun ; règle de TVA sur les billets ; appartenance du Cameroun à la région WhatsApp et montants ; documentation API MTN et Campay accessibles ; délais de règlement MTN ; amendement Amadeus primaire.
