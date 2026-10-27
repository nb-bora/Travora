# ADR-0003 — Stack et architecture technique

- **Statut** : accepté et implémenté (27 octobre 2026)
- **Documents liés** : [architecture](../architecture.md), [12](../12-plan-recentre-60-jours.md), [ADR-0001](ADR-0001-plateforme-multimodale-connecteurs.md), [ADR-0002](ADR-0002-registre-fournisseurs.md)

## Contexte

Un développeur seul doit livrer un MVP financier multi-tenant à fort enjeu de confiance : une fuite entre agences ou une écriture comptable altérée ruinerait le produit. Le réseau est lent et intermittent ; le Mobile Money et WhatsApp dominent ; aucune intégration externe n'est autorisée au MVP. L'hébergement n'est pas décidé.

## Décision

1. **Django 6.1** sur **PostgreSQL 15 ou plus**, gestion des dépendances par **Poetry**, Python 3.14.
   - Django 5.2 LTS n'a plus de support régulier depuis le 3 décembre 2025 (sécurité seule jusqu'en avril 2028) ; Django 6.1 a un support régulier jusqu'en avril 2027 (page officielle des versions, lue le 27 octobre 2026). Migration vers la prochaine LTS à prévoir avant avril 2027, date à confirmer.
   - Python 3.14 : supporté par Django 6.1 (FAQ officielle) et nécessaire à `uuid.uuid7`.
2. **Monolithe modulaire** : un module par domaine, façade publique, frontières imposées par `import-linter`. Pas de microservices, pas d'événements internes.
3. **Isolation par la base** : `tenant_id` (ici `agency_id`) sur toute table du plan de données, RLS **forcée**, variables de transaction `app.agency_id` et `app.user_id` posées par un contexte transactionnel, rôle d'exécution sans propriété ni contournement. Le comportement de la RLS (refus par défaut, `FORCE`, contournement par superutilisateur et `BYPASSRLS`, contraintes d'unicité et de clé étrangère hors RLS) a été relu dans la documentation officielle de PostgreSQL.
4. **Défense en profondeur côté ORM** : filtre d'agence automatique et refus d'écrire pour une autre agence.
5. **Journal comptable en ajout seul**, appliqué par le code, les droits du rôle d'exécution et des déclencheurs ; équilibre par déclencheur différé ; correction par contre-passation ; soldes et marges dérivés ; montants entiers en XAF.
6. **Idempotence** par clés uniques en base, pour les écritures comptables et les paiements ; imports rejouables.
7. **Aucune intégration externe** : pas d'API de paiement, de GDS ni de WhatsApp Business ; saisie manuelle et lien `wa.me`.
8. **Pas de file de tâches** : aucun traitement asynchrone n'est nécessaire à ce stade ; PostgreSQL suffira le jour venu.
9. **Pas d'administration Django** : elle verrait zéro ligne sous RLS et élargirait la surface d'attaque ; les commandes du concierge la remplacent.
10. **Pipeline CI/CD** : qualité (lint, format, typage, frontières), tests sur PostgreSQL 17 avec couverture minimale, vulnérabilités et licences, image de production ; publication sur étiquette de version après rejeu complet de la CI. Pas de déploiement automatique tant que l'hébergement n'est pas décidé.

## Conséquences

- **Positives** : trois niveaux d'isolation indépendants ; un journal qu'aucun rôle applicatif ne peut altérer ; une base de code unique ; des frontières contrôlées automatiquement ; un test qui échoue si une table échappe à l'isolation.
- **Négatives** : la RLS impose des conventions strictes (variables de transaction, rôle d'exécution distinct, migration de politique par table) ; les tests d'isolation doivent endosser le rôle d'exécution, car le super-utilisateur contourne la RLS ; WeasyPrint exige Pango (vérifié dans l'image, pas sous Windows).
- **À surveiller** : le support régulier de Django 6.1 prend fin en avril 2027 ; la règle d'une agence par utilisateur ; les performances des agrégations de soldes si les volumes dépassent largement ceux visés (30 à 150 dossiers par mois par agence).

## Alternatives écartées

- **FastAPI et Next.js** : deux bases de code pour une seule personne, sans bénéfice au MVP ; pages serveur plus légères sur réseau lent.
- **Un schéma ou une base par agence** : isolation forte mais exploitation lourde pour un développeur seul ; reste possible comme niveau supérieur pour un client exigeant.
- **Filtrage applicatif seul** : un oubli de `.filter()` fuirait entre agences ; la RLS le rend impossible.
- **Solde stocké et mis à jour** : divergence possible avec le journal ; le solde est toujours calculé.
- **Bibliothèque de grand livre tierce** (django-ledger : GPL ; django-hordak : compatibilité avec Django 6.1 non vérifiée) : le journal minimal nécessaire est petit, et ses invariants sont mieux maîtrisés en interne.
