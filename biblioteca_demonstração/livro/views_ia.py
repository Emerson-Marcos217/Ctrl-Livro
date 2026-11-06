"""Tela de conversa: mantém somente as seis últimas mensagens na sessão."""

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import FormularioRecomendacao
from .catalogo import catalogo_atual
from .recomendacoes import ErroRecomendacao, recomendar
from .limites_ia import reservar_pedido


@login_required
@require_http_methods(["GET", "POST"])
def assistente(request):
    historico = request.session.get("conversa_livros", [])
    formulario = FormularioRecomendacao()
    if request.method == "POST":
        if request.POST.get("acao") == "limpar":
            request.session.pop("conversa_livros", None)
            return redirect("assistente_livros")
        formulario = FormularioRecomendacao(request.POST)
        if formulario.is_valid():
            dados = formulario.cleaned_data
            try:
                reservar_pedido(request.user)
                resposta = recomendar(dados["pergunta"], historico)
            except ErroRecomendacao as erro:
                formulario.add_error(None, str(erro))
            else:
                historico = (historico + [
                    {"papel": "leitor", "mensagem": dados["pergunta"]},
                    {"papel": "assistente", **resposta},
                ])[-6:]
                request.session["conversa_livros"] = historico
                # Atualizar a página não dispara uma segunda geração de resposta.
                return redirect("assistente_livros")

    ids = [item["id"] for turno in historico for item in turno.get("recomendacoes", [])]
    livros = {livro.pk: livro for livro in catalogo_atual().filter(pk__in=ids)}
    conversa = []
    for turno in historico:
        conversa.append({
            **turno,
            "cartoes": [{"livro": livros[item["id"]], "motivo": item["motivo"]}
                        for item in turno.get("recomendacoes", []) if item["id"] in livros],
        })
    return render(request, "livro/assistente.html", {
        "form": formulario, "conversa": conversa,
        "ia_local": settings.IA_PROVEDOR == "ollama",
    })
