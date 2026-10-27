# 12 — Plan recentré : les 60 prochains jours

Version 1, 27 octobre 2026. Ce document recentre le plan sur le MVP le plus petit qui peut convaincre trois agences de payer et d'utiliser l'outil. Il applique les règles du cadrage du fondateur (un seul plan payant, pas de connecteur, pas de moteur de réservation, modes autres que l'aérien seulement sur demande de pilote). Il complète [01](01-cahier-des-charges.md) et ne le remplace pas : les exigences hors MVP y restent, classées P2 ou P3.

Légende des preuves : **V** primaire officielle ; **S** secondaire ; **?** non établi.

## 1. Problème central, en une phrase

Le gérant d'une agence de billetterie de Douala ou Yaoundé ne sait pas, à tout moment, combien ses clients lui doivent ni ce qu'il a réellement gagné sur chaque dossier, parce que l'information est éparpillée entre WhatsApp, Excel, le GDS et un cahier — et que chaque dossier doit être retapé à chaque étape.

## 2. Le douleur la plus fréquente et la plus coûteuse

Trois douleurs, classées par fréquence observée dans les entretiens préparatoires ([06](06-validation-terrain-et-demarrage-a-chaud.md)) et par coût. Le classement est mon hypothèse, à confirmer en entretien.

1. **Retaper et perdre le fil** : le même dossier est saisi dans le GDS, dans Excel et sur WhatsApp. C'est la double saisie.
2. **Ne pas savoir qui doit quoi** : le solde client est dans la tête de l'agent, et les paiements Mobile Money se perdent.
3. **Ne pas voir la marge** : le prix d'achat, les frais et la commission ne se rejoignent jamais.

Le MVP attaque 1 (par le collage), 2 (par le solde calculé) et 3 (par la marge). La relance et l'envoi du devis passent par WhatsApp, sans API.

## 3. Ce que le MVP contient

| Brique | Contenu minimal |
|---|---|
| Clients et passagers | Un client payeur ; un ou plusieurs passagers par dossier ; nom tel que sur le document ; téléphone |
| Dossier | Un dossier, un client, des lignes (billet, frais, autre), des paiements, un solde |
| Devis | Versions figées à l'envoi ; PDF avec logo ; date de validité ; envoi par lien WhatsApp |
| Lignes | Type : **billet aérien** (avec numéro, saisi ou collé) ou **prestation libre** (libellé, coût, prix de vente) |
| Paiements | Espèces, virement, Mobile Money : référence obligatoire, pas d'API |
| Coût et marge | Coût fournisseur et frais par ligne ; marge calculée ; jamais visible pour le rôle agent |
| Solde | Calculé à partir des paiements et des lignes ; jamais saisi |
| Tableau de bord | Quatre chiffres : dossiers en cours ; ce que les clients doivent ; marge encaissée ; dossiers à risque |
| Alertes | Trois alertes seulement : solde impayé au-delà de N jours ; départ dans moins de 7 jours avec solde non nul ; devis expiré |
| Rôles | Deux rôles : gérant (tout voir) et agent (sans coût ni marge) |
| Démarrage | Saisie guidée par le fondateur de 10 à 20 dossiers ouverts par pilote ; pas d'importeur |

**Collage de billet** : l'agent colle le texte du PNR ou de l'e-ticket. L'application pré-remplit le numéro de billet et les noms par des règles simples ; l'agent confirme. Le texte brut est conservé. Pas d'analyse automatique avant d'avoir vingt exemples réels par pilote.

## 4. Ce qu'on refuse de construire maintenant, et le déclencheur

| Refusé | Pourquoi | Déclencheur concret pour l'envisager |
|---|---|---|
| Connecteurs fournisseurs, webhooks, API GDS | Contrats, maintenance, temps | Un fournisseur avec contrat signé et au moins 30 % du volume d'une agence pilote |
| API Mobile Money pour l'encaissement | La saisie manuelle avec référence suffit au MVP | Au moins trois agences payantes et un volume de rapprochements manuels mesuré à partir des données réelles |
| API WhatsApp Business | Coût, vérification d'entreprise, modèles de messages | Trois agences payantes et une grille tarifaire du Cameroun lue (voir [05](05-integrations-et-canaux.md) §3) |
| Quotas, plans de sièges, schémas par mode | Complexité sans preuve de besoin | Un pilote qui vend des places en volume et fournit dix exemples de titres |
| Modes autres que l'aérien, en tant que modules | Pas de volume prouvé | Un pilote qui fait au moins 20 % de ses dossiers hors aérien, sur deux mois |
| Plusieurs succursales | Une agence pilote n'en a pas besoin | Un pilote multi-sites |
| Facture fiscale et e-facturation | Texte DGI non disponible ; avis fiscal en attente (R16) | Spécification publiée et avis écrit d'un fiscaliste |
| Parseur automatique | Formats hétérogènes, risque d'erreur | Vingt exemples réels par pilote et un taux de correction mesuré |
| Import Excel générique | Coût élevé pour un usage ponctuel | Trois pilotes ayant chacun plus de 50 dossiers historiques à reprendre |
| Règles configurables (frais, pénalités) | Dette technique avant besoin | Deux agences qui demandent deux règles différentes et documentées |
| Niveau 3 (réservation temps réel multi-fournisseurs) | Hors périmètre jusqu'à preuve écrite | Décision écrite du fondateur après trois pilotes actifs |
| Plusieurs plans tarifaires | Pas de données d'usage | Trois mois de données d'usage de trois agences |

## 5. Compromis à valider : la prestation libre

La règle « modes non aériens seulement sur demande de pilote » a un défaut réel : un gérant qui vend aussi un transfert ou une chambre d'hôtel avec son billet ne peut pas calculer son solde si ces lignes n'existent pas. Il revient alors à son cahier, et l'outil est abandonné.

**Proposition** : une ligne de type « prestation libre » (libellé, coût, prix de vente, date) sans logique propre. Elle ne parse rien, ne gère ni quota ni statut, et n'entre dans aucun module. Elle sert seulement à ce que le solde et la marge soient justes.

C'est une exception à la règle du cadrage. **Je la recommande, mais elle relève de ta décision.**

## 6. Ordre de construction

Un seul développeur. Chaque semaine finit par quelque chose d'utilisable, testé et montré à un pilote.

| Semaines | Livrable | Critère de passage |
|---|---|---|
| 1 à 2 | Socle : Django 6.1, PostgreSQL, deux agences de test, dossier, client, passager, lignes, journal | Tests d'isolation entre agences passent ; le journal refuse toute modification (§7) |
| 3 | Devis : versions figées, PDF, lien WhatsApp | Un devis PDF produit en moins de deux secondes ; lien wa.me testé sur téléphone réel |
| 4 | Paiements, soldes, marge, tableau de bord à quatre chiffres | Solde calculé = somme des écritures ; un pilote saisit dix dossiers réels de bout en bout |
| 5 | Collage de billet, alertes (trois), rôles (deux) | Un pilote colle un vrai e-ticket et corrige moins de deux champs |
| 6 | Mise en production pour trois pilotes, sauvegarde et restauration testées | Hébergement décidé (R4) ; restauration réussie sur une base vierge |
| 7 à 8 | Usage réel : démarrage à chaud, support, corrections | Au moins deux pilotes ont saisi la semaine complète à plus de 70 % |

**Arrêts** :
- Fin semaine 4 : aucun pilote n'a saisi de dossier réel → on arrête le développement et on revoit le problème avec les pilotes.
- Fin semaine 8 : moins de deux pilotes utilisent l'outil à plus de 70 % → on arrête les nouvelles fonctions et on diagnostique.
- Jour 90 : moins de trois agences paient → on revoit le segment ou le prix, pas les fonctions.

**Limite de pilotes** : trois au maximum pour un fondateur seul. Quatre ou cinq seraient le plafond.

## 7. Comment faire : ce que disent les documentations officielles

| Besoin | Source officielle consultée | Ce qu'elle dit | Verdict | Conséquence |
|---|---|---|---|---|
| Version de Python | Documentation Django 6.1, FAQ d'installation | Django 6.1 supporte Python 3.12, 3.13, 3.14 et 3.15 (ajouté en 6.1.3) | **V** | Python 3.14, déjà installé en local, convient |
| Base de données | Documentation Django, bases supportées | PostgreSQL 15 et plus ; psycopg 3.1.12 ou plus | **V** | PostgreSQL 15 minimum |
| Invariants en base | Documentation Django, contraintes | `UniqueConstraint` avec `condition` et `CheckConstraint` sont créées dans la base ; la validation applicative passe par `validate()` | **V** | Unicité de la référence de paiement par agence, et montants positifs, en contrainte de base |
| Cloisonnement | Documentation PostgreSQL, RLS | Politique absente = refus par défaut ; `FORCE ROW LEVEL SECURITY` pour le propriétaire ; superutilisateurs et `BYPASSRLS` contournent la RLS ; unicité et clés étrangères la contournent aussi | **V** | Rôle applicatif sans `BYPASSRLS` ; `FORCE` activé ; attention aux canaux cachés de la contrainte d'unicité |
| Devise | Liste officielle ISO 4217 (SIX, publiée le 17 septembre 2026) | XAF : nom « CFA Franc BEAC », code numérique 950, unité mineure **0** | **V** | Montants en entiers, sans décimales. Les centimes existent historiquement mais ne se saisissent pas |
| PDF | Documentation WeasyPrint | Python 3.10 ou plus, Pango 1.44 ou plus ; polices à installer, ou `@font-face` avec `FontConfiguration` ; lent sur de longs documents, à garder dans un processus persistant | **V** | Devis court : pas de problème. Polices embarquées. Génération en tâche de fond si la file grossit |
| Lien WhatsApp | Documentation officielle WhatsApp | Page d'aide non atteinte. Source tierce : `https://wa.me/<numéro international sans +>?text=<texte encodé>` ; le message reste modifiable par le client | **S** | À confirmer sur la page officielle avant mise en production. Principe : le message est un texte prérempli, pas un envoi |
| Numéro de billet aérien | Résolution IATA 722 | Non atteinte. Sources secondaires : 13 chiffres avec un préfixe de 3 chiffres pour le code compagnie | **S** | Règle de pré-remplissage seulement ; la vérification du chiffre de contrôle est à faire sur la résolution |
| Coupons par billet électronique | Politique d'une compagnie citant la Résolution 722f | Quatre coupons de vol au maximum par numéro (une compagnie) | **S** | Une ligne de billet peut avoir jusqu'à quatre segments ; à confirmer pour les autres compagnies |
| Frais Mobile Money | Pages tarifaires des fournisseurs ([05](05-integrations-et-canaux.md) §2) | Campay 2 % à l'encaissement (V, fournisseur) ; MTN « between 1% » (◐) ; Notch Pay non publié (V) | **V** / **◐** | Pas d'intégration au MVP : le tarif sert seulement au calcul de l'abonnement |
| Remise BSP | Document IATA « Recent changes to BSP remittance rules » | Marchés hebdomadaires : cinq jours ouvrés ou sept jours calendaires | **V** | Le MVP ne fait pas de rapprochement BSP ; il enregistre la date de vente |

**Points techniques restant à faire confirmer dans leur documentation avant le code** :

- Les règles d'append-only sur la table du journal : `REVOKE UPDATE, DELETE` au rôle applicatif, à vérifier dans la documentation PostgreSQL sur `GRANT` ;
- L'équilibre débit/crédit d'une transaction : une contrainte différée, à vérifier dans la documentation PostgreSQL sur `CREATE TRIGGER` et `CONSTRAINT`, ou une validation applicative testée par propriétés. Je recommande les deux.

## 8. Ambiguïtés qui bloquent vraiment le démarrage du code

Quatre seulement. Les questions juridiques et commerciales attendent (voir §9).

1. **Django 6.1 ou 5.2 LTS** : je recommande 6.1 (support régulier jusqu'en avril 2027, vérifié). Confirmation attendue.
2. **Prestation libre** (§5) : oui ou non.
3. **Deux rôles seulement** au MVP : oui ou non.
4. **Dépôt** : nom et compte GitHub. Pas de commit sans ton accord.

## 9. Ce qui attend, sans bloquer le code

- Hébergement : décision juridique avant toute donnée de pilote réelle (R4). Le développement se fait en local.
- Avis fiscal sur les abonnements (R16) et sur les billets : avant la première facturation.
- Texte officiel de la loi 2024/017 : avant le premier pilote.
- Comptes développeur MTN et Campay, créés par toi : pour la phase 2 seulement.
- Recherche d'antériorité OAPI du nom : avant tout investissement d'identité visuelle.

## 10. Lien avec les autres documents

- Le plan recentré ne supprime pas [11](11-flux-reels-par-mode-et-plateforme.md) ni l'[ADR-0001](adr/ADR-0001-plateforme-multimodale-connecteurs.md) : ils décrivent la cible à long terme. Le MVP ne les implémente pas.
- Les exigences de [01](01-cahier-des-charges.md) restent valables, mais sont classées P2 ou P3 quand elles dépassent le MVP décrit ici.
- Les entretiens de [06](06-validation-terrain-et-demarrage-a-chaud.md) doivent porter d'abord sur la douleur n° 1 et la marge (§2).
