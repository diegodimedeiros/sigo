from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class ReportosHomeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportos",
            password="SenhaForte123!",
        )
        self.client.force_login(self.user)

    def test_home_renderiza_modulo(self):
        response = self.client.get(reverse("reportos:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atendimento")
        self.assertContains(response, "Flora")
        self.assertContains(response, "Manejo")

    def test_subareas_renderizam(self):
        response_atendimento = self.client.get(reverse("reportos:atendimento_home"))
        response_manejo = self.client.get(reverse("reportos:manejo_home"))
        response_flora = self.client.get(reverse("reportos:flora_home"))

        self.assertEqual(response_atendimento.status_code, 200)
        self.assertEqual(response_manejo.status_code, 200)
        self.assertEqual(response_flora.status_code, 200)
        self.assertContains(response_atendimento, "Atendimento")
        self.assertContains(response_manejo, "Manejo")
        self.assertContains(response_flora, "Flora")
