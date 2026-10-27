from django.db import migrations

from apps.shared_kernel.rls import AGENCY_SETTING_SQL, tenant_policy

forward, reverse = tenant_policy(
    "tenancy_agency", using=f"id = {AGENCY_SETTING_SQL}"
)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0001_initial")]

    operations = [migrations.RunSQL(forward, reverse)]
