# 04 — Conformité, risques et plans de repli

Version 2, mise à jour le 27 octobre 2026 après vérification sur sources primaires. Le détail des vérifications, avec citations et verdicts, est dans [08-verifications-primaires-2026-10-27.md](08-verifications-primaires-2026-10-27.md) ; les identifiants T-, B-, L- y renvoient.

**Ce document n'est pas un avis juridique ni comptable.** Les points marqués **À faire trancher** doivent passer par un juriste ou un comptable avant le premier pilote payant.

Légende : **V** vérifié sur source primaire ; **S** secondaire seulement ; **?** non établi ; **C** contesté.

## 1. Protection des données (loi n° 2024/017)

| Sujet | État | Ce que nous en retenons | Implication produit |
|---|---|---|---|
| Texte officiel (Journal officiel) | **?** (L-01) | Introuvable ; tout ce qui suit est secondaire | Obtenir le texte officiel avant toute conception juridique |
| Promulgation (23 décembre 2024) | **S** (L-02) | Date de référence | — |
| Entrée en vigueur (23 juin 2026) | **S** (L-04) | Une seule source de presse | Traiter la loi comme applicable |
| Autorité APDP (article 53) | **S** (L-03) | Autorité indépendante ; publie la liste des pays adéquats | Surveiller cette liste |
| Décret d'application | **?** (L-06) | Aucun trouvé | Inconnu |
| Rôles responsable et sous-traitant | **S** | Agence = responsable ; Travora = sous-traitant | Contrat de sous-traitance (DPA) par agence |
| Formalités : autorisation, déclaration, avis | **S** | Catégorie incertaine selon les sources | Champ « formalité » et numéro par traitement |
| Registre des traitements | **S** | Tenu par le responsable et le sous-traitant | Export par agence |
| DPO | **C** (L-05) | Les grandes structures des secteurs télécoms, banque et assurance en devraient un, selon une source ; un rapport précédent indique qu'il ne figure pas dans la version finale. Les agences ne sont pas dans ces secteurs | Champ « référent » non bloquant ; **à faire trancher** |
| Consentement, information, droits | **S** | Outils paramétrables, preuves horodatées, révocation | Mentions configurables par l'agence |
| Données sensibles et mineurs | **S** | Protection renforcée des pièces de voyage | Chiffrement des champs sensibles ; marquage des mineurs |
| Violation de données | **S** | Notification « immédiate » dans la version lue ; 72 h dans un projet antérieur | Cible interne : 72 h ; procédure d'incident |
| Transferts hors du Cameroun | **S** | Autorisation préalable, pays adéquats, clauses types ; amende pénale pouvant aller jusqu'à 1 milliard de FCFA pour les personnes morales | Hébergement et sous-traitants sont des transferts potentiels ; décision avant pilote |
| Durées de conservation | **?** | Aucune durée trouvée | Paramétrable par catégorie |

**Conséquences.** La règle de transfert vise toute l'application, pas seulement les passeports : noms, téléphones et dossiers sont des données personnelles. Envoyer ces données à un modèle d'IA hébergé à l'étranger est un transfert : l'analyse doit être déterministe, ou le contenu masqué avant tout appel externe.

## 2. Fiscalité

Source principale : le guide de la DGI sur la TVA (T-01 à T-13 dans 08). C'est un **guide de vulgarisation**, pas le Code général des impôts ; les articles qu'il cite n'ont pas été lus.

