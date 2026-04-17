import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from sigo.models import Assinatura, ConfiguracaoSistema, Notificacao, Pessoa, Unidade
from sigo_core.catalogos import catalogo_bc_data

from .models import AcessoColaboradores, AcessoTerceiros, AchadosPerdidos, ControleAtivos, ControleChaves, ControleEfetivo, CrachaProvisorio, LiberacaoAcesso, Ocorrencia


class OcorrenciasFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.create(name="group_siop")
        self.user.groups.add(self.group_siop)
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

    def test_ocorrencias_index_renderiza_sem_data_registro(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:ocorrencias_index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Últimos registros")
        self.assertContains(response, f"#{self.ocorrencia.pk}")

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

    def test_api_acesso_terceiros_list_returns_success_contract(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:api_acesso_terceiros"),
            {"limit": 10, "offset": 0},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertIn("pagination", payload["meta"])
        self.assertEqual(payload["meta"]["pagination"]["count"], 1)
        self.assertEqual(payload["data"]["acessos"][0]["id"], self.acesso.pk)

    def test_api_acesso_terceiros_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:api_acesso_terceiros"),
            {"limit": "abc", "offset": "xyz"},
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_acesso_terceiros_create_json_returns_success_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:acesso_terceiros_new"),
            data=json.dumps(
                {
                    "entrada": "2026-03-29T18:30",
                    "saida": "",
                    "empresa": "Visitantes SA",
                    "nome": "Carla Souza",
                    "documento": "98765432100",
                    "p1": "antonio_garcia",
                    "placa_veiculo": "BRA2E19",
                    "descricao": "Cadastro criado via teste JSON.",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["ok"])
        created = AcessoTerceiros.objects.get(pk=body["data"]["id"])
        self.assertEqual(created.nome, "Carla Souza")
        self.assertEqual(created.documento, "98765432100")
        self.assertEqual(created.p1, "antonio_garcia")
        notification = Notificacao.objects.get(titulo="Acesso de Terceiros | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)
        self.assertEqual(notification.link, created.get_absolute_url())

    def test_api_acesso_terceiros_detail_returns_structured_payload(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:api_acesso_terceiros_detail", args=[self.acesso.pk])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], self.acesso.pk)
        self.assertEqual(payload["data"]["nome"], "Marcos Lima")
        self.assertEqual(payload["data"]["documento"], "12345678900")

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

    def test_acesso_terceiros_edit_json_returns_success_and_updates(self):
        self.client.force_login(self.user)
        entrada_local = timezone.localtime(self.acesso.entrada)
        saida_local = entrada_local + timedelta(hours=1)

        response = self.client.post(
            reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]),
            data=json.dumps(
                {
                    "entrada": entrada_local.strftime("%Y-%m-%dT%H:%M"),
                    "saida": saida_local.strftime("%Y-%m-%dT%H:%M"),
                    "empresa": "PrestServ Atualizada JSON",
                    "nome": "Marcos Lima",
                    "documento": "12345678900",
                    "p1": "antonio_garcia",
                    "placa_veiculo": "XYZ9K88",
                    "descricao": "Descrição alterada via teste JSON.",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.acesso.refresh_from_db()
        self.assertEqual(self.acesso.empresa, "PrestServ Atualizada JSON")
        self.assertEqual(self.acesso.placa_veiculo, "XYZ9K88")
        self.assertIsNotNone(self.acesso.saida)
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

    def test_acesso_terceiros_com_saida_nao_pode_ser_editado_via_json(self):
        self.client.force_login(self.user)
        self.acesso.saida = self.acesso.entrada + timedelta(hours=1)
        self.acesso.save(update_fields=["saida"])

        response = self.client.post(
            reverse("siop:acesso_terceiros_edit", args=[self.acesso.pk]),
            data=json.dumps(
                {
                    "entrada": timezone.localtime(self.acesso.entrada).strftime("%Y-%m-%dT%H:%M"),
                    "saida": timezone.localtime(self.acesso.saida).strftime("%Y-%m-%dT%H:%M"),
                    "empresa": "Nao deve alterar",
                    "nome": "Marcos Lima",
                    "documento": "12345678900",
                    "p1": "antonio_garcia",
                    "placa_veiculo": "XYZ9K88",
                    "descricao": "Não deve salvar",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "business_rule_violation")
        self.acesso.refresh_from_db()
        self.assertEqual(self.acesso.empresa, "PrestServ")


class AcessoColaboradoresFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="colaboradores",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]
        self.unidade = Unidade.objects.create(
            nome="Parque do Caracol",
            sigla="PC",
            cidade="Canela",
            uf="RS",
        )
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def _payload(self):
        return {
            "pessoa_colaborador": ["abner_mauricio", "ana_silva"],
            "entrada": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "saida": "",
            "placa_veiculo": "ABC1D23",
            "p1": "lucas_cunha",
            "descricao_acesso": "Acesso interno para atividade operacional.",
        }

    def test_acesso_colaboradores_create_persiste_registro(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("siop:acesso_colaboradores_new"), data=self._payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AcessoColaboradores.objects.count(), 2)
        created = list(AcessoColaboradores.objects.order_by("id"))
        self.assertEqual({item.pessoa.nome for item in created}, {"Abner Mauricio", "Ana Silva"})
        self.assertTrue(all(item.p1 == "lucas_cunha" for item in created))
        self.assertTrue(all(item.placa_veiculo == "ABC1D23" for item in created))
        self.assertTrue(all(item.unidade == self.unidade for item in created))
        self.assertTrue(all(item.pessoa.documento.startswith("COLAB-") for item in created))
        self.assertEqual(
            Notificacao.objects.filter(titulo="Acesso de Colaboradores | Novo Registrado").count(),
            2,
        )

    def test_api_acesso_colaboradores_list_returns_success_contract(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Pessoa Um", documento="11111111111")
        AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now(),
            pessoa=pessoa,
            p1="lucas_cunha",
            descricao_acesso="Acesso interno",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_acesso_colaboradores"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(len(payload["data"]["registros"][0]["pessoas"]), 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoas"][0]["nome"], "Pessoa Um")
        self.assertEqual(payload["data"]["registros"][0]["p1_label"], "Lucas Cunha")

    def test_api_acesso_colaboradores_aplica_filtros_de_status_e_p1(self):
        self.client.force_login(self.user)
        AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Pessoa Em Aberto", documento="11111111112"),
            p1="lucas_cunha",
            descricao_acesso="Registro em aberto",
            criado_por=self.user,
            modificado_por=self.user,
        )
        AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now() - timedelta(hours=2),
            saida=timezone.now() - timedelta(hours=1),
            pessoa=Pessoa.objects.create(nome="Pessoa Concluida", documento="11111111113"),
            p1="antonio_garcia",
            descricao_acesso="Registro concluído",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(
            reverse("siop:api_acesso_colaboradores"),
            {"status": "em_aberto", "p1": "lucas_cunha"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoas"][0]["nome"], "Pessoa Em Aberto")
        self.assertEqual(payload["data"]["registros"][0]["p1"], "lucas_cunha")

    def test_acesso_colaboradores_edit_atualiza_registro(self):
        self.client.force_login(self.user)
        acesso = AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Pessoa Inicial", documento="00011122233"),
            p1="lucas_cunha",
            descricao_acesso="Inicial",
            criado_por=self.user,
            modificado_por=self.user,
        )

        payload = self._payload()
        payload["pessoa_colaborador"] = ["ana_silva"]
        payload["pessoa_nome"] = [""]
        payload["placa_veiculo"] = "XYZ9K88"
        payload["saida"] = timezone.localtime(timezone.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(reverse("siop:acesso_colaboradores_edit", args=[acesso.pk]), data=payload)

        self.assertEqual(response.status_code, 302)
        acesso.refresh_from_db()
        self.assertEqual(acesso.placa_veiculo, "XYZ9K88")
        self.assertIsNotNone(acesso.saida)
        self.assertEqual(acesso.pessoa.nome, "Ana Silva")

    def test_acesso_colaboradores_list_renderiza_registros(self):
        self.client.force_login(self.user)
        AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Pessoa Teste", documento="99999999999"),
            p1="lucas_cunha",
            descricao_acesso="Registro de listagem",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:acesso_colaboradores_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pessoa Teste")
        self.assertContains(response, "Lucas Cunha")

    def test_acesso_colaboradores_export_xlsx_returns_file(self):
        self.client.force_login(self.user)
        AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Pessoa Teste", documento="99999999999"),
            p1="lucas_cunha",
            descricao_acesso="Registro exportável",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(reverse("siop:acesso_colaboradores_export"), data={"formato": "xlsx"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_acesso_colaboradores_rejeita_colaborador_duplicado_no_mesmo_registro(self):
        self.client.force_login(self.user)
        payload = self._payload()
        payload["pessoa_colaborador"] = ["abner_mauricio", "abner_mauricio"]

        response = self.client.post(reverse("siop:acesso_colaboradores_new"), data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não repita o mesmo colaborador no mesmo acesso.")
        self.assertEqual(AcessoColaboradores.objects.count(), 0)

    def test_acesso_colaboradores_accepta_nome_digitado_manualmente(self):
        self.client.force_login(self.user)
        payload = self._payload()
        payload["pessoa_colaborador"] = ["abner_mauricio", ""]
        payload["pessoa_nome"] = ["", "Colaborador Visitante"]

        response = self.client.post(reverse("siop:acesso_colaboradores_new"), data=payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AcessoColaboradores.objects.count(), 2)
        self.assertEqual(
            set(AcessoColaboradores.objects.values_list("pessoa__nome", flat=True)),
            {"Abner Mauricio", "Colaborador Visitante"},
        )

    def test_acesso_colaboradores_edit_rejeita_multiplos_nomes(self):
        self.client.force_login(self.user)
        acesso = AcessoColaboradores.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            entrada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Pessoa Inicial", documento="00011122234"),
            p1="lucas_cunha",
            descricao_acesso="Inicial",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(reverse("siop:acesso_colaboradores_edit", args=[acesso.pk]), data=self._payload())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cada registro aceita apenas um colaborador. Crie novos registros separados.")


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

    def test_api_achados_perdidos_list_returns_success_contract(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:api_achados_perdidos"),
            {"limit": 10, "offset": 0},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertIn("pagination", payload["meta"])
        self.assertEqual(payload["meta"]["pagination"]["count"], 1)
        self.assertEqual(payload["data"]["itens"][0]["id"], self.item.pk)

    def test_api_achados_perdidos_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:api_achados_perdidos"),
            {"limit": "abc", "offset": "xyz"},
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_achados_perdidos_create_json_returns_success_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_new"),
            data=json.dumps(
                {
                    "tipo": "documentos",
                    "situacao": "achado",
                    "status": "recebido",
                    "area": "area_administrativo",
                    "local": "ciop",
                    "organico": "false",
                    "descricao": "Novo item criado via teste JSON.",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        created = AchadosPerdidos.objects.get(pk=payload["data"]["id"])
        self.assertEqual(created.tipo, "documentos")
        self.assertEqual(created.situacao, "achado")
        self.assertEqual(created.status, "recebido")

    def test_api_achado_perdido_detail_returns_structured_payload(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("siop:api_achado_perdido_detail", args=[self.item.pk])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], self.item.pk)
        self.assertEqual(payload["data"]["tipo"], "documentos")
        self.assertEqual(payload["data"]["situacao"], "achado")

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

    def test_achados_perdidos_edit_json_returns_success_and_updates(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:achados_perdidos_edit", args=[self.item.pk]),
            data=json.dumps(
                {
                    "tipo": "documentos",
                    "situacao": "achado",
                    "status": "recebido",
                    "area": "area_administrativo",
                    "local": "ciop",
                    "organico": "false",
                    "descricao": "Item alterado via teste JSON.",
                    "colaborador": "Prestador Externo",
                    "setor": "Terceirizada",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.descricao, "Item alterado via teste JSON.")
        self.assertEqual(self.item.colaborador, "Prestador Externo")
        self.assertEqual(self.item.setor, "Terceirizada")

    def test_achados_perdidos_status_final_nao_pode_ser_editado_via_json(self):
        self.client.force_login(self.user)
        self.item.status = "entregue"
        self.item.pessoa = Pessoa.objects.create(nome="Ana Paula", documento="11122233344")
        self.item.data_devolucao = timezone.now()
        self.item.save()

        response = self.client.post(
            reverse("siop:achados_perdidos_edit", args=[self.item.pk]),
            data=json.dumps(
                {
                    "descricao": "Nao deve alterar",
                    "status": "entregue",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "business_rule_violation")

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


class CrachaProvisorioFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="crachas",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]
        self.unidade = Unidade.objects.create(
            nome="Parque do Caracol",
            sigla="PC",
            cidade="Canela",
            uf="RS",
        )
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def test_retirada_do_cracha_persiste_registro(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:crachas_provisorios_new"),
            data={
                "cracha": "cracha_provisorio_01",
                "entrega": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "pessoa_documento": "12345678900",
                "observacao": "Retirada inicial do crachá.",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = CrachaProvisorio.objects.latest("id")
        self.assertEqual(created.cracha, "cracha_provisorio_01")
        self.assertIsNone(created.devolucao)
        self.assertEqual(created.unidade, self.unidade)
        self.assertEqual(created.unidade_sigla, self.unidade.sigla)
        notification = Notificacao.objects.get(titulo="Crachás Provisórios | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)

    def test_api_crachas_list_returns_success_contract(self):
        self.client.force_login(self.user)
        CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            documento="12345678900",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_crachas_provisorios"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoa"], "Carlos Souza")

    def test_api_crachas_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_crachas_provisorios"), {"limit": "abc"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_mesmo_cracha_nao_pode_ser_retirado_sem_devolucao(self):
        self.client.force_login(self.user)
        CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            documento="12345678900",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:crachas_provisorios_new"),
            data={
                "cracha": "cracha_provisorio_01",
                "entrega": "2026-03-29T20:00",
                "devolucao": "",
                "pessoa_nome": "Ana Lima",
                "pessoa_documento": "98765432100",
                "observacao": "Tentativa de retirada duplicada.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Este crachá ainda está em uso e só ficará disponível após a devolução.",
        )
        self.assertEqual(CrachaProvisorio.objects.count(), 1)

    def test_cracha_volta_a_ficar_disponivel_apos_devolucao(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Carlos Souza", documento="12345678900")
        cracha = CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=pessoa,
            documento="12345678900",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:crachas_provisorios_edit", args=[cracha.pk]),
            data={
                "cracha": "cracha_provisorio_01",
                "entrega": timezone.localtime(cracha.entrega).strftime("%Y-%m-%dT%H:%M"),
                "devolucao": (timezone.localtime(cracha.entrega) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                "pessoa_nome": "Carlos Souza",
                "pessoa_documento": "12345678900",
                "observacao": "Crachá devolvido.",
            },
        )

        self.assertEqual(response.status_code, 302)
        cracha.refresh_from_db()
        self.assertIsNotNone(cracha.devolucao)
        notification = Notificacao.objects.get(titulo="Crachás Provisórios | Concluído")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)

        second_response = self.client.post(
            reverse("siop:crachas_provisorios_new"),
            data={
                "cracha": "cracha_provisorio_01",
                "entrega": "2026-03-30T08:00",
                "devolucao": "",
                "pessoa_nome": "Ana Lima",
                "pessoa_documento": "98765432100",
                "observacao": "Nova retirada após devolução.",
            },
        )

        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(CrachaProvisorio.objects.count(), 2)
        novo = CrachaProvisorio.objects.latest("id")
        self.assertEqual(novo.cracha, "cracha_provisorio_01")
        self.assertIsNone(novo.devolucao)

    def test_cracha_edit_atualiza_registro(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Carlos Souza", documento="12345678900")
        cracha = CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=pessoa,
            documento="12345678900",
            observacao="Inicial",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:crachas_provisorios_edit", args=[cracha.pk]),
            data={
                "cracha": "cracha_provisorio_01",
                "entrega": timezone.localtime(cracha.entrega).strftime("%Y-%m-%dT%H:%M"),
                "devolucao": "",
                "pessoa_nome": "Carlos Souza Atualizado",
                "pessoa_documento": "12345678900",
                "observacao": "Atualizado",
            },
        )

        self.assertEqual(response.status_code, 302)
        cracha.refresh_from_db()
        self.assertEqual(cracha.pessoa.nome, "Carlos Souza Atualizado")
        self.assertEqual(cracha.observacao, "Atualizado")

    def test_cracha_export_csv_returns_file(self):
        self.client.force_login(self.user)
        CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            documento="12345678900",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:crachas_provisorios_export"),
            data={"formato": "csv"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

    def test_cracha_list_filtra_em_uso(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Carlos Souza", documento="12345678900")
        CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=pessoa,
            documento="12345678900",
            criado_por=self.user,
            modificado_por=self.user,
        )
        CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_02",
            entrega=timezone.now(),
            devolucao=timezone.now() + timedelta(hours=1),
            pessoa=Pessoa.objects.create(nome="Ana Lima", documento="98765432100"),
            documento="98765432100",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:crachas_provisorios_list"), {"status": "em_uso"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carlos Souza")
        self.assertNotContains(response, "Ana Lima")

    def test_cracha_list_renderiza_status_em_uso(self):
        self.client.force_login(self.user)
        CrachaProvisorio.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            cracha="cracha_provisorio_01",
            entrega=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            documento="12345678900",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:crachas_provisorios_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carlos Souza")
        self.assertContains(response, "Em uso")


class ControleAtivosFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="ativos",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]
        self.unidade = Unidade.objects.create(
            nome="Parque do Caracol",
            sigla="PC",
            cidade="Canela",
            uf="RS",
        )
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def test_retirada_do_ativo_persiste_registro(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:controle_ativos_new"),
            data={
                "equipamento": "radio_01",
                "destino": "bombeiro_civil",
                "retirada": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "observacao": "Retirada inicial do ativo.",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = ControleAtivos.objects.latest("id")
        self.assertEqual(created.equipamento, "radio_01")
        self.assertEqual(created.destino, "bombeiro_civil")
        self.assertIsNone(created.devolucao)
        self.assertEqual(created.unidade, self.unidade)
        self.assertEqual(created.unidade_sigla, self.unidade.sigla)
        notification = Notificacao.objects.get(titulo="Controle de Ativos | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)

    def test_api_controle_ativos_list_returns_success_contract(self):
        self.client.force_login(self.user)
        ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_01",
            destino="bombeiro_civil",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_controle_ativos"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoa"], "Carlos Souza")

    def test_api_controle_ativos_filtra_por_status_e_respeita_offset(self):
        self.client.force_login(self.user)
        ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_01",
            destino="bombeiro_civil",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Primeiro Ativo", documento="12345678901"),
            criado_por=self.user,
            modificado_por=self.user,
        )
        ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="lanterna_01",
            destino="jardinagem",
            retirada=timezone.now() - timedelta(hours=3),
            devolucao=timezone.now() - timedelta(hours=1),
            pessoa=Pessoa.objects.create(nome="Segundo Ativo", documento="12345678902"),
            criado_por=self.user,
            modificado_por=self.user,
        )
        ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_02",
            destino="limpeza",
            retirada=timezone.now() - timedelta(hours=4),
            pessoa=Pessoa.objects.create(nome="Terceiro Ativo", documento="12345678903"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(
            reverse("siop:api_controle_ativos"),
            {"status": "em_uso", "limit": 1, "offset": 1},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["pagination"]["total"], 2)
        self.assertEqual(payload["meta"]["pagination"]["count"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoa"], "Terceiro Ativo")

    def test_api_controle_ativos_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_controle_ativos"), {"limit": "abc"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_mesmo_ativo_nao_pode_ser_retirado_sem_devolucao(self):
        self.client.force_login(self.user)
        ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_01",
            destino="bombeiro_civil",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_ativos_new"),
            data={
                "equipamento": "radio_01",
                "destino": "atendimento",
                "retirada": "2026-03-29T20:00",
                "devolucao": "",
                "pessoa_nome": "Ana Lima",
                "observacao": "Tentativa de retirada duplicada.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Este ativo ainda está em uso e só ficará disponível após a devolução.",
        )
        self.assertEqual(ControleAtivos.objects.count(), 1)

    def test_ativo_volta_a_ficar_disponivel_apos_devolucao(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Carlos Souza", documento="12345678900")
        ativo = ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_01",
            destino="bombeiro_civil",
            retirada=timezone.now(),
            pessoa=pessoa,
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_ativos_edit", args=[ativo.pk]),
            data={
                "equipamento": "radio_01",
                "destino": "bombeiro_civil",
                "retirada": timezone.localtime(ativo.retirada).strftime("%Y-%m-%dT%H:%M"),
                "devolucao": (timezone.localtime(ativo.retirada) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                "pessoa_nome": "Carlos Souza",
                "observacao": "Ativo devolvido.",
            },
        )

        self.assertEqual(response.status_code, 302)
        ativo.refresh_from_db()
        self.assertIsNotNone(ativo.devolucao)
        notification = Notificacao.objects.get(titulo="Controle de Ativos | Concluído")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)

        second_response = self.client.post(
            reverse("siop:controle_ativos_new"),
            data={
                "equipamento": "radio_01",
                "destino": "limpeza",
                "retirada": "2026-03-30T08:00",
                "devolucao": "",
                "pessoa_nome": "Ana Lima",
                "observacao": "Nova retirada após devolução.",
            },
        )

        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(ControleAtivos.objects.count(), 2)
        novo = ControleAtivos.objects.latest("id")
        self.assertEqual(novo.equipamento, "radio_01")
        self.assertEqual(novo.destino, "limpeza")
        self.assertIsNone(novo.devolucao)

    def test_ativo_edit_atualiza_registro(self):
        self.client.force_login(self.user)
        ativo = ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_01",
            destino="bombeiro_civil",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            observacao="Inicial",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_ativos_edit", args=[ativo.pk]),
            data={
                "equipamento": "radio_01",
                "destino": "limpeza",
                "retirada": timezone.localtime(ativo.retirada).strftime("%Y-%m-%dT%H:%M"),
                "devolucao": "",
                "pessoa_nome": "Carlos Souza Atualizado",
                "observacao": "Atualizado",
            },
        )

        self.assertEqual(response.status_code, 302)
        ativo.refresh_from_db()
        self.assertEqual(ativo.destino, "limpeza")
        self.assertEqual(ativo.pessoa.nome, "Carlos Souza Atualizado")
        self.assertEqual(ativo.observacao, "Atualizado")

    def test_ativo_export_xlsx_returns_file(self):
        self.client.force_login(self.user)
        ControleAtivos.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            equipamento="radio_01",
            destino="bombeiro_civil",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_ativos_export"),
            data={"formato": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            response["Content-Type"],
        )

    def test_ativo_rejeita_destino_fora_da_lista_permitida(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:controle_ativos_new"),
            data={
                "equipamento": "radio_01",
                "destino": "ciop",
                "retirada": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "observacao": "Destino inválido.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione um destino permitido para o controle de ativos.")
        self.assertEqual(ControleAtivos.objects.count(), 0)

    def test_ativo_destino_invalido_retorna_erro(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:controle_ativos_new"),
            data={
                "equipamento": "radio_01",
                "destino": "facilities",
                "retirada": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "observacao": "Destino inválido.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione um destino permitido para o controle de ativos.")
        self.assertEqual(ControleAtivos.objects.count(), 0)


class ControleChavesFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="chaves",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]
        self.unidade = Unidade.objects.create(
            nome="Parque do Caracol",
            sigla="PC",
            cidade="Canela",
            uf="RS",
        )
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def test_retirada_da_chave_persiste_registro(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:controle_chaves_new"),
            data={
                "area_chave": "Administrativo",
                "chave": "adm_001",
                "retirada": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "observacao": "Retirada inicial da chave.",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = ControleChaves.objects.latest("id")
        self.assertEqual(created.chave, "adm_001")
        self.assertIsNone(created.devolucao)
        self.assertEqual(created.unidade, self.unidade)
        self.assertEqual(created.unidade_sigla, self.unidade.sigla)
        notification = Notificacao.objects.get(titulo="Controle de Chaves | Novo Registrado")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)

    def test_api_controle_chaves_list_returns_success_contract(self):
        self.client.force_login(self.user)
        ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="adm_001",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_controle_chaves"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoa"], "Carlos Souza")

    def test_api_controle_chaves_filtra_por_area(self):
        self.client.force_login(self.user)
        ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="adm_001",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Pessoa ADM", documento="12345678911"),
            criado_por=self.user,
            modificado_por=self.user,
        )
        ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="ciop_004",
            retirada=timezone.now() - timedelta(hours=1),
            pessoa=Pessoa.objects.create(nome="Pessoa CIOP", documento="12345678912"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_controle_chaves"), {"area": "CIOP"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoa"], "Pessoa CIOP")

    def test_api_controle_chaves_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_controle_chaves"), {"limit": "abc"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_mesma_chave_nao_pode_ser_retirada_sem_devolucao(self):
        self.client.force_login(self.user)
        ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="adm_001",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_chaves_new"),
            data={
                "area_chave": "Administrativo",
                "chave": "adm_001",
                "retirada": "2026-03-29T20:00",
                "devolucao": "",
                "pessoa_nome": "Ana Lima",
                "observacao": "Tentativa de retirada duplicada.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Esta chave ainda está em uso e só ficará disponível após a devolução.",
        )
        self.assertEqual(ControleChaves.objects.count(), 1)

    def test_chave_volta_a_ficar_disponivel_apos_devolucao(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Carlos Souza", documento="12345678900")
        chave = ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="adm_001",
            retirada=timezone.now(),
            pessoa=pessoa,
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_chaves_edit", args=[chave.pk]),
            data={
                "area_chave": "Administrativo",
                "chave": "adm_001",
                "retirada": timezone.localtime(chave.retirada).strftime("%Y-%m-%dT%H:%M"),
                "devolucao": (timezone.localtime(chave.retirada) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                "pessoa_nome": "Carlos Souza",
                "observacao": "Chave devolvida.",
            },
        )

        self.assertEqual(response.status_code, 302)
        chave.refresh_from_db()
        self.assertIsNotNone(chave.devolucao)
        notification = Notificacao.objects.get(titulo="Controle de Chaves | Concluído")
        self.assertEqual(notification.modulo, Notificacao.MODULO_SIOP)
        self.assertEqual(notification.grupo, self.group_siop)

        second_response = self.client.post(
            reverse("siop:controle_chaves_new"),
            data={
                "area_chave": "Administrativo",
                "chave": "adm_001",
                "retirada": "2026-03-30T08:00",
                "devolucao": "",
                "pessoa_nome": "Ana Lima",
                "observacao": "Nova retirada após devolução.",
            },
        )

        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(ControleChaves.objects.count(), 2)
        novo = ControleChaves.objects.latest("id")
        self.assertEqual(novo.chave, "adm_001")
        self.assertIsNone(novo.devolucao)

    def test_chave_list_renderiza_registro(self):
        self.client.force_login(self.user)
        ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="adm_001",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            observacao="Registro para listagem",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:controle_chaves_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carlos Souza")
        self.assertContains(response, "Porta do Administrativo")

    def test_chave_export_xlsx_returns_file(self):
        self.client.force_login(self.user)
        ControleChaves.objects.create(
            unidade=self.unidade,
            unidade_sigla=self.unidade.sigla,
            chave="adm_001",
            retirada=timezone.now(),
            pessoa=Pessoa.objects.create(nome="Carlos Souza", documento="12345678900"),
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:controle_chaves_export"),
            data={"formato": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_chave_rejeita_area_incompativel(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:controle_chaves_new"),
            data={
                "area_chave": "CIOP",
                "chave": "adm_001",
                "retirada": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "observacao": "Área incompatível.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione uma chave compatível com a área escolhida.")
        self.assertEqual(ControleChaves.objects.count(), 0)

    def test_chave_exige_compatibilidade_entre_area_e_chave(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("siop:controle_chaves_new"),
            data={
                "area_chave": "Portaria",
                "chave": "adm_001",
                "retirada": "2026-03-29T19:00",
                "devolucao": "",
                "pessoa_nome": "Carlos Souza",
                "observacao": "Área incompatível.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione uma chave compatível com a área escolhida.")
        self.assertEqual(ControleChaves.objects.count(), 0)


class ControleEfetivoFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="efetivo",
            password="senha-forte-123",
        )
        self.catalogo_bc = catalogo_bc_data()

    def _payload(self):
        return {
            "plantao": "Diurno",
            "atendimento": "Ana Atendimento",
            "bilheteria": "Bruno Bilheteria",
            "bombeiro_civil": self.catalogo_bc[0]["chave"],
            "bombeiro_civil_2": self.catalogo_bc[1]["chave"],
            "bombeiro_hidraulico": "Edu BH",
            "ciop": "Fernanda CIOP",
            "eletrica": "Guilherme Elétrica",
            "artifice_civil": "Helena Artífice",
            "ti": "Igor TI",
            "facilities": "Julia Facilities",
            "manutencao": "Kaique Manutenção",
            "jardinagem": "Larissa Jardinagem",
            "limpeza": "Marcos Limpeza",
            "seguranca_trabalho": "Nina ST",
            "seguranca_patrimonial": "Otávio SP",
            "meio_ambiente": "Paula MA",
            "engenharia": "Rafael Engenharia",
            "estapar": "Sofia Estapar",
        }

    def test_efetivo_create_persiste_registro(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("siop:efetivo_new"), data=self._payload())

        self.assertEqual(response.status_code, 302)
        created = ControleEfetivo.objects.latest("id")
        self.assertEqual(created.plantao, "Diurno")
        self.assertEqual(created.atendimento, "Ana Atendimento")
        self.assertEqual(created.bombeiro_civil, self.catalogo_bc[0]["valor"])
        self.assertEqual(created.bombeiro_civil_2, self.catalogo_bc[1]["valor"])
        self.assertEqual(created.ciop, "Fernanda CIOP")
        self.assertEqual(created.modificado_por, self.user)

    def test_api_efetivo_list_returns_success_contract(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="Diurno",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil=self.catalogo_bc[0]["valor"],
            bombeiro_civil_2=self.catalogo_bc[1]["valor"],
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_efetivo"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["plantao"], "Diurno")

    def test_api_efetivo_filtra_por_busca_textual(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="Diurno",
            atendimento="Equipe A",
            bilheteria="Bilheteria A",
            ciop="Fernanda CIOP",
            criado_por=self.user,
            modificado_por=self.user,
        )
        ControleEfetivo.objects.create(
            plantao="Noturno",
            atendimento="Equipe B",
            bilheteria="Bilheteria B",
            ciop="Carlos Monitoramento",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:api_efetivo"), {"q": "Fernanda"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["plantao"], "Diurno")

    def test_api_efetivo_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_efetivo"), {"limit": "abc"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_efetivo_edit_atualiza_registro(self):
        self.client.force_login(self.user)
        registro = ControleEfetivo.objects.create(
            plantao="Inicial",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil="Inicial BC1",
            bombeiro_civil_2="Inicial BC2",
            bombeiro_hidraulico="Inicial BH",
            ciop="Inicial CIOP",
            eletrica="Inicial Elétrica",
            artifice_civil="Inicial Artífice",
            ti="Inicial TI",
            facilities="Inicial Facilities",
            manutencao="Inicial Manutenção",
            jardinagem="Inicial Jardinagem",
            limpeza="Inicial Limpeza",
            seguranca_trabalho="Inicial ST",
            seguranca_patrimonial="Inicial SP",
            meio_ambiente="Inicial MA",
            engenharia="Inicial Engenharia",
            estapar="Inicial Estapar",
            criado_por=self.user,
            modificado_por=self.user,
        )

        payload = self._payload()
        payload["plantao"] = "Noturno"
        payload["atendimento"] = "Atendimento Atualizado"
        payload["ciop"] = "Novo CIOP"

        response = self.client.post(reverse("siop:efetivo_edit", args=[registro.pk]), data=payload)

        self.assertEqual(response.status_code, 302)
        registro.refresh_from_db()
        self.assertEqual(registro.plantao, "Noturno")
        self.assertEqual(registro.atendimento, "Atendimento Atualizado")
        self.assertEqual(registro.ciop, "Novo CIOP")

    def test_efetivo_nao_permite_repetir_bombeiro_civil(self):
        self.client.force_login(self.user)
        payload = self._payload()
        payload["bombeiro_civil_2"] = payload["bombeiro_civil"]

        response = self.client.post(reverse("siop:efetivo_new"), data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bombeiro Civil 2 não pode repetir o mesmo nome do Bombeiro Civil 1.")
        self.assertEqual(ControleEfetivo.objects.count(), 0)

    def test_efetivo_permite_apenas_um_registro_por_dia(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="Diurno",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil=self.catalogo_bc[0]["valor"],
            bombeiro_civil_2=self.catalogo_bc[1]["valor"],
            bombeiro_hidraulico="Inicial BH",
            ciop="Inicial CIOP",
            eletrica="Inicial Elétrica",
            artifice_civil="Inicial Artífice",
            ti="Inicial TI",
            facilities="Inicial Facilities",
            manutencao="Inicial Manutenção",
            jardinagem="Inicial Jardinagem",
            limpeza="Inicial Limpeza",
            seguranca_trabalho="Inicial ST",
            seguranca_patrimonial="Inicial SP",
            meio_ambiente="Inicial MA",
            engenharia="Inicial Engenharia",
            estapar="Inicial Estapar",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(reverse("siop:efetivo_new"), data=self._payload())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe um registro de efetivo criado hoje. Edite o registro existente em vez de criar um novo.")
        self.assertEqual(ControleEfetivo.objects.count(), 1)

    def test_efetivo_export_csv_returns_file(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="Diurno",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil=self.catalogo_bc[0]["valor"],
            bombeiro_civil_2=self.catalogo_bc[1]["valor"],
            bombeiro_hidraulico="Inicial BH",
            ciop="Inicial CIOP",
            eletrica="Inicial Elétrica",
            artifice_civil="Inicial Artífice",
            ti="Inicial TI",
            facilities="Inicial Facilities",
            manutencao="Inicial Manutenção",
            jardinagem="Inicial Jardinagem",
            limpeza="Inicial Limpeza",
            seguranca_trabalho="Inicial ST",
            seguranca_patrimonial="Inicial SP",
            meio_ambiente="Inicial MA",
            engenharia="Inicial Engenharia",
            estapar="Inicial Estapar",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:efetivo_export"),
            data={"formato": "csv"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

    def test_efetivo_list_renderiza_registro_criado(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="Diurno",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil=self.catalogo_bc[0]["valor"],
            bombeiro_civil_2=self.catalogo_bc[1]["valor"],
            bombeiro_hidraulico="Inicial BH",
            ciop="Inicial CIOP",
            eletrica="Inicial Elétrica",
            artifice_civil="Inicial Artífice",
            ti="Inicial TI",
            facilities="Inicial Facilities",
            manutencao="Inicial Manutenção",
            jardinagem="Inicial Jardinagem",
            limpeza="Inicial Limpeza",
            seguranca_trabalho="Inicial ST",
            seguranca_patrimonial="Inicial SP",
            meio_ambiente="Inicial MA",
            engenharia="Inicial Engenharia",
            estapar="Inicial Estapar",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:efetivo_list"), {"q": "Diurno"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diurno")
        self.assertContains(response, self.user.username)

    def test_efetivo_dashboard_conta_plantao_como_posto_pendente(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil=self.catalogo_bc[0]["valor"],
            bombeiro_civil_2=self.catalogo_bc[1]["valor"],
            bombeiro_hidraulico="Inicial BH",
            ciop="Inicial CIOP",
            eletrica="Inicial Elétrica",
            artifice_civil="Inicial Artífice",
            ti="Inicial TI",
            facilities="Inicial Facilities",
            manutencao="Inicial Manutenção",
            jardinagem="Inicial Jardinagem",
            limpeza="Inicial Limpeza",
            seguranca_trabalho="Inicial ST",
            seguranca_patrimonial="Inicial SP",
            meio_ambiente="Inicial MA",
            engenharia="Inicial Engenharia",
            estapar="Inicial Estapar",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("siop:efetivo_index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard"]["postos_pendentes"], 1)

    def test_efetivo_export_xlsx_returns_file(self):
        self.client.force_login(self.user)
        ControleEfetivo.objects.create(
            plantao="Diurno",
            atendimento="Inicial Atendimento",
            bilheteria="Inicial Bilheteria",
            bombeiro_civil=self.catalogo_bc[0]["valor"],
            bombeiro_civil_2=self.catalogo_bc[1]["valor"],
            bombeiro_hidraulico="Inicial BH",
            ciop="Inicial CIOP",
            eletrica="Inicial Elétrica",
            artifice_civil="Inicial Artífice",
            ti="Inicial TI",
            facilities="Inicial Facilities",
            manutencao="Inicial Manutenção",
            jardinagem="Inicial Jardinagem",
            limpeza="Inicial Limpeza",
            seguranca_trabalho="Inicial ST",
            seguranca_patrimonial="Inicial SP",
            meio_ambiente="Inicial MA",
            engenharia="Inicial Engenharia",
            estapar="Inicial Estapar",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.post(
            reverse("siop:efetivo_export"),
            data={"formato": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class LiberacaoAcessoFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="liberacao",
            password="senha-forte-123",
        )
        self.group_siop = Group.objects.get_or_create(name="group_siop")[0]

    def _payload(self):
        return {
            "pessoa_nome": ["Marcos da Silva", "Ana Souza"],
            "pessoa_documento": ["12345678900", "98765432100"],
            "motivo": "Acesso temporário para atividade técnica.",
            "data_liberacao": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "empresa": "PrestServ",
            "solicitante": "Coordenação Operacional",
        }

    def test_liberacao_acesso_create_persiste_registro(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("siop:liberacao_acesso_new"), data=self._payload())

        self.assertEqual(response.status_code, 302)
        created = LiberacaoAcesso.objects.latest("id")
        self.assertEqual(created.pessoas.count(), 2)
        self.assertEqual(created.pessoas.first().nome, "Marcos da Silva")
        self.assertEqual(created.pessoas.first().documento, "12345678900")
        self.assertEqual(created.empresa, "PrestServ")
        self.assertEqual(created.modificado_por, self.user)
        notification = Notificacao.objects.get(titulo="Liberação de Acesso | Novo Registrado")
        self.assertEqual(notification.grupo, self.group_siop)

    def test_api_liberacao_acesso_list_returns_success_contract(self):
        self.client.force_login(self.user)
        liberacao = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        liberacao.pessoas.set(
            [
                Pessoa.objects.create(nome="Pessoa Um", documento="11111111111"),
                Pessoa.objects.create(nome="Pessoa Dois", documento="22222222222"),
            ]
        )

        response = self.client.get(reverse("siop:api_liberacao_acesso"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(len(payload["data"]["registros"][0]["pessoas"]), 2)

    def test_api_liberacao_acesso_filtra_por_empresa_e_solicitante(self):
        self.client.force_login(self.user)
        primeira = LiberacaoAcesso.objects.create(
            motivo="Atividade técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Alfa",
            solicitante="Coordenação Alfa",
            criado_por=self.user,
            modificado_por=self.user,
        )
        primeira.pessoas.add(Pessoa.objects.create(nome="Pessoa Alfa", documento="33333333333"))
        segunda = LiberacaoAcesso.objects.create(
            motivo="Visita institucional.",
            data_liberacao=timezone.now() - timedelta(days=1),
            empresa="Empresa Beta",
            solicitante="Coordenação Beta",
            criado_por=self.user,
            modificado_por=self.user,
        )
        segunda.pessoas.add(Pessoa.objects.create(nome="Pessoa Beta", documento="44444444444"))

        response = self.client.get(
            reverse("siop:api_liberacao_acesso"),
            {"empresa": "Beta", "solicitante": "Coordenação Beta"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["empresa"], "Empresa Beta")

    def test_api_liberacao_acesso_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("siop:api_liberacao_acesso"), {"limit": "abc"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_liberacao_acesso_create_salva_anexo(self):
        self.client.force_login(self.user)
        arquivo = SimpleUploadedFile("liberacao.txt", b"conteudo teste", content_type="text/plain")

        response = self.client.post(
            reverse("siop:liberacao_acesso_new"),
            data={**self._payload(), "anexos": [arquivo]},
        )

        self.assertEqual(response.status_code, 302)
        created = LiberacaoAcesso.objects.latest("id")
        self.assertEqual(created.anexos.count(), 1)
        self.assertEqual(created.anexos.first().nome_arquivo, "liberacao.txt")

    def test_liberacao_acesso_edit_atualiza_registro(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Nome Inicial", documento="00011122233")
        registro = LiberacaoAcesso.objects.create(
            motivo="Motivo inicial",
            data_liberacao=timezone.now(),
            empresa="Empresa Inicial",
            solicitante="Solicitante Inicial",
            criado_por=self.user,
            modificado_por=self.user,
        )
        registro.pessoas.add(pessoa)

        payload = self._payload()
        payload["empresa"] = "Empresa Atualizada"
        payload["solicitante"] = "Solicitante Atualizado"

        response = self.client.post(reverse("siop:liberacao_acesso_edit", args=[registro.pk]), data=payload)

        self.assertEqual(response.status_code, 302)
        registro.refresh_from_db()
        self.assertEqual(registro.empresa, "Empresa Atualizada")
        self.assertEqual(registro.solicitante, "Solicitante Atualizado")
        self.assertEqual(registro.pessoas.count(), 2)
        self.assertIn("Ana Souza", list(registro.pessoas.values_list("nome", flat=True)))
        self.assertIn("98765432100", list(registro.pessoas.values_list("documento", flat=True)))
        notification = Notificacao.objects.get(titulo="Liberação de Acesso | Atualizado")
        self.assertEqual(notification.grupo, self.group_siop)

    def test_liberacao_acesso_edit_nao_muta_pessoa_global_existente(self):
        self.client.force_login(self.user)
        pessoa_global = Pessoa.objects.create(nome="Pessoa Compartilhada", documento="00011122233")
        registro = LiberacaoAcesso.objects.create(
            motivo="Motivo inicial",
            data_liberacao=timezone.now(),
            empresa="Empresa Inicial",
            solicitante="Solicitante Inicial",
            criado_por=self.user,
            modificado_por=self.user,
        )
        registro.pessoas.add(pessoa_global)

        response = self.client.post(
            reverse("siop:liberacao_acesso_edit", args=[registro.pk]),
            data={
                "pessoa_nome": ["Nome Alterado"],
                "pessoa_documento": ["99988877766"],
                "motivo": "Motivo alterado",
                "data_liberacao": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "empresa": "Empresa Atualizada",
                "solicitante": "Solicitante Atualizado",
            },
        )

        self.assertEqual(response.status_code, 302)
        pessoa_global.refresh_from_db()
        self.assertEqual(pessoa_global.nome, "Pessoa Compartilhada")
        self.assertEqual(pessoa_global.documento, "00011122233")
        registro.refresh_from_db()
        pessoa_vinculada = registro.pessoas.get()
        self.assertNotEqual(pessoa_vinculada.id, pessoa_global.id)
        self.assertEqual(pessoa_vinculada.nome, "Nome Alterado")
        self.assertEqual(pessoa_vinculada.documento, "99988877766")

    def test_liberacao_acesso_list_renderiza_registros(self):
        self.client.force_login(self.user)
        pessoa_1 = Pessoa.objects.create(nome="Pessoa Teste", documento="99999999999")
        pessoa_2 = Pessoa.objects.create(nome="Pessoa Extra", documento="88888888888")
        registro = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        registro.pessoas.set([pessoa_1, pessoa_2])

        response = self.client.get(reverse("siop:liberacao_acesso_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pessoa Teste")
        self.assertContains(response, "Pessoa Extra")
        self.assertContains(response, "Empresa Teste")

    def test_liberacao_acesso_registra_chegada_para_uma_pessoa(self):
        self.client.force_login(self.user)
        pessoa_1 = Pessoa.objects.create(nome="Pessoa Um", documento="11111111111")
        pessoa_2 = Pessoa.objects.create(nome="Pessoa Dois", documento="22222222222")
        liberacao = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        liberacao.pessoas.set([pessoa_1, pessoa_2])

        response = self.client.post(
            reverse("siop:api_liberacao_acesso_chegada", args=[liberacao.pk]),
            data={
                "chegada_acao": "single",
                "pessoa_id": pessoa_1.id,
                "p1": "lucas_cunha",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(AcessoTerceiros.objects.count(), 1)
        acesso = AcessoTerceiros.objects.latest("id")
        self.assertEqual(acesso.pessoa, pessoa_1)
        self.assertEqual(acesso.empresa, "Empresa Teste")
        self.assertEqual(acesso.p1, "lucas_cunha")
        self.assertEqual(acesso.descricao_acesso, "Visita técnica.")
        liberacao.refresh_from_db()
        self.assertEqual(liberacao.chegadas_registradas, [pessoa_1.id])
        notification = Notificacao.objects.get(titulo="Liberação de Acesso | Chegada Registrada")
        self.assertEqual(notification.grupo, self.group_siop)

    def test_liberacao_acesso_registra_chegada_para_todos(self):
        self.client.force_login(self.user)
        pessoa_1 = Pessoa.objects.create(nome="Pessoa Um", documento="11111111111")
        pessoa_2 = Pessoa.objects.create(nome="Pessoa Dois", documento="22222222222")
        liberacao = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        liberacao.pessoas.set([pessoa_1, pessoa_2])

        response = self.client.post(
            reverse("siop:api_liberacao_acesso_chegada", args=[liberacao.pk]),
            data={
                "chegada_acao": "all",
                "p1": "lucas_cunha",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(AcessoTerceiros.objects.count(), 2)
        self.assertEqual(
            set(AcessoTerceiros.objects.values_list("pessoa__nome", flat=True)),
            {"Pessoa Um", "Pessoa Dois"},
        )
        liberacao.refresh_from_db()
        self.assertEqual(set(liberacao.chegadas_registradas), {pessoa_1.id, pessoa_2.id})

    def test_liberacao_acesso_chegada_de_todos_ja_registrada_nao_duplica(self):
        self.client.force_login(self.user)
        pessoa_1 = Pessoa.objects.create(nome="Pessoa Um", documento="11111111111")
        pessoa_2 = Pessoa.objects.create(nome="Pessoa Dois", documento="22222222222")
        liberacao = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
            chegadas_registradas=[pessoa_1.id, pessoa_2.id],
        )
        liberacao.pessoas.set([pessoa_1, pessoa_2])

        response = self.client.post(
            reverse("siop:api_liberacao_acesso_chegada", args=[liberacao.pk]),
            data={"chegada_acao": "all", "p1": "lucas_cunha"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(AcessoTerceiros.objects.count(), 0)
        self.assertIn("Nenhuma chegada foi registrada.", response.json()["error"]["message"])

    def test_liberacao_acesso_export_xlsx_returns_file(self):
        self.client.force_login(self.user)
        liberacao = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        liberacao.pessoas.set(
            [
                Pessoa.objects.create(nome="Pessoa Um", documento="11111111111"),
                Pessoa.objects.create(nome="Pessoa Dois", documento="22222222222"),
            ]
        )

        response = self.client.post(
            reverse("siop:liberacao_acesso_export"),
            data={"formato": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            response["Content-Type"],
        )

    def test_liberacao_acesso_rejeita_documento_duplicado_no_mesmo_registro(self):
        self.client.force_login(self.user)
        payload = self._payload()
        payload["pessoa_documento"] = ["12345678900", "12345678900"]

        response = self.client.post(reverse("siop:liberacao_acesso_new"), data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não repita o mesmo documento na mesma liberação.")
        self.assertEqual(LiberacaoAcesso.objects.count(), 0)

    def test_liberacao_acesso_chegada_sem_p1_nao_cria_acesso(self):
        self.client.force_login(self.user)
        pessoa = Pessoa.objects.create(nome="Pessoa Um", documento="11111111111")
        liberacao = LiberacaoAcesso.objects.create(
            motivo="Visita técnica.",
            data_liberacao=timezone.now(),
            empresa="Empresa Teste",
            solicitante="Solicitante Teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        liberacao.pessoas.set([pessoa])

        response = self.client.post(
            reverse("siop:api_liberacao_acesso_chegada", args=[liberacao.pk]),
            data={"chegada_acao": "single", "pessoa_id": pessoa.id, "p1": ""},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.json()["error"]["message"], "Selecione o P1 para registrar a chegada.")
        self.assertEqual(AcessoTerceiros.objects.count(), 0)


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
