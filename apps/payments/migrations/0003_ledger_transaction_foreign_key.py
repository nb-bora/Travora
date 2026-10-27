import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0003_case_foreign_key"),
        ("payments", "0002_rls"),
    ]

    operations = [
        migrations.RenameField("payment", "ledger_transaction_id", "ledger_transaction"),
        migrations.AlterField(
            model_name="payment",
            name="ledger_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="ledger.ledgertransaction",
            ),
        ),
    ]
