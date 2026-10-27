# ADR-0002 — Registre extensible de fournisseurs

- **Statut** : proposé (27 octobre 2026)
- **Documents liés** : [13](../13-catalogue-fournisseurs.md), [11](../11-flux-reels-par-mode-et-plateforme.md), [ADR-0001](ADR-0001-plateforme-multimodale-connecteurs.md), [12](../12-plan-recentre-60-jours.md)

## Contexte

Une agence peut vendre des billets via plusieurs GDS, plusieurs agrégateurs NDC, des compagnies directes, des cars, des trains, des bateaux, des hôtels, des locations et des assurances. Le nombre de fournisseurs existants est grand, et chacun a ses conditions d'accès. Aucune liste n'est exhaustive, et les conditions évoluent. La plateforme doit donc accepter autant de fournisseurs que nécessaire, sans qu'un ajout remette en cause le métier.

## Décision

1. **Le fournisseur est une donnée, pas une branche de code.** Chaque fournisseur a une fiche : type de voyage, rôle, canal (API, fichier, téléphone, guichet, plateforme), règlement (BSP, consolidateur, compte direct, dépôt, commission), capacités déclarées, statut d'accès.
2. **Un type de voyage peut avoir plusieurs fournisseurs, et un fournisseur peut couvrir plusieurs types.** La relation est `Fournisseur ↔ TypeDeVoyage` avec des attributs propres (ex. : un GDS pour l'aérien, avec un identifiant de bureau propre à chaque pays).
3. **Le code d'un fournisseur est un adaptateur qui implémente un port par capacité** (catalogue, réservation, émission, annulation, statut, relevé, paiement). Une capacité non implémentée ou non déclarée n'apparaît pas dans l'interface.
4. **Un canal sans API est un adaptateur comme les autres** : saisie guidée, import de relevé. Il implémente les mêmes ports et produit les mêmes événements.
5. **Les identifiants externes ne sont jamais la clé de l'agence.** Chaque objet interne garde ses références externes par fournisseur (PNR, numéro de billet, code de réservation) dans une table dédiée, unique par fournisseur et par agence.
6. **Les credentials sont par agence, chiffrés, et jamais exposés au navigateur.**
7. **Un fournisseur n'est activable pour une agence que si son statut est `ACTIF` ou `MANUEL`.** Passer à `ACTIF` exige : contrat signé, identifiants fournis, tests de contrat passés contre le bac à sable du fournisseur, et accord écrit de l'agence.
8. **Aucun scraping.** Un fournisseur dont les données ne sont accessibles que par extraction est `EXCLU`.
9. **Aucune promesse commerciale.** Les fournisseurs `CONTRAT` ou `A_VERIFIER` ne sont jamais affichés aux agences.

## Ce qui est construit maintenant, et ce qui attend

| Élément | Maintenant | Quand |
|---|---|---|
| Table de catalogue (fiches des fournisseurs, statuts) | Oui, en données administrées par le fondateur, sans interface agence | Semaine 1 du plan 12 |
| Table de liaison fournisseur ↔ agence, avec statut d'activation | Oui | Semaine 1 |
| Table de références externes | Oui, vide au MVP | Semaine 1 |
| Port de canal `MANUEL` (saisie) | Oui : c'est le chemin du MVP | Semaine 3 |
| Ports d'API (catalogue, réservation, émission…) | Non | Après le premier contrat signé |
| Adaptateur réel | Non | Après le premier contrat signé et la décision écrite du fondateur |
| Import de relevés (`STATEMENT_IMPORT`) | Non | Après trois pilotes actifs |

Le déclencheur de chaque ligne est écrit dans [12](../12-plan-recentre-60-jours.md) §4.

## Conséquences

- Positives : ajouter un fournisseur est une fiche et, s'il a une API, un adaptateur. Le journal financier, le solde et les alertes n'ont pas à changer.
- Négatives : une abstraction par capacité coûte du temps. Elle n'est justifiée que par le nombre réel de fournisseurs, qui n'existe pas encore. Un fournisseur sans contrat ne rapporte rien, quel que soit son nombre de lignes dans le catalogue.
- À surveiller : le nombre de fournisseurs `ACTIF` par agence. Au-delà de deux par type de voyage, la complexité de réconciliation augmente vite ; le critère est à mesurer avec les pilotes.

## Alternatives écartées

- **Un plugin chargé dynamiquement depuis une liste externe** : sécurité, tests et support impossibles à tenir.
- **Un connecteur générique qui traduit tous les formats** : le réel a trop de variantes ; mieux vaut une fiche par fournisseur et un adaptateur testé.
- **Afficher le catalogue complet aux agences** : promesse non tenue, interdite par les constantes du cadrage.
