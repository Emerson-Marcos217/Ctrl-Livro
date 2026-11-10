import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionHandler
from django.test import SimpleTestCase
from google.auth.exceptions import GoogleAuthError

from biblioteca.banco import configurar_banco
from biblioteca.credenciais_google import obter_credenciais_google

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_BANCO = {
    "BIBLIOTECA_BANCO": "firebase", "BIBLIOTECA_CONEXAO": "connector",
    "PGDATABASE": "banco-teste", "PGUSER": "usuario-teste", "PGPASSWORD": "somente-teste",
    "CLOUD_SQL_CONNECTION_NAME": "projeto-teste:us-east4:instancia-teste",
}


class HospedagemTests(SimpleTestCase):
    def test_vercel_recusa_sqlite_e_proxy_local(self):
        for env in ({"VERCEL": "1"}, {**ENV_BANCO, "VERCEL": "1", "BIBLIOTECA_CONEXAO": "proxy"}):
            with self.subTest(env=env), self.assertRaises(ImproperlyConfigured):
                configurar_banco(env, BASE_DIR)

    def test_cloud_sql_nao_usa_host_ou_sslmode_do_proxy(self):
        banco = configurar_banco({**ENV_BANCO, "PGHOST": "127.0.0.1", "PGPORT": "5432",
                                  "PGSSLMODE": "disable"}, BASE_DIR)
        self.assertEqual(banco["ENGINE"], "biblioteca.backends.cloudsql")
        self.assertEqual((banco["HOST"], banco["PORT"], banco["CONN_MAX_AGE"]), ("", "", 0))
        self.assertNotIn("sslmode", banco["OPTIONS"])

    def test_cloud_sql_exige_instancia_sem_voltar_ao_sqlite(self):
        env = {k: v for k, v in ENV_BANCO.items() if k != "CLOUD_SQL_CONNECTION_NAME"}
        with self.assertRaisesMessage(ImproperlyConfigured, "CLOUD_SQL_CONNECTION_NAME"):
            configurar_banco(env, BASE_DIR)

    @patch("biblioteca.backends.cloudsql.base.obter_conector")
    def test_backend_preserva_adaptadores_e_isolamento_do_django(self, conector):
        import psycopg
        banco = configurar_banco(ENV_BANCO, BASE_DIR)
        handler = ConnectionHandler({"default": banco})
        wrapper = handler["default"]
        parametros = wrapper.get_connection_params()
        self.assertIn("context", parametros)
        self.assertIn("cursor_factory", parametros)
        conexao = wrapper.get_new_connection(parametros)
        self.assertIs(conexao, conector.return_value.connect.return_value)
        chamada = conector.return_value.connect.call_args
        self.assertEqual(chamada.args, (ENV_BANCO["CLOUD_SQL_CONNECTION_NAME"], "psycopg"))
        self.assertEqual(chamada.kwargs["db"], "banco-teste")
        self.assertEqual(chamada.kwargs["timeout"], 10)
        self.assertEqual(chamada.kwargs["ip_type"], "PUBLIC")
        self.assertNotIn("dbname", chamada.kwargs)
        self.assertNotIn("host", chamada.kwargs)
        self.assertIs(wrapper.Database.OperationalError, psycopg.OperationalError)
        self.assertEqual(wrapper.isolation_level, psycopg.IsolationLevel.READ_COMMITTED)

    @patch("biblioteca.credenciais_google.google.auth.default")
    @patch.dict(os.environ, {}, clear=True)
    def test_desktop_continua_usando_login_local(self, adc):
        adc.return_value = (Mock(), "projeto-teste")
        self.assertIs(obter_credenciais_google(), adc.return_value[0])

    @patch("biblioteca.credenciais_google.google.auth.default")
    @patch.dict(os.environ, {"VERCEL": "1"}, clear=True)
    def test_vercel_nao_tenta_encontrar_login_do_computador(self, adc):
        with self.assertRaisesMessage(GoogleAuthError, "GOOGLE_CREDENTIALS_JSON"):
            obter_credenciais_google()
        adc.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    def test_json_invalido_nao_expoe_conteudo(self):
        for conteudo in ("segredo-invalido", '[]', '{"type":"authorized_user","refresh_token":"segredo"}'):
            with self.subTest(conteudo=conteudo):
                os.environ["GOOGLE_CREDENTIALS_JSON"] = conteudo
                with self.assertRaises(GoogleAuthError) as erro:
                    obter_credenciais_google()
                self.assertNotIn("segredo", str(erro.exception))
                self.assertIsNone(erro.exception.__cause__)

    @patch("biblioteca.credenciais_google.service_account.Credentials.from_service_account_info")
    @patch("biblioteca.credenciais_google.google.auth.default")
    @patch.dict(os.environ, {"VERCEL": "1", "GOOGLE_CREDENTIALS_JSON": '{"type":"service_account"}'}, clear=True)
    def test_hospedagem_usa_identidade_do_servidor(self, adc, criar):
        self.assertIs(obter_credenciais_google(), criar.return_value)
        adc.assert_not_called()
        criar.side_effect = ValueError("segredo-na-excecao")
        with self.assertRaises(GoogleAuthError) as erro:
            obter_credenciais_google()
        self.assertNotIn("segredo", str(erro.exception))

    def executar_settings(self, alteracoes=None, codigo="import biblioteca.settings"):
        env = {k: v for k, v in os.environ.items() if not k.startswith(
            ("DJANGO_", "VERCEL", "PG", "BIBLIOTECA_", "SQL_CONNECT_", "GOOGLE_", "IA_"))}
        env.update(ENV_BANCO)
        env.update({"VERCEL": "1", "VERCEL_URL": "teste.vercel.app",
                    "DJANGO_SECRET_KEY": "teste-isolado-sem-valor-em-producao-" * 3,
                    "GOOGLE_CREDENTIALS_JSON": '{"type":"service_account"}',
                    "SQL_CONNECT_ATIVO": "1"})
        for chave, valor in (alteracoes or {}).items():
            if valor is None:
                env.pop(chave, None)
            else:
                env[chave] = valor
        return subprocess.run([sys.executable, "-c", codigo], cwd=BASE_DIR, env=env,
                              capture_output=True, text=True, timeout=30)

    def test_producao_falha_sem_segredos_ou_com_debug(self):
        casos = [({"DJANGO_SECRET_KEY": None}, "DJANGO_SECRET_KEY"),
                 ({"DJANGO_DEBUG": "1"}, "DJANGO_DEBUG"),
                 ({"GOOGLE_CREDENTIALS_JSON": None}, "GOOGLE_CREDENTIALS_JSON"),
                 ({"BIBLIOTECA_BANCO": "sqlite"}, "SQLite"),
                 ({"DJANGO_ALLOWED_HOSTS": "*"}, "DJANGO_ALLOWED_HOSTS")]
        for env, mensagem in casos:
            with self.subTest(env=env):
                resultado = self.executar_settings(env)
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn(mensagem, resultado.stderr)

    def test_wsgi_https_e_formulario_funcionam_sem_conectar_no_build(self):
        codigo = '''
import json
from biblioteca.wsgi import application
from django.conf import settings
from django.test import Client
c = Client(enforce_csrf_checks=True)
r = c.get('/auth/login/', HTTP_HOST='teste.vercel.app', HTTP_X_FORWARDED_PROTO='https')
assert r.status_code == 200, r.status_code
assert r.cookies[settings.CSRF_COOKIE_NAME]['secure']
assert c.get('/auth/login/', HTTP_HOST='teste.vercel.app').status_code == 301
assert c.post('/auth/login/', HTTP_HOST='teste.vercel.app', HTTP_X_FORWARDED_PROTO='https').status_code == 403
assert c.get('/auth/login/', HTTP_HOST='outro.vercel.app', HTTP_X_FORWARDED_PROTO='https').status_code == 400
print(json.dumps({'debug': settings.DEBUG, 'engine': settings.DATABASES['default']['ENGINE'],
                  'provedor': settings.IA_PROVEDOR, 'cookie': settings.SESSION_COOKIE_SECURE}))
'''
        resultado = self.executar_settings(codigo=codigo)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        dados = json.loads(resultado.stdout)
        self.assertFalse(dados["debug"])
        self.assertTrue(dados["cookie"])
        self.assertEqual(dados["engine"], "biblioteca.backends.cloudsql")
        self.assertEqual(dados["provedor"], "gemini")
