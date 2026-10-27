# Travora — documentation de conception

Version 0.2, mise à jour le 27 octobre 2026. Ces documents sont des **hypothèses de conception**. Ils ne remplacent ni un avis juridique, ni un avis comptable, ni les entretiens avec les agences.

## Index

| Fichier | Contenu |
|---|---|
| [00-glossaire-et-conventions.md](00-glossaire-et-conventions.md) | Termes métier, codes, conventions techniques et documentaires |
| [01-cahier-des-charges.md](01-cahier-des-charges.md) | Vision, personas, décisions D1 à D7, périmètre MVP, exigences F, N, C, critères d'acceptation, prix |
| [02-etude-existant-et-reutilisation.md](02-etude-existant-et-reutilisation.md) | Solutions existantes, cahiers des charges types, réutilisation du monolithe FairFare, briques et licences |
| [03-modele-de-donnees-et-invariants.md](03-modele-de-donnees-et-invariants.md) | Isolation par agence, entités, machines d'état, journal financier, configuration, ports |
| [04-conformite-et-risques.md](04-conformite-et-risques.md) | Loi 2024/017, fiscalité, autres cadres, registre des risques R1 à R17, plans de repli |
| [05-integrations-et-canaux.md](05-integrations-et-canaux.md) | Entrée des données (GDS, BSP), paiements et opérateurs, WhatsApp, coûts |
| [06-validation-terrain-et-demarrage-a-chaud.md](06-validation-terrain-et-demarrage-a-chaud.md) | Comptage du marché, entretiens, critères d'arrêt, import de démarrage à chaud, plan de 90 jours |
| [08-verifications-primaires-2026-10-27.md](08-verifications-primaires-2026-10-27.md) | **Registre des vérifications** : chaque point vérifié, avec citation, verdict et date |
| [11-flux-reels-par-mode-et-plateforme.md](11-flux-reels-par-mode-et-plateforme.md) | Flux réels par mode, ambiguïtés à lever, modèles de règlement, fournisseurs et capacités, éventualités |
| [adr/ADR-0001-plateforme-multimodale-connecteurs.md](adr/ADR-0001-plateforme-multimodale-connecteurs.md) | Décision d'architecture : plateforme multimodale à connecteurs et règles versionnées (proposée, cible long terme) |
| [13-catalogue-fournisseurs.md](13-catalogue-fournisseurs.md) | **Catalogue de tous les fournisseurs recensés**, par type de voyage (GDS, NDC, cars, trains, bateaux, hôtels, locations, assurances, paiement), avec leurs conditions d'accès et le niveau de preuve |
| [adr/ADR-0002-registre-fournisseurs.md](adr/ADR-0002-registre-fournisseurs.md) | Décision : registre extensible de fournisseurs (fiches en données, adaptateurs par capacité, activation conditionnée au contrat) |
| [12-plan-recentre-60-jours.md](12-plan-recentre-60-jours.md) | **Plan de référence pour les 60 prochains jours** : MVP réduit, refus explicites avec déclencheurs, ordre de construction, comment faire selon les documentations officielles |

Les registres générés `09` et `10` n'existent pas : le workflow de recherche a été arrêté. Le registre de référence est `08`.

## Niveaux de preuve

- **V** vérifié sur source primaire (officielle, ou page tarifaire du fournisseur pour ses propres prix) ;
- **◐** partiel ; **S** secondaire seulement ; **?** non établi ; **C** contesté.

## Ce qui est vérifié, ce qui ne l'est pas

**Vérifié sur source primaire le 27/10/2026** : taux, seuil, exigibilité et déclaration de la TVA ; règles de TVA sur les commissions d'agence et les débours ; règle hebdomadaire de remise BSP ; Orange Money Web Payment disponible au Cameroun, avec approbation de la banque centrale ; frais MTN « between 1% » ; Campay (2 % à l'encaissement) ; Notch Pay (délais) ; 1 000 messages WhatsApp de service gratuits par mois ; Django 5.2 et 6.1 ; licences Procrastinate et WeasyPrint.

**Non établi** : texte officiel de la loi 2024/017 et décret d'application ; calendrier BSP du Cameroun ; TVA propre aux billets d'avion ; statut fiscal de Travora pour ses abonnements ; coût WhatsApp au Cameroun ; documentation d'accès MTN et Campay ; courrier officiel d'Amadeus sur la fermeture du Self-Service.

## Points à traiter avant tout engagement

1. Autorisation écrite de FairFareHQ avant toute copie de code ou de document ([02](02-etude-existant-et-reutilisation.md) §5.1).
2. Jeton SonarQube exposé dans le `README.md` du dépôt FairFare : à révoquer ([02](02-etude-existant-et-reutilisation.md) §5.3).
3. Avis fiscal : TVA sur les abonnements, traitement des billets, mentions de facture ([04](04-conformite-et-risques.md) §2, R16).
4. Décision d'hébergement avec un juriste ([04](04-conformite-et-risques.md) §1).
5. Lecture du texte officiel de la loi 2024/017 et de son décret ([04](04-conformite-et-risques.md) §1).
6. Recherche d'antériorité OAPI du nom ([04](04-conformite-et-risques.md) §4).
7. Dix entretiens et comptage du marché ([06](06-validation-terrain-et-demarrage-a-chaud.md)).
