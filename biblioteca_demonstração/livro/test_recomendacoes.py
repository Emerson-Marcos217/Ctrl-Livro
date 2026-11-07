import json
from io import BytesIO, StringIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Categoria, Exemplar, Livro, UsoIA
from .recomendacoes import ErroRecomendacao, consultar_ia, recomendar


@override_settings(IA_PROVEDOR="ollama", IA_HOSPEDADA=False, OLLAMA_MODEL="qwen2.5:3b")
class RecomendacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leitor = get_user_model().objects.create_user("teste-ia")
        cls.categoria = Categoria.objects.create(nome="Fantasia")
        cls.livro = Livro.objects.create(
            nome="Viagem de teste", autor="Autora", sinopse="Uma viagem com amigos.",
            cadastrado_por=cls.leitor,
        )
        cls.livro.categorias.add(cls.categoria)
        cls.exemplar = Exemplar.objects.create(livro=cls.livro, codigo="IA-1")
        cls.oculto = Livro.objects.create(nome="Livro oculto", autor="Outro", ativo=False, cadastrado_por=cls.leitor)
        cls.indisponivel = Livro.objects.create(nome="Sem cópias", autor="Outro", cadastrado_por=cls.leitor)

    def setUp(self):
        UsoIA.objects.all().delete()
        self.client.force_login(self.leitor)
        self.url = reverse("assistente_livros")
        self.preferencias_patch = patch("livro.recomendacoes.interpretar_preferencias")
        self.preferencias = self.preferencias_patch.start()
        self.addCleanup(self.preferencias_patch.stop)
        self.preferencias.return_value = {"quantidade": 3, "criterios": [
            {"tipo": "tema", "valores": ["viagem"], "origem": "viagem", "excluir": False},
        ]}

    def resposta(self):
        return {"mensagem": "Veja esta sugestão.", "recomendacoes": [
            {"id": self.livro.pk, "evidencias": [{"criterio": 0, "trecho": "Uma viagem com amigos."}]},
        ]}

    def test_login_e_csrf_obrigatorios(self):
        self.assertEqual(Client().get(self.url).status_code, 302)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.leitor)
        self.assertEqual(cliente.post(self.url, {"pergunta": "Fantasia"}).status_code, 403)

    @patch("livro.recomendacoes.consultar_ia")
    def test_apenas_catalogo_permitido_sem_dados_do_leitor(self, ia):
        ia.return_value = self.resposta()
        recomendar("Quero fantasia", [])
        dados = ia.call_args.args[0]
        self.assertEqual([livro["id"] for livro in dados["catalogo"]], [self.livro.pk])
        self.assertEqual(dados["catalogo"][0]["exemplares_disponiveis"], 1)
        self.assertNotIn("cadastrado_por", dados["catalogo"][0])
        self.assertNotIn("teste-ia", json.dumps(dados))

    @patch("livro.recomendacoes.consultar_ia")
    def test_rejeita_ids_inventados_ocultos_e_duplicados(self, ia):
        ia.return_value = {"mensagem": "Sugestões", "recomendacoes": [
            {"id": 99999, "motivo": "Inventado"},
            {"id": self.oculto.pk, "motivo": "Oculto"},
            {"id": self.livro.pk, "evidencias": [{"criterio": 0, "trecho": "Uma viagem com amigos."}]},
        ]}
        self.assertEqual([r["id"] for r in recomendar("Fantasia", [])["recomendacoes"]], [self.livro.pk])
        ia.return_value["recomendacoes"] = [
            {"id": self.livro.pk, "evidencias": [{"criterio": 0, "trecho": "Uma viagem com amigos."}]},
            {"id": self.livro.pk, "motivo": "Duplicado"},
            {"id": True, "motivo": "Tipo inválido"},
        ]
        self.assertEqual(len(recomendar("Fantasia", [])["recomendacoes"]), 1)

    @patch("livro.recomendacoes.consultar_ia")
    def test_confere_disponibilidade_apos_resposta(self, ia):
        def responder(dados):
            Exemplar.objects.filter(pk=self.exemplar.pk).update(status="emprestado")
            return self.resposta()
        ia.side_effect = responder
        resposta = self.client.post(self.url, {"pergunta": "Fantasia"}, follow=True)
        self.assertContains(resposta, self.livro.nome)
        self.assertContains(resposta, "Sem exemplar disponível")
        self.assertNotContains(resposta, "Disponível para solicitar")

    @patch("livro.recomendacoes.consultar_ia")
    def test_catalogo_vazio_e_limite_nao_chamam_ia(self, ia):
        with patch("livro.recomendacoes.LIMITE_CATALOGO", 1):
            with self.assertRaises(ErroRecomendacao):
                recomendar("Fantasia", [])
        Livro.objects.update(ativo=False)
        self.assertEqual(recomendar("Fantasia", [])["recomendacoes"], [])
        ia.assert_not_called()

    @patch("livro.recomendacoes.consultar_ia")
    def test_conversa_refresh_limpeza_e_escape_html(self, ia):
        ia.return_value = self.resposta()
        ia.return_value["mensagem"] = "<script>alert(1)</script>"
        resposta = self.client.post(self.url, {"pergunta": "Quero fantasia"}, follow=True)
        self.assertContains(resposta, self.livro.nome)
        self.assertNotContains(resposta, "&lt;script&gt;")
        self.assertNotContains(resposta, "<script>alert(1)</script>")
        self.client.get(self.url)
        self.assertEqual(ia.call_count, 1)
        UsoIA.objects.all().delete()
        self.client.post(self.url, {"pergunta": "Prefiro aventuras"})
        self.assertEqual(self.preferencias.call_args.args[1][0]["mensagem"], "Quero fantasia")
        self.client.post(self.url, {"acao": "limpar"})
        self.assertNotIn("conversa_livros", self.client.session)

    @patch("livro.recomendacoes.consultar_ia")
    def test_pergunta_vazia_longa_e_clique_repetido(self, ia):
        for pergunta in ("", "a" * 1001):
            self.client.post(self.url, {"pergunta": pergunta})
        ia.assert_not_called()
        ia.return_value = self.resposta()
        self.client.post(self.url, {"pergunta": "Fantasia"})
        resposta = self.client.post(self.url, {"pergunta": "Fantasia"})
        self.assertContains(resposta, "Aguarde alguns segundos")
        self.assertEqual(ia.call_count, 1)

    @patch("livro.recomendacoes.consultar_ia")
    def test_livro_ocultado_nao_reaparece_no_historico(self, ia):
        ia.return_value = self.resposta()
        self.client.post(self.url, {"pergunta": "Fantasia"})
        Livro.objects.filter(pk=self.livro.pk).update(ativo=False)
        self.assertNotContains(self.client.get(self.url), self.livro.nome)

    def resposta_ollama(self):
        return {"message": {"role": "assistant", "content": json.dumps(self.resposta())},
                "done": True, "done_reason": "stop"}

    @patch("livro.recomendacoes.build_opener")
    def test_conexao_direta_local_e_formato_http(self, abrir):
        abrir.return_value.open.return_value.__enter__.return_value.read.side_effect = [
            b'{"details":{"family":"qwen2"}}', json.dumps(self.resposta_ollama()).encode(),
        ]
        self.assertEqual(consultar_ia({"pedido": "Fantasia"}), self.resposta())
        chamadas = abrir.return_value.open.call_args_list
        self.assertEqual([c.args[0].full_url for c in chamadas], [
            "http://127.0.0.1:11434/api/show", "http://127.0.0.1:11434/api/chat",
        ])
        pedido = chamadas[1].args[0]
        corpo = json.loads(pedido.data)
        self.assertIsNone(pedido.get_header("Authorization"))
        self.assertIsNone(pedido.get_header("X-goog-api-key"))
        self.assertFalse(corpo["stream"])
        self.assertEqual(corpo["format"]["required"], ["recomendacoes"])
        self.assertEqual(corpo["options"]["num_ctx"], 16384)
        self.assertEqual(chamadas[1].kwargs["timeout"], 180)
        self.assertEqual(abrir.call_args.args[0].proxies, {})
        handler = abrir.call_args.args[1]
        self.assertIsNone(handler.redirect_request(None, None, 307, "", {}, "https://example.com"))

    @patch("livro.recomendacoes.enviar_pedido")
    def test_erros_de_conexao_e_tempo_na_pagina(self, rede):
        for erro, trecho in [(URLError("segredo"), "Abra o aplicativo Ollama"),
                             (TimeoutError("segredo"), "demorou demais")]:
            with self.subTest(erro=erro):
                UsoIA.objects.all().delete()
                rede.side_effect = erro
                resposta = self.client.post(self.url, {"pergunta": "Fantasia"})
                self.assertContains(resposta, trecho)
                self.assertNotContains(resposta, "segredo")
                self.assertNotIn("conversa_livros", self.client.session)

    @patch("livro.recomendacoes.enviar_pedido")
    def test_erros_http_orientam_sem_expor_pedido_ou_repetir(self, rede):
        for status, trecho in [(404, "ollama pull"), (400, "configuração"),
                              (401, "negou acesso"), (500, "memória"), (503, "ocupado")]:
            with self.subTest(status=status):
                rede.reset_mock()
                rede.side_effect = HTTPError("http://127.0.0.1:11434", status, "erro", {},
                                             BytesIO(b'{"error":"segredo dados do leitor"}'))
                with self.assertRaises(ErroRecomendacao) as contexto:
                    consultar_ia({})
                self.assertIn(trecho, str(contexto.exception))
                self.assertNotIn("segredo", str(contexto.exception))
                self.assertEqual(rede.call_count, 1)

    @patch("livro.recomendacoes.enviar_pedido")
    def test_modelo_remoto_rejeitado_antes_de_enviar_conversa(self, rede):
        for detalhes in [{"remote_host": "https://ollama.com"}, {"remote_model": "remoto"}]:
            rede.reset_mock()
            rede.return_value = detalhes
            with self.assertRaisesMessage(ErroRecomendacao, "usa a nuvem"):
                consultar_ia({"pedido": "dados pessoais"})
            rede.assert_called_once_with("/api/show", {"model": "qwen2.5:3b"}, timeout=10)

    @patch("livro.recomendacoes.enviar_pedido")
    def test_modelo_invalido_ou_cloud_nao_chama_rede(self, rede):
        for modelo in ["", "qwen:cloud", "modelo-cloud", "https://example.com", "../modelo"]:
            with self.settings(OLLAMA_MODEL=modelo):
                with self.assertRaises(ErroRecomendacao):
                    consultar_ia({})
        rede.assert_not_called()

    @patch("livro.recomendacoes.enviar_pedido")
    def test_entrada_grande_nao_e_truncada(self, rede):
        with self.assertRaisesMessage(ErroRecomendacao, "nova conversa"):
            consultar_ia({"catalogo": ["a" * 12000]})
        rede.assert_not_called()

    @patch("livro.recomendacoes.enviar_pedido")
    def test_respostas_invalidas_e_incompletas(self, rede):
        for resposta in [None, [], {}, {"done": False},
                         {"done": True, "done_reason": "length"},
                         {"done": True, "done_reason": "stop", "message": {"content": "[]"}},
                         {"done": True, "done_reason": "stop", "message": {"content": "{}"}},
                         {"done": True, "done_reason": "stop", "message": {"content": "não json"}}]:
            rede.side_effect = [{}, resposta]
            with self.assertRaises(ErroRecomendacao):
                consultar_ia({})

    @patch("livro.recomendacoes.build_opener")
    def test_json_invalido_e_resposta_grande(self, abrir):
        for bruto in [b"nao json", b"x" * 256001]:
            abrir.return_value.open.return_value.__enter__.return_value.read.return_value = bruto
            with self.assertRaises(ErroRecomendacao):
                consultar_ia({})

    @override_settings(GEMINI_API_KEY="", OPENAI_API_KEY="")
    def test_tela_local_habilitada_sem_chave(self):
        resposta = self.client.get(self.url)
        self.assertContains(resposta, "IA local")
        self.assertNotContains(resposta, "aguardando configuração")
        self.assertNotContains(resposta, "disabled")
        self.assertNotContains(resposta, "Google Gemini")

    @patch("livro.recomendacoes.enviar_pedido")
    def test_fluxo_completo_ollama(self, rede):
        rede.side_effect = [{}, self.resposta_ollama()]
        resposta = self.client.post(self.url, {"pergunta": "Quero uma viagem com amigos"}, follow=True)
        self.assertContains(resposta, self.livro.nome)
        self.assertContains(resposta, "Disponível para solicitar")
        self.assertEqual(len(self.client.session["conversa_livros"]), 2)
        self.client.get(self.url)
        self.assertEqual(rede.call_count, 2)

    @patch("livro.recomendacoes.enviar_pedido")
    def test_diagnostico_apenas_dados_ficticios(self, rede):
        preferencias = {"message": {"content": '{"criterios": []}'}, "done": True, "done_reason": "stop"}
        rede.side_effect = [{}, preferencias, {}, self.resposta_ollama()]
        saida = StringIO()
        call_command("diagnosticar_ia", stdout=saida)
        self.assertIn("Conexão e formato de resposta aceitos", saida.getvalue())
        self.assertIn("Ollama local", saida.getvalue())
        dados = json.loads(rede.call_args.args[1]["messages"][1]["content"])
        self.assertEqual(dados["catalogo"], [])
        self.assertEqual(dados["historico"], [])

    @patch("livro.recomendacoes.enviar_pedido")
    def test_diagnostico_oculta_tokens(self, rede):
        corpo = b'{"error":"modelo ausente sk-teste-token AIza-token-ficticio Bearer segredo"}'
        rede.side_effect = HTTPError("http://127.0.0.1:11434", 404, "erro", {}, BytesIO(corpo))
        with self.assertRaises(CommandError) as contexto:
            call_command("diagnosticar_ia", stdout=StringIO())
        mensagem = str(contexto.exception)
        self.assertIn("modelo ausente", mensagem)
        for segredo in ["sk-teste-token", "AIza-token-ficticio", "segredo"]:
            self.assertNotIn(segredo, mensagem)

    @patch("livro.recomendacoes.consultar_ia")
    def test_formato_invalido_e_historico_limitado(self, ia):
        for resposta in ([], {}, {"recomendacoes": {}}):
            ia.return_value = resposta
            with self.assertRaises(ErroRecomendacao):
                recomendar("Fantasia", [])
        ia.return_value = self.resposta()
        for numero in range(5):
            UsoIA.objects.all().delete()
            self.client.post(self.url, {"pergunta": f"Fantasia {numero}"})
        self.assertEqual(len(self.client.session["conversa_livros"]), 6)
        self.assertEqual(len(self.preferencias.call_args.args[1]), 6)

