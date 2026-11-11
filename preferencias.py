"""Requisitos de leitura e conferência das evidências usando apenas o cadastro."""

import re
import unicodedata


# Relações geográficas conservadoras, conferidas em:
# https://unstats.un.org/unsd/methodology/m49/overview/
# Países transcontinentais não são expandidos automaticamente.
LOCAIS_EUROPEUS = (
    "europa", "albania", "alemanha", "andorra", "austria", "belarus", "bielorrussia",
    "belgica", "bosnia e herzegovina", "bulgaria", "croacia", "dinamarca",
    "eslovaquia", "eslovenia", "espanha", "estonia", "finlandia", "franca",
    "grecia", "hungria", "irlanda", "islandia", "italia", "letonia",
    "liechtenstein", "lituania", "luxemburgo", "macedonia do norte", "malta",
    "moldavia", "moldova", "monaco", "montenegro", "noruega", "paises baixos",
    "holanda", "polonia", "portugal", "reino unido", "gra bretanha", "inglaterra",
    "escocia", "pais de gales", "irlanda do norte", "republica tcheca", "tchequia",
    "romenia", "san marino", "servia", "suecia", "suica", "ucrania", "vaticano",
)
ALIASES_LOCAIS = {
    "europa": ("europeu", "europeia", "europeus", "europeias"),
    "franca": ("frances", "francesa", "franceses", "francesas"),
    "inglaterra": ("ingles", "inglesa", "ingleses", "inglesas"),
    "portugal": ("portugues", "portuguesa", "portugueses", "portuguesas"),
    "brasil": ("brasileiro", "brasileira", "brasileiros", "brasileiras"),
    "alemanha": ("alemao", "alema", "alemaes", "alemas"),
    "espanha": ("espanhol", "espanhola", "espanhois", "espanholas"),
    "italia": ("italiano", "italiana", "italianos", "italianas"),
    "reino unido": ("britanico", "britanica", "britanicos", "britanicas"),
}
_LOCAL_POR_ALIAS = {alias: local for local, aliases in ALIASES_LOCAIS.items() for alias in aliases}
_PADRAO_ALIAS_LOCAL = re.compile(r"\b(?:" + "|".join(map(re.escape, _LOCAL_POR_ALIAS)) + r")\b")


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", texto))


def contem(texto, trecho):
    return bool(normalizar(trecho)) and f" {normalizar(trecho)} " in f" {normalizar(texto)} "


def normalizar_categoria(texto):
    """Reconhece flexões conhecidas sem alterar títulos, autores ou locais."""
    return re.sub(r"\b(?:romances|romantic[oa]s?)\b", "romance", normalizar(texto))


def normalizar_preferencia(texto):
    """Equivalências de linguagem, sem confundir futuro com um gênero."""
    return re.sub(r"\b(?:futur[oa]s?|futuristas?|futuristic[oa]s?)\b",
                  "futuro", normalizar_categoria(texto))


def pede_ambientacao_futura(texto):
    return "futuro" in normalizar_preferencia(texto).split()


def contem_preferencia(texto, trecho):
    """Aceita a mesma preferência com outra flexão na extração do modelo."""
    valor = normalizar_preferencia(trecho)
    return bool(valor) and f" {valor} " in f" {normalizar_preferencia(texto)} "


def normalizar_ambientacao(texto):
    """Normaliza gentílicos no pedido, sem inferir país a partir de continente."""
    return _PADRAO_ALIAS_LOCAL.sub(lambda m: _LOCAL_POR_ALIAS[m.group()], normalizar(texto))


def ambientacao_geografica_conhecida(valor):
    return normalizar_ambientacao(valor) in (*LOCAIS_EUROPEUS, "brasil")


def contem_ambientacao(texto, trecho):
    """Confere a origem do critério, aceitando 'europeia' como 'Europa'."""
    valor = normalizar_ambientacao(trecho)
    return bool(valor) and f" {valor} " in f" {normalizar_ambientacao(texto)} "


def corresponde_ambientacao(sinopse, valor):
    """Relaciona a região pedida a topônimos explícitos, somente na sinopse."""
    local = normalizar_ambientacao(valor)
    if local == "europa":
        locais = LOCAIS_EUROPEUS
    elif local == "reino unido":
        locais = ("reino unido", "gra bretanha", "inglaterra", "escocia", "pais de gales", "irlanda do norte")
    else:
        locais = (local,)
    return any(contem(sinopse, nome) for nome in locais)


def atende_requisitos(livro, criterios):
    """Gênero, local, título e autor são conferidos antes da seleção pelo modelo.

    Temas exigem sinopse e serão avaliados semanticamente com evidência. Não
    usamos a nacionalidade do autor para a ambientação. Regiões podem abranger
    países citados explicitamente na sinopse, conforme as relações cadastradas.
    Valores do mesmo requisito são alternativas; requisitos distintos se somam.
    """
    for criterio in criterios:
        tipo, valores = criterio["tipo"], criterio["valores"]
        if tipo == "categoria":
            encontrado = any(normalizar_categoria(v) == normalizar_categoria(c) for v in valores for c in livro["categorias"])
        elif tipo in ("ambientacao", "autor", "titulo"):
            campo = {"ambientacao": "sinopse", "autor": "autor", "titulo": "titulo"}[tipo]
            if not livro[campo].strip():
                return False
            conferir = corresponde_ambientacao if tipo == "ambientacao" else contem
            encontrado = any(conferir(livro[campo], v) for v in valores)
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
        if tipo == "categoria":
            trecho = next((t for t in trechos if any(
                normalizar_categoria(t) == normalizar_categoria(v) for v in criterio["valores"]
            )), None)
        elif tipo == "ambientacao":
            trecho = next((t for t in trechos if any(
                corresponde_ambientacao(t, v) for v in criterio["valores"]
            )), None)
        else:
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
            if trecho not in livro["categorias"] or not any(normalizar_categoria(trecho) == normalizar_categoria(v) for v in criterio["valores"]):
                return None
        elif not campo or trecho not in livro[campo]:
            return None
        elif criterio["tipo"] in ("ambientacao", "autor", "titulo"):
            conferir = corresponde_ambientacao if criterio["tipo"] == "ambientacao" else contem
            if not any(conferir(trecho, v) for v in criterio["valores"]):
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
