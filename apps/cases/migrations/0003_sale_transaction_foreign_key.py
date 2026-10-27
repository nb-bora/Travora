import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cases", "0002_rls"),
        ("ledger", "0003_case_foreign_key"),
    ]

    operations = [
        migrations.RenameField("caseline", "sale_transaction_id", "sale_transaction"),
        migrations.AlterField(
            model_name="caseline",
            name="sale_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="ledger.ledgertransaction",
            ),
        ),
    ]
