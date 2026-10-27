import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cases", "0002_rls"),
        ("ledger", "0002_rls_and_guards"),
    ]

    operations = [
        migrations.RenameField("ledgertransaction", "case_id", "case"),
        migrations.AlterField(
            model_name="ledgertransaction",
            name="case",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="cases.case",
            ),
        ),
    ]
