"""Escolhe a área do usuário e recebe o cadastro público de leitores."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import FormularioCadastroLeitor


@login_required
def abrir_pagina_inicial(request):
    """Encaminha a pessoa para o catálogo ou para o painel do bibliotecário."""
    pode_gerenciar_emprestimos = request.user.has_perm("livro.gerenciar_circulacao")

    if pode_gerenciar_emprestimos:
        return redirect("painel_bibliotecario")

    return redirect("catalogo")


@require_http_methods(["GET", "POST"])
def cadastrar_leitor(request):
    """Cria uma conta de leitor; o formulário não escolhe permissões."""
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        formulario = FormularioCadastroLeitor(request.POST)

        if formulario.is_valid():
            try:
                with transaction.atomic():
                    usuario = formulario.save()
                    grupo_leitor, grupo_criado = Group.objects.get_or_create(
                        name="Leitor"
                    )
                    usuario.groups.add(grupo_leitor)
            except IntegrityError:
                formulario.add_error("email", "Este e-mail já tem uma conta.")
            else:
                messages.success(
                    request,
                    "Conta criada! Entre com seu e-mail e senha.",
                )
                return redirect("login")
    else:
        formulario = FormularioCadastroLeitor()

    return render(request, "usuarios/cadastro.html", {"form": formulario})
