from typing import Any, ClassVar

from django.db import models

from apps.shared_kernel.models import TenantManager, TenantScopedModel


class AppendOnlyViolation(RuntimeError):
    pass


class AppendOnlyQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        raise AppendOnlyViolation(f"{self.model.__name__} est en ajout seul.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise AppendOnlyViolation(f"{self.model.__name__} est en ajout seul.")

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        raise AppendOnlyViolation(f"{self.model.__name__} est en ajout seul.")


class AppendOnlyManager(TenantManager.from_queryset(AppendOnlyQuerySet)):  # type: ignore[misc]
    pass


class AppendOnlyModel(TenantScopedModel):
    """Table en ajout seul : aucune ligne n'est jamais modifiée ni supprimée.

    Le code refuse les écritures ; PostgreSQL les refuse aussi (droits du rôle
    d'exécution et déclencheurs, voir ``apps.shared_kernel.rls.append_only_guard``).
    """

    objects: ClassVar[AppendOnlyManager] = AppendOnlyManager()

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise AppendOnlyViolation(f"{type(self).__name__} est en ajout seul.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise AppendOnlyViolation(f"{type(self).__name__} est en ajout seul.")
