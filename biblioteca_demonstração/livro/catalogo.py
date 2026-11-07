"""Consulta compartilhada pelo catálogo e pelo assistente de leitura."""

from django.db.models import Count, Q

from .models import Exemplar, Livro


def catalogo_atual():
    return Livro.objects.filter(ativo=True).prefetch_related("categorias").annotate(
        disponiveis=Count(
            "exemplares", filter=Q(exemplares__status=Exemplar.Status.DISPONIVEL),
        ),
    )
