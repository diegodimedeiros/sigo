# Generated manually on 2026-04-06

import django.db.models.deletion
from django.db import migrations, models


def migrate_acessocolaboradores_pessoas(apps, schema_editor):
    AcessoColaboradores = apps.get_model("siop", "AcessoColaboradores")

    for acesso in AcessoColaboradores.objects.all().iterator():
        primeira_pessoa = acesso.pessoa.order_by("id").first()
        if primeira_pessoa is None:
            continue
        acesso.pessoa_vinculada_id = primeira_pessoa.id
        acesso.save(update_fields=["pessoa_vinculada"])


class Migration(migrations.Migration):

    dependencies = [
        ("siop", "0018_acessocolaboradores"),
        ("sigo", "0006_notificacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="acessocolaboradores",
            name="pessoa_vinculada",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="sigo.pessoa",
            ),
        ),
        migrations.RunPython(
            migrate_acessocolaboradores_pessoas,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="acessocolaboradores",
            name="pessoa",
        ),
        migrations.RenameField(
            model_name="acessocolaboradores",
            old_name="pessoa_vinculada",
            new_name="pessoa",
        ),
        migrations.AlterField(
            model_name="acessocolaboradores",
            name="pessoa",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="acessos_colaboradores",
                to="sigo.pessoa",
            ),
        ),
    ]
