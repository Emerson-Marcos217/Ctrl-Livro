"""API Gemini chamada exclusivamente pelo servidor, sem SDK ou arquivos de chave."""

import json
import re
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings

from .ia_erros import ErroRecomendacao


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Não encaminhar a chave nem os dados a outro destino.
        return None


def conferir_chave():
    """Explica erros de colagem sem revelar nenhum trecho da credencial."""
    chave = settings.GEMINI_API_KEY.strip()
    if not chave:
        raise ErroRecomendacao("O assistente está aguardando configuração. Avise a biblioteca.")
    # A chave é opaca: pontuação como ponto, barra e '=' pode fazer parte
    # de credenciais. A validade é decidida pela API, não por um alfabeto local.
    problemas = []
    if any(ord(c) < 32 or ord(c) == 127 for c in chave):
        problemas.append("caracteres de controle, possivelmente introduzidos pela colagem no terminal")
    if any(c.isspace() for c in chave):
        problemas.append("espaços ou quebras de linha no meio do valor")
    if any(c in "\"'“”‘’" for c in chave):
        problemas.append("aspas junto da chave")
    if "*" in chave or "…" in chave:
        problemas.append("marcas de ocultação; copie a chave completa pelo botão de copiar")
    if not chave.isascii():
        problemas.append("caracteres não ASCII; confira se foi copiado somente o valor da chave")
    if problemas:
        raise ErroRecomendacao("A chave configurada contém " + "; ".join(problemas) + ".")
    return chave


def consultar_gemini(dados, instrucoes, formato):
    chave = conferir_chave()
    modelo = settings.GEMINI_MODEL.strip()
    if not re.fullmatch(r"gemini-[a-z0-9][a-z0-9.-]{0,100}", modelo):
        raise ErroRecomendacao("Configure GEMINI_MODEL com um identificador de modelo Gemini válido.")
    entrada = json.dumps(dados, ensure_ascii=False)
    if len((entrada + instrucoes).encode("utf-8")) > 12000:
        raise ErroRecomendacao("O pedido e o catálogo estão grandes para esta consulta. Comece uma nova conversa e faça um pedido mais breve.")
    corpo = {
        "systemInstruction": {"parts": [{"text": instrucoes}]},
        "contents": [{"role": "user", "parts": [{"text": entrada}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": formato,
            "maxOutputTokens": 4096,
            "candidateCount": 1,
        },
    }
    pedido = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": chave},
        method="POST",
    )
    try:
        # Sem repetição automática: cada tentativa pode consumir a cota da API.
        with build_opener(SemRedirecionamento()).open(pedido, timeout=settings.GEMINI_TIMEOUT) as conexao:
            bruto = conexao.read(256001)
        if len(bruto) > 256000:
            raise ValueError("Resposta muito grande")
        resposta = json.loads(bruto)
        if resposta.get("promptFeedback", {}).get("blockReason"):
            raise ErroRecomendacao("A IA não conseguiu responder a esse pedido. Tente reformular sua preferência de leitura.")
        candidato = resposta["candidates"][0]
        if candidato.get("finishReason") != "STOP":
            raise ErroRecomendacao("A IA não concluiu a resposta. Tente um pedido mais breve.")
        partes = candidato["content"]["parts"]
        texto = "".join(p["text"] for p in partes if not p.get("thought", False))
        return json.loads(texto)
    except HTTPError as erro:
        mensagens = {
            400: "A configuração da IA precisa ser revisada pela biblioteca.",
            401: "A IA não aceitou a credencial configurada. Avise a biblioteca.",
            403: "O acesso à IA foi negado. Avise a biblioteca.",
            404: "O modelo de IA configurado não está disponível. Avise a biblioteca.",
            429: "A IA atingiu o limite de uso. Tente mais tarde ou avise a biblioteca.",
            503: "A IA está temporariamente indisponível. Tente novamente mais tarde.",
            504: "A IA demorou demais para responder. Tente novamente mais tarde.",
        }
        mensagem = mensagens.get(erro.code, "Não foi possível consultar a IA. Tente novamente mais tarde.")
        erro.close()
        # Nem o diagnóstico mostra o corpo remoto, que pode conter dados ou chaves.
        raise ErroRecomendacao(f"{mensagem} Referência: HTTP {erro.code}.") from None
    except TimeoutError:
        raise ErroRecomendacao("A IA demorou demais para responder. Tente novamente mais tarde.") from None
    except (OSError, HTTPException):
        raise ErroRecomendacao("Não foi possível conectar ao serviço de IA. Tente novamente mais tarde.") from None
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise ErroRecomendacao("A IA enviou uma resposta inválida. Tente novamente.") from None
