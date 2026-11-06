from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .ia_erros import ErroRecomendacao
from .models import UsoIA


def reservar_pedido(usuario):
    """Conta tentativas antes da API; libera o bloqueio antes da chamada remota."""
    with transaction.atomic():
        uso, _ = UsoIA.objects.select_for_update().get_or_create(usuario=usuario)
        agora = timezone.now()
        if uso.quantidade and agora - uso.ultimo_pedido < timedelta(seconds=settings.IA_INTERVALO_SEGUNDOS):
            raise ErroRecomendacao("Aguarde alguns segundos antes de enviar outro pedido.")
        if agora - uso.inicio >= timedelta(hours=1):
            uso.inicio, uso.quantidade = agora, 0
        if uso.quantidade >= settings.IA_PEDIDOS_POR_HORA:
            raise ErroRecomendacao("Você atingiu o limite de pedidos desta hora. Tente novamente mais tarde.")
        uso.quantidade += 1
        uso.ultimo_pedido = agora
        uso.save(update_fields=["inicio", "quantidade", "ultimo_pedido"])
