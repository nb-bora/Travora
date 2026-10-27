from django.db import migrations

from apps.shared_kernel.rls import tenant_policy

case_policy = tenant_policy("cases_case")
line_policy = tenant_policy("cases_line")


class Migration(migrations.Migration):
    dependencies = [("cases", "0001_initial")]

    operations = [
        migrations.RunSQL(*case_policy),
        migrations.RunSQL(*line_policy),
    ]
