from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

class AutenticacaoTests(TestCase):
    def test_cadastro_publico_sempre_leitor(self):
        response = self.client.post(reverse("cadastro"), {
            "nome": "Maria Leitora", "email": "Maria@Example.com",
            "password1": "LeituraBoa!2026", "password2": "LeituraBoa!2026",
            "is_staff": "on", "is_superuser": "on", "groups": "Bibliotecario",
        })
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="maria@example.com")
        self.assertTrue(user.check_password("LeituraBoa!2026"))
        self.assertTrue(user.groups.filter(name="Leitor").exists())
        self.assertFalse(user.groups.filter(name="Bibliotecario").exists())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_login_por_email_e_redirecionamento_por_perfil(self):
        user = User.objects.create_user("maria@example.com", password="LeituraBoa!2026")
        response = self.client.post(reverse("login"), {
            "username": "MARIA@EXAMPLE.COM", "password": "LeituraBoa!2026"}, follow=True)
        self.assertEqual(response.resolver_match.url_name, "catalogo")
        user.groups.add(Group.objects.get(name="Bibliotecario"))
        response = self.client.get(reverse("inicio"), follow=True)
        self.assertEqual(response.resolver_match.url_name, "painel_bibliotecario")

    def test_login_errado_e_inativo_bloqueados(self):
        user = User.objects.create_user("maria@example.com", password="LeituraBoa!2026")
        response = self.client.post(reverse("login"), {"username": user.username, "password": "errada"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        user.is_active = False
        user.save()
        self.client.post(reverse("login"), {"username": user.username, "password": "LeituraBoa!2026"})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cadastro_duplicado_e_senha_fraca(self):
        User.objects.create_user("maria@example.com")
        response = self.client.post(reverse("cadastro"), {
            "nome": "Maria", "email": "MARIA@example.com",
            "password1": "LeituraBoa!2026", "password2": "LeituraBoa!2026"})
        self.assertContains(response, "Este e-mail já tem uma conta.")
        self.client.post(reverse("cadastro"), {
            "nome": "João", "email": "joao@example.com", "password1": "123", "password2": "123"})
        self.assertFalse(User.objects.filter(username="joao@example.com").exists())

    def test_logout_por_post(self):
        user = User.objects.create_user("maria@example.com")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("sair")).status_code, 405)
        self.client.post(reverse("sair"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_externo_nao_redireciona(self):
        User.objects.create_user("maria@example.com", password="LeituraBoa!2026")
        response = self.client.post(reverse("login"), {
            "username": "maria@example.com", "password": "LeituraBoa!2026",
            "next": "https://example.org/"})
        self.assertRedirects(response, reverse("inicio"), fetch_redirect_response=False)

    def test_comando_cria_bibliotecario_sem_superpoderes(self):
        with patch("usuarios.management.commands.criar_bibliotecario.getpass",
                   side_effect=["LeituraBoa!2026", "LeituraBoa!2026"]):
            call_command("criar_bibliotecario", email="Equipe@example.com", nome="Equipe", stdout=StringIO())
        user = User.objects.get(username="equipe@example.com")
        self.assertTrue(user.has_perm("livro.gerenciar_circulacao"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_promocao_e_grupos_idempotentes(self):
        user = User.objects.create_user("maria@example.com")
        call_command("promover_bibliotecario", user.username, stdout=StringIO())
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.has_perm("livro.add_livro"))
        from usuarios.permissoes import criar_grupos_e_permissoes
        from django.apps import apps
        criar_grupos_e_permissoes(apps.get_app_config("livro"), using="default")
        self.assertEqual(Group.objects.filter(name="Bibliotecario").count(), 1)
