from pathlib import Path
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from requests.exceptions import Timeout

from biblioteca.banco import configurar_banco
from .models import Categoria, Exemplar, Livro
from .sql_connect import ErroSQLConnect, executar_consulta, livros_do_acervo


class ConfiguracaoBancoTests(SimpleTestCase):
    def test_firebase_incompleto_nao_volta_para_sqlite(self):
        with self.assertRaises(ImproperlyConfigured):
            configurar_banco({"BIBLIOTECA_BANCO": "firebase"}, Path("."))

    def test_postgresql_sem_opcoes_exclusivas_do_sqlite(self):
        banco = configurar_banco({"BIBLIOTECA_BANCO": "firebase", "PGHOST": "localhost",
                                  "PGDATABASE": "biblioteca", "PGUSER": "usuario",
                                  "PGPASSWORD": "senha-de-teste"}, Path("."))
        self.assertEqual(banco["ENGINE"], "django.db.backends.postgresql")
        self.assertNotIn("transaction_mode", banco["OPTIONS"])
        self.assertEqual(banco["OPTIONS"]["sslmode"], "require")

    def test_modo_desconhecido_falha(self):
        with self.assertRaises(ImproperlyConfigured):
            configurar_banco({"BIBLIOTECA_BANCO": "firbase"}, Path("."))


@override_settings(SQL_CONNECT_PROJECT="projeto-teste", SQL_CONNECT_LOCATION="us-central1",
                   SQL_CONNECT_SERVICE="biblioteca", SQL_CONNECT_CONNECTOR="biblioteca")
class ClienteSQLConnectTests(SimpleTestCase):
    @patch("livro.sql_connect.AuthorizedSession")
    @patch("livro.sql_connect.obter_credenciais_google", return_value=Mock())
    def test_consulta_autenticada_com_timeout_sem_redirecionamento(self, credenciais, sessao):
        post = sessao.return_value.__enter__.return_value.post
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"data": {"acervoLivros": []}}
        self.assertEqual(executar_consulta([5]), {"acervoLivros": []})
        argumentos = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0],
                         "https://firebasedataconnect.googleapis.com/v1/projects/projeto-teste/"
                         "locations/us-central1/services/biblioteca/connectors/biblioteca:impersonateQuery")
        self.assertEqual(argumentos["json"]["extensions"], {})
        self.assertEqual(argumentos["json"]["variables"], {"ids": ["5"]})
        self.assertEqual(argumentos["timeout"], 15)
        self.assertFalse(argumentos["allow_redirects"])
        post.return_value.status_code = 403
        post.return_value.text = "segredo-que-nao-pode-aparecer"
        with self.assertRaises(ErroSQLConnect) as erro:
            executar_consulta([5])
        self.assertNotIn("segredo", str(erro.exception))
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"errors": [{"message": "detalhes internos"}]}
        with self.assertRaises(ErroSQLConnect):
            executar_consulta([5])
        post.side_effect = Timeout()
        with self.assertRaises(ErroSQLConnect):
            executar_consulta([5])

    @override_settings(SQL_CONNECT_PROJECT="")
    def test_configuracao_ausente(self):
        with self.assertRaises(ErroSQLConnect):
            executar_consulta([1])

    @patch("livro.sql_connect.executar_consulta")
    def test_resposta_nao_pode_introduzir_outros_livros(self, executar):
        executar.return_value = {"acervoLivros": [{"id": "999"}]}
        with self.assertRaises(ErroSQLConnect):
            livros_do_acervo([1])
        executar.return_value = {"acervoLivros": []}
        self.assertEqual(livros_do_acervo([1]), [])


@override_settings(SQL_CONNECT_ATIVO=True)
class AcervoSQLConnectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("leitor-sql-connect")
        cls.categoria = Categoria.objects.create(nome="Romance")
        cls.livro = Livro.objects.create(nome="Livro local", autor="Autora", cadastrado_por=cls.usuario)
        cls.livro.categorias.add(cls.categoria)
        Exemplar.objects.create(livro=cls.livro, codigo="FIREBASE-1")
        Livro.objects.create(nome="Oculto", autor="Autora", ativo=False, cadastrado_por=cls.usuario)

    @patch("livro.sql_connect.executar_consulta")
    def test_pagina_le_do_conector_e_preserva_filtros(self, executar):
        self.client.force_login(self.usuario)
        executar.return_value = {"acervoLivros": [{
            "id": str(self.livro.pk), "nome": "Título vindo do SQL Connect", "autor": "Autora",
            "coAutor": "", "sinopse": "Texto", "disponiveis": "1", "categorias": ["Romance"],
        }]}
        resposta = self.client.get(reverse("catalogo"), {"categoria": self.categoria.pk, "disponivel": "1"})
        self.assertContains(resposta, "Título vindo do SQL Connect")
        self.assertContains(resposta, "Romance")
        self.assertEqual(resposta.context["total"], 1)
        executar.assert_called_once_with([self.livro.pk])

    @patch("livro.views.livros_do_acervo", side_effect=ErroSQLConnect("credencial-secreta"))
    def test_falha_nao_parece_acervo_vazio_nem_expoe_credencial(self, buscar):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("catalogo"))
        self.assertContains(resposta, "Não foi possível carregar o acervo", status_code=503)
        self.assertNotContains(resposta, "credencial-secreta", status_code=503)
        self.assertNotContains(resposta, "Livro local", status_code=503)

    @patch("livro.views.livros_do_acervo")
    def test_visitante_nao_consulta_api(self, buscar):
        self.assertEqual(self.client.get(reverse("catalogo")).status_code, 302)
        buscar.assert_not_called()
