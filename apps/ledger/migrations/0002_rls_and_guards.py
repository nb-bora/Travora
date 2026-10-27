from django.db import migrations

from apps.shared_kernel.rls import append_only_guard, tenant_policy

BALANCE_FUNCTION = """
CREATE OR REPLACE FUNCTION ledger_assert_balanced() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    difference bigint;
BEGIN
    SELECT COALESCE(SUM(CASE WHEN direction = 'debit' THEN amount_xaf ELSE -amount_xaf END), 0)
      INTO difference
      FROM ledger_posting
     WHERE transaction_id = NEW.transaction_id;
    IF difference <> 0 THEN
        RAISE EXCEPTION 'écriture % déséquilibrée (écart %)', NEW.transaction_id, difference
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END
$$
"""

BALANCE_TRIGGER = """
CREATE CONSTRAINT TRIGGER ledger_posting_balanced
AFTER INSERT ON ledger_posting
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION ledger_assert_balanced()
"""

transaction_policy = tenant_policy("ledger_transaction")
posting_policy = tenant_policy("ledger_posting")
transaction_guard = append_only_guard("ledger_transaction")
posting_guard = append_only_guard("ledger_posting")


class Migration(migrations.Migration):
    dependencies = [("ledger", "0001_initial")]

    operations = [
        migrations.RunSQL(*transaction_policy),
        migrations.RunSQL(*posting_policy),
        migrations.RunSQL(*transaction_guard),
        migrations.RunSQL(*posting_guard),
        migrations.RunSQL(
            [BALANCE_FUNCTION, BALANCE_TRIGGER],
            ["DROP TRIGGER ledger_posting_balanced ON ledger_posting"],
        ),
    ]
