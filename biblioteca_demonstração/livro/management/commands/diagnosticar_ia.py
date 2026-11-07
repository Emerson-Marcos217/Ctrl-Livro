"""Testa o provedor configurado, enviando somente dados fictícios."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from livro.recomendacoes import ErroRecomendacao, consultar_ia
from livro.gemini import conferir_chave


class Command(BaseCommand):
    help = "Faz uma chamada de teste à IA, sem enviar o catálogo, e mostra o diagnóstico local."

    def add_arguments(self, parser):
        parser.add_argument("--configuracao", action="store_true",
                            help="Confere apenas a colagem da chave Gemini, sem chamar a API.")

    def handle(self, *args, **options):
        if options["configuracao"]:
            if settings.IA_PROVEDOR != "gemini":
                raise CommandError("Configure IA_PROVEDOR=gemini para conferir a chave.")
            try:
                conferir_chave()
            except ErroRecomendacao as erro:
                raise CommandError(str(erro)) from None
            self.stdout.write("Formato da chave aceito localmente. A validade e a cota ainda precisam do teste da API.")
            return
        provedor = "Ollama local" if settings.IA_PROVEDOR == "ollama" else "Gemini"
        self.stdout.write(f"Testando {provedor} com dados fictícios. Nenhum dado do acervo será enviado.")
        try:
            consultar_ia({"pedido": "Quero romance", "historico": []},
                         diagnostico=True, etapa="preferencias")
            consultar_ia({
                "pedido": "Teste de conexão: responda com uma mensagem breve e nenhuma recomendação.",
                "historico": [],
                "catalogo": [],
            }, diagnostico=True)
        except ErroRecomendacao as erro:
            raise CommandError(str(erro)) from None
        self.stdout.write(self.style.SUCCESS(
            "Conexão e formato de resposta aceitos. Se o site ainda falhar, "
            "reinicie o servidor neste terminal e teste uma nova conversa com uma pergunta."
        ))
