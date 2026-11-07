"""Teste opcional do formulário com Ollama real e banco de dados de teste."""

import os
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Categoria, Livro, UsoIA


@skipUnless(os.environ.get("TESTAR_OLLAMA") == "1", "Requer Ollama local: TESTAR_OLLAMA=1")
@override_settings(IA_PROVEDOR="ollama", IA_HOSPEDADA=False)
class OllamaRealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leitor = get_user_model().objects.create_user("teste-ollama-real")
        romance = Categoria.objects.create(nome="Romance")
        fantasia = Categoria.objects.create(nome="Fantasia")
        aventura = Categoria.objects.create(nome="Aventura")
        cls.orgulho = Livro.objects.create(
            nome="Orgulho e Preconceito", autor="Jane Austen", cadastrado_por=cls.leitor,
            sinopse="Elizabeth Bennet precisa lidar com expectativas de casamento e diferenças sociais na Inglaterra rural.",
        )
        cls.orgulho.categorias.add(romance)
        cls.hobbit = Livro.objects.create(
            nome="O Hobbit", autor="Tolkien", cadastrado_por=cls.leitor,
            sinopse="Bilbo participa de uma jornada com anões para recuperar um tesouro guardado por um dragão.",
        )
        cls.hobbit.categorias.add(fantasia, aventura)

    def test_formulario_com_modelo_real_e_continuacao(self):
        self.client.force_login(self.leitor)
        url = reverse("assistente_livros")
        casos = [
            ("quero um romance", self.orgulho.pk, True),
            ("gosto de fantasia", self.hobbit.pk, True),
            ("quero uma historia com aventura", self.hobbit.pk, True),
            ("me recomenda um livro", None, True),
            ("eu quero uma historia de romance que se passando na Inglaterra rural", self.orgulho.pk, True),
            ("quero um romance na França", None, True),
            ("quero um romance", self.orgulho.pk, True),
            ("que se passe na Inglaterra rural", self.orgulho.pk, False),
            ("agora quero fantasia", self.hobbit.pk, False),
        ]
        for pedido, esperado, limpar in casos:
            with self.subTest(pedido=pedido):
                if limpar:
                    self.client.post(url, {"acao": "limpar"})
                UsoIA.objects.all().delete()
                resposta = self.client.post(url, {"pergunta": pedido}, follow=True)
                self.assertEqual(resposta.status_code, 200)
                self.assertTrue(resposta.redirect_chain, "O formulário retornou erro em vez de salvar a resposta")
                self.assertNotContains(resposta, "Não consegui identificar")
                turno = self.client.session["conversa_livros"][-1]
                ids = [s["id"] for s in turno["recomendacoes"]]
                self.assertEqual(ids, [esperado] if esperado else [])
