from django.db import migrations

from apps.shared_kernel.rls import tenant_policy

forward, reverse = tenant_policy("payments_payment")


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]

    operations = [migrations.RunSQL(forward, reverse)]
