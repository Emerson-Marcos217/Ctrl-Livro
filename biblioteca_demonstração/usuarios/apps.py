from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        # ready é chamado pelo Django quando a aplicação é carregada.
        from django.db.models.signals import post_migrate
        from .permissoes import criar_grupos_e_permissoes

        post_migrate.connect(
            criar_grupos_e_permissoes,
            dispatch_uid="biblioteca.grupos",
        )
