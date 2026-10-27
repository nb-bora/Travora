# ADR-0001 — Plateforme multimodale à connecteurs et règles versionnées

- **Statut** : proposé (27 octobre 2026), en attente de validation du fondateur sur A8 (niveau 3 hors périmètre). **Précisé le même jour par [12](../12-plan-recentre-60-jours.md)** : le MVP n'implémente ni connecteurs, ni schémas par mode, ni règles configurables ; cette ADR décrit la cible à long terme et ses déclencheurs.
- **Documents liés** : [01](../01-cahier-des-charges.md), [03](../03-modele-de-donnees-et-invariants.md), [11](../11-flux-reels-par-mode-et-plateforme.md)

## Contexte

Travora doit couvrir tous les modes de voyage (avion, car, train, bateau, hôtel, transfert, location, assurance), avec des fournisseurs très différents : un GDS sous contrat, un transporteur qui vend au guichet, une plateforme avec API, un fichier d'horaires. Il doit aussi absorber les changements (nouveau mode, nouveau fournisseur, nouvelle taxe, nouvelle règle d'annulation) sans réécriture. Il est construit par une seule personne.

## Décision

1. **Le noyau est un modèle interne unique** : Offre, Engagement, Titre, Segment, Quota, RègleAnnulation, ÉvénementFournisseur, avec un vocabulaire d'états commun (voir [11](../11-flux-reels-par-mode-et-plateforme.md) §7).
2. **Chaque fournisseur est décrit par un canal, un modèle de règlement et des capacités déclarées.** Aucune API n'est supposée. Une capacité non déclarée n'apparaît pas dans l'interface.
3. **Les différences entre fournisseurs se traitent par connecteurs** : un connecteur implémente un contrat et est testé par ce contrat. Il est activé par agence, et seulement si un droit ou un contrat le permet.
4. **La personnalisation utilise quatre mécanismes, dans cet ordre** : donnée, règle versionnée, workflow à étapes prédéfinies, connecteur. Il n'y a aucun code fourni par le client.
5. **Les règles** (frais, taxes, pénalités, seuils d'alerte) sont des plages versionnées par date d'effet, limitées à des conditions prédéfinies (mode, fournisseur, date, montant, délai avant départ).
6. **Le niveau 3** (recherche et réservation temps réel multi-fournisseurs) est **hors périmètre** tant que cette ADR n'est pas amendée.
7. **Les modes entrent un par un**, dans l'ordre fixé par les pilotes, selon le critère R15.

## Conséquences

- Positives : une nouvelle éventualité se traite le plus souvent sans toucher au journal financier ni à l'isolation entre agences. Un fournisseur sans API reste utilisable.
- Négatives : le modèle est plus abstrait que ce qu'un seul mode demanderait ; chaque connecteur est une maintenance ; le nombre de règles peut croître ; la table de correspondance des codes doit être tenue à jour.
- À surveiller : si plus de 30 % du temps de développement part hors aérien avant le premier pilote, on recentre (R15).

## Alternatives écartées

- **Un modèle par mode** (une table `Billet`, une table `TicketBus`, une table `TicketTrain`…) : duplique la logique financière et les alertes, et chaque nouveau mode est une migration.
- **Un moteur de règles général** (scripts ou expressions fournis par le client) : impossible à tester, risque de sécurité, support intenable pour une personne.
- **Un agrégateur en temps réel dès le MVP** : contrats, disponibilité, responsabilité d'émission ; voir A8.
