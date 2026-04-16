from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from sigo.models import Assinatura, ConfiguracaoSistema, Foto, Geolocalizacao, Notificacao, Unidade
from sesmt.models import ControleAtendimento, Flora, Manejo, Testemunha, Himenoptero


class AtendimentoFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="sesmt", password="senha-forte-123")
        self.group = Group.objects.create(name="group_sesmt")
        self.user.groups.add(self.group)
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

    def test_atendimento_new_cria_registro_real(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("sesmt:atendimento_new"), data=self._payload())

        self.assertEqual(response.status_code, 302)
        atendimento = ControleAtendimento.objects.get()
        self.assertEqual(atendimento.unidade, self.unidade)
        self.assertEqual(atendimento.pessoa.nome, "Diego Medeiros")
        self.assertEqual(atendimento.responsavel_atendimento, "Luciana Pires")
        self.assertEqual(Notificacao.objects.filter(modulo=Notificacao.MODULO_SESMT).count(), 1)

    def test_atendimento_list_renderiza_registro_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:atendimento_new"), data=self._payload())

        response = self.client.get(reverse("sesmt:atendimento_list"), {"q": "Diego"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diego Medeiros")
        self.assertContains(response, "Mal súbito")

    def test_atendimento_view_renderiza_detalhe_real(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("sesmt:atendimento_new"),
            data=self._payload(
                houve_remocao="on",
                transporte="ambulancia_parque",
                encaminhamento="hospital_publico",
                hospital="Hospital Teste",
            ),
        )
        atendimento = ControleAtendimento.objects.get()

        response = self.client.get(reverse("sesmt:atendimento_view", args=[atendimento.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carregando resumo do atendimento")
        self.assertContains(response, reverse("sesmt:api_atendimento_detail", args=[atendimento.pk]))
        self.assertContains(response, reverse("sesmt:atendimento_export_view_pdf", args=[atendimento.pk]))

    def test_api_atendimento_create_retorna_contrato_de_sucesso(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("sesmt:api_atendimento"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)
        self.assertIn("redirect_url", payload["data"])
        atendimento = ControleAtendimento.objects.get()
        self.assertEqual(payload["data"]["id"], atendimento.pk)

    def test_api_atendimento_detail_retorna_payload_estruturado(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("sesmt:atendimento_new"),
            data=self._payload(
                houve_remocao="on",
                transporte="ambulancia_parque",
                encaminhamento="hospital_publico",
                hospital="Hospital Teste",
            ),
        )
        atendimento = ControleAtendimento.objects.get()

        response = self.client.get(reverse("sesmt:api_atendimento_detail", args=[atendimento.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], atendimento.pk)
        self.assertEqual(payload["data"]["pessoa"]["nome"], "Diego Medeiros")
        self.assertEqual(payload["data"]["transporte_label"], "Ambulância Parque")

    def test_api_atendimento_update_retorna_sucesso_e_atualiza(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:atendimento_new"), data=self._payload())
        atendimento = ControleAtendimento.objects.get()

        response = self.client.post(
            reverse("sesmt:api_atendimento_detail", args=[atendimento.pk]),
            data=self._payload(
                responsavel_atendimento="Fernanda Costa",
                atendimentos="on",
                primeiros_socorros="curativo",
                descricao="Atendimento atualizado via API.",
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        atendimento.refresh_from_db()
        self.assertTrue(atendimento.atendimentos)
        self.assertEqual(atendimento.responsavel_atendimento, "Fernanda Costa")
        self.assertEqual(atendimento.primeiros_socorros, "curativo")
        self.assertEqual(payload["data"]["redirect_url"], atendimento.get_absolute_url())
        self.assertEqual(Notificacao.objects.filter(modulo=Notificacao.MODULO_SESMT).count(), 2)

    def test_api_atendimento_list_filtra_por_status_e_paginacao(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:atendimento_new"), data=self._payload(pessoa_nome="Pessoa Atendimento", pessoa_documento="111"))
        self.client.post(
            reverse("sesmt:atendimento_new"),
            data=self._payload(
                pessoa_nome="Pessoa Recusa",
                pessoa_documento="222",
                recusa_atendimento="on",
                descricao="Recusa formal registrada.",
            ),
        )

        response = self.client.get(
            reverse("sesmt:api_atendimento"),
            {"status": "recusa", "limit": 1, "offset": 0},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["meta"]["pagination"]["count"], 1)
        self.assertEqual(payload["data"]["registros"][0]["pessoa"], "Pessoa Recusa")
        self.assertEqual(payload["data"]["registros"][0]["atendimento_label"], "Não")

    def test_api_atendimento_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("sesmt:api_atendimento"), {"limit": "abc", "offset": "xyz"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_api_atendimento_visitante_estrangeiro_exige_provincia_em_vez_de_estado(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("sesmt:api_atendimento"),
            data=self._payload(
                tipo_pessoa="visitante_estrangeiro",
                contato_estado="",
                contato_pais="Argentina",
            ),
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("contato_provincia", payload["error"]["details"])

        response = self.client.post(
            reverse("sesmt:api_atendimento"),
            data=self._payload(
                tipo_pessoa="visitante_estrangeiro",
                contato_estado="",
                contato_provincia="Misiones",
                contato_pais="Argentina",
                pessoa_documento="55566677788",
            ),
        )

        self.assertEqual(response.status_code, 201)
        atendimento = ControleAtendimento.objects.latest("id")
        self.assertEqual(atendimento.contato.provincia, "Misiones")
        self.assertIsNone(atendimento.contato.estado)

    def test_api_atendimento_create_persiste_ate_duas_testemunhas(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("sesmt:api_atendimento"),
            data=self._payload(
                testemunha="true",
                **{
                    "testemunhas[0][nome]": "Ana Testemunha",
                    "testemunhas[0][documento]": "11122233344",
                    "testemunhas[0][telefone]": "54999111111",
                    "testemunhas[0][data_nascimento]": "1990-01-10",
                    "testemunhas[1][nome]": "Bruno Testemunha",
                    "testemunhas[1][documento]": "55566677788",
                    "testemunhas[1][telefone]": "54999222222",
                    "testemunhas[1][data_nascimento]": "1988-03-15",
                },
            ),
        )

        self.assertEqual(response.status_code, 201)
        atendimento = ControleAtendimento.objects.get()
        self.assertEqual(atendimento.testemunhas.count(), 2)
        self.assertEqual(Testemunha.objects.count(), 2)

    def test_api_atendimento_rejeita_mais_de_duas_testemunhas(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("sesmt:api_atendimento"),
            data=self._payload(
                testemunha="true",
                **{
                    "testemunhas[0][nome]": "Ana Testemunha",
                    "testemunhas[0][documento]": "11122233344",
                    "testemunhas[0][telefone]": "54999111111",
                    "testemunhas[0][data_nascimento]": "1990-01-10",
                    "testemunhas[1][nome]": "Bruno Testemunha",
                    "testemunhas[1][documento]": "55566677788",
                    "testemunhas[1][telefone]": "54999222222",
                    "testemunhas[1][data_nascimento]": "1988-03-15",
                    "testemunhas[2][nome]": "Carla Testemunha",
                    "testemunhas[2][documento]": "99988877766",
                    "testemunhas[2][telefone]": "54999333333",
                    "testemunhas[2][data_nascimento]": "1992-05-20",
                },
            ),
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("testemunhas", payload["error"]["details"])

    def test_api_atendimento_create_persiste_fotos_geolocalizacao_e_assinatura(self):
        self.client.force_login(self.user)

        foto = SimpleUploadedFile(
            "atendimento.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )

        response = self.client.post(
            reverse("sesmt:api_atendimento"),
            data=self._payload(
                geo_latitude="-29.3142851",
                geo_longitude="-50.8541445",
                assinatura_atendido="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sXxQ0YAAAAASUVORK5CYII=",
                fotos=foto,
            ),
        )

        self.assertEqual(response.status_code, 201)
        atendimento = ControleAtendimento.objects.get()
        self.assertEqual(Foto.objects.filter(object_id=atendimento.id).count(), 1)
        self.assertEqual(Geolocalizacao.objects.filter(object_id=atendimento.id).count(), 1)
        self.assertEqual(Assinatura.objects.filter(object_id=atendimento.id).count(), 1)

    def test_api_atendimento_recusa_aceita_conjunto_minimo_sem_documento_e_contato(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("sesmt:api_atendimento"),
            data={
                "tipo_pessoa": "visitante",
                "recusa_atendimento": "true",
                "pessoa_nome": "Pessoa em Recusa",
                "area_atendimento": "entrada",
                "local": "entrada_de_pedestres",
                "data_atendimento": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "tipo_ocorrencia": "mal_subito",
                "responsavel_atendimento": "Luciana Pires",
                "descricao": "Atendimento recusado no local.",
            },
        )

        self.assertEqual(response.status_code, 201)
        atendimento = ControleAtendimento.objects.latest("id")
        self.assertTrue(atendimento.recusa_atendimento)
        self.assertTrue(atendimento.pessoa.documento.startswith("RECUSA-"))
        self.assertIsNone(atendimento.contato)

    def test_atendimento_export_gera_csv_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:atendimento_new"), data=self._payload())

        response = self.client.post(
            reverse("sesmt:atendimento_export"),
            data={"formato": "csv"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])


class ManejoFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="manejo", password="senha-forte-123")
        self.group = Group.objects.create(name="group_sesmt")
        self.user.groups.add(self.group)
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

    def test_api_manejo_create_retorna_contrato_de_sucesso(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("sesmt:api_manejo"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        manejo = Manejo.objects.get()
        self.assertEqual(payload["data"]["id"], manejo.pk)
        self.assertEqual(manejo.unidade, self.unidade)
        self.assertEqual(Notificacao.objects.filter(modulo=Notificacao.MODULO_SESMT).count(), 1)

    def test_api_manejo_create_abre_apenas_com_captura(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("sesmt:api_manejo"),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 201)
        manejo = Manejo.objects.get()
        self.assertFalse(manejo.realizado_manejo)
        self.assertEqual(Foto.objects.filter(object_id=manejo.id, tipo=Foto.TIPO_CAPTURA).count(), 1)
        self.assertEqual(Foto.objects.filter(object_id=manejo.id, tipo=Foto.TIPO_SOLTURA).count(), 0)
        self.assertEqual(Geolocalizacao.objects.filter(object_id=manejo.id, tipo="captura").count(), 1)
        self.assertEqual(Geolocalizacao.objects.filter(object_id=manejo.id, tipo="soltura").count(), 0)

    def test_api_manejo_detail_finaliza_com_soltura(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_manejo"), data=self._payload())
        manejo = Manejo.objects.get()
        foto_soltura = SimpleUploadedFile("soltura.jpg", b"release", content_type="image/jpeg")

        response = self.client.post(
            reverse("sesmt:api_manejo_detail", args=[manejo.pk]),
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
        manejo.refresh_from_db()
        self.assertTrue(manejo.realizado_manejo)
        self.assertEqual(Foto.objects.filter(object_id=manejo.id, tipo=Foto.TIPO_SOLTURA).count(), 1)
        self.assertEqual(Geolocalizacao.objects.filter(object_id=manejo.id, tipo="soltura").count(), 1)
        self.assertEqual(Notificacao.objects.filter(modulo=Notificacao.MODULO_SESMT).count(), 2)

    def test_api_manejo_detail_rejeita_finalizacao_sem_foto_soltura(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_manejo"), data=self._payload())
        manejo = Manejo.objects.get()

        response = self.client.post(
            reverse("sesmt:api_manejo_detail", args=[manejo.pk]),
            data=self._payload(
                realizado_manejo="true",
                responsavel_manejo="jean_carlos_da_silva_agirres",
                area_soltura="trilhas_e_locais",
                local_soltura="trilha_do_silencio",
                descricao_local_soltura="Soltura em área protegida.",
                latitude_soltura="-29.3152851",
                longitude_soltura="-50.8551445",
            ),
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertIn("foto_soltura", payload["error"]["details"])

    def test_api_manejo_rejeita_abertura_sem_foto_captura(self):
        self.client.force_login(self.user)

        payload = self._payload()
        payload.pop("foto_captura", None)
        payload["descricao_local"] = ""
        payload["latitude_captura"] = ""
        payload["longitude_captura"] = ""
        response = self.client.post(reverse("sesmt:api_manejo"), data=payload)

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("foto_captura", payload["error"]["details"])
        self.assertIn("descricao_local", payload["error"]["details"])
        self.assertIn("latitude_captura", payload["error"]["details"])
        self.assertIn("longitude_captura", payload["error"]["details"])

    def test_api_manejo_detail_retorna_payload_estruturado(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_manejo"), data=self._payload())
        manejo = Manejo.objects.get()

        response = self.client.get(reverse("sesmt:api_manejo_detail", args=[manejo.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], manejo.pk)
        self.assertEqual(payload["data"]["classe"], "Mamífero")
        self.assertEqual(payload["data"]["responsavel_manejo"], "-")

    def test_api_manejo_list_filtra_por_status(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_manejo"), data=self._payload(nome_popular="quati"))
        manejo_realizado = Manejo.objects.get()
        self.client.post(
            reverse("sesmt:api_manejo_detail", args=[manejo_realizado.pk]),
            data=self._payload(
                nome_popular="quati",
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
                foto_soltura=SimpleUploadedFile("soltura.jpg", b"release", content_type="image/jpeg"),
            ),
        )
        self.client.post(
            reverse("sesmt:api_manejo"),
            data=self._payload(
                nome_popular="coruja",
                classe="ave",
            ),
        )

        response = self.client.get(reverse("sesmt:api_manejo"), {"status": "pendente", "limit": 10, "offset": 0})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["pagination"]["total"], 1)
        self.assertEqual(payload["data"]["registros"][0]["status_label"], "Pendente")

    def test_manejo_export_gera_csv_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_manejo"), data=self._payload())

        response = self.client.post(reverse("sesmt:manejo_export"), data={"formato": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])


class FloraFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="flora", password="senha-forte-123")
        self.group = Group.objects.create(name="group_sesmt")
        self.user.groups.add(self.group)
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

    def test_api_flora_create_persiste_fotos_e_geolocalizacao(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("sesmt:api_flora"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        flora = Flora.objects.get()
        self.assertEqual(flora.unidade, self.unidade)
        self.assertTrue(flora.isolamento_area)
        self.assertEqual(Foto.objects.filter(object_id=flora.id, tipo=Foto.TIPO_FLORA_ANTES).count(), 1)
        self.assertEqual(Foto.objects.filter(object_id=flora.id, tipo=Foto.TIPO_FLORA_DEPOIS).count(), 0)
        self.assertEqual(Geolocalizacao.objects.filter(object_id=flora.id).count(), 1)
        self.assertEqual(Notificacao.objects.filter(modulo=Notificacao.MODULO_SESMT).count(), 1)

    def test_api_flora_create_exige_isolamento_area(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("sesmt:api_flora"), data=self._payload(isolamento_area=""))

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertIn("isolamento_area", payload["error"]["details"])

    def test_flora_list_renderiza_registro_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_flora"), data=self._payload())

        response = self.client.get(reverse("sesmt:flora_list"), {"q": "Araucária"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Araucária")
        self.assertContains(response, "Em andamento")

    def test_api_flora_detail_retorna_payload_estruturado(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_flora"), data=self._payload())
        flora = Flora.objects.get()

        response = self.client.get(reverse("sesmt:api_flora_detail", args=[flora.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], flora.pk)
        self.assertEqual(payload["data"]["responsavel_registro"], "Diego Geloch")
        self.assertEqual(len(payload["data"]["evidencias"]["foto_antes"]), 1)
        self.assertEqual(len(payload["data"]["evidencias"]["foto_depois"]), 0)

    def test_flora_export_gera_csv_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_flora"), data=self._payload())

        response = self.client.post(reverse("sesmt:flora_export"), data={"formato": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])


class HimenopterosFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="himenopteros", password="senha-forte-123")
        self.group = Group.objects.create(name="group_sesmt")
        self.user.groups.add(self.group)
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

    def test_api_himenopteros_create_persiste_foto_e_geolocalizacao(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("sesmt:api_himenopteros"), data=self._payload())

        self.assertEqual(response.status_code, 201)
        registro = Himenoptero.objects.get()
        self.assertEqual(registro.unidade, self.unidade)
        self.assertEqual(Foto.objects.filter(object_id=registro.id, tipo=Foto.TIPO_CAPTURA).count(), 1)
        self.assertEqual(Geolocalizacao.objects.filter(object_id=registro.id).count(), 1)
        self.assertEqual(Notificacao.objects.filter(modulo=Notificacao.MODULO_SESMT).count(), 1)

    def test_notifications_list_exibe_registro_do_sesmt_para_usuario_do_grupo(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_himenopteros"), data=self._payload())

        response = self.client.get(reverse("sesmt:notifications_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monitor Himenóptero | Novo Registrado")

    def test_himenopteros_list_renderiza_registro_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_himenopteros"), data=self._payload())

        response = self.client.get(reverse("sesmt:himenopteros_list"), {"q": "Vespa"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vespa")
        self.assertContains(response, "Alto - risco iminente")

    def test_api_himenopteros_detail_retorna_payload_estruturado(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_himenopteros"), data=self._payload())
        registro = Himenoptero.objects.get()

        response = self.client.get(reverse("sesmt:api_himenopteros_detail", args=[registro.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], registro.pk)
        self.assertEqual(payload["data"]["responsavel_registro"], "Diego Geloch")
        self.assertEqual(len(payload["data"]["evidencias"]["fotos"]), 1)

    def test_api_himenopteros_update_preserva_isolamento_area_sem_exigir_reenvio(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_himenopteros"), data=self._payload(isolamento_area="true"))
        registro = Himenoptero.objects.get()

        response = self.client.post(
            reverse("sesmt:api_himenopteros_detail", args=[registro.pk]),
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
        registro.refresh_from_db()
        self.assertTrue(registro.isolamento_area)

    def test_himenopteros_export_gera_csv_real(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sesmt:api_himenopteros"), data=self._payload())

        response = self.client.post(reverse("sesmt:himenopteros_export"), data={"formato": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])
