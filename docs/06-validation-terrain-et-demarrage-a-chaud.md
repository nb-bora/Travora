# 06 — Validation terrain, pilotes et démarrage à chaud

Rien dans ce dossier n'a encore été confronté à une agence réelle. Ce document organise cette confrontation et fixe des seuils de décision, proposés par moi et à ajuster.

## 1. Compter le marché (semaines 1 à 2)

Aucun chiffre fiable du nombre d'agences camerounaises n'a été trouvé.

1. Sources : liste IATA des agents du Cameroun (filtrage par pays), agréments du ministère du Tourisme et des Loisirs (MINTOUL), annuaires professionnels, repérage terrain à Douala et Yaoundé.
2. Objectif : un tableau de 100 agences qualifiées (nom, ville, accréditation IATA ou non, GDS utilisé, nombre d'agents, source d'approvisionnement : BSP, consolidateur, compagnie directe).
3. Appel de qualification de 3 questions : combien de billets par mois ? émettez-vous vous-mêmes ou via un consolidateur ? comment suivez-vous les soldes clients ?
4. Seuil : moins de 25 agences adressables qualifiées (au moins 30 dossiers par mois) : revoir segment ou prix avant de coder.

## 2. Entretiens (semaines 1 à 4)

**Cible** : le gérant, pas l'agent. Dix entretiens d'une heure, dont au moins trois agences qui passent par un consolidateur et au moins une qui est consolidateur ou grande agence revendant à des sous-agences (hypothèse à tester : leur douleur de créances est plus aiguë).

**Méthode** : demander à voir le dernier dossier de bout en bout, sans collecter de documents personnels inutiles ; ne pas présenter le produit avant la fin.

### Questions classées par priorité

| Priorité | Question | Ce qu'elle décide |
|---|---|---|
| 🔴 | Montrez-moi votre dernier dossier, de la demande au billet. Où chaque information se trouve-t-elle ? | Sources de données à ingérer, double saisie réelle |
| 🔴 | Combien de clients vous doivent de l'argent aujourd'hui ? Comment le savez-vous ? | Valeur du suivi des soldes |
| 🔴 | Quand avez-vous perdu de l'argent la dernière fois (frais oubliés, marge négative, impayé) ? Combien ? | Valeur récupérée, prix |
| 🔴 | Qui connaît votre marge ? Voulez-vous que vos agents la voient ? | Permissions par champ |
| 🟠 | Émettez-vous avec Amadeus ou un autre GDS ? Avez-vous activé l'interface comptable (fichier AIR) ? | Option 3 d'ingestion |
| 🟠 | Comment payez-vous votre fournisseur (BSP, consolidateur) ? À quelle fréquence ? | Rapprochement fournisseur |
| 🟠 | Comment vos clients paient-ils (espèces, virement, MTN, Orange) ? Quel numéro encaisse ? | Paiements, rapprochement |
| 🟠 | Avez-vous un compte marchand Orange Money ou MTN, ou passez-vous par un agrégateur ? Depuis combien de temps, et combien de temps a pris l'approbation ? | Orange exige une approbation de la banque centrale (R17) ; délais réels |
| 🟠 | Qui fait votre comptabilité ? Que vous demande-t-il ? Comment traitez-vous la TVA sur les billets ? | Export comptable, traitement fiscal |
| 🟠 | Quels modes vendez-vous (avion, bus, train, bateau, hôtel…) et dans quelles proportions ? Montrez-moi un billet de bus ou de train type | Ordre des parseurs, schémas de champs par mode |
| 🟠 | Êtes-vous revendeur de billets de transport, ou compagnie qui vend ses propres places ? | Frontière avec le module d'inventaire (phase 3) |
| 🟡 | Quels outils payez-vous aujourd'hui ? Combien ? | Prix de référence |
| 🟡 | Combien paieriez-vous pour résoudre ce problème ? Seriez-vous prêt à payer un pilote ? | Prix, engagement |
| 🟢 | Quelle est la connexion Internet de l'agence ? Quels appareils ? | Contraintes techniques |

### Critères de décision à la fin de la semaine 4

| Résultat | Décision |
|---|---|
| Au moins 3 agences acceptent de payer un pilote (même 10 000 FCFA) et de confier leur historique réel | Passer au MVP |
| Moins de 2 sur 10 paient quoi que ce soit | Ne pas coder : revoir le segment (consolidateurs, voyages d'affaires) ou le problème |
| Douleur dominante = créances et soldes | Prioriser journal et relances |
| Douleur dominante = saisie des dossiers | Prioriser collage de PNR et transfert d'e-mail |

## 3. Démarrage à chaud (onboarding d'une agence pilote)

Principe : importer le **vivant** (dossiers ouverts et soldes d'ouverture), pas l'archive. Les dossiers dont le départ est dans les 90 jours ou dont le solde est non nul sont repris ; le reste reste dans l'ancien outil, consultable.

### 3.1 Sources, par rentabilité décroissante

1. Excel ou CSV avec assistant de correspondance de colonnes, mémorisé par agence.
2. Texte de PNR ou d'e-ticket collé.
3. PDF d'e-ticket.
4. Export de conversation WhatsApp joint au dossier comme pièce, sans analyse automatique au début.

### 3.2 Garanties

- Aperçu avant validation.
- Chaque import est un lot identifié et annulable.
- Idempotence : une empreinte par ligne évite les doublons en cas de ré-import.
- Rapport des lignes rejetées, corrigible.
- Soldes d'ouverture enregistrés comme écritures du journal (le journal reste en ajout seul).

### 3.3 Réconciliation avant bascule

1. Totaux des soldes clients et des dettes fournisseurs dans Travora égaux à ceux du tableur de l'agence, au franc près.
2. Deux semaines en parallèle avec l'ancien outil.
3. Bascule signée par le gérant.

### 3.4 Indicateur principal

Part des nouveaux dossiers du mois créés dans Travora : **au moins 80 % à la semaine 4** ; moins de 50 % à la semaine 3 : diagnostic de friction avant toute nouvelle fonction.

## 4. Plan de 90 jours révisé

| Période | Contenu | Sortie attendue |
|---|---|---|
| Jours 1 à 30 | Comptage du marché, 10 entretiens, décisions D1 à D6 (voir cahier des charges), avis juridique sur l'hébergement, recherche d'antériorité du nom, autorisation FairFare si réutilisation de code. Aucun code produit sauf un prototype jetable | Décision de passer ou non au MVP |
| Jours 31 à 60 | MVP réduit (voir cahier des charges §4), déploiement chez 3 à 5 pilotes avec démarrage à chaud, tests d'intrusion inter-agences et de restauration | Pilotes utilisant le produit |
| Jours 61 à 90 | Mesure du temps gagné et de l'argent récupéré, rapport mensuel « valeur récupérée », première facturation d'abonnement, décision sur la phase 2 | Chiffres pour décider |

## 5. Indicateurs de suivi

| Indicateur | Cible | Fréquence |
|---|---|---|
| Part des nouveaux dossiers saisis dans Travora | ≥ 80 % à la semaine 4 | Hebdomadaire |
| Écart de réconciliation (trésorerie, créances, dettes) | 0 | Quotidien |
| Valeur récupérée / prix de l'abonnement | ≥ 3 | Mensuelle |
| Taux de correction manuelle du parseur par champ | Mesuré, à réduire | Hebdomadaire |
| Temps de support par pilote | ≤ 20 % du temps du fondateur au total | Hebdomadaire |
| Restauration de sauvegarde testée | Réussie chaque mois | Mensuelle |
| Incident d'isolation inter-agences | 0 | Continu |
