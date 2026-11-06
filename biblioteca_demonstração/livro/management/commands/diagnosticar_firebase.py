from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, DatabaseError

from livro.catalogo import catalogo_atual
from livro.sql_connect import ErroSQLConnect, livros_do_acervo


class Command(BaseCommand):
    help = "Confere PostgreSQL e uma leitura autenticada pelo Firebase SQL Connect."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Ainda está usando SQLite. Configure BIBLIOTECA_BANCO=firebase e as variáveis PG*.")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            amostra = list(catalogo_atual().order_by("pk")[:12])
        except DatabaseError as erro:
            raise CommandError("Não foi possível ler o PostgreSQL. Confira a conexão e execute migrate.") from erro
        self.stdout.write("PostgreSQL: conexão e tabelas acessíveis.")
        try:
            # Mesmo um acervo vazio precisa validar a API; -1 nunca é um ID gerado pelo Django.
            remotos = livros_do_acervo([livro.pk for livro in amostra] or [-1])
        except ErroSQLConnect as erro:
            raise CommandError(str(erro)) from erro
        esperado = [(l.pk, l.nome, l.autor, l.co_autor, l.sinopse, l.disponiveis,
                     [c.nome for c in l.categorias.all()]) for l in amostra]
        recebido = [(l.pk, l.nome, l.autor, l.co_autor, l.sinopse, l.disponiveis,
                     l.categorias["all"]) for l in remotos]
        if esperado != recebido:
            raise CommandError("Os dados divergem. Confira se Django e SQL Connect apontam para o mesmo banco; repita sem cadastros simultâneos.")
        self.stdout.write(self.style.SUCCESS("SQL Connect: consulta autenticada funcionando; amostra consistente com o Django."))
        if not settings.SQL_CONNECT_ATIVO:
            self.stdout.write("Para usar a API na página do acervo, configure SQL_CONNECT_ATIVO=1 e reinicie o servidor.")
