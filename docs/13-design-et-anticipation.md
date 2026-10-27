# 13 — Interface et moteur d'anticipation

- **Statut** : proposition de conception, à valider. Rien de ce document n'est construit.
- **Pour qui** : le fondateur et la personne qui développera l'interface.
- **Liens** : [architecture](architecture.md), [ADR-0003](adr/ADR-0003-stack-et-architecture-technique.md), [04 conformité](04-conformite-et-risques.md).

## 0. Ce qui est vérifié, ce qui est proposé, ce qui bloque

- **Vérifié** : les contrats de chaque module (dossiers, lignes, paiements, devis, tableau de bord) existent et sont testés. L'interface s'appuie sur les façades `services/public.py` sans rien contourner.
- **Proposé** : tout le reste (design, moteur, flux). Les références à Linear, Notion, Attio, Stripe, Amadeus ou Salesforce décrivent des principes de conception généraux, pas une étude de leurs écrans. Les couleurs sont à rapprocher du **logo réel de Travora**, que je n'ai pas : les codes ci-dessous sont une base cohérente (navy profond + teal), pas la charte.
- **Bloquant avant l'interface** (décision de la directive d'ingénierie) : les défauts de fond restants (agence inactive, bornes de dates et clôture de période, droits des personnes) doivent être corrigés ou acceptés. Le design peut avancer en parallèle ; le code d'interface commence après.
- **Décision juridique avant tout LLM externe** : envoyer des données de clients (noms, téléphones, soldes) à un fournisseur de modèle hébergé hors du Cameroun est un transfert de données personnelles. C'est une décision du fondateur (voir §4.7). Le moteur est donc conçu pour **fonctionner sans LLM** et accueillir un modèle ensuite.

## 1. Principes non négociables

1. **Proposer, jamais exécuter.** Une suggestion pré-remplit ; l'utilisateur confirme. Aucune écriture financière sans un geste explicite. Toute action confirmée est annulable ou se corrige par contre-passation (le journal est en ajout seul).
2. **Zéro saisie évitable.** Chaque écran part de ce que le système sait déjà : collage d'un billet, client récent, tarif habituel, mode de paiement habituel.
3. **Le déterministe d'abord, le LLM ensuite.** Les règles et les statistiques simples prédisent la plupart des besoins, de façon explicable et gratuite. Le LLM sert à ce que les règles ne savent pas faire : lire un texte libre, rédiger un message, formuler une explication.
4. **Le rôle décide de ce qui est visible, côté serveur.** Un agent ne voit ni coût ni marge, ni dans l'écran, ni dans une suggestion, ni dans ce qui est envoyé à un modèle.
5. **Discret, jamais envahissant.** Au plus une suggestion principale visible par écran ; les autres attendent dans un tiroir. Une suggestion refusée ne revient pas à l'identique de sitôt.
6. **Réseau lent d'abord.** Pages serveur légères, peu de JavaScript, polices locales, aucune dépendance bloquante à un service externe. Utilisable au pouce sur un téléphone d'entrée de gamme.
7. **Chaque suggestion s'explique en une ligne** (« Parce que 3 dossiers DLA-CDG saisis ce matin ») et se règle (« Moins de ce type »).

## 2. Système de design

### 2.1 Couleurs (jetons)

Contrastes calculés (WCAG, texte normal ≥ 4,5).

| Rôle | Clair | Sombre | Usage |
|---|---|---|---|
| Navy 900 (marque) | `#0B1F3A` | `#E6EDF5` (texte) | Titres, barre latérale |
| Navy 700 | `#16335A` | `#94A3B8` | Éléments de structure |
| Teal 600 (action) | `#0F766E` | `#5EEAD4` | Boutons principaux, liens, focus |
| Teal 400 (accent) | `#2DD4BF` | `#2DD4BF` | Fonds d'accent, texte navy dessus (8,9:1) |
| Teal 50 | `#CCFBF1` | `#0F2E2B` | Fond des suggestions |
| Fond | `#F8FAFC` | `#0B1220` | Page |
| Surface | `#FFFFFF` | `#111A2B` | Cartes |
| Bordure | `#E2E8F0` | `#223049` | Séparateurs |
| Texte | `#0B1F3A` (16,5:1) | `#E6EDF5` (15,9:1) | |
| Texte secondaire | `#475569` (7,6:1) | `#94A3B8` (7,3:1) | |
| Succès | `#15803D` sur `#DCFCE7` | | Soldé, émis |
| Attention | `#92400E` sur `#FEF3C7` | | Départ proche, coût manquant |
| Danger | `#B91C1C` sur `#FEE2E2` | | Impayé en retard, annulé |

