from django.apps import AppConfig
from django.db.models.signals import post_migrate


class TenancyConfig(AppConfig):
    name = "apps.tenancy"
    label = "tenancy"

    def ready(self) -> None:
        from apps.tenancy.privileges import grant_runtime_privileges

        post_migrate.connect(
            grant_runtime_privileges, sender=self, dispatch_uid="tenancy.grant_runtime_privileges"
        )
