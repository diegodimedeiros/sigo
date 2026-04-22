from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from sesmt.models import ControleAtendimento, Flora, Himenoptero, Manejo
from sigo.models import Assinatura, ConfiguracaoSistema, Foto, Unidade

User = get_user_model()


class ReportosHomeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportos",
            password="SenhaForte123!",
        )
        group = Group.objects.create(name="group_reportos")
        self.user.groups.add(group)
        self.client.force_login(self.user)

    def test_home_renderiza_modulo(self):
        response = self.client.get(reverse("reportos:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atendimento")
        self.assertContains(response, "Flora")
        self.assertContains(response, "Manejo")
        self.assertContains(response, "Himenópteros")
        self.assertContains(response, 'data-pwa-sync-detail')
        self.assertContains(response, reverse("reportos:offline_diagnostics"))

    def test_offline_diagnostics_renderiza(self):
        response = self.client.get(reverse("reportos:offline_diagnostics"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diagnóstico Offline")
        self.assertContains(response, 'data-pwa-diag-cache-list')

    def test_subareas_renderizam(self):
        response_atendimento = self.client.get(reverse("reportos:atendimento_index"))
        response_manejo = self.client.get(reverse("reportos:manejo_index"))
        response_flora = self.client.get(reverse("reportos:flora_index"))
        response_himenopteros = self.client.get(reverse("reportos:himenopteros_index"))

        self.assertEqual(response_atendimento.status_code, 200)
        self.assertEqual(response_manejo.status_code, 200)
        self.assertEqual(response_flora.status_code, 200)
        self.assertEqual(response_himenopteros.status_code, 200)
        self.assertContains(response_atendimento, "Atendimento")
        self.assertContains(response_manejo, "Manejo")
        self.assertContains(response_flora, "Flora")
        self.assertContains(response_himenopteros, "Monitor Himenóptero")

    def test_formularios_novos_renderizam(self):
        response_atendimento = self.client.get(reverse("reportos:atendimento_new"))
        response_manejo = self.client.get(reverse("reportos:manejo_new"))
        response_flora = self.client.get(reverse("reportos:flora_new"))
        response_himenopteros = self.client.get(reverse("reportos:himenopteros_new"))

        self.assertEqual(response_atendimento.status_code, 200)
        self.assertEqual(response_manejo.status_code, 200)
        self.assertEqual(response_flora.status_code, 200)
        self.assertEqual(response_himenopteros.status_code, 200)
        self.assertContains(response_atendimento, "Novo Registro de Atendimento")
        self.assertContains(response_manejo, "Novo Registro de Manejo")
        self.assertContains(response_flora, "Novo Registro de Flora")
        self.assertContains(response_himenopteros, "Novo Registro de Himenóptero")

    def test_api_catalogos_retorna_dados_para_uso_offline(self):
        response = self.client.get(reverse("reportos:api_catalogos"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("locais_por_area", payload["data"])
        self.assertIn("especies_por_classe", payload["data"])

    def test_export_routes_are_registered(self):
        self.assertEqual(reverse("reportos:atendimento_export"), "/reportos/atendimento/exportar/")
        self.assertEqual(reverse("reportos:api_atendimento_export"), "/reportos/api/atendimento/export/")
        self.assertEqual(reverse("reportos:manejo_export"), "/reportos/manejo/exportar/")
        self.assertEqual(reverse("reportos:api_manejo_export"), "/reportos/api/manejo/export/")
        self.assertEqual(reverse("reportos:flora_export"), "/reportos/flora/exportar/")
        self.assertEqual(reverse("reportos:api_flora_export"), "/reportos/api/flora/export/")
        self.assertEqual(reverse("reportos:himenopteros_export"), "/reportos/himenopteros/exportar/")
        self.assertEqual(reverse("reportos:api_himenopteros_export"), "/reportos/api/himenopteros/export/")

    def test_old_home_aliases_are_not_registered(self):
        with self.assertRaises(NoReverseMatch):
            reverse("reportos:atendimento_home")
        with self.assertRaises(NoReverseMatch):
            reverse("reportos:manejo_home")
        with self.assertRaises(NoReverseMatch):
            reverse("reportos:flora_home")


class ReportosAtendimentoApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportos_api",
            password="SenhaForte123!",
        )
        group = Group.objects.create(name="group_reportos")
        self.user.groups.add(group)
        self.client.force_login(self.user)
        self.unidade = Unidade.objects.create(nome="Parque do Caracol", sigla="PC")
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def _payload(self, **overrides):
        payload = {
            "tipo_pessoa": "colaborador",
            "pessoa_nome": "Diego Medeiros",
            "pessoa_documento": "12345678900",
            "contato_endereco": "Rodovia do Parque, 1000",
            "contato_bairro": "Caracol",
            "contato_cidade": "Canela",
            "contato_estado": "RS",
            "contato_pais": "Brasil",
            "telefone": "54999999999",
            "email": "diego@example.com",
            "area_atendimento": "entrada",
            "local": "entrada_de_pedestres",
            "data_atendimento": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "tipo_ocorrencia": "mal_subito",
            "responsavel_atendimento": "Luciana Pires",
            "descricao": "Paciente atendido com primeiros socorros e liberado.",
            "primeiros_socorros": "",
        }
        payload.update(overrides)
        return payload

    def test_api_atendimento_create_retorna_redirect_do_reportos(self):
        response = self.client.post(reverse("reportos:api_atendimento"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        atendimento = ControleAtendimento.objects.get()
        self.assertEqual(payload["data"]["id"], atendimento.pk)
        self.assertEqual(
            payload["data"]["redirect_url"],
            reverse("reportos:atendimento_view", args=[atendimento.pk]),
        )


class ReportosManejoApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportos_manejo",
            password="SenhaForte123!",
        )
        group = Group.objects.create(name="group_reportos")
        self.user.groups.add(group)
        self.client.force_login(self.user)
        self.unidade = Unidade.objects.create(nome="Parque do Caracol", sigla="PC")
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def _payload(self, **overrides):
        foto_captura = SimpleUploadedFile("captura.jpg", b"capture", content_type="image/jpeg")
        payload = {
            "data_hora": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "classe": "mamifero",
            "nome_popular": "quati",
            "nome_cientifico": "Nasua nasua",
            "estagio_desenvolvimento": "Adulto",
            "area_captura": "entrada",
            "local_captura": "entrada_de_pedestres",
            "descricao_local": "Próximo ao acesso principal.",
            "importancia_medica": "false",
            "realizado_manejo": "false",
            "responsavel_manejo": "",
            "area_soltura": "",
            "local_soltura": "",
            "descricao_local_soltura": "",
            "acionado_orgao_publico": "false",
            "orgao_publico": "",
            "numero_boletim_ocorrencia": "",
            "motivo_acionamento": "",
            "observacoes": "Animal conduzido sem intercorrências.",
            "latitude_captura": "-29.3142851",
            "longitude_captura": "-50.8541445",
            "latitude_soltura": "",
            "longitude_soltura": "",
            "foto_captura": foto_captura,
        }
        payload.update(overrides)
        return payload

    def test_api_manejo_create_retorna_redirect_do_reportos(self):
        response = self.client.post(reverse("reportos:api_manejo"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        manejo = Manejo.objects.get()
        self.assertEqual(payload["data"]["id"], manejo.pk)
        self.assertEqual(payload["data"]["redirect_url"], reverse("reportos:manejo_view", args=[manejo.pk]))

    def test_api_manejo_detail_reescreve_urls_de_evidencias(self):
        self.client.post(reverse("reportos:api_manejo"), data=self._payload())
        manejo = Manejo.objects.get()
        content_type = ContentType.objects.get_for_model(Manejo)

        Foto.objects.create(
            content_type=content_type,
            object_id=manejo.pk,
            tipo=Foto.TIPO_SOLTURA,
            nome_arquivo="soltura.jpg",
            mime_type="image/jpeg",
            arquivo=b"release-image",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("reportos:api_manejo_detail", args=[manejo.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        fotos_captura = payload["data"]["evidencias"]["fotos_captura"]
        fotos_soltura = payload["data"]["evidencias"]["fotos_soltura"]
        self.assertGreaterEqual(len(fotos_captura), 1)
        self.assertEqual(len(fotos_soltura), 1)
        self.assertTrue(fotos_captura[0]["url"].startswith("/reportos/manejo/"))
        self.assertTrue(fotos_soltura[0]["url"].startswith("/reportos/manejo/"))

    def test_api_manejo_update_mantem_redirect_do_reportos(self):
        self.client.post(reverse("reportos:api_manejo"), data=self._payload())
        manejo = Manejo.objects.get()
        foto_soltura = SimpleUploadedFile("soltura.jpg", b"release", content_type="image/jpeg")

        response = self.client.post(
            reverse("reportos:api_manejo_detail", args=[manejo.pk]),
            data=self._payload(
                realizado_manejo="true",
                responsavel_manejo="jean_carlos_da_silva_agirres",
                area_soltura="trilhas_e_locais",
                local_soltura="trilha_do_silencio",
                descricao_local_soltura="Soltura em área protegida.",
                acionado_orgao_publico="true",
                orgao_publico="Polícia Ambiental",
                numero_boletim_ocorrencia="BO-12345",
                motivo_acionamento="Avaliação preventiva.",
                latitude_soltura="-29.3152851",
                longitude_soltura="-50.8551445",
                foto_soltura=foto_soltura,
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        manejo.refresh_from_db()
        self.assertTrue(manejo.realizado_manejo)
        self.assertEqual(payload["data"]["redirect_url"], reverse("reportos:manejo_view", args=[manejo.pk]))


class ReportosFloraApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportos_flora",
            password="SenhaForte123!",
        )
        group = Group.objects.create(name="group_reportos")
        self.user.groups.add(group)
        self.client.force_login(self.user)
        self.unidade = Unidade.objects.create(nome="Parque do Caracol", sigla="PC")
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def _payload(self, **overrides):
        foto_antes = SimpleUploadedFile("antes.jpg", b"before", content_type="image/jpeg")
        payload = {
            "data_hora_inicio": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "responsavel_registro": "diego_pereira_bicca_geloch",
            "area": "entrada",
            "local": "entrada_de_pedestres",
            "condicao": "presenca_de_galhos_secos",
            "isolamento_area": "true",
            "justificativa": "Monitoramento de rotina.",
            "latitude": "-29.3142851",
            "longitude": "-50.8541445",
            "foto_antes": foto_antes,
        }
        payload.update(overrides)
        return payload

    def test_api_flora_create_retorna_redirect_do_reportos(self):
        response = self.client.post(reverse("reportos:api_flora"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        flora = Flora.objects.get()
        self.assertEqual(payload["data"]["id"], flora.pk)
        self.assertEqual(payload["data"]["redirect_url"], reverse("reportos:flora_view", args=[flora.pk]))

    def test_api_flora_detail_reescreve_urls_de_evidencias(self):
        self.client.post(reverse("reportos:api_flora"), data=self._payload())
        flora = Flora.objects.get()
        content_type = ContentType.objects.get_for_model(Flora)

        Foto.objects.create(
            content_type=content_type,
            object_id=flora.pk,
            tipo=Foto.TIPO_FLORA_DEPOIS,
            nome_arquivo="depois.jpg",
            mime_type="image/jpeg",
            arquivo=b"after-image",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("reportos:api_flora_detail", args=[flora.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        fotos_antes = payload["data"]["evidencias"]["foto_antes"]
        fotos_depois = payload["data"]["evidencias"]["foto_depois"]
        self.assertGreaterEqual(len(fotos_antes), 1)
        self.assertEqual(len(fotos_depois), 1)
        self.assertTrue(fotos_antes[0]["url"].startswith("/reportos/flora/"))
        self.assertTrue(fotos_depois[0]["url"].startswith("/reportos/flora/"))

    def test_api_flora_update_mantem_redirect_do_reportos(self):
        self.client.post(reverse("reportos:api_flora"), data=self._payload())
        flora = Flora.objects.get()

        response = self.client.post(
            reverse("reportos:api_flora_detail", args=[flora.pk]),
            data=self._payload(
                responsavel_registro="outro_responsavel",
                justificativa="Atualização via API do ReportOS.",
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        flora.refresh_from_db()
        self.assertEqual(payload["data"]["redirect_url"], reverse("reportos:flora_view", args=[flora.pk]))


class ReportosHimenopterosApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportos_himenopteros",
            password="SenhaForte123!",
        )
        group = Group.objects.create(name="group_reportos")
        self.user.groups.add(group)
        self.client.force_login(self.user)
        self.unidade = Unidade.objects.create(nome="Parque do Caracol", sigla="PC")
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def _payload(self, **overrides):
        foto = SimpleUploadedFile("registro.jpg", b"image-data", content_type="image/jpeg")
        payload = {
            "data_hora_inicio": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "responsavel_registro": "diego_pereira_bicca_geloch",
            "area": "entrada",
            "local": "entrada_de_pedestres",
            "descricao_local": "Estrutura próxima à bilheteria.",
            "hipomenoptero": "vespa",
            "popular": "Vespa",
            "especie": "Vespidae sp.",
            "proximidade_pessoas": "alta",
            "classificacao_risco": "alto",
            "isolamento_area": "true",
            "condicao": "ninho_estrutura",
            "acao_realizada": "isolamento_area",
            "observacao": "Área isolada para inspeção técnica.",
            "justificativa_tecnica": "",
            "latitude": "-29.3142851",
            "longitude": "-50.8541445",
            "fotos": foto,
        }
        payload.update(overrides)
        return payload

    def test_api_himenopteros_create_retorna_redirect_do_reportos(self):
        response = self.client.post(reverse("reportos:api_himenopteros"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        registro = Himenoptero.objects.get()
        self.assertEqual(payload["data"]["id"], registro.pk)
        self.assertEqual(payload["data"]["redirect_url"], reverse("reportos:himenopteros_view", args=[registro.pk]))

    def test_api_himenopteros_detail_reescreve_urls_de_evidencias(self):
        self.client.post(reverse("reportos:api_himenopteros"), data=self._payload())
        registro = Himenoptero.objects.get()

        response = self.client.get(reverse("reportos:api_himenopteros_detail", args=[registro.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        fotos = payload["data"]["evidencias"]["fotos"]
        self.assertEqual(len(fotos), 1)
        self.assertTrue(fotos[0]["url"].startswith("/reportos/himenopteros/"))

    def test_api_himenopteros_update_mantem_redirect_do_reportos(self):
        self.client.post(reverse("reportos:api_himenopteros"), data=self._payload())
        registro = Himenoptero.objects.get()

        response = self.client.post(
            reverse("reportos:api_himenopteros_detail", args=[registro.pk]),
            data={
                "data_hora_inicio": timezone.localtime(registro.data_hora_inicio).strftime("%Y-%m-%dT%H:%M"),
                "data_hora_fim": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "responsavel_registro": "outro_responsavel",
                "area": "outra_area",
                "local": "outro_local",
                "descricao_local": "Estrutura próxima à bilheteria, com atualização.",
                "hipomenoptero": "marimbondo",
                "popular": "Marimbondo",
                "especie": "Vespidae sp.",
                "proximidade_pessoas": "baixa",
                "classificacao_risco": "baixo",
                "condicao": "sem_intervencao",
                "acao_realizada": "monitoramento",
                "observacao": "Acompanhamento realizado sem nova exigência de isolamento.",
                "justificativa_tecnica": "",
                "latitude": "-29.3142851",
                "longitude": "-50.8541445",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        registro.refresh_from_db()
        self.assertEqual(payload["data"]["redirect_url"], reverse("reportos:himenopteros_view", args=[registro.pk]))

    def test_api_atendimento_list_reescreve_view_url_para_reportos(self):
        self.client.post(reverse("reportos:api_atendimento"), data=self._payload())

        response = self.client.get(reverse("reportos:api_atendimento"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(len(payload["data"]["registros"]), 1)
        self.assertTrue(payload["data"]["registros"][0]["view_url"].startswith("/reportos/atendimento/"))

    def test_api_atendimento_detail_reescreve_urls_de_evidencias(self):
        self.client.post(reverse("reportos:api_atendimento"), data=self._payload())
        atendimento = ControleAtendimento.objects.get()
        content_type = ContentType.objects.get_for_model(ControleAtendimento)

        Foto.objects.create(
            content_type=content_type,
            object_id=atendimento.pk,
            tipo=Foto.TIPO_CAPTURA,
            nome_arquivo="foto.jpg",
            mime_type="image/jpeg",
            arquivo=b"fake-image-content",
            criado_por=self.user,
            modificado_por=self.user,
        )
        Assinatura.objects.create(
            content_type=content_type,
            object_id=atendimento.pk,
            nome_arquivo="assinatura.png",
            mime_type="image/png",
            arquivo=b"fake-signature-content",
            criado_por=self.user,
            modificado_por=self.user,
        )

        response = self.client.get(reverse("reportos:api_atendimento_detail", args=[atendimento.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        fotos = payload["data"]["evidencias"]["fotos"]
        assinaturas = payload["data"]["evidencias"]["assinaturas"]
        self.assertEqual(len(fotos), 1)
        self.assertEqual(len(assinaturas), 1)
        self.assertTrue(fotos[0]["url"].startswith("/reportos/atendimento/"))
        self.assertIn("/fotos/", fotos[0]["url"])
        self.assertTrue(assinaturas[0]["url"].startswith("/reportos/atendimento/"))
        self.assertIn("/assinaturas/", assinaturas[0]["url"])

    def test_api_atendimento_update_mantem_redirect_do_reportos(self):
        self.client.post(reverse("reportos:api_atendimento"), data=self._payload())
        atendimento = ControleAtendimento.objects.get()

        response = self.client.post(
            reverse("reportos:api_atendimento_detail", args=[atendimento.pk]),
            data=self._payload(
                responsavel_atendimento="Fernanda Costa",
                atendimentos="on",
                primeiros_socorros="curativo",
                descricao="Atendimento atualizado via API do ReportOS.",
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        atendimento.refresh_from_db()
        self.assertEqual(atendimento.responsavel_atendimento, "Fernanda Costa")
        self.assertEqual(
            payload["data"]["redirect_url"],
            reverse("reportos:atendimento_view", args=[atendimento.pk]),
        )
