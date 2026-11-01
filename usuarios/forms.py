from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm as DjangoUserCreationForm

from farmacontrol.formularios import aplicar_classe_input, marcar_campos_obrigatorios

from .models import Users


class UserChargeForm(UserChangeForm):
    """Edição de usuário pelo Gestor/Admin dentro do sistema (usuário, e-mail, cargo)."""

    class Meta(UserChangeForm.Meta):
        model = Users
        fields = ('username', 'email', 'cargo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O UserChangeForm do Django declara um campo de senha "hasheada" com
        # links de ajuda do /admin; aqui a troca de senha tem tela própria.
        self.fields.pop('password', None)
        aplicar_classe_input(self)
        marcar_campos_obrigatorios(self)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # O e-mail não pode repetir, exceto o do próprio usuário sendo editado.
        if Users.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este email já está em uso.')
        return email


class UserCreationForm(DjangoUserCreationForm):
    """Cadastro de novo usuário (usuário, e-mail, cargo e senha com confirmação)."""

    class Meta(DjangoUserCreationForm.Meta):
        model = Users
        fields = ('username', 'email', 'cargo', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classe_input(self)
        marcar_campos_obrigatorios(self)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError('Este email já está em uso.')
        return email
