from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


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
