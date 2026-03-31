import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from sigo.models import Assinatura, ConfiguracaoSistema, Notificacao, Pessoa, Unidade

from .models import AcessoTerceiros, AchadosPerdidos, Ocorrencia


class OcorrenciasFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.create(name="group_siop")
        self.ocorrencia = Ocorrencia.objects.create(
            tipo_pessoa="visitante",
            data_ocorrencia=timezone.now(),
            natureza="seguranca",
            tipo="agressao",
            area="area_administrativo",
            local="ciop",
            descricao="Ocorrência base para testes.",
            criado_por=self.user,
            modificado_por=self.user,
        )

    def test_ocorrencias_pages_require_login(self):
        urls = [
            reverse("siop:ocorrencias_index"),
            reverse("siop:ocorrencias_list"),
            reverse("siop:ocorrencias_new"),
            reverse("siop:ocorrencias_view", args=[self.ocorrencia.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)

    def test_api_ocorrencias_list_returns_success_contract(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_ocorrencias"), {"limit": 10, "offset": 0})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertIn("pagination", payload["meta"])
        self.assertEqual(payload["meta"]["pagination"]["count"], 1)

    def test_api_ocorrencias_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_ocorrencias"), {"limit": "abc", "offset": "xyz"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_ocorrencia_create_json_returns_success_and_persists(self):
        self.client.force_login(self.user)

        payload = {
            "data": "2026-03-29T14:30",
            "natureza": "Segurança",
            "tipo": "Agressão",
            "area": "Área Administrativo",
            "local": "CIOP",
            "pessoa": "Visitante",
            "descricao": "Nova ocorrência criada via teste.",
            "cftv": "true",
            "bombeiro_civil": "false",
            "status": "false",
        }

        response = self.client.post(
            reverse("siop:ocorrencias_new"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["ok"])
        created = Ocorrencia.objects.get(pk=body["data"]["id"])
        self.assertEqual(created.natureza, "seguranca")
        self.assertEqual(created.tipo_pessoa, "visitante")
        self.assertFalse(created.status)
        self.assertEqual(created.criado_por, self.user)
        notification = Notificacao.objects.get(titulo="Ocorrência | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, created.get_absolute_url())

    def test_ocorrencia_detail_api_returns_structured_payload(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_ocorrencia_detail", args=[self.ocorrencia.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], self.ocorrencia.pk)
        self.assertEqual(payload["data"]["natureza"], "Segurança")
        self.assertEqual(payload["data"]["natureza_key"], "seguranca")

    def test_ocorrencia_edit_json_returns_success_and_updates(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:ocorrencias_edit", args=[self.ocorrencia.pk]),
            data=json.dumps(
                {
                    "descricao": "Descrição alterada via teste.",
                    "cftv": "true",
                    "bombeiro_civil": "true",
                    "status": "true",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.descricao, "Descrição alterada via teste.")
        self.assertTrue(self.ocorrencia.cftv)
        self.assertTrue(self.ocorrencia.bombeiro_civil)
        self.assertTrue(self.ocorrencia.status)
        notification = Notificacao.objects.get(titulo="Ocorrência | Concluído")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, self.ocorrencia.get_absolute_url())

    def test_ocorrencia_edit_sem_finalizar_publica_notificacao_de_atualizacao(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:ocorrencias_edit", args=[self.ocorrencia.pk]),
            data=json.dumps(
                {
                    "descricao": "Descrição atualizada sem concluir.",
                    "cftv": "true",
                    "bombeiro_civil": "false",
                    "status": "false",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        notification = Notificacao.objects.get(titulo="Ocorrência | Atualizado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, self.ocorrencia.get_absolute_url())

    def test_ocorrencia_edit_page_renderiza_quando_em_aberto(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:ocorrencias_edit", args=[self.ocorrencia.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Ocorrência")

    def test_ocorrencia_edit_page_redireciona_quando_finalizada(self):
        self.client.force_login(self.user)
        self.ocorrencia.status = True
        self.ocorrencia.save(update_fields=["status"])

        response = self.client.get(reverse("siop:ocorrencias_edit", args=[self.ocorrencia.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("siop:ocorrencias_view", args=[self.ocorrencia.pk]))

    def test_ocorrencia_finalizada_nao_pode_ser_editada(self):
        self.client.force_login(self.user)
        self.ocorrencia.status = True
        self.ocorrencia.save(update_fields=["status"])

        response = self.client.post(
            reverse("siop:ocorrencias_edit", args=[self.ocorrencia.pk]),
            data=json.dumps(
                {
                    "descricao": "Nao deve alterar",
                    "cftv": "false",
                    "bombeiro_civil": "false",
                    "status": "true",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "business_rule_violation")


class AcessoTerceirosFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="porteiro",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]
        self.pessoa = Pessoa.objects.create(
            nome="Marcos Lima",
            documento="12345678900",
        )
        self.acesso = AcessoTerceiros.objects.create(
            entrada=timezone.now(),
            pessoa=self.pessoa,
            empresa="PrestServ",
            placa_veiculo="ABC1D23",
            p1="antonio_garcia",
            descricao_acesso="Acesso base para testes.",
            criado_por=self.user,
            modificado_por=self.user,
        )

    def test_acesso_terceiros_create_html_redirects_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:acesso_terceiros_new"),
            data={
                "entrada": "2026-03-29T18:30",
                "saida": "",
                "empresa": "Visitantes SA",
                "nome": "Carla Souza",
                "documento": "98765432100",
                "p1": "antonio_garcia",
                "placa_veiculo": "BRA2E19",
                "descricao": "Cadastro criado via teste.",
            },
        )

        created = AcessoTerceiros.objects.exclude(pk=self.acesso.pk).latest("id")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("siop:acesso_terceiros_view", args=[created.pk]))
        self.assertEqual(created.nome, "Carla Souza")
        self.assertEqual(created.documento, "98765432100")
        self.assertEqual(created.p1, "antonio_garcia")
        notification = Notificacao.objects.get(titulo="Acesso de Terceiros | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, created.get_absolute_url())

    def test_acesso_terceiros_export_pdf_view_returns_file(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:acesso_terceiros_export_view_pdf", args=[self.acesso.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_acesso_terceiros_edit_page_renderiza(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Acesso")

    def test_acesso_terceiros_edit_html_atualiza_registro(self):
        self.client.force_login(self.user)
        entrada_local = timezone.localtime(self.acesso.entrada)
        saida_local = entrada_local + timedelta(hours=1)

        response = self.client.post(
            reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]),
            data={
                "entrada": entrada_local.strftime("%Y-%m-%dT%H:%M"),
                "saida": saida_local.strftime("%Y-%m-%dT%H:%M"),
                "empresa": "PrestServ Atualizada",
                "nome": "Marcos Lima",
                "documento": "12345678900",
                "p1": "antonio_garcia",
                "placa_veiculo": "XYZ9K88",
                "descricao": "Descrição alterada via teste.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("siop:acesso_terceiros_view", args=[self.acesso.pk]))
        self.acesso.refresh_from_db()
        self.assertEqual(self.acesso.empresa, "PrestServ Atualizada")
        self.assertEqual(self.acesso.placa_veiculo, "XYZ9K88")
        notification = Notificacao.objects.get(titulo="Acesso de Terceiros | Concluído")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, self.acesso.get_absolute_url())

    def test_acesso_terceiros_edit_sem_saida_publica_notificacao_de_atualizacao(self):
        self.client.force_login(self.user)
        entrada_local = timezone.localtime(self.acesso.entrada)

        response = self.client.post(
            reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]),
            data={
                "entrada": entrada_local.strftime("%Y-%m-%dT%H:%M"),
                "saida": "",
                "empresa": "PrestServ Revisada",
                "nome": "Marcos Lima",
                "documento": "12345678900",
                "p1": "antonio_garcia",
                "placa_veiculo": "AAA1B11",
                "descricao": "Atualização sem saída.",
            },
        )

        self.assertEqual(response.status_code, 302)
        notification = Notificacao.objects.get(titulo="Acesso de Terceiros | Atualizado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, self.acesso.get_absolute_url())

    def test_acesso_terceiros_edit_page_redireciona_quando_ja_tem_saida(self):
        self.client.force_login(self.user)
        self.acesso.saida = self.acesso.entrada + timedelta(hours=1)
        self.acesso.save(update_fields=["saida"])

        response = self.client.get(reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("siop:acesso_terceiros_view", args=[self.acesso.pk]))

    def test_acesso_terceiros_com_saida_nao_pode_ser_editado(self):
        self.client.force_login(self.user)
        self.acesso.saida = self.acesso.entrada + timedelta(hours=1)
        self.acesso.save(update_fields=["saida"])

        response = self.client.post(
            reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]),
            data={
                "entrada": timezone.localtime(self.acesso.entrada).strftime("%Y-%m-%dT%H:%M"),
                "saida": timezone.localtime(self.acesso.saida).strftime("%Y-%m-%dT%H:%M"),
                "empresa": "Nao deve alterar",
                "nome": "Marcos Lima",
                "documento": "12345678900",
                "p1": "antonio_garcia",
                "placa_veiculo": "XYZ9K88",
                "descricao": "Não deve salvar",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acessos com saída registrada não podem ser editados.")
        self.acesso.refresh_from_db()
        self.assertEqual(self.acesso.empresa, "PrestServ")


class AchadosPerdidosFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="achados",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]
        self.item = AchadosPerdidos.objects.create(
            tipo="documentos",
            situacao="achado",
            descricao="Item base para testes.",
            local="ciop",
            area="area_administrativo",
            organico=False,
            status="recebido",
            criado_por=self.user,
            modificado_por=self.user,
        )

    def test_achados_perdidos_create_html_redirects_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "recebido",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Novo item criado via teste.",
            },
        )

        created = AchadosPerdidos.objects.exclude(pk=self.item.pk).latest("id")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("siop:achados_perdidos_view", args=[created.pk]))
        self.assertEqual(created.tipo, "documentos")
        self.assertEqual(created.situacao, "achado")
        self.assertEqual(created.status, "recebido")
        notification = Notificacao.objects.get(titulo="Achados e Perdidos | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, created.get_absolute_url())

    def test_achados_perdidos_forca_status_perdido_quando_situacao_e_perdido(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "perdido",
                "status": "recebido",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Item perdido deve ajustar o status automaticamente.",
            },
        )

        created = AchadosPerdidos.objects.exclude(pk=self.item.pk).latest("id")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(created.situacao, "perdido")
        self.assertEqual(created.status, "perdido")
        notification = Notificacao.objects.get(titulo="Achados e Perdidos | Novo Registrado")
        self.assertEqual(notification.grupo, self.group_siop)

    def test_achados_perdidos_achado_nao_aceita_status_perdido(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "perdido",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Item achado não pode assumir status perdido.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Itens achados não podem ter status Perdido.")

    def test_achados_perdidos_nao_organico_aceita_colaborador_texto_livre(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "recebido",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "colaborador": "Prestador Externo",
                "setor": "Terceirizada",
                "descricao": "Item com colaborador em texto livre.",
            },
        )

        created = AchadosPerdidos.objects.exclude(pk=self.item.pk).latest("id")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(created.colaborador, "Prestador Externo")
        self.assertEqual(created.setor, "Terceirizada")

    def test_achados_perdidos_export_pdf_view_returns_file(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:achados_perdidos_export_view_pdf", args=[self.item.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_achados_perdidos_edit_page_renderiza_quando_item_esta_em_aberto(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:achados_perdidos_edit", args=[self.item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Item")

    def test_achados_perdidos_edit_page_redireciona_quando_status_final(self):
        self.client.force_login(self.user)
        self.item.status = "entregue"
        self.item.pessoa = Pessoa.objects.create(nome="Ana Paula", documento="11122233344")
        self.item.data_devolucao = timezone.now()
        self.item.save()

        response = self.client.get(reverse("siop:achados_perdidos_edit", args=[self.item.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("siop:achados_perdidos_view", args=[self.item.pk]))

    def test_achados_perdidos_entregue_exige_assinatura(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "entregue",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Entrega sem assinatura deve falhar.",
                "pessoa_nome": "Ana Paula",
                "pessoa_documento": "11122233344",
                "data_devolucao": "2026-03-29T19:30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Colete a assinatura para concluir com status Entregue.")

    def test_achados_perdidos_entregue_salva_assinatura(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "entregue",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Entrega com assinatura deve persistir.",
                "pessoa_nome": "Ana Paula",
                "pessoa_documento": "11122233344",
                "data_devolucao": "2026-03-29T19:30",
                "assinatura_entrega": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5W0AAAAASUVORK5CYII=",
            },
        )

        created = AchadosPerdidos.objects.exclude(pk=self.item.pk).latest("id")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(created.status, "entregue")
        self.assertEqual(created.assinaturas.count(), 1)
        self.assertIsInstance(created.assinaturas.first(), Assinatura)
        creation_notification = Notificacao.objects.get(titulo="Achados e Perdidos | Novo Registrado")
        final_notification = Notificacao.objects.get(titulo="Achados e Perdidos | Concluído")
        self.assertEqual(creation_notification.grupo, self.group_siop)
        self.assertEqual(final_notification.grupo, self.group_siop)
        self.assertEqual(final_notification.link, created.get_absolute_url())

    def test_achados_perdidos_edit_sem_finalizar_publica_notificacao_de_atualizacao(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_edit", args=[self.item.pk]),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "recebido",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Item atualizado sem conclusão.",
            },
        )

        self.assertEqual(response.status_code, 302)
        notification = Notificacao.objects.get(titulo="Achados e Perdidos | Atualizado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, self.item.get_absolute_url())


class UnidadeAutoAssignmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="unidade",
            password="senha-forte-123",
        )
        self.unidade = Unidade.objects.create(
            nome="Parque do Caracol",
            sigla="PC",
            cidade="Canela",
            uf="RS",
        )
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def test_ocorrencia_nova_recebe_unidade_ativa(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:ocorrencias_new"),
            data={
                "pessoa": "visitante",
                "data": "2026-03-29T19:00",
                "natureza": "seguranca",
                "tipo": "agressao",
                "area": "area_administrativo",
                "local": "ciop",
                "descricao": "Ocorrência com unidade automática.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        created = Ocorrencia.objects.latest("id")
        self.assertEqual(created.unidade, self.unidade)
        self.assertEqual(created.unidade_sigla, self.unidade.sigla)

    def test_acesso_terceiros_novo_recebe_unidade_ativa(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:acesso_terceiros_new"),
            data={
                "entrada": "2026-03-29T19:00",
                "empresa": "Fornecedor Teste",
                "nome": "Carlos Souza",
                "documento": "12345678900",
                "p1": "lucas_cunha",
                "descricao": "Acesso com unidade automática.",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = AcessoTerceiros.objects.latest("id")
        self.assertEqual(created.unidade, self.unidade)
        self.assertEqual(created.unidade_sigla, self.unidade.sigla)

    def test_achado_perdido_novo_recebe_unidade_ativa(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data={
                "tipo": "documentos",
                "situacao": "achado",
                "status": "recebido",
                "area": "area_administrativo",
                "local": "ciop",
                "organico": "false",
                "descricao": "Achado com unidade automática.",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = AchadosPerdidos.objects.latest("id")
        self.assertEqual(created.unidade, self.unidade)
        self.assertEqual(created.unidade_sigla, self.unidade.sigla)
