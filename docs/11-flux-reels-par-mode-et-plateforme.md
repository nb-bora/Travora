# 11 — Flux réels par mode et conception de la plateforme

Version 1, 27 octobre 2026. Ce document traduit l'ambition « point central pour tous les voyages, extensible à tout fournisseur » en flux que vivent réellement les agences, en modèle de données et en règles. Il remplace les hypothèses de [03](03-modele-de-donnees-et-invariants.md) §2 et §4.3 sur les points listés en §6.

Légende des preuves : **V** primaire (officielle, ou page du fournisseur pour ses propres informations) ; **S** secondaire (presse, résumé de recherche, plateforme tierce) ; **H** hypothèse de terrain, à valider par entretien. **Aucune** source n'a été trouvée pour certaines pratiques de terrain : elles sont marquées H, pas S.

## 1. Ce que ce document établit, et ce qu'il n'établit pas

- Établi (S) : des pratiques réelles de vente au Cameroun pour l'avion et le train, un exemple documenté de vente « appel puis paiement mobile » par une compagnie aérienne nationale, et des plateformes de billetterie d'autocar au Kenya et au Nigeria.
- Non établi : quels cars, quels bateaux et quels trains vendent aujourd'hui en ligne au Cameroun, leurs horaires, leurs règles d'annulation, et ce que chaque transporteur demande comme pièce d'identité. Ces points se vérifient en entretien (§9), pas en ligne.

## 2. Ambiguïtés à lever

Pour chaque ambiguïté, la position par défaut s'applique tant que tu n'as pas tranché.

| # | Ambiguïté | Pourquoi ça compte | Position par défaut |
|---|---|---|---|
| A1 | Travora gère-t-il des **places** (plan de sièges, départs) ou seulement des **quotas** et des titres vendus ? | Un plan de sièges est un autre produit (inventaire) | Quotas comptés (nombre de places, pas de numéro de siège) ; plan de sièges hors périmètre |
| A2 | Qui **émet** le titre : le transporteur, ou l'agence (tour-opérateur qui affrète un car) ? | Le numéro de titre et sa responsabilité changent | Le transporteur émet ; l'agence peut enregistrer un titre qu'elle a émise elle-même (type d'émetteur) |
| A3 | Qui **encaisse** et qui doit quoi au fournisseur ? | Ça détermine toutes les écritures du journal | Six modèles de règlement (§5) ; l'agence doit choisir un modèle par fournisseur |
| A4 | Qui **rembourse** en cas d'annulation par le transporteur ? | Litige client, et marge perdue | La règle du fournisseur fait foi pour lui ; l'agence applique sa propre politique ; Travora enregistre les deux |
| A5 | Quelles **pièces d'identité** sont exigées par les transporteurs routiers, ferroviaires et maritimes ? | Donnée personnelle, minimisation (loi 2024/017) | Champ optionnel configurable par mode et par fournisseur ; aucun scan ; à vérifier auprès de 3 transporteurs |
| A6 | Une **correspondance** entre deux fournisseurs différents est-elle garantie par l'agence ? | Responsabilité en cas de retard | Non garantie par défaut : alerte de risque de rupture, pas de garantie automatique |
| A7 | Quelle **devise** pour les tarifs ? | Les tarifs de car sont en XAF ; l'international peut être en EUR ou USD | XAF par défaut, devise d'origine conservée et taux figé à la saisie |
| A8 | Le **niveau 3** (réservation en temps réel multi-fournisseurs) | Changerait le produit | Hors périmètre tant qu'il n'est pas décidé (voir [01](01-cahier-des-charges.md) D7) |

## 3. Principes issus du réel

