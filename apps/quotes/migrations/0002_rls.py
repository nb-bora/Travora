from django.db import migrations

from apps.shared_kernel.rls import tenant_policy

forward, reverse = tenant_policy("quotes_quote")


class Migration(migrations.Migration):
    dependencies = [("quotes", "0001_initial")]

    operations = [migrations.RunSQL(forward, reverse)]
