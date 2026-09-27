"""Formulários de entrada e cadastro de leitores."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


ModeloUsuario = get_user_model()


class FormularioLogin(AuthenticationForm):
    """Aproveita a validação de senha do Django e usa e-mail como identificação."""

    # username e password são os nomes esperados pelo login do Django.
    username = forms.EmailField(
        label="E-mail",
        max_length=150,
        widget=forms.EmailInput(
            attrs={"autocomplete": "username", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean_username(self):
        email = self.cleaned_data["username"]
        return email.strip().lower()


class FormularioCadastroLeitor(UserCreationForm):
    """Cria uma conta usando a proteção e a confirmação de senha do Django."""

    nome = forms.CharField(label="Nome completo", max_length=150)
    email = forms.EmailField(label="E-mail", max_length=150)

    class Meta:
        model = ModeloUsuario
        fields = ("nome", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        email_ja_cadastrado = ModeloUsuario.objects.filter(
            username__iexact=email,
        ).exists()

        if email_ja_cadastrado:
            raise forms.ValidationError("Este e-mail já tem uma conta.")

        return email

    def save(self, commit=True):
        # super().save prepara a conta e protege a senha antes de salvar.
        usuario = super().save(commit=False)
        usuario.username = self.cleaned_data["email"]
        usuario.email = self.cleaned_data["email"]
        usuario.first_name = self.cleaned_data["nome"]

        if commit:
            usuario.save()

        return usuario
