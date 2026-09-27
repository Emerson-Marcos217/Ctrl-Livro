from django.contrib import admin
from django.urls import include, path

from usuarios.views import abrir_pagina_inicial


urlpatterns = [
    path("", abrir_pagina_inicial, name="inicio"),
    path("admin/", admin.site.urls),
    path("auth/", include("usuarios.urls")),
    path("livro/", include("livro.urls")),
]
