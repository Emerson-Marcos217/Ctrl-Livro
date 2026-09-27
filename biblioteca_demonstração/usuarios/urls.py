from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import FormularioLogin
from .views import cadastrar_leitor


urlpatterns = [
    # O próprio Django cuida de entrar e sair da conta.
    path(
        "login/",
        LoginView.as_view(
            template_name="usuarios/login.html",
            authentication_form=FormularioLogin,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("cadastro/", cadastrar_leitor, name="cadastro"),
    path("sair/", LogoutView.as_view(), name="sair"),
]