| Sujet | État | Ce que dit la source | Implication produit |
|---|---|---|---|
| Taux général | **V** (T-01) | 19,25 % (17,5 % majoré de 10 % de centimes additionnels communaux) | Taux paramétrable par ligne et par date d'effet |
| Assujettissement | **V** (T-02) | Chiffre d'affaires annuel de 50 millions de FCFA ou plus | Suivi du seuil par agence |
| Commissions des agences de voyage | **V** (T-03) | Commissions taxables | La commission est une ligne taxable |
| Exigibilité des services | **V** (T-04) | À l'encaissement du prix | TVA calculée à l'encaissement, ligne par ligne |
| Base des services | **V** (T-05) | Rémunération totale perçue ; débours exclus | Le débours doit être un type de ligne distinct |
| Billets d'avion | **?** (T-12) | Non traité par le guide | Hypothèse (I) : si le prix du billet est un débours, la base taxable serait la commission. **À faire trancher** par un comptable ou la DGI |
| Déclaration | **V** (T-07) | Mensuelle, dans les 15 jours du mois suivant | Export mensuel de la TVA collectée |
| Mentions des factures | **V** (T-08) | Parties, prix HT, taux et montant de TVA, « etc. » | Gabarit avec numérotation continue ; liste complète à obtenir |
| Factures du système de l'administration | **V** (T-09) | La déduction suppose des factures générées par le système de facturation de l'administration | Le module facture doit pouvoir s'y raccorder ; modalités non publiées dans ce guide |
| Paiement en espèces | **V** (T-06) | Pas de déduction au-delà de 100 000 FCFA payés en espèces | Alerte à l'encaissement |
| Comptabilité | **V** | Tenue conforme au système OHADA | Export vers un plan OHADA |
| Prestataire étranger | **V** (T-10) | La TVA s'applique aux opérations réalisées au Cameroun même si le prestataire est établi à l'étranger | **Risque R16** (voir §4) |
| Prestations immatérielles | **V** (T-11) | Taxées au lieu d'établissement du client (conseil, télécommunications, internet) | **Risque R16** : l'abonnement Travora facturé à une agence camerounaise est probablement soumis à la TVA camerounaise. **À faire trancher** |
| E-facturation (loi de finances 2026) | **S** | Annoncée par un blog d'éditeur ; aucun texte de la DGI trouvé | Architecture prête ; ne pas promettre la conformité |

## 3. Autres cadres

| Sujet | État | Ce que nous en retenons | Implication produit |
|---|---|---|---|
| Agrément des agences (ministère du Tourisme et des Loisirs) | **S** | Arrêté introuvable ; régime particulier pour le pèlerinage (2027) | Champs « numéro d'agrément » et « date d'expiration » ; Travora n'a pas besoin de cet agrément, **à confirmer** |
| Cybersécurité (loi 2010/012) et ANTIC | **S** | Obligations précises non trouvées | Journalisation, chiffrement, gestion des accès, plan d'incident |
| Services de paiement (BEAC, COBAC) | **S** | Seuls les établissements agréés fournissent des services de paiement (règlement 04/18, source secondaire) | Travora enregistre les paiements, ne détient aucun fonds et n'initie aucun ordre ; **à faire trancher** |
| Compte marchand chez l'opérateur | **V** (O-02) | Orange : approbation par la banque centrale ; MTN : plafonds BEAC | Un encaissement direct par l'agence peut prendre du temps à ouvrir (**R17**) |
| Extension CEMAC | **?** | Non recherchée de façon concluante | Pays par agence, TVA et gabarits par pays, hébergement par pays |

## 4. Registre des risques

| # | Risque | Mécanisme de réduction | Seuil de décision |
|---|---|---|---|
| R1 | **Adoption (double saisie)** | Collage de PNR et d'e-tickets ; transfert d'e-mail ; démarrage à chaud ; devis envoyé en trois clics par WhatsApp | Moins de 50 % des nouveaux dossiers dans Travora à la semaine 3 : diagnostic avant toute nouvelle fonction |
| R2 | Économie du Cameroun seul | Comptage du marché ; prix selon le volume ; rapport « valeur récupérée » ; prépaiement annuel | Valeur récupérée inférieure à 3 fois le prix, ou moins de 25 agences qualifiées : revoir segment ou prix |
| R3 | Acheteur différent de l'utilisateur | Deux interfaces ; relevé de commission pour l'agent ; permissions par champ | Un agent saisit moins de 50 % de ses dossiers : entretien |
| R4 | Données personnelles et hébergement | §1 ; décision écrite ; portabilité ; masquage avant tout modèle d'IA | Décision écrite avant le premier pilote |
| R5 | Nom « Travora » | Recherche d'antériorité OAPI sur trois noms (classes 9, 35, 42, à confirmer par un conseil) ; domaines .com et .cm | Dépôt avant le lancement commercial |
| R6 | TVA et facturation | §2 ; modules fiscaux après validation d'un comptable | Spécification de la DGI publiée : planifier |
| R7 | Fiabilité du parseur | Pré-remplissage avec confirmation ; texte brut conservé ; corpus anonymisé ; aucune écriture financière automatique | Taux de correction manuelle par champ |
| R8 | Intégrité financière | Journal en ajout seul ; idempotence ; tests de propriétés ; période verrouillée ; sauvegarde et restauration testée | Écart de réconciliation : zéro |
| R9 | Coût des canaux | `wa.me` d'abord ; API WhatsApp ensuite, coût refacturé ; notifications dans l'application | Lire la grille du Cameroun avant tout chiffrage |
| R10 | Fondateur seul | Pas plus de 5 pilotes ; runbook ; supervision | Support au-delà de 20 % du temps : arrêter les nouveaux pilotes |
| R11 | Impayés d'abonnement | Prépaiement ; lecture seule après 14 jours ; jamais de suppression | — |
| R12 | Propriété intellectuelle de FairFare | Autorisation écrite avant toute copie ; sinon réimplémentation des principes | Réponse écrite avant d'importer du code |
| R13 | Dépendance à Amadeus | Aucune au MVP ; port d'ingestion interchangeable | Accès refusé ou modifié : bascule sur collage et e-mail |
| R14 | Paiement ambigu ou en double | Webhook = signal ; confirmation par appel de statut ; références uniques ; état « à revoir » | Aucun paiement « réussi » sans confirmation |
| R15 | Dispersion du périmètre (tous modes) | Un seul parseur au MVP (aérien) ; schéma par mode ; inventaire hors périmètre | Plus de 30 % du temps hors aérien avant le premier pilote : recentrer |
| R16 | **TVA sur l'abonnement Travora** | Faire trancher par un fiscaliste : statut de Travora, immatriculation éventuelle, TVA sur les abonnements ; prix affichés avec la TVA ou hors taxe selon l'avis | Avis écrit avant la première facturation |
| R17 | **Ouverture d'un compte marchand** (Orange : approbation de la banque centrale) | Démarrer par l'agrégateur ou la saisie manuelle ; ne pas dépendre d'un compte direct au MVP | Délai d'approbation constaté chez les pilotes : planifier en conséquence |

