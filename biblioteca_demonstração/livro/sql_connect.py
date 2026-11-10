"""Leitura do acervo pela API REST do Firebase SQL Connect, somente no servidor."""

import re
from types import SimpleNamespace

from biblioteca.credenciais_google import obter_credenciais_google
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import RequestException

from django.conf import settings


class ErroSQLConnect(Exception):
    pass


def endereco_conector():
    valores = [settings.SQL_CONNECT_PROJECT, settings.SQL_CONNECT_LOCATION,
               settings.SQL_CONNECT_SERVICE, settings.SQL_CONNECT_CONNECTOR]
    if not all(re.fullmatch(r"[a-z][a-z0-9-]*", valor) for valor in valores):
        raise ErroSQLConnect("Configure o projeto, a região, o serviço e o conector do SQL Connect.")
    projeto, regiao, servico, conector = valores
    return ("https://firebasedataconnect.googleapis.com/v1/"
            f"projects/{projeto}/locations/{regiao}/services/{servico}/"
            f"connectors/{conector}:impersonateQuery")


def executar_consulta(ids):
    url = endereco_conector()
    try:
        credenciais = obter_credenciais_google()
        with AuthorizedSession(credenciais) as sessao:
            resposta = sessao.post(url, json={
                "operationName": "LivrosDoAcervo",
                "variables": {"ids": [str(pk) for pk in ids]},
                # Acesso do servidor via IAM, sem impersonar um leitor Firebase.
                "extensions": {},
            }, timeout=15, allow_redirects=False)
        if resposta.status_code != 200:
            # Não exibe corpo da resposta, tokens nem credenciais ao leitor.
            raise ErroSQLConnect(f"Falha na consulta ao SQL Connect (HTTP {resposta.status_code}).")
        dados = resposta.json()
    except GoogleAuthError as erro:
        raise ErroSQLConnect("Configure as credenciais Google do servidor para acessar o SQL Connect.") from erro
    except RequestException as erro:
        raise ErroSQLConnect("Não foi possível conectar ao SQL Connect. Tente novamente.") from erro
    except ValueError as erro:
        raise ErroSQLConnect("O SQL Connect retornou uma resposta inválida.") from erro
    if not isinstance(dados, dict) or dados.get("errors"):
        raise ErroSQLConnect("A consulta do SQL Connect falhou. Confira o conector e as permissões do servidor.")
    return dados.get("data")


def inteiro(valor):
    if type(valor) is int and valor >= 0:
        return valor
    if isinstance(valor, str) and valor.isascii() and valor.isdigit():
        return int(valor)
    raise ValueError("Inteiro inválido")


def livros_do_acervo(ids):
    """Busca só a página solicitada; omite livros desativados durante a consulta."""
    ids = list(ids)
    if not ids:
        return []
    dados = executar_consulta(ids)
    try:
        itens = dados["acervoLivros"]
        if not isinstance(itens, list):
            raise ValueError("Lista inválida")
        livros = {}
        for item in itens:
            pk = inteiro(item["id"])
            if pk not in ids or pk in livros:
                raise ValueError("Identificador inesperado")
            campos = ("nome", "autor", "coAutor", "sinopse")
            if not all(isinstance(item[campo], str) for campo in campos):
                raise ValueError("Texto inválido")
            categorias = item["categorias"]
            if not isinstance(categorias, list) or not all(isinstance(c, str) for c in categorias):
                raise ValueError("Categorias inválidas")
            livros[pk] = SimpleNamespace(
                pk=pk, nome=item["nome"], autor=item["autor"],
                co_autor=item["coAutor"], sinopse=item["sinopse"],
                disponiveis=inteiro(item["disponiveis"]),
                categorias={"all": categorias},
            )
        return [livros[pk] for pk in ids if pk in livros]
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroSQLConnect("O SQL Connect retornou dados incompatíveis com o acervo.") from erro