@override_settings(IA_PROVEDOR="ollama", IA_HOSPEDADA=False)
class RecomendacaoFundamentadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leitor = get_user_model().objects.create_user("teste-evidencias")
        cls.romance = Categoria.objects.create(nome="Romance")
        cls.aventura = Categoria.objects.create(nome="Aventura")
        cls.orgulho = Livro.objects.create(cadastrado_por=cls.leitor,
            nome="Orgulho e Preconceito", autor="Jane Austen",
            sinopse="Elizabeth Bennet enfrenta expectativas de casamento na Inglaterra rural.",
        )
        cls.orgulho.categorias.add(cls.romance)
        cls.principe = Livro.objects.create(cadastrado_por=cls.leitor, nome="O Pequeno Príncipe", autor="Autor francês", sinopse="")
        cls.principe.categorias.add(cls.aventura)
        cls.casmurro = Livro.objects.create(cadastrado_por=cls.leitor, nome="Dom Casmurro", sinopse="Uma história de ciúme e amor.")
        cls.casmurro.categorias.add(cls.romance)

    def preferencias(self, local="Inglaterra rural"):
        return {"quantidade": 3, "criterios": [
            {"tipo": "categoria", "valor": "Romance", "excluir": False},
            {"tipo": "ambientacao", "valor": local, "excluir": False},
        ]}

    @patch("livro.recomendacoes.consultar_ia")
    def test_pedido_real_exige_genero_e_ambientacao(self, ia):
        ia.return_value = self.preferencias()
        r = recomendar("eu quero uma historia de romance que se passando na Inglaterra rural", [])
        self.assertEqual([s["id"] for s in r["recomendacoes"]], [self.orgulho.pk])
        self.assertIn(self.orgulho.sinopse, r["recomendacoes"][0]["motivo"])
        self.assertIn("Romance", r["recomendacoes"][0]["motivo"])
        self.assertNotIn("França", json.dumps(r, ensure_ascii=False))
        # A IA interpreta; as condições objetivas são conferidas pelo sistema.
        ia.assert_called_once()
        self.assertEqual(ia.call_args.kwargs["etapa"], "preferencias")

    @patch("livro.recomendacoes.consultar_ia")
    def test_franca_sem_comprovacao_nao_recebe_alternativa(self, ia):
        ia.return_value = self.preferencias("França")
        r = recomendar("Quero um romance na França", [])
        self.assertEqual(r["recomendacoes"], [])
        self.assertIn("Não encontrei", r["mensagem"])
        ia.assert_called_once()

    @patch("livro.recomendacoes.consultar_ia")
    def test_ambientacao_nao_usa_nacionalidade_do_autor(self, ia):
        self.principe.autor = "Escritor da França"
        self.principe.save()
        ia.return_value = {"quantidade": 3, "criterios": [
            {"tipo": "ambientacao", "valor": "França", "excluir": False},
        ]}
        self.assertEqual(recomendar("Quero uma história na França", [])["recomendacoes"], [])

    @patch("livro.recomendacoes.consultar_ia")
    def test_sem_sinopse_nao_chega_a_selecao_por_tema(self, ia):
        ia.side_effect = [
            {"quantidade": 3, "criterios": [{"tipo": "tema", "valor": "amizade", "excluir": False}]},
            {"recomendacoes": []},
        ]
        recomendar("Quero uma história sobre amizade", [])
        ids = [l["id"] for l in ia.call_args.args[0]["catalogo"]]
        self.assertNotIn(self.principe.pk, ids)

    @patch("livro.recomendacoes.consultar_ia")
    def test_texto_inventado_e_mensagem_livre_nunca_sao_exibidos(self, ia):
        preferencias = {"quantidade": 3, "criterios": [
            {"tipo": "tema", "valor": "amor", "excluir": False},
        ]}
        for trecho in ["Uma história na França.", "", "amor"]:
            ia.side_effect = [preferencias, {"mensagem": "O livro se passa na França!", "recomendacoes": [
                {"id": self.casmurro.pk, "motivo": "Pode ser adaptado à França", "evidencias": [{"criterio": 0, "trecho": trecho}]},
            ]}]
            r = recomendar("Quero uma história de amor", [])
            self.assertEqual(r["recomendacoes"], [])
            self.assertNotIn("França", r["mensagem"])
        ia.side_effect = [preferencias, {"mensagem": "O livro se passa na França!", "recomendacoes": [
            {"id": self.casmurro.pk, "evidencias": [{"criterio": 0, "trecho": self.casmurro.sinopse}]},
        ]}]
        r = recomendar("Quero uma história de amor", [])
        self.assertEqual(len(r["recomendacoes"]), 1)
        self.assertIn(self.casmurro.sinopse, r["recomendacoes"][0]["motivo"])
        self.assertNotIn("França", json.dumps(r, ensure_ascii=False))

    @patch("livro.recomendacoes.consultar_ia")
    def test_cada_tema_precisa_de_evidencia(self, ia):
        ia.side_effect = [
            {"quantidade": 3, "criterios": [
                {"tipo": "tema", "valor": "amor", "excluir": False},
                {"tipo": "tema", "valor": "amizade", "excluir": False},
            ]},
            {"recomendacoes": [{"id": self.casmurro.pk, "evidencias": [{"criterio": 0, "trecho": self.casmurro.sinopse}]}]},
        ]
        self.assertEqual(recomendar("Quero amor e amizade", [])["recomendacoes"], [])

    @patch("livro.recomendacoes.consultar_ia")
    def test_sinopse_alterada_durante_geracao_invalida_evidencia(self, ia):
        preferencias = {"quantidade": 3, "criterios": [{"tipo": "tema", "valor": "amor", "excluir": False}]}
        def responder(dados, **kwargs):
            if kwargs.get("etapa") == "preferencias":
                return preferencias
            Livro.objects.filter(pk=self.casmurro.pk).update(sinopse="Outro texto.")
            return {"recomendacoes": [{"id": self.casmurro.pk, "evidencias": [{"criterio": 0, "trecho": self.casmurro.sinopse}]}]}
        ia.side_effect = responder
        self.assertEqual(recomendar("Quero amor", [])["recomendacoes"], [])

    @patch("livro.recomendacoes.consultar_ia")
    def test_historico_usa_apenas_o_que_o_leitor_disse(self, ia):
        ia.return_value = self.preferencias()
        historico = [
            {"papel": "leitor", "mensagem": "Quero romance"},
            {"papel": "assistente", "mensagem": "O Pequeno Príncipe se passa na França", "recomendacoes": []},
        ]
        r = recomendar("Que se passe na Inglaterra rural", historico)
        self.assertEqual([s["id"] for s in r["recomendacoes"]], [self.orgulho.pk])
        self.assertEqual(ia.call_args.args[0]["historico"], ["Quero romance"])
        self.assertNotIn("Pequeno", json.dumps(ia.call_args.args[0]))

    @patch("livro.recomendacoes.consultar_ia")
    def test_exclusao_de_genero_e_quantidade(self, ia):
        ia.return_value = {"quantidade": 1, "criterios": [
            {"tipo": "categoria", "valor": "Romance", "excluir": True},
        ]}
        r = recomendar("Só um livro, não quero romance", [])
        self.assertEqual([s["id"] for s in r["recomendacoes"]], [self.principe.pk])
        ia.return_value = {"quantidade": 1, "criterios": [
            {"tipo": "categoria", "valor": "Romance", "excluir": False},
        ]}
        self.assertEqual(len(recomendar("Só um romance", [])["recomendacoes"]), 1)

    @patch("livro.recomendacoes.consultar_ia")
    def test_sem_preferencia_pergunta_e_dado_ausente_nao_e_inventado(self, ia):
        ia.return_value = {"quantidade": 3, "criterios": []}
        self.assertIn("Que gênero", recomendar("Olá", [])["mensagem"])
        ia.return_value = {"quantidade": 3, "criterios": [
            {"tipo": "nao_verificavel", "valor": "100 páginas", "excluir": False},
        ]}
        r = recomendar("Quero um livro de 100 páginas", [])
        self.assertEqual(r["recomendacoes"], [])
        self.assertIn("informações suficientes", r["mensagem"])

    @patch("livro.recomendacoes.enviar_pedido")
    def test_preferencias_invalidas_sao_rejeitadas_na_resposta_do_modelo(self, rede):
        for valor in [None, {}, {"criterios": {}}, {"criterios": [{}]},
                      {"criterios": [{"tipo": "categoria", "valor": "romance", "excluir": "false"}]},
                      {"criterios": [{"tipo": "sql", "valor": "romance", "excluir": False}]},
                      {"criterios": [{"tipo": "tema", "valor": "", "excluir": False}]}]:
            rede.side_effect = [{}, {"done": True, "done_reason": "stop", "message": {"content": json.dumps(valor)}}]
            with self.subTest(valor=valor), self.assertRaises(ErroRecomendacao):
                consultar_ia({"pedido": "Quero romance"}, etapa="preferencias")


