from django.db import migrations

from apps.shared_kernel.rls import append_only_guard, tenant_policy

policy_forward, policy_reverse = tenant_policy("audit_event")
guard_forward, guard_reverse = append_only_guard("audit_event")


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [
        migrations.RunSQL(policy_forward, policy_reverse),
        migrations.RunSQL(guard_forward, guard_reverse),
    ]
