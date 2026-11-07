import json
from datetime import timedelta
from io import BytesIO, StringIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .ia_erros import ErroRecomendacao
from .limites_ia import reservar_pedido
from .models import Categoria, Livro, UsoIA
from .recomendacoes import consultar_ia


def resposta_gemini(resultado, motivo="STOP"):
    return json.dumps({"candidates": [{
        "finishReason": motivo,
        "content": {"parts": [{"text": json.dumps(resultado)}]},
    }]}).encode()


@override_settings(IA_PROVEDOR="gemini", GEMINI_API_KEY="chave-ficticia",
                   GEMINI_MODEL="gemini-3.5-flash-lite", GEMINI_TIMEOUT=20)
class GeminiTests(SimpleTestCase):
    @patch("livro.gemini.build_opener")
    def test_credencial_opaca_com_pontuacao_chega_intacta_ao_cabecalho(self, abrir):
        chave_ficticia = "teste.ficticio/mais+dados=final:valor"
        abrir.return_value.open.return_value.__enter__.return_value.read.return_value = resposta_gemini({"recomendacoes": []})
        with self.settings(GEMINI_API_KEY=chave_ficticia):
            self.assertEqual(consultar_ia({}), {"recomendacoes": []})
        pedido = abrir.return_value.open.call_args.args[0]
        self.assertEqual(pedido.get_header("X-goog-api-key"), chave_ficticia)
        self.assertNotIn(chave_ficticia, pedido.full_url)
        self.assertNotIn(chave_ficticia.encode(), pedido.data)

    @patch("livro.gemini.build_opener")
    def test_diagnostico_colagem_sem_expor_chave_ou_chamar_rede(self, abrir):
        for valor, motivo in [('"segredo"', "aspas"), ("segredo\x16", "controle"),
                              ("segredo x", "espaços"), ("segredo***", "ocultação")]:
            with self.settings(GEMINI_API_KEY=valor), self.assertRaises(CommandError) as erro:
                call_command("diagnosticar_ia", configuracao=True, stdout=StringIO())
            self.assertIn(motivo, str(erro.exception))
            self.assertNotIn("segredo", str(erro.exception))
        saida = StringIO()
        call_command("diagnosticar_ia", configuracao=True, stdout=saida)
        self.assertIn("aceito localmente", saida.getvalue())
        abrir.assert_not_called()

    @patch("livro.gemini.build_opener")
    @patch("livro.recomendacoes.enviar_pedido")
    def test_contrato_rest_duas_etapas_sem_ollama(self, local, abrir):
        leitura = abrir.return_value.open.return_value.__enter__.return_value.read
        exemplos = [("preferencias", {"criterios": []}), ("selecao", {"recomendacoes": []})]
        for etapa, resultado in exemplos:
            leitura.return_value = resposta_gemini(resultado)
            self.assertEqual(consultar_ia({"pedido": "Quero romance"}, etapa=etapa), resultado)
            pedido = abrir.return_value.open.call_args.args[0]
            self.assertEqual(pedido.full_url, "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent")
            self.assertEqual(pedido.get_header("X-goog-api-key"), "chave-ficticia")
            self.assertNotIn("chave-ficticia", pedido.full_url)
            self.assertNotIn(b"chave-ficticia", pedido.data)
            corpo = json.loads(pedido.data)
            self.assertEqual(corpo["generationConfig"]["responseMimeType"], "application/json")
            self.assertNotIn("responseFormat", corpo["generationConfig"])
            self.assertEqual(corpo["generationConfig"]["responseJsonSchema"]["required"], list(resultado))
            self.assertEqual(abrir.return_value.open.call_args.kwargs["timeout"], 20)
        local.assert_not_called()
        self.assertIsNone(abrir.call_args.args[0].redirect_request(None, None, 307, "", {}, "https://outro.example"))

    @patch("livro.gemini.build_opener")
    def test_configuracao_invalida_e_entrada_grande_nao_chamam_api(self, abrir):
        for config in ({"GEMINI_API_KEY": ""}, {"GEMINI_API_KEY": "x\r\ny"},
                       {"GEMINI_MODEL": "../outro?key=x"}, {"IA_PROVEDOR": "invalido"},
                       {"IA_PROVEDOR": "ollama", "IA_HOSPEDADA": True}):
            with self.settings(**config), self.assertRaises(ErroRecomendacao):
                consultar_ia({})
        with self.assertRaises(ErroRecomendacao):
            consultar_ia({"pedido": "x" * 12001})
        abrir.assert_not_called()

    @patch("livro.gemini.build_opener")
    def test_erros_http_nao_expoem_corpo_nem_repetem_pedido(self, abrir):
        for status in (400, 401, 403, 404, 429, 500, 503, 504, 307):
            abrir.reset_mock()
            abrir.return_value.open.side_effect = HTTPError("https://example.com", status, "segredo", {}, BytesIO(b'chave-ficticia mensagem do leitor'))
            with self.assertRaises(ErroRecomendacao) as erro:
                consultar_ia({}, diagnostico=True)
            self.assertIn(f"HTTP {status}", str(erro.exception))
            self.assertNotIn("chave-ficticia", str(erro.exception))
            self.assertNotIn("leitor", str(erro.exception))
            self.assertEqual(abrir.return_value.open.call_count, 1)

    @patch("livro.gemini.build_opener")
    def test_falhas_de_rede_sem_detalhes_internos(self, abrir):
        for falha in (TimeoutError("chave-ficticia"), URLError("chave-ficticia")):
            abrir.return_value.open.side_effect = falha
            with self.assertRaises(ErroRecomendacao) as erro:
                consultar_ia({})
            self.assertNotIn("chave-ficticia", str(erro.exception))

    @patch("livro.gemini.build_opener")
    def test_recusa_respostas_incompletas_bloqueadas_e_invalidas(self, abrir):
        exemplos = [b"[]", b"{}", b"null", b"nao json", b"x" * 256001,
                    b'{"promptFeedback":{"blockReason":"SAFETY"}}',
                    resposta_gemini({"recomendacoes": []}, "MAX_TOKENS"),
                    resposta_gemini({"recomendacoes": []}, "SAFETY"),
                    resposta_gemini({"recomendacoes": {}})]
        for bruto in exemplos:
            abrir.return_value.open.return_value.__enter__.return_value.read.return_value = bruto
            with self.assertRaises(ErroRecomendacao):
                consultar_ia({})
        abrir.return_value.open.return_value.__enter__.return_value.read.return_value = resposta_gemini({"criterios": [{"tipo": "inventado"}]})
        with self.assertRaises(ErroRecomendacao):
            consultar_ia({}, etapa="preferencias")

    @patch("livro.gemini.build_opener")
    def test_diagnostico_gemini_envia_apenas_exemplo(self, abrir):
        abrir.return_value.open.return_value.__enter__.return_value.read.side_effect = [
            resposta_gemini({"criterios": []}), resposta_gemini({"recomendacoes": []}),
        ]
        saida = StringIO()
        call_command("diagnosticar_ia", stdout=saida)
        self.assertIn("Testando Gemini", saida.getvalue())
        self.assertEqual(abrir.return_value.open.call_count, 2)
        pedido = json.loads(abrir.return_value.open.call_args.args[0].data)
        dados = json.loads(pedido["contents"][0]["parts"][0]["text"])
        self.assertEqual(dados["catalogo"], [])
        self.assertEqual(dados["historico"], [])