- **P1 — L'unité n'est pas le billet.** Il y a trois objets distincts : l'**engagement** auprès du fournisseur (une place retenue, un PNR, un code de réservation), le **titre** émis (le billet) et le **segment** (le déplacement). Un engagement peut exister sans titre, et un titre peut être annulé sans que l'engagement le soit.
- **P2 — Chaque fournisseur a un canal et un règlement, et aucune API n'est supposée.** Un transporteur peut être joint par téléphone, dans son guichet, par une plateforme, ou par fichier. Le canal décrit comment on obtient les informations ; le règlement décrit qui doit quoi à qui.
- **P3 — « Payé » ne veut pas dire « émis ».** Le fournisseur fixe les délais : limite d'émission d'un PNR (avion), expiration d'une place retenue tant que le paiement n'est pas validé (plateformes d'autocar, S), embarquement (bateau, train).
- **P4 — Les règles d'annulation dépendent de l'heure.** Le même billet a une pénalité différente à 48 h, 12 h et 1 h du départ. Les règles sont des plages horaires, versionnées par date d'effet.
- **P5 — Le réel est désordonné.** Numéros saisis à la main, doublons, corrections, changements d'horaire, remplacement de véhicule. Toute modification passe par un événement journalisé, et toute correction est une contre-écriture ou une nouvelle version, jamais une réécriture.

## 4. Flux réels par mode

Pour chaque mode : les étapes observées, ce qui change de mains, où Travora intervient, et les exceptions.

### 4.1 Avion

**Flux observé (S, presse sur une compagnie nationale).** Le client appelle ou écrit ; l'agent donne horaires et tarifs ; le client paie par MTN Mobile Money ou Orange Money ; le paiement déclenche un retrait et un code de validation ; une fois validé, le billet est confirmé et une confirmation est envoyée par e-mail avec le numéro de billet.

**Flux agence (S et connaissance du secteur).**
1. Demande (WhatsApp, téléphone, comptoir).
2. Recherche et tarification dans le GDS, ou auprès de la compagnie.
3. Devis avec frais de service.
4. Paiement (acompte ou total).
5. Création du PNR, avec limite d'émission (TL).
6. Émission du billet. Le règlement passe par le BSP ou par un consolidateur (§5).
7. Modifications : échange, réémission, remboursement, avec pénalités fixées par la compagnie et frais de l'agence.

**Ce que Travora ajoute.** Le suivi des TL, le rapprochement sur le numéro de billet, la marge par billet, et le relevé de remise.

**Exceptions réelles.** Le billet émis puis annulé dans les 24 h (règle dite de « void », à vérifier par le comptable) ; le nom ne correspond pas au document ; la compagnie change l'horaire.

### 4.2 Car (autocar interurbain)

**Flux observé.** Les plateformes d'autocar en Afrique de l'Est et au Nigeria vendent des places en ligne et envoient un billet électronique (S, BuuPass et 9jaBus). Au Cameroun, certaines compagnies VIP testent le paiement mobile depuis plusieurs années (S, sans nom ni détail de fonctionnement).

**Flux H (à valider), la plupart des cars au Cameroun.**
1. Le voyageur se présente au guichet d'une gare, ou appelle, ou passe par un intermédiaire.
2. Le siège est choisi (ou il n'y a pas de siège numéroté : « premier arrivé »).
3. Paiement en espèces, ou par mobile money avec un numéro de transaction.
4. Un billet papier ou un message avec un numéro est remis.
5. Le jour du départ, le voyageur monte ; le chauffeur ou le contrôleur vérifie le billet ; le nombre de places est mis à jour (ou non).
6. Annulation : pénalité selon le délai, souvent en espèces au guichet.

**Ce que change l'agence.** Elle vend des places dont elle dispose par quota (A1), souvent acheté d'avance (modèle PREPAID_BLOCK, §5), ou elle revend des billets du transporteur en dépôt (COUNTER_CONSIGNMENT).

**Exceptions réelles (H).** Retard ou panne : remplacement de véhicule, changement de gare de départ, bus complet à un arrêt intermédiaire, voyageur qui arrive après la fermeture de l'embarquement.

### 4.3 Train

**Flux observé.** Camrail exploite la ligne Douala–Yaoundé. L'achat de billets par Orange Money et MTN Mobile Money est annoncé comme possible, et une billetterie électronique est annoncée (S, presse non datée ; à vérifier auprès de Camrail). L'express a été relancé après 2016 ; en novembre 2024, la presse indique que seule la ligne Douala–Yaoundé a un train express qui dessert certaines gares seulement (S). Les interruptions de trafic existent (S, 2022).

**Flux agence (H).** Les billets sont achetés au guichet ou en ligne ; l'agence peut en revendre en dépôt (COUNTER_CONSIGNMENT) ou acheter des places (PREPAID_BLOCK). Le tarif dépend de la classe. Les horaires peuvent changer (SupplierEvent `schedule_changed`).

**Exceptions réelles (S et H).** Suspension de la ligne : remboursement intégral ou report, selon la règle de l'opérateur. Changement d'horaire : alerte aux voyageurs, nouvel itinéraire ou remboursement.

### 4.4 Bateau (ferry, liaison maritime)

**Flux observé.** Une liaison Douala–Malabo–Bata est citée dans un guide de voyage non daté, avec une durée d'environ 12 h (S, à confirmer ; son fonctionnement actuel n'est pas établi). Une liaison Limbe–Calabar hebdomadaire est citée par un agrégateur, sans date de mise à jour (S, obsolète). Les horaires et les exploitants actuels n'ont pas été trouvés.

**Flux agence (H).** Billet vendu au bureau de l'exploitant ou à l'agence ; billet avec le nom du passager et, si un véhicule voyage, sa plaque ; manifeste transmis au port. Le départ dépend de la météo : une annulation pour raison de mer entraîne un remboursement intégral ou un report.

**Ce qui est propre au bateau.** Documents de voyage pour une liaison internationale ; véhicule rattaché au passager ; annulation pour raison de sécurité, traitée par l'exploitant.

### 4.5 Hôtel, transfert, location, assurance

Ces modes suivent les mêmes principes : un engagement (réservation), un titre (bon d'hôtel, billet de transfert, contrat de location, certificat d'assurance), des règles d'annulation par heure. Ils ne changent pas le modèle ; ils ajoutent des champs au schéma du mode. Aucun flux spécifique n'a été recherché dans cette passe.

## 5. Modèles de règlement

La conséquence comptable dépend du modèle. Le journal ([03](03-modele-de-donnees-et-invariants.md) §4) n'accepte que ces écritures ; le modèle est choisi par fournisseur.

| Modèle | Ce qui se passe | Effet comptable principal | Exemples probables |
|---|---|---|---|
| **BSP_REMITTANCE** | Vente au nom de l'agence ; le fournisseur est réglé par la remise périodique | Dette BSP à la vente ; règlement à la remise | Compagnies aériennes (S : IATA, remises hebdomadaires ou bimensuelles) |
| **CONSOLIDATOR_ACCOUNT** | Compte chez un consolidateur, rechargé par virement | Débit du compte à l'émission ; dette = prix net | Aérien, sans accréditation (S) |
| **DIRECT_INVOICE** | Le fournisseur facture l'agence | Dette fournisseur à l'échéance de la facture | Partenaires contractuels (H) |
| **PREPAID_BLOCK** | L'agence achète un quota de places à l'avance | Actif « stock de places » ; charge à chaque place vendue ; invendu restitué ou perdu selon contrat | Cars et trains (H) |
| **COUNTER_CONSIGNMENT** | L'agence vend les billets du transporteur et reverse le cash, moins sa commission | Dette fournisseur = encaissé − commission ; billets invendus rendus | Cars et bateaux (H) |
| **COMMISSION_ONLY** | Le fournisseur encaisse tout et verse une commission | Produit commission à la réception du relevé | Plateformes et agrégateurs (H) |

**Conséquence.** Le journal de [03](03-modele-de-donnees-et-invariants.md) §4.3 ne couvre que BSP et consolidateur. Il faut ajouter les quatre autres modèles, et un type de stock (places ou titres en dépôt) qui n'est pas une vente.

## 6. Corrections proposées aux documents

| Document | Correction |
|---|---|
| [03](03-modele-de-donnees-et-invariants.md) §2 | Remplacer `Booking` et `TravelDocument` par : **Offre** (produit d'un fournisseur), **Engagement** (référence chez le fournisseur, état, délai), **Titre** (numéro, émetteur, schéma de numérotation), **Segment**, **Quota**, **RèglesAnnulation**, **ÉvénementFournisseur** |
| [03](03-modele-de-donnees-et-invariants.md) §4.3 | Ajouter les six modèles de règlement (§5) |
| [03](03-modele-de-donnees-et-invariants.md) §3 | Machine d'état par mode, à partir d'un vocabulaire commun (§7) |
| [01](01-cahier-des-charges.md) F-TRA | Ajouter le canal et le règlement par fournisseur ; les quotas ; les règles d'annulation par plage horaire ; les événements fournisseur |
| [06](06-validation-terrain-et-demarrage-a-chaud.md) | Ajouter des questions par mode (§9) |
| [00](00-glossaire-et-conventions.md) | Ajouter : engagement, titre, quota, canal, modèle de règlement, événement fournisseur |

### 6.1 Identifiants de titre

Un titre n'a pas un format universel. Il se décrit par trois éléments : **émetteur**, **schéma de numérotation**, **numéro**. Exemples : un billet aérien est identifié par le code compagnie suivi d'un numéro de série (S, guide Trams ; la numérotation complète est décrite par IATA) ; un billet de car, un titre de train ou de bateau a un schéma propre à l'exploitant, à recenser avec les pilotes (H). Le schéma est une donnée de configuration, pas une règle codée.

## 7. Vocabulaire commun des états

Une commande passe par les mêmes étapes, quel que soit le mode :

`proposée → acceptée → engagement retenu → engagement confirmé → payée (partielle ou totale) → titre émis → utilisée | non présentée | annulée | remboursée (partiel ou total)`

Les délais sont portés par l'engagement, pas par la commande :

| Mode | Engagement retenu | Confirmé | Titre émis | Délai qui fait alerte |
|---|---|---|---|---|
| Avion | PNR créé | Statut confirmé | Billet émis | Limite d'émission (TL) |
| Car | Place retenue | Paiement reçu par le transporteur | Billet remis | Expiration de la place retenue |
| Train | Place réservée | Paiement reçu | Billet remis | Heure de départ |
| Bateau | Place ou véhicule retenu | Confirmé par l'exploitant | Billet émis | Heure de départ ; alerte météo si l'exploitant la transmet |

La correspondance entre le vocabulaire commun et le vocabulaire de chaque fournisseur est une table versionnée, pas du code.

Le modèle `OTA` (OpenTravel Alliance) distingue les codes de transport Air, Rail, Bus, Boat, Private Auto et Other (S, schéma mis en miroir par un tiers). Travora reprend ces codes comme noyau du champ `mode`, avec des sous-modes configurables (car ordinaire ou VIP ; train express ou omnibus ; bateau passager ou passager et véhicule). Le modèle tarifaire NeTEx (tarifs zonaux, forfaitaires, par distance) peut servir de vocabulaire pour les tarifs de car et de train (S, documentation CEN) ; je ne recommande pas de l'implémenter.

## 8. Fournisseurs : archétypes et capacités

Un fournisseur ne déclare que les capacités qu'il offre. L'interface n'affiche jamais une action qu'il ne supporte pas.

Capacités possibles : `CATALOGUE` (lire l'offre), `HOLD` (retenir une place), `CONFIRM`, `ISSUE` (émettre un titre), `CANCEL`, `REFUND_STATUS`, `PUSH_EVENTS` (recevoir des événements), `STATEMENT_IMPORT` (importer un relevé), `PAYMENT` (accepter un paiement).

| Archétype | Exemple | Canal | Capacités typiques | Règlement | Statut |
|---|---|---|---|---|---|
| A. GDS | Amadeus (Enterprise) | API sous contrat | CATALOGUE, HOLD, CONFIRM, ISSUE, CANCEL | BSP_REMITTANCE | S : Self-Service fermé le 17 juillet 2026 ; Enterprise sous contrat |
| B. Compagnie directe sans API | Compagnie aérienne nationale (appel et paiement mobile) | Téléphone, e-mail | CONFIRM, ISSUE (manuel) | DIRECT_INVOICE ou paiement direct | S (presse) |
| C. Opérateur avec guichet | Car, train | Guichet, téléphone | HOLD (manuel), ISSUE (manuel) | PREPAID_BLOCK ou COUNTER_CONSIGNMENT | H |
| D. Plateforme avec API | Plateformes de billetterie d'autocar (Kenya, Nigeria) | API, événements | CATALOGUE, HOLD, CONFIRM, ISSUE, CANCEL, PUSH_EVENTS | COMMISSION_ONLY ou CONSOLIDATOR_ACCOUNT | S ; aucune plateforme de ce type confirmée au Cameroun |
| E. Fichier d'horaires | GTFS, NeTEx | Fichier | CATALOGUE (horaires seulement) | — | S |
| F. Agrégateur de paiement | MTN, Orange, agrégateurs | API webhook et statut | PAYMENT | Encaissement direct chez l'agence | V (voir [05](05-integrations-et-canaux.md)) |

**Règle de conception.** Un connecteur implémente un contrat : une capacité déclarée = une implémentation testée. Un archétype B ou C ne demande aucune API : la capacité `ISSUE` y est une saisie guidée ou un import, avec la même traçabilité.

## 9. Éventualités → mécanisme

La personnalisation passe par quatre mécanismes, dans cet ordre de préférence :

1. **Donnée** : un champ, un schéma, une valeur de liste. Aucune modification de code.
2. **Règle versionnée** : frais, taxes, pénalités, seuils d'alerte. Conditions limitées au mode, au fournisseur, à la date, au montant et au délai avant le départ. Chaque règle a une date d'effet.
3. **Workflow à étapes prédéfinies** : une liste fermée de types d'étapes (validation par le gérant, paiement, envoi, relance). L'agence assemble l'ordre, elle n'écrit pas de code.
4. **Connecteur** : un nouveau fournisseur ou un nouveau canal, écrit et revu par le fondateur, testé par contrat.

Il n'y a aucun code fourni par le client. Une éventualité qui n'entre dans aucun de ces mécanismes est une demande de nouvelle version, pas une exception.

| Éventualité | Exemple réel | Mécanisme |
|---|---|---|
| Nouveau mode (covoiturage, hélicoptère, bus de nuit) | Une agence ajoute un service | Donnée : nouveau mode et schéma |
| Fournisseur sans API | Un car vendu au guichet | Archétype C : saisie guidée, import de relevé |
| Fournisseur qui devient une API | Une compagnie ouvre une interface | Nouveau connecteur ; l'ancien canal reste en secours |
| Annulation par le transporteur | Bateau annulé pour raison de mer | `ÉvénementFournisseur` (annulation) → workflow : report ou remboursement intégral |
| Changement d'horaire | Train avancé de vingt minutes | `ÉvénementFournisseur` (horaire) → alerte aux voyageurs concernés |
| Pénalité qui varie selon l'heure | 10 % à 48 h, 50 % à 2 h | Règle versionnée à plages horaires |
| Remplacement de véhicule | Car de moindre capacité | Événement (véhicule) ; le nombre de places du quota est recalculé |
| Correspondance manquée | Car arrivé en retard pour un avion | Alerte de rupture ; garantie selon A6 |
| Taxe ou TVA modifiée | Changement de taux | Taux versionné par date d'effet |
| Devise étrangère | Billet international en EUR | Taux figé à la saisie |
| Quota épuisé | Plus de places pour le car de 14 h | Blocage ou alerte selon la règle de l'agence |
| Fournisseur injoignable | API en panne | Mode dégradé : saisie manuelle ; événements mis en file |
| Fournisseur change ses codes | Nouveau code de compagnie | Table de correspondance versionnée |
| Billet à nom mal orthographié | Erreur de saisie | Correction tracée (nouvelle version), jamais une réécriture |
| Voyageur change de date | Échange | Nouveau titre lié à l'original ; contre-écriture de la différence |
| Remboursement partiel | Voyageur ne prend que l'aller | Contre-écriture partielle |
| Agence ferme ou change de propriétaire | Fin d'activité | Export complet ; lecture seule |

## 10. Risques propres à cette ambition

- **Dispersion** : chaque mode ajoute des règles et des exceptions. Le critère du risque R15 ([04](04-conformite-et-risques.md) §4) s'applique : un mode n'entre au périmètre qu'avec des volumes réels chez un pilote.
- **Sources de vérité multiples** : un billet existe chez le transporteur, dans Travora, et chez le client. Travora doit dire laquelle fait foi (le transporteur pour l'état du titre, Travora pour le règlement).
- **Dépendance aux données du transporteur** : sans API, l'état réel n'est connu que par saisie ou import. Les rapprochements sont alors plus lents.
- **Responsabilité** : la correspondance, l'annulation et le remboursement engagent l'agence. La politique doit être écrite dans les conditions de vente de l'agence.
- **Réglementation du transport** : agrément, autorité de régulation et règles d'identification des voyageurs n'ont pas été recherchés dans cette passe.

## 11. Entretiens à ajouter (pour la vérification de terrain)

Par mode, à poser en plus de [06](06-validation-terrain-et-demarrage-a-chaud.md) :

- **Car** : Comment réservez-vous une place ? Y a-t-il des sièges numérotés ? Quelle pièce d'identité est demandée ? Quelle est la règle d'annulation, à quelles heures ? Qui garde l'argent si un car ne part pas ?
- **Train** : Quels canaux de vente utilisez-vous ? Les billets électroniques existent-ils ? Qui rembourse une suspension ?
- **Bateau** : Quelles liaisons vendez-vous ? Les billets portent-ils le nom du passager, la plaque du véhicule, les deux ? Comment sont traitées les annulations pour raison de mer ?
- **Tous** : Qu'avez-vous déjà perdu par une annulation non prévue ? Quel document vous montre que quelqu'un a payé ?

## 12. Ordre des étapes

1. Lever les ambiguïtés A1 à A7 (§2).
2. Entretiens par mode (§11), avec 10 billets réels anonymisés par mode.
3. Vérifier les points « non établi » : billetterie actuelle de Camrail, noms des compagnies d'autocar et leurs canaux, liaisons maritimes actuelles.
4. Écrire l'ADR-0001 et appliquer les corrections du §6.
5. Ce n'est qu'après cela que l'ossature multimodale est écrite.

## 13. Sources

- Camrail, billetterie électronique et mobile money (S) : https://www.digitalbusiness.africa/cameroun-camrail-annonce-sa-plateforme-numerique-dachat-de-billets/
- Camrail, express Douala–Yaoundé, historique et interruptions (S) : https://www.businessincameroon.com/transport/1302-9965-camrail-to-restart-the-yaounde-douala-train-service-in-april-2020 ; https://ecomatin.net/camrail-suspend-le-trafic-entre-douala-et-yaounde-a-cause-dun-incident-sur-la-voie-ferree
- Compagnie aérienne nationale, paiement par mobile money (S) : https://www.digitalbusiness.africa/cameroun-les-clients-de-camair-co-peuvent-payer-leur-billet-davion-par-mtn-mobile-money-et-orange-money/ ; https://www.camer.be/76033/12:1/cameroun-camair-co-les-billets-davions-desormais-accessibles-par-mobile-money-cameroon.html
- Cars VIP et mobile money (S) : https://www.camer.be/76033/12:1/economie
- Plateformes de billetterie d'autocar (S) : https://techcabal.com/2024/04/30/buupass-acquires-quickbus/ ; https://vc4a.com/ventures/9jabus/?lang=es
- Paiement d'API pour le mobile money (S) : https://opensourcelab.dfki.de/cases/khenz
- Liaisons maritimes (S, non actuelles) : https://www.rome2rio.com/s/Limbe/Lagos ; https://www.horizonsunlimited.com/hubb/sub-saharan-africa/nigeria-to-cameroon-84198
- OpenTravel, messages et codes de transport (S) : https://www.autorentalnews.com/73209/opentravel-alliance-releases-2010b-implementation-guide ; https://opentravel.org/opentravel-messaging-business-functionality/
- NeTEx, tarifs (S) : https://netex-cen.eu/group/comparison-with-other-standards/