Règle : le teal 400 ne sert jamais de couleur de texte sur fond clair (contraste insuffisant) ; sur teal 400, le texte est navy 900. Aucune information portée par la couleur seule : toujours une icône ou un mot.

### 2.2 Typographie

- Famille : **Inter** (variable, hébergée localement, sous-ensemble latin étendu pour les accents), repli `system-ui`. Pas de police distante.
- Chiffres **tabulaires** partout où l'on compare des montants (`font-variant-numeric: tabular-nums`).
- Échelle : 12 / 14 (corps par défaut) / 16 / 20 / 24 / 32. Interligne 1,5 pour le texte, 1,2 pour les titres. Titres en 600, jamais en 800.
- Montants : `1 250 000 XAF`, espace fine insécable entre les milliers, jamais de décimales (XAF n'a pas d'unité mineure).
- Dates : `27 oct. 2026`, jours relatifs quand utile (« demain », « dans 3 j »). Fuseau de l'agence.

### 2.3 Espacement, formes, ombres

- Grille de 4 px ; pas courants 8 / 12 / 16 / 24 / 32.
- Rayons : 8 px (champs, boutons), 12 px (cartes), 999 px (badges).
- Ombres : une seule élévation douce pour les cartes (`0 1px 2px rgba(11,31,58,.06)`), une pour les menus et la palette (`0 8px 24px rgba(11,31,58,.14)`). Le reste se fait par la bordure.
- Densité : deux modes, **Confort** (par défaut, lignes de 48 px) et **Compact** (36 px) pour les gérants qui parcourent beaucoup de dossiers.

### 2.4 Composants

| Composant | Règle |
|---|---|
| Bouton principal | Teal 600, texte blanc, 40 px (44 px sur mobile). Un seul par zone. |
| Bouton secondaire | Bordure, fond surface. Tertiaire : texte seul. |
| Champ | Libellé au-dessus, aide en dessous, erreur en texte + icône, jamais en rouge seul. |
| Carte | Surface, bordure, rayon 12 ; titre, valeur, détail. |
| Badge d'état | Pastille + mot : Ouvert, Soldé, En retard, À émettre, Annulé. |
| Ligne de dossier | Icône du mode (avion, bus, train, bateau, étoile pour prestation libre), libellé, passager, prix ; coût et marge seulement pour le gérant. |
| **Carte de suggestion** | Fond teal 50, bord gauche teal 600, icône d'éclair, une phrase d'action, une ligne de raison, boutons **Confirmer** / **Modifier** / **Pas maintenant**, menu « Pourquoi ? / Moins de ce type ». |
| Toast | En bas à gauche, 5 s, avec **Annuler** quand l'action est réversible. |
| Palette de commandes | `Ctrl/⌘ K` : actions, dossiers, clients, plus les suggestions en tête. Aussi accessible par une loupe sur mobile. |
| Zone de collage | Un grand champ « Collez un billet, un message WhatsApp ou un e-ticket » en tête de l'écran Aujourd'hui. |
| Tiroir latéral | Détail d'une ligne ou d'un paiement sans quitter la liste. |

### 2.5 États