@override_settings(IA_PROVEDOR="gemini", GEMINI_API_KEY="chave-ficticia")
class GeminiFormularioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("leitor-gemini")
        cls.livro = Livro.objects.create(nome="Romance de teste", autor="Autora", cadastrado_por=cls.usuario)
        cls.livro.categorias.add(Categoria.objects.create(nome="Romance"))

    @patch("livro.gemini.build_opener")
    def test_pagina_e_recomendacao_com_provedor_remoto(self, abrir):
        self.client.force_login(self.usuario)
        abrir.return_value.open.return_value.__enter__.return_value.read.return_value = resposta_gemini({"criterios": [{"tipo": "categoria", "valor": "romance", "excluir": False}]})
        resposta = self.client.post(reverse("assistente_livros"), {"pergunta": "Quero romance"}, follow=True)
        self.assertContains(resposta, self.livro.nome)
        self.assertContains(resposta, "enviadas ao Google Gemini")
        self.assertNotContains(resposta, "não são enviadas ao Google")
        self.assertNotContains(resposta, "chave-ficticia")
        self.assertEqual(UsoIA.objects.get(usuario=self.usuario).quantidade, 1)

    @patch("livro.gemini.build_opener")
    def test_falha_na_pagina_nao_salva_resposta_e_conta_tentativa(self, abrir):
        self.client.force_login(self.usuario)
        abrir.return_value.open.side_effect = TimeoutError()
        resposta = self.client.post(reverse("assistente_livros"), {"pergunta": "Quero romance"})
        self.assertContains(resposta, "demorou demais")
        self.assertNotIn("conversa_livros", self.client.session)
        self.assertEqual(UsoIA.objects.get(usuario=self.usuario).quantidade, 1)

    def test_limite_persiste_entre_sessoes_e_renova_apos_uma_hora(self):
        reservar_pedido(self.usuario)
        # Um novo objeto/cliente não reinicia o contador guardado no banco.
        usuario_nova_instancia = get_user_model().objects.get(pk=self.usuario.pk)
        with self.assertRaisesMessage(ErroRecomendacao, "Aguarde alguns segundos"):
            reservar_pedido(usuario_nova_instancia)
        UsoIA.objects.filter(usuario=self.usuario).update(quantidade=20, ultimo_pedido=timezone.now()-timedelta(seconds=10))
        with self.assertRaisesMessage(ErroRecomendacao, "limite de pedidos"):
            reservar_pedido(usuario_nova_instancia)
        UsoIA.objects.filter(usuario=self.usuario).update(inicio=timezone.now()-timedelta(hours=1, seconds=1))
        reservar_pedido(usuario_nova_instancia)
        self.assertEqual(UsoIA.objects.get(usuario=self.usuario).quantidade, 1)
        outro = get_user_model().objects.create_user("outro-leitor")
        reservar_pedido(outro)
        self.assertEqual(UsoIA.objects.get(usuario=outro).quantidade, 1)