class InterpretacaoSimplesTests(TestCase):
    @patch("livro.recomendacoes.consultar_ia")
    def test_romance_simples_nao_exige_origem_repetida(self, ia):
        from .recomendacoes import interpretar_preferencias
        ia.return_value = {"criterios": [{"tipo": "categoria", "valor": "romance", "excluir": False}]}
        r = interpretar_preferencias("quero um romance", [], ["Romance", "Fantasia"])
        self.assertEqual(r["criterios"][0]["valores"], ["Romance"])
        self.assertEqual(r["quantidade"], 3)
        self.assertNotIn("categorias_cadastradas", ia.call_args.args[0])

    @patch("livro.recomendacoes.consultar_ia")
    def test_genero_deduzido_nao_vira_exigencia(self, ia):
        from .recomendacoes import interpretar_preferencias
        ia.return_value = {"criterios": [
            {"tipo": "categoria", "valor": "romance", "excluir": False},
            {"tipo": "tema", "valor": "amor", "excluir": False},
        ]}
        r = interpretar_preferencias("quero um livro sobre amor", [], ["Romance"])
        self.assertEqual([c["tipo"] for c in r["criterios"]], ["tema"])

    @patch("livro.recomendacoes.consultar_ia")
    def test_mudanca_explicita_remove_restricoes_antigas(self, ia):
        from .recomendacoes import interpretar_preferencias
        ia.return_value = {"criterios": [{"tipo": "tema", "valor": "fantasia", "excluir": False}]}
        historico = [{"papel": "leitor", "mensagem": "Romance na Inglaterra rural"}]
        r = interpretar_preferencias("agora quero fantasia", historico, ["Fantasia"])
        self.assertEqual(ia.call_args.args[0]["historico"], [])
        self.assertEqual(r["criterios"][0]["tipo"], "categoria")
        historico.append({"papel": "leitor", "mensagem": "agora quero fantasia"})
        interpretar_preferencias("com viagens", historico, ["Fantasia"])
        self.assertEqual(ia.call_args.args[0]["historico"], ["agora quero fantasia"])

    @patch("livro.recomendacoes.consultar_ia")
    def test_local_inventado_continua_bloqueado(self, ia):
        from .recomendacoes import interpretar_preferencias
        ia.return_value = {"criterios": [{"tipo": "ambientacao", "valor": "França", "excluir": False}]}
        with self.assertRaises(ErroRecomendacao):
            interpretar_preferencias("romance na Inglaterra rural", [], ["Romance"])

    def test_quantidade_pedida(self):
        from .recomendacoes import quantidade_pedida
        for texto, quantidade in [("só um romance", 1), ("quero dois livros", 2), ("3 recomendações", 3), ("quero romance", 3)]:
            self.assertEqual(quantidade_pedida(texto), quantidade)
