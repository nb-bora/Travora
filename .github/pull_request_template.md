## Objet

<!-- Ce que cette modification change, et pourquoi. -->

## Contrôles

- [ ] Les tests passent, y compris l'isolation entre agences
- [ ] Toute nouvelle table du plan de données hérite de `TenantScopedModel`, a sa politique RLS (migration `…_rls.py`) et est alimentée dans `tests/test_isolation_all_tables.py`
- [ ] Aucune écriture comptable n'est modifiée ou supprimée (contre-écriture seulement)
- [ ] Le coût et la marge ne sortent jamais pour un agent
- [ ] Aucune dépendance sous licence AGPL, GPL, SSPL ou BSL
- [ ] Les frontières entre applications sont respectées (`lint-imports`)
