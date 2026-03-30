from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from sigo.models import Operador


User = get_user_model()


class CurrentUserAvatarViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="diego",
            password="senha123",
            first_name="Diego",
            email="diego@example.com",
        )
        self.client.force_login(self.user)

    def test_returns_default_avatar_when_operator_photo_is_missing(self):
        response = self.client.get(reverse("sigo:current_user_avatar"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertGreater(len(response.content), 0)

    def test_returns_operator_photo_when_available(self):
        Operador.objects.create(
            user=self.user,
            foto=b"fake-image-content",
            foto_nome_arquivo="avatar.png",
            foto_mime_type="image/png",
            foto_tamanho=len(b"fake-image-content"),
        )

        response = self.client.get(reverse("sigo:current_user_avatar"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, b"fake-image-content")


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="maria",
            password="SenhaAtual123!",
            first_name="Maria",
            email="maria@example.com",
        )
        self.client.force_login(self.user)

    def test_profile_page_renders(self):
        response = self.client.get(reverse("sigo:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meu Perfil")

    def test_can_update_operator_photo(self):
        response = self.client.post(
            reverse("sigo:profile"),
            {
                "action": "update_photo",
                "foto": SimpleUploadedFile("avatar.png", b"pngdata", content_type="image/png"),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        operador = Operador.objects.get(user=self.user)
        self.assertEqual(operador.foto, b"pngdata")
        self.assertEqual(operador.foto_mime_type, "image/png")

    def test_can_change_password_and_keep_session(self):
        response = self.client.post(
            reverse("sigo:profile"),
            {
                "action": "change_password",
                "old_password": "SenhaAtual123!",
                "new_password1": "NovaSenha456@",
                "new_password2": "NovaSenha456@",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha456@"))

    def test_can_remove_operator_photo(self):
        Operador.objects.create(
            user=self.user,
            foto=b"pngdata",
            foto_nome_arquivo="avatar.png",
            foto_mime_type="image/png",
            foto_tamanho=len(b"pngdata"),
        )

        response = self.client.post(
            reverse("sigo:profile"),
            {"action": "remove_photo"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        operador = Operador.objects.get(user=self.user)
        self.assertIsNone(operador.foto)
        self.assertIsNone(operador.foto_nome_arquivo)
        self.assertIsNone(operador.foto_mime_type)
        self.assertEqual(operador.foto_tamanho, 0)
