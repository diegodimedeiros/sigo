# Generated manually on 2026-04-05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siop", "0006_controleefetivo_crachaprovisorio"),
    ]

    operations = [
        migrations.AddField(
            model_name="crachaprovisorio",
            name="cracha",
            field=models.CharField(
                db_index=True,
                default="cracha_provisorio_01",
                max_length=50,
                verbose_name="Crachá",
            ),
            preserve_default=False,
        ),
    ]
