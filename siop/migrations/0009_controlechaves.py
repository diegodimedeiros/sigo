# Generated manually on 2026-04-05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sigo", "0006_notificacao"),
        ("siop", "0008_controleativos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ControleChaves",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="Criado em")),
                ("modificado_em", models.DateTimeField(auto_now=True, verbose_name="Modificado em")),
                ("unidade_sigla", models.CharField(blank=True, db_index=True, max_length=50, null=True, verbose_name="Sigla da Unidade")),
                ("retirada", models.DateTimeField(db_index=True, verbose_name="Data e Hora da Retirada")),
                ("devolucao", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Data e Hora da Devolução")),
                ("chave", models.CharField(db_index=True, max_length=255, verbose_name="Chave")),
                ("observacao", models.TextField(blank=True, null=True, verbose_name="Observação")),
                ("criado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="%(class)s_criados", to=settings.AUTH_USER_MODEL, verbose_name="Criado por")),
                ("modificado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="%(class)s_modificados", to=settings.AUTH_USER_MODEL, verbose_name="Modificado por")),
                ("pessoa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="controles_chaves", to="sigo.pessoa")),
                ("unidade", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="controles_chaves", to="sigo.unidade", verbose_name="Unidade")),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
