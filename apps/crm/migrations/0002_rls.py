from django.db import migrations

from apps.shared_kernel.rls import tenant_policy

forward, reverse = tenant_policy("crm_customer")


class Migration(migrations.Migration):
    dependencies = [("crm", "0001_initial")]

    operations = [migrations.RunSQL(forward, reverse)]