- **Survol / actif** : fond +4 % de navy ; actif : −1 px de translation, pas d'animation longue. **Focus** : anneau teal 2 px, toujours visible au clavier.
- **Chargement** : squelettes gris, jamais de roue plein écran ; un bouton en cours de requête reste cliquable une seule fois (idempotence côté serveur).
- **Vide** : un dessin sobre, une phrase utile, une action (« Aucun dossier ouvert. Collez un billet pour commencer. »). Jamais une page blanche.
- **Erreur** : dit ce qui s'est passé, ce qui est conservé, quoi faire. Le texte saisi n'est jamais perdu.
- **Succès** : toast discret, la ligne concernée se met à jour en place.
- **Hors ligne / réseau lent** : bandeau « Connexion lente », les saisies restent dans le formulaire ; aucune écriture n'est considérée faite avant la réponse du serveur.
- Animations ≤ 150 ms, désactivées si `prefers-reduced-motion`.

## 3. Architecture d'interface

### 3.1 Structure globale

- **Bureau (≥ 1024 px)** : barre latérale de 232 px (navy 900, repliable en icônes), barre supérieure (recherche / palette, agence, cloche des suggestions, profil), zone principale (max 1200 px), tiroir à droite à la demande.
- **Tablette** : barre latérale repliée en icônes.
- **Mobile** : barre d'onglets en bas (Aujourd'hui, Dossiers, +, Argent, Plus). Le bouton **+** ouvre la zone de collage et les créations rapides. Listes en cartes, pas en tableaux.
- Navigation : 5 entrées pour un agent (Aujourd'hui, Dossiers, Clients, Devis, Encaissements), 2 de plus pour le gérant (Argent : soldes et marges ; Journal et audit).

### 3.2 Les six écrans du MVP

1. **Aujourd'hui** (accueil). En haut, la zone de collage. Dessous : la carte de suggestion principale ; les quatre chiffres du gérant (créances, marge encaissée, dossiers ouverts, départs sous 7 jours) ; les trois alertes ; « À faire aujourd'hui », liste priorisée (départs demain non émis, impayés en retard, devis qui expirent). Pour un agent : mêmes blocs sans marges.
2. **Dossiers**. Liste filtrable par vues enregistrées (Ouverts, Départs sous 7 jours, À émettre, Impayés, Clos) ; colonnes : référence, client, trajet, départ, prix, solde, état. Recherche instantanée. Sélection multiple pour actions groupées. Le tiroir montre le dossier sans quitter la liste.
3. **Dossier** (détail). En-tête : client, référence, état, solde dû en grand. Colonne centrale : lignes (avion, bus, train, bateau, prestation) puis paiements puis devis, en frise chronologique. Colonne droite : actions possibles selon l'état (Ajouter une ligne, Encaisser, Émettre, Envoyer le devis, Clore, Rouvrir [gérant]). Le gérant voit coût et marge par ligne ; l'agent ne voit que les prix.
4. **Clients**. Liste, fiche (téléphone au format international, dossiers, solde cumulé, dernier contact) et bouton de relance pré-rempli.
5. **Devis**. Liste par état (brouillon, envoyé, accepté, expiré) ; éditeur de lignes ; aperçu du PDF ; bouton « Envoyer par WhatsApp » (lien `wa.me` pré-rempli). Un devis envoyé est figé, la modification crée une version.
6. **Encaissements et soldes** (gérant : **Argent**). Saisie rapide d'un paiement (mode, montant, référence), liste des créances par ancienneté (0-7, 8-30, 30+ jours), écritures du journal en lecture. Gérant seulement : marges.

### 3.3 Rester léger malgré l'intelligence

- Les suggestions sont un **fragment HTML** chargé après le contenu principal (`hx-trigger="load"`) : si le moteur est lent ou hors service, la page reste complète.
- Zéro appel à un LLM pendant un affichage de page. Le LLM n'intervient que sur un geste (coller un texte, demander un brouillon) et se charge en arrière-plan avec un indicateur.
- Un seul fragment de suggestion par écran, quelques centaines d'octets.

## 4. Moteur d'anticipation

### 4.1 Idée directrice

Un **moteur de suggestions** qui produit des propositions typées (« créer ce dossier », « relancer ce client », « répéter ce tarif »), chacune avec une action pré-remplie, une raison, un score et un rôle autorisé. Trois sources, par ordre de préférence :

1. **Règles métier** sur l'état de la base (impayé de plus de 10 jours, départ demain non émis, coût manquant). Fiables, explicables, sans apprentissage.
2. **Statistiques d'habitude** par utilisateur et par agence (fréquences, récence, heures) : trajets, tarifs, marges, modes de paiement. Simples agrégats, pas de modèle entraîné.
3. **LLM**, borné à : extraire des champs d'un texte collé, rédiger le message de relance dans le ton de l'agence, résumer « pourquoi ». Il ne décide jamais seul d'une action.

Ce que le LLM ne fait pas : écrire dans la base, voir un coût ou une marge pour un agent, contourner une confirmation.

### 4.2 Ce qui est observé (événements)

Table `assist_event` (plan de données : `agency_id`, RLS forcée, ajout seul) : `user_id`, `occurred_at`, `type`, `object_type`, `object_id`, `context` (écran, mode de transport, trajet, plage horaire, montant arrondi). Types : dossier créé, ligne ajoutée, ligne émise, paiement saisi, devis envoyé, suggestion vue / confirmée / modifiée / refusée / reportée. On **ne stocke pas** de texte libre de client ni de texte collé brut.

Ce qui existe déjà et se réutilise : le journal d'audit et le journal comptable donnent les faits financiers ; `assist_event` n'ajoute que les gestes d'usage et les réponses aux suggestions.

### 4.3 Mémoire

- **Courte** (la session) : l'écran, le dossier ouvert, les 10 derniers gestes, le contenu du presse-papiers collé. Dans la session, rien de persistant.
- **Longue** : table `assist_pattern` recalculée par une commande de gestion planifiée (pas de file de tâches, conforme à l'ADR-0003) : par utilisateur et par agence, fréquences des trajets, tarif et marge médians par trajet (marge : gérant seulement), mode de paiement habituel, heures de pointe, taux d'acceptation par type de suggestion.
- **Contrôle de l'utilisateur** : écran « Ce que Travora a appris de moi », avec « Oublier » par motif, « Tout oublier », et un interrupteur par type de suggestion. Le gérant peut désactiver l'assistant pour l'agence.

### 4.4 Types de suggestions

| Type | Déclencheur | Action pré-remplie | Rôle |
|---|---|---|---|
| **Collage** | Texte collé reconnu comme billet | Client + dossier + ligne(s) + devis | tous |
| **Répétition** | N saisies similaires récentes | Même trajet / tarif / transporteur | tous (marge visible au gérant seulement) |
| **Relance** | Solde dû > seuil de jours | Message WhatsApp pré-rempli | tous (voit le solde) |
| **Urgence** | Départ ≤ 48 h et ligne non émise ou coût manquant | Liste groupée, ouvrir en un clic | tous |
| **Encaissement** | Paiement attendu et habituel (mode, montant du solde) | Paiement pré-rempli | tous |
| **Clôture** | Solde nul, dossier ouvert | Proposer la clôture | tous |
| **Groupée** | Plusieurs suggestions du même type | Tout confirmer en un clic, avec liste | selon le type |
| **Revue de fin de journée** | Heure habituelle de fin de l'utilisateur | Liste priorisée et actions groupées | tous |

### 4.5 UX des suggestions

- **Où** : (1) la carte principale sur Aujourd'hui, sous la zone de collage ; (2) en contexte dans un dossier (bandeau fin sous l'en-tête) ; (3) la palette de commandes en tête de liste ; (4) la cloche : tiroir de toutes les suggestions en attente. Jamais de fenêtre modale, jamais de son.
- **Forme** : « Créer le dossier de **Marie Ndong** : DLA-CDG, 520 000 XAF, départ 20 nov. » ; ligne de raison ; **Confirmer** (Entrée), **Modifier** (ouvre le formulaire pré-rempli), **Pas maintenant** (Échap).
- **Confirmation** : un clic ou Entrée. Pour une action groupée, la liste est dépliée avec des cases cochées par défaut ; l'utilisateur décoche ce qu'il ne veut pas.
- **Refus** : « Pas maintenant » la reporte jusqu'au lendemain ; « Moins de ce type » baisse sa fréquence ; après 3 refus d'affilée d'un type, il passe en tiroir seulement.
- **Annulation** : après confirmation, un toast **Annuler** (dossier créé : annulable ; paiement saisi : annulation par le gérant ; écriture comptable : contre-passation, jamais effacement).
- **Raccourcis clavier** : `Entrée` confirmer, `E` modifier, `Échap` reporter, `S` suggestion suivante.

### 4.6 Garde-fous

- **Jamais d'exécution automatique.** Même la « confirmation groupée » exige un geste.
- **Rôles** : chaque suggestion est calculée avec l'acteur courant ; coût et marge n'apparaissent ni dans le texte, ni dans les valeurs pré-remplies, ni dans ce qui est transmis à un modèle pour un agent. Test automatique : un agent ne reçoit jamais un champ financier interne dans le moteur.
- **Limites de fréquence** : au plus une suggestion visible par écran ; au plus 3 notifications par jour ; aucune suggestion pendant la saisie d'un formulaire.
- **Confiance** : sous un seuil de score ou si un champ extrait est ambigu (numéro de billet à 12 chiffres, téléphone invalide), la suggestion devient une **question** (« Est-ce bien 057-2345678901 ? ») au lieu d'une proposition.
- **Données manquantes** : jamais de valeur inventée. Coût inconnu reste inconnu ; une ligne sans coût n'est pas proposée à l'émission.
- **Évaluation** : chaque type est mesuré (taux de confirmation, de modification, de refus). Un type sous 30 % de confirmation est retiré ou revu.
- **Interrupteur** par type, par utilisateur, par agence ; mode « sans LLM » toujours fonctionnel.
- **Traçabilité** : chaque confirmation produit les mêmes entrées d'audit qu'un geste manuel, plus la mention « via suggestion ».

### 4.7 Architecture technique recommandée

Un nouveau module `assistant`, dans la même forme que les autres (`models`, `selectors`, `services/commands`, `services/public`, `dto`, `exceptions`, `constants`), placé au niveau du tableau de bord, au-dessus de `quotes` :

```
web (nouvelle couche : vues, gabarits, htmx)  →  concierge | dashboard | assistant → quotes → payments → cases → …
```

- `assistant` appelle **uniquement les façades publiques** des autres modules (lecture des dossiers, soldes, devis ; exécution d'une action confirmée par la même façade qu'un geste manuel). import-linter le garantit.
- **Générateurs** : une fonction par type de suggestion, `generate(actor) -> list[Suggestion]`, pure et testable.
- **Port LLM** : une interface `LanguageModel` avec trois méthodes étroites (`extract_booking(text)`, `draft_message(context)`, `explain(suggestion)`), trois adaptateurs : `NoModel` (par défaut), un modèle hébergé, un modèle local. Entrées minimales et pseudonymisées ; sorties validées par un schéma strict (JSON) ; toute sortie hors schéma est ignorée.
- **Modèle hébergé : décision fondateur.** Il implique un transfert de données personnelles. Avant tout branchement : choix du fournisseur, lieu de traitement, contrat, information des clients de l'agence, durée de conservation (voir [04](04-conformite-et-risques.md)). Sans cette décision, `NoModel` ; l'extraction d'un billet collé se fait par l'analyseur déterministe existant (`propose_ticket_numbers`), étendu par des motifs.
- **Pas de file de tâches** (ADR-0003) : les suggestions temporelles sont calculées à l'ouverture et par une commande planifiée (par exemple toutes les 15 minutes) ; les appels LLM se font dans la requête du geste, avec un délai d'attente court et un repli sur le formulaire vide.
- **Coût et latence** : un appel par collage, pas par page. Plafond journalier par agence. Journal des appels (sans contenu) pour la facturation et l'audit.

## 5. Flux complets

### A. Création d'un dossier à partir d'un collage de billet

1. Marie, agent, copie un e-ticket depuis un e-mail et la colle dans la zone de collage de **Aujourd'hui**.
2. Immédiatement (analyseur déterministe, sans attendre un modèle) : numéro de billet à 13 chiffres, nom du passager, trajet, date, transporteur détectés.
3. La carte de suggestion apparaît : « **Créer le dossier de NDONG/MARIE** : DLA-CDG, Air France, départ 20 nov., billet 057-2345678901. Client existant : Marie Ndong (+237 677 …) ». Champs douteux surlignés.
4. L'historique de l'agence propose le prix habituel du trajet ; pour l'agent, seul le prix s'affiche, le coût reste une saisie qu'il connaît (champ « Coût d'achat », qu'il peut remplir mais ne relit jamais).
5. Marie appuie sur **Entrée** : client trouvé ou créé, dossier ouvert, ligne ajoutée, devis brouillon prêt. Le toast dit « Dossier 2026-0042 créé — Annuler ».
6. Suggestion suivante : « Envoyer le devis à Marie par WhatsApp ? » → ouvre WhatsApp avec le message pré-rempli ; l'envoi se fait dans WhatsApp, par l'utilisatrice.
7. Si l'extraction est incertaine (numéro de 12 chiffres), l'écran pose la question avant de proposer quoi que ce soit.

Gestes : 1 collage, 1 confirmation (au lieu de remplir client, dossier, ligne, devis).

### B. Relance d'impayés

1. En ouvrant Aujourd'hui à 9 h, Paul, gérant, voit : « **3 clients ont un solde en retard de plus de 10 jours — 1 840 000 XAF.** Préparer les relances ? ».
2. **Confirmer** ouvre une liste groupée, cases cochées : client, dossier, montant dû, jours de retard, dernier contact. Il décoche un client qui a promis de payer vendredi.
3. Pour chaque ligne, un brouillon de message dans le ton de l'agence, avec le montant et les modes de paiement habituels. Sans LLM : modèle de texte fixe ; avec LLM : variation et politesse adaptées, mêmes faits, validés contre le solde réel.
4. **Relancer** ouvre successivement les liens WhatsApp pré-remplis ; Paul envoie depuis WhatsApp. Chaque relance est notée au dossier (« relancé le 27 oct. ») et la suggestion ne revient pas avant 7 jours.
5. Quand un paiement arrive, la suggestion « Encaisser 400 000 XAF de Ndong par Mobile Money ? » est pré-remplie avec la référence à saisir.

### C. Fin de journée et dossiers à risque

1. À l'heure habituelle de fin de Paul (apprise, ajustable : par défaut 17 h 45), la cloche passe à 1 et Aujourd'hui affiche : « **4 dossiers partent demain et ne sont pas émis.** ».
2. La liste est priorisée par risque : coût manquant (bloque l'émission), solde non réglé, billet sans passager. Chaque ligne dit ce qui manque.
3. Actions groupées : « Demander les coûts manquants à Marie » (rappel interne), « Émettre les 2 lignes prêtes » (confirmation avec liste), « Relancer le solde de 1 client ».
4. Les lignes sans coût ne sont **jamais** proposées à l'émission : la liste dit « Coût à saisir ».
5. Une ligne de résumé : « Demain : 4 départs, 1 impayé, 0 incident ». Le gérant peut ensuite quitter l'écran sans autre geste.

## 6. Spécifications techniques (Django + htmx)

### 6.1 Intégration sans casser la simplicité

- **Gabarits serveur** + htmx ; pas d'application monopage. Un seul fichier JavaScript maison (raccourcis clavier, palette), le reste est htmx.
- **Fragment de suggestion** : `<div hx-get="/assistant/suggestion?screen=today" hx-trigger="load, every 60s [document.visibilityState=='visible']" hx-swap="outerHTML">`. La page se rend sans lui.
- **Actions** : `hx-post="/assistant/suggestions/<id>/confirm"` renvoie le fragment mis à jour (toast + ligne modifiée via `hx-swap-oob`).
- **Idempotence** : la confirmation porte la clé d'idempotence de la suggestion ; un double clic ou un rejeu réseau ne crée rien en double (réutilise le mécanisme du journal et des paiements).
- **Validation à la confirmation** : la suggestion n'est qu'une description ; à la confirmation, le serveur **revérifie tout** (rôle, état du dossier, solde actuel) par les services habituels. Une suggestion périmée est refusée avec un message clair.
- **Accessibilité** : régions `aria-live="polite"` pour les nouvelles suggestions, focus géré après un échange, tout est utilisable au clavier.

### 6.2 Stockage

Trois tables du plan de données, avec `agency_id`, RLS forcée et migration de politique, branchées sur le test d'isolation de toutes les tables :

- `assist_event` : ajout seul, rétention 13 mois.
- `assist_pattern` : agrégats par utilisateur et agence, recalculables, supprimables.
- `assist_suggestion` : `kind`, `payload` (action pré-remplie), `reason`, `score`, `state` (proposée, vue, confirmée, modifiée, refusée, reportée, périmée), `expires_at`, `idempotency_key`, `actor_role`.

Les agrégats par utilisateur sont des données personnelles de l'employé : information, accès, effacement prévus (écran « Ce que Travora a appris de moi »).

### 6.3 Déclenchement

- **À l'affichage** : le fragment appelle `AssistantService.suggest(actor, screen, context)`, qui exécute les générateurs applicables, trie par score, applique les limites de fréquence, renvoie au plus une carte et un compteur.
- **Par événement** : après un geste (collage, ajout de ligne, paiement), le serveur renvoie en `hx-swap-oob` la suggestion suivante contextuelle (calcul léger, dans la même requête).
- **Par le temps** : une commande `assistant_tick` (planificateur du système ou de l'hébergeur) matérialise les suggestions temporelles (fin de journée, retards) pour chaque agence, dans `tenant_scope`, puis s'arrête. Pas de file de tâches.
- **Apprentissage** : une commande quotidienne recalcule `assist_pattern` à partir de `assist_event`.

### 6.4 Tests exigés

- Isolation : un agent ne reçoit jamais coût ou marge dans le moteur (test sur tous les générateurs).
- Une suggestion périmée ou devenue interdite est refusée à la confirmation.
- Idempotence de la confirmation.
- Jeu de textes collés réels, anonymisés, pour l'extraction ; seuil de précision défini avant la mise en production.
- Mode `NoModel` : toutes les suggestions de règles fonctionnent sans LLM.

## 7. Roadmap

**Phase 0 — conditions** (avant le code d'interface)
- Décider le sort de l'agence inactive, des bornes de dates et de la clôture de période ; corriger les défauts restants.
- Décider si un modèle hébergé est autorisé (juridique), sinon `NoModel`.
- Valider la charte avec le vrai logo ; faire tester une maquette cliquable à 3 agents et 1 gérant réels.

**Phase 1 — MVP interface + anticipation par règles** (le cœur utile)
- Couche `web` : connexion, Aujourd'hui, Dossiers, Dossier, Clients, Devis, Encaissements ; système de design, palette de commandes, mobile.
- Module `assistant` avec `NoModel` : collage (analyseur déterministe), relance (modèle de texte fixe), urgence, encaissement, clôture, revue de fin de journée.
- Événements, tiroir de suggestions, écran de contrôle des données apprises.
- Mesure : taux de confirmation par type, temps pour créer un dossier (avant/après).

**Phase 2 — habitudes et LLM borné**
- Habitudes (répétition de trajet/tarif/transporteur), heures apprises, groupage.
- Port `LanguageModel` avec un adaptateur (selon la décision juridique) : extraction de texte libre, brouillons de messages, explications.
- Évaluation continue, seuils de confiance, plafonds de coût.

**Phase 3 — profondeur**
- Suggestions inter-dossiers (saisonnalité, clients récurrents, risque d'impayé estimé par historique).
- Fournisseurs enregistrés (registre pays, mode, canal, API éventuelle) et règlements fournisseurs.
- Mode hors ligne partiel, application installable (PWA), notifications.

## 8. Ce que je recommande en premier

1. Valider ce document, la charte et la décision sur le LLM externe.
2. Corriger les défauts de fond restants (Phase 0).
3. Construire la Phase 1 **sans LLM** : elle livre déjà l'essentiel de la promesse (un geste au lieu de dix), de façon explicable, et fournit les données qui diront si un modèle apporte quelque chose de plus.
