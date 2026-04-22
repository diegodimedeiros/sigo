from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from sigo.models import ConfiguracaoSistema, Notificacao, Operador, Unidade
from sigo.access import allowed_notification_modules, can_access_namespace


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
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertGreater(len(response.content), 0)
        self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))

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


class NotificationAccessPolicyTests(TestCase):
    def test_user_without_module_groups_sees_only_sigo_context(self):
        user = User.objects.create_user(username="sem_grupo", password="SenhaForte123!")

        allowed = allowed_notification_modules(user)

        self.assertEqual(allowed, {"", "sigo"})

    def test_user_with_siop_group_receives_siop_notifications(self):
        user = User.objects.create_user(username="com_siop", password="SenhaForte123!")
        group = Group.objects.create(name="group_siop")
        user.groups.add(group)

        allowed = allowed_notification_modules(user)

        self.assertEqual(allowed, {"", "sigo", "siop"})


class ModuleNamespaceAccessPolicyTests(TestCase):
    def test_reportos_group_can_access_reportos_namespace(self):
        user = User.objects.create_user(username="com_reportos", password="SenhaForte123!")
        group = Group.objects.create(name="group_reportos")
        user.groups.add(group)

        self.assertTrue(can_access_namespace(user, "reportos"))
        self.assertFalse(can_access_namespace(user, "siop"))
        self.assertFalse(can_access_namespace(user, "sesmt"))

    def test_user_without_reportos_group_is_blocked_in_reportos_namespace(self):
        user = User.objects.create_user(username="somente_sesmt", password="SenhaForte123!")
        group = Group.objects.create(name="group_sesmt")
        user.groups.add(group)

        self.assertFalse(can_access_namespace(user, "reportos"))

    def test_reportos_home_returns_403_without_reportos_group(self):
        user = User.objects.create_user(username="sem_reportos", password="SenhaForte123!")
        self.client.force_login(user)

        response = self.client.get(reverse("reportos:home"))

        self.assertEqual(response.status_code, 403)


class LogoutCleanupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="logout_user",
            password="SenhaForte123!",
        )
        self.client.force_login(self.user)

    def test_authenticated_layout_exposes_logout_cleanup_hook(self):
        response = self.client.get(reverse("sigo:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-sigo-logout="true"')
        self.assertContains(response, "sigo/assets/js/sigo/logout-cleanup.js")

    def test_login_page_runs_cleanup_on_load(self):
        self.client.logout()

        response = self.client.get(reverse("sigo:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-sigo-cleanup-on-load="true"')
        self.assertContains(response, "sigo/assets/js/sigo/logout-cleanup.js")

    def test_logout_route_redirects_to_login_and_clears_session(self):
        response = self.client.post(reverse("sigo:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("sigo:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class NotificationFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="operador_siop",
            password="SenhaForte123!",
            first_name="Operador",
        )
        self.client.force_login(self.user)

        self.group_siop = Group.objects.create(name="group_siop")
        self.user.groups.add(self.group_siop)

        self.group = Group.objects.create(name="Operacoes")
        self.user.groups.add(self.group)

        self.unidade = Unidade.objects.create(
            nome="Parque Teste",
            sigla="PT",
            cidade="Canela",
            uf="RS",
        )
        ConfiguracaoSistema.objects.create(unidade_ativa=self.unidade)

    def test_module_notification_is_visible(self):
        Notificacao.objects.create(
            titulo="Nova ocorrência",
            mensagem="Ocorrência aguardando revisão.",
            modulo=Notificacao.MODULO_SIOP,
        )
        Notificacao.objects.create(
            titulo="Somente SESMT",
            mensagem="Fluxo sesmt.",
            modulo=Notificacao.MODULO_SESMT,
        )

        response = self.client.get(reverse("siop:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova ocorrência")
        self.assertNotContains(response, "Somente SESMT")

    def test_group_and_user_filters(self):
        Notificacao.objects.create(
            titulo="Grupo OK",
            mensagem="Mensagem do grupo.",
            modulo=Notificacao.MODULO_SIOP,
            grupo=self.group,
        )
        Notificacao.objects.create(
            titulo="Outro usuário",
            mensagem="Não deve aparecer.",
            modulo=Notificacao.MODULO_SIOP,
            usuario=User.objects.create_user(username="externo", password="SenhaForte123!"),
        )

        response = self.client.get(reverse("siop:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grupo OK")
        self.assertNotContains(response, "Outro usuário")

    def test_top_notifications_module_no_siop_prioriza_namespace_atual(self):
        response = self.client.get(
            reverse("siop:home"),
            HTTP_REFERER=f"{reverse('sigo:notifications_list')}?modulo=sigo",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["top_notifications_module"], Notificacao.MODULO_SIOP)
        self.assertContains(response, reverse("siop:notifications_list"))

    def test_ver_todas_no_siop_aponta_para_central_do_proprio_modulo(self):
        response = self.client.get(reverse("siop:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("siop:notifications_list"))

    def test_lista_de_notificacoes_do_siop_renderiza_no_modulo(self):
        Notificacao.objects.create(
            titulo="Somente SIOP",
            mensagem="Fluxo do siop.",
            modulo=Notificacao.MODULO_SIOP,
        )

        response = self.client.get(reverse("siop:notifications_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "siop/notifications.html")
        self.assertContains(response, "Somente SIOP")

    def test_mark_all_as_read(self):
        Notificacao.objects.create(
            titulo="Pendente",
            mensagem="Mensagem pendente.",
            modulo=Notificacao.MODULO_SIOP,
        )

        response = self.client.post(
            reverse("sigo:notifications_mark_all_read"),
            data={"modulo": Notificacao.MODULO_SIOP, "next": reverse("siop:home")},
        )

        self.assertEqual(response.status_code, 302)
        notificacao = Notificacao.objects.get(titulo="Pendente")
        self.assertTrue(notificacao.lidos_por.filter(id=self.user.id).exists())

    def test_mark_all_as_read_ignora_modulo_forjado(self):
        notificacao_siop = Notificacao.objects.create(
            titulo="SIOP Pendente",
            mensagem="Mensagem do siop.",
            modulo=Notificacao.MODULO_SIOP,
        )
        notificacao_sesmt = Notificacao.objects.create(
            titulo="SESMT Pendente",
            mensagem="Mensagem do sesmt.",
            modulo=Notificacao.MODULO_SESMT,
        )

        response = self.client.post(
            reverse("sigo:notifications_mark_all_read"),
            data={"modulo": Notificacao.MODULO_SESMT, "next": reverse("siop:home")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(notificacao_siop.lidos_por.filter(id=self.user.id).exists())
        self.assertFalse(notificacao_sesmt.lidos_por.filter(id=self.user.id).exists())

    def test_mark_all_as_read_na_central_preserva_modulo_explicito(self):
        notificacao_siop = Notificacao.objects.create(
            titulo="SIOP Central",
            mensagem="Mensagem do siop.",
            modulo=Notificacao.MODULO_SIOP,
        )
        notificacao_sesmt = Notificacao.objects.create(
            titulo="SESMT Central",
            mensagem="Mensagem do sesmt.",
            modulo=Notificacao.MODULO_SESMT,
        )

        response = self.client.post(
            reverse("sigo:notifications_mark_all_read"),
            data={
                "modulo": Notificacao.MODULO_SIOP,
                "next": f"{reverse('sigo:notifications_list')}?modulo=siop",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('sigo:notifications_list')}?modulo=siop")
        self.assertTrue(notificacao_siop.lidos_por.filter(id=self.user.id).exists())
        self.assertFalse(notificacao_sesmt.lidos_por.filter(id=self.user.id).exists())

    def test_open_notification_marks_read(self):
        notificacao = Notificacao.objects.create(
            titulo="Abrir item",
            mensagem="Clique para abrir.",
            modulo=Notificacao.MODULO_SIOP,
            link=reverse("siop:home"),
        )

        response = self.client.get(
            reverse("sigo:notification_open", args=[notificacao.id]),
            data={"modulo": Notificacao.MODULO_SIOP, "next": reverse("siop:home")},
        )

        self.assertEqual(response.status_code, 302)
        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lidos_por.filter(id=self.user.id).exists())

    def test_open_notification_ignora_modulo_forjado(self):
        notificacao = Notificacao.objects.create(
            titulo="Abrir item protegido",
            mensagem="Clique para abrir.",
            modulo=Notificacao.MODULO_SIOP,
            link=reverse("siop:home"),
        )

        response = self.client.get(
            reverse("sigo:notification_open", args=[notificacao.id]),
            data={"modulo": Notificacao.MODULO_SESMT, "next": reverse("siop:home")},
        )

        self.assertEqual(response.status_code, 302)
        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lidos_por.filter(id=self.user.id).exists())

    def test_open_notification_funciona_mesmo_partindo_de_lista_em_outro_contexto(self):
        notificacao = Notificacao.objects.create(
            titulo="Abrir item da lista",
            mensagem="Clique para abrir.",
            modulo=Notificacao.MODULO_SIOP,
            link="/siop/ocorrencias/1/",
        )

        response = self.client.get(
            reverse("sigo:notification_open", args=[notificacao.id]),
            data={"next": "/notificacoes/?modulo=sigo"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/siop/ocorrencias/1/")
        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lidos_por.filter(id=self.user.id).exists())

    def test_open_notification_redireciona_para_link_do_item_sem_ancora(self):
        notificacao = Notificacao.objects.create(
            titulo="Ocorrência interna",
            mensagem="Abrir no detalhe.",
            modulo=Notificacao.MODULO_SIOP,
            link="/siop/ocorrencias/99/",
        )

        response = self.client.get(
            reverse("sigo:notification_open", args=[notificacao.id]),
            data={"next": reverse("siop:home")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/siop/ocorrencias/99/")

    def test_notifications_list_mostra_apenas_ultimos_sete_dias(self):
        recente = Notificacao.objects.create(
            titulo="Recente",
            mensagem="Dentro da janela.",
            modulo=Notificacao.MODULO_SIOP,
        )
        antiga = Notificacao.objects.create(
            titulo="Antiga",
            mensagem="Fora da janela.",
            modulo=Notificacao.MODULO_SIOP,
        )
        Notificacao.objects.filter(id=antiga.id).update(criado_em=timezone.now() - timedelta(days=8))

        response = self.client.get(
            reverse("sigo:notifications_list"),
            data={"modulo": Notificacao.MODULO_SIOP},
        )
        notifications = list(response.context["notifications"])
        titles = [item.titulo for item in notifications]

        self.assertEqual(response.status_code, 200)
        self.assertIn(recente.titulo, titles)
        self.assertNotIn(antiga.titulo, titles)

    def test_notifications_list_respeita_modulo_informado(self):
        Notificacao.objects.create(
            titulo="Somente SIOP",
            mensagem="Fluxo do siop.",
            modulo=Notificacao.MODULO_SIOP,
        )
        Notificacao.objects.create(
            titulo="Somente SESMT",
            mensagem="Fluxo do sesmt.",
            modulo=Notificacao.MODULO_SESMT,
        )

        response = self.client.get(
            reverse("sigo:notifications_list"),
            data={"modulo": Notificacao.MODULO_SIOP},
        )
        notifications = list(response.context["notifications"])
        titles = [item.titulo for item in notifications]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Somente SIOP", titles)
        self.assertNotIn("Somente SESMT", titles)

    def test_notifications_list_prioriza_modulo_explicito_mesmo_com_referer(self):
        Notificacao.objects.create(
            titulo="Somente SIOP",
            mensagem="Fluxo do siop.",
            modulo=Notificacao.MODULO_SIOP,
        )
        Notificacao.objects.create(
            titulo="Somente SIGO",
            mensagem="Fluxo do sigo.",
            modulo=Notificacao.MODULO_SIGO,
        )

        response = self.client.get(
            reverse("sigo:notifications_list"),
            data={"modulo": Notificacao.MODULO_SIOP},
            HTTP_REFERER=f"{reverse('sigo:notifications_list')}?modulo=sigo",
        )
        notifications = list(response.context["notifications"])
        titles = [item.titulo for item in notifications]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Somente SIOP", titles)
        self.assertNotIn("Somente SIGO", titles)

    def test_segmented_notification_requires_module(self):
        notificacao = Notificacao(
            titulo="Sem módulo",
            mensagem="Direcionada sem contexto.",
            grupo=self.group,
        )

        with self.assertRaises(ValidationError) as exc:
            notificacao.full_clean()

        self.assertIn("modulo", exc.exception.message_dict)
