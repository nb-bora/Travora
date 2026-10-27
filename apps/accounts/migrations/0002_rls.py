from django.db import migrations

from apps.shared_kernel.rls import AGENCY_PREDICATE, USER_SETTING_SQL, tenant_policy

forward, reverse = tenant_policy(
    "accounts_membership",
    using=f"{AGENCY_PREDICATE} OR user_id = {USER_SETTING_SQL}",
    check=AGENCY_PREDICATE,
)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [migrations.RunSQL(forward, reverse)]
