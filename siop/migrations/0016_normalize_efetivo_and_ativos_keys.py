from django.db import migrations, models


def normalize_ativos_destino(apps, schema_editor):
    ControleAtivos = apps.get_model("siop", "ControleAtivos")
    ControleAtivos.objects.filter(destino="facilites").update(destino="facilities")


class Migration(migrations.Migration):

    dependencies = [
        ("siop", "0015_liberacaoacesso_chegadas_registradas"),
    ]

    operations = [
        migrations.RunPython(normalize_ativos_destino, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="controleefetivo",
                    old_name="manutenção",
                    new_name="manutencao",
                ),
                migrations.AlterField(
                    model_name="controleefetivo",
                    name="manutencao",
                    field=models.CharField(
                        db_column="manutenção",
                        max_length=255,
                        verbose_name="Responsável Manutenção",
                    ),
                ),
            ],
        ),
    ]
