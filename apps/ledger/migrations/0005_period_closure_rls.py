from django.db import migrations

from apps.shared_kernel.rls import append_only_guard, tenant_policy

closure_policy = tenant_policy("ledger_period_closure")
closure_guard = append_only_guard("ledger_period_closure")


class Migration(migrations.Migration):
    dependencies = [("ledger", "0004_period_closure")]

    operations = [
        migrations.RunSQL(*closure_policy),
        migrations.RunSQL(*closure_guard),
    ]
