"""Requisitos de leitura e conferência das evidências usando apenas o cadastro."""

import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", texto))


def contem(texto, trecho):
    return bool(normalizar(trecho)) and f" {normalizar(trecho)} " in f" {normalizar(texto)} "


def atende_requisitos(livro, criterios):
    """Gênero, local, título e autor são conferidos antes da seleção pelo modelo.

    Temas exigem sinopse e serão avaliados semanticamente com evidência. Não
    usamos a nacionalidade do autor nem conhecimento externo para a ambientação.
    Valores do mesmo requisito são alternativas; requisitos distintos se somam.
    """
    for criterio in criterios:
        tipo, valores = criterio["tipo"], criterio["valores"]
        if tipo == "categoria":
            encontrado = any(normalizar(v) == normalizar(c) for v in valores for c in livro["categorias"])
        elif tipo in ("ambientacao", "autor", "titulo"):
            campo = {"ambientacao": "sinopse", "autor": "autor", "titulo": "titulo"}[tipo]
            if not livro[campo].strip():
                return False
            encontrado = any(contem(livro[campo], v) for v in valores)
        elif tipo == "tema":
            if not livro["sinopse"].strip() or criterio["excluir"]:
                return False
            continue
        else:
            return False
        if encontrado == criterio["excluir"]:
            return False
    return True


def evidencias_objetivas(livro, criterios):
    """Os campos objetivos já conferidos não dependem de cópia feita pelo modelo."""
    evidencias = []
    for indice, criterio in enumerate(criterios):
        if criterio["excluir"] or criterio["tipo"] == "tema":
            continue
        tipo = criterio["tipo"]
        if tipo == "categoria":
            trechos = livro["categorias"]
        elif tipo == "ambientacao":
            trechos = re.split(r"(?<=[.!?])\s+", livro["sinopse"])
        else:
            trechos = [livro[tipo]]
        trecho = next((t for t in trechos if any(contem(t, v) for v in criterio["valores"])), None)
        if trecho:
            evidencias.append({"criterio": indice, "trecho": trecho})
    return evidencias


def motivo_comprovado(livro, criterios, evidencias):
    """Não exibe prosa gerada pelo modelo; monta o motivo com trechos conferidos."""
    if not isinstance(evidencias, list) or len(evidencias) > 6:
        return None
    comprovados = set()
    trechos = []
    campos = {"categoria": "categorias", "ambientacao": "sinopse", "tema": "sinopse",
              "autor": "autor", "titulo": "titulo"}
    rotulos = {"categorias": "Categoria cadastrada", "sinopse": "Na sinopse cadastrada",
               "autor": "Autor cadastrado", "titulo": "Título cadastrado"}
    for evidencia in evidencias:
        if not isinstance(evidencia, dict):
            return None
        indice, trecho = evidencia.get("criterio"), evidencia.get("trecho")
        if type(indice) is not int or not 0 <= indice < len(criterios):
            return None
        criterio = criterios[indice]
        if criterio["excluir"] or indice in comprovados:
            return None
        campo = campos.get(criterio["tipo"])
        if not isinstance(trecho, str) or not trecho.strip() or len(trecho) > 700:
            return None
        # Exigimos cópia literal; uma paráfrase poderia adicionar fatos inventados.
        if campo == "categorias":
            if trecho not in livro["categorias"] or not any(normalizar(trecho) == normalizar(v) for v in criterio["valores"]):
                return None
        elif not campo or trecho not in livro[campo]:
            return None
        elif criterio["tipo"] in ("ambientacao", "autor", "titulo"):
            if not any(contem(trecho, v) for v in criterio["valores"]):
                return None
        elif len(normalizar(trecho)) < 12:
            return None
        comprovados.add(indice)
        frase = f'{rotulos[campo]}: “{trecho}”'
        if frase not in trechos:
            trechos.append(frase)
    obrigatorios = {i for i, c in enumerate(criterios) if not c["excluir"]}
    if comprovados != obrigatorios:
        return None
    return "\n".join(trechos) or "Selecionado conforme as categorias e os filtros informados."
