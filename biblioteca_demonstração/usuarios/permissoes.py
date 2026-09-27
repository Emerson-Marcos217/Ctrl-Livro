"""Cria os dois perfis e define o que a equipe da biblioteca pode fazer."""

from django.contrib.auth.models import Group, Permission


def criar_grupos_e_permissoes(sender, **kwargs):
    """É chamada automaticamente depois do comando migrate."""
    if sender.label != "livro":
        return

    nome_do_banco = kwargs.get("using", "default")
    Group.objects.using(nome_do_banco).get_or_create(name="Leitor")
    grupo_bibliotecario, grupo_criado = Group.objects.using(nome_do_banco).get_or_create(
        name="Bibliotecario"
    )

    nomes_das_permissoes = [
        "view_livro",
        "add_livro",
        "change_livro",
        "view_categoria",
        "add_categoria",
        "change_categoria",
        "view_exemplar",
        "add_exemplar",
        "change_exemplar",
        "gerenciar_circulacao",
    ]
    permissoes_da_equipe = Permission.objects.using(nome_do_banco).filter(
        content_type__app_label="livro",
        codename__in=nomes_das_permissoes,
    )

    for permissao in permissoes_da_equipe:
        grupo_bibliotecario.permissions.add(permissao)