### Faits sur le nom (recherche limitée au web anglophone)

- Une marque TRAVORA est enregistrée aux États-Unis au nom de Seawind Ventures LLC pour le conseil, la planification de voyages et la réservation en ligne (statut à confirmer sur le registre officiel).
- Travora Networks, Inc. détient une marque plus ancienne (dépôt de 2011, statut non confirmé).
- « Travora Hub » est un logiciel de réservation en marque blanche sur Capterra (éditeur non identifié).
- Recherche OAPI : **non effectuée**. Nom de travail conservé.

## 5. Éventualités et plans de repli

| Éventualité | Effet | Prévu dans la conception |
|---|---|---|
| Accès GDS refusé ou retiré | Plus d'import automatique | Collage, transfert d'e-mail et import de fichier restent disponibles ; port interchangeable |
| L'APDP exige un hébergement local | Changement d'hébergeur | Portabilité (conteneurs, PostgreSQL, stockage compatible S3) ; région par agence |
| Opérateur de paiement indisponible | Paiement en attente | Saisie manuelle avec identifiant ; relance ; état « à revoir » |
| Agrégateur ferme ou change ses tarifs | Coût ou rupture | Port de paiement ; plusieurs adaptateurs |
| Double débit ou statut incertain | Litige | Référence externe unique ; procédure de litige ; remboursement manuel tracé |
| Traitement fiscal des billets tranché autrement | Marges fausses | Type de ligne et règle versionnée par date d'effet |
| E-facturation rendue obligatoire | Non-conformité | Factures structurées et immuables ; connecteur à ajouter |
| Une agence quitte Travora | Données à restituer | Export complet à tout moment ; lecture seule avant fermeture |
| Plusieurs succursales | Isolation interne | Succursales, rôles et périmètres ; rapports par succursale |
| Hôtels, assurances, transferts ajoutés | Types de réservation | Dossier avec réservations de types différents ; types de fournisseurs configurables |
| Devise étrangère | Erreur de change | Montant d'origine, taux et montant en XAF figés |
| Réémission, échange, remboursement partiel | Écritures complexes | Contre-passation partielle et nouvelle vente ; jamais de modification |
| Erreur découverte après clôture | Période verrouillée | Correction sur la période courante, avec référence |
| Panne ou compromission du serveur | Perte de données | Sauvegarde quotidienne chiffrée ; restauration testée chaque mois |
| Fuite entre agences | Atteinte à la confiance | RLS ; clés étrangères composites ; tests d'intrusion en CI |
| Le fondateur est indisponible | Support interrompu | Runbook ; documentation ; accès d'urgence documenté |
| Connexion lente ou coupée | Saisie perdue | Interface légère ; brouillons locaux ; synchronisation au retour du réseau |
| Concurrent arrive localement | Pression sur les prix | Différenciation : Mobile Money, FCFA, petites agences, export libre |
| Marché trop petit | Revenus insuffisants | Extension CEMAC ; revenu moyen par agence accru par le volume |
