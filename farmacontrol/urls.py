from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from usuarios.views import LoginRedirecionadoView
from . import views as views_farmacontrol

urlpatterns = [
    # Página inicial o login
    path('', LoginRedirecionadoView.as_view(), name='login'),

    # Pagina admin e outras rotas
    path('admin/', admin.site.urls),
    path('estoque/', include('estoque.urls')),
    path('api/', include('estoque.api_urls')),
    path('usuarios/', include('usuarios.urls')),

    # Rotas de troca/recuperação de senha do Django. NÃO usamos
    # `include('django.contrib.auth.urls')` inteiro de propósito: esse
    # include também registra URLs chamadas 'login' e 'logout', e como
    # ele vinha depois no arquivo, essas duas "ganhavam" de qualquer
    # `reverse('login')`/`{% url 'login' %}` do sistema — fazendo toda
    # tela de login cair na view genérica do Django (sem a nossa
    # mensagem de erro customizada) em vez da nossa LoginRedirecionadoView.
    # Login e logout já têm suas próprias rotas em usuarios/urls.py.
    # (password_reset — recuperação de senha por e-mail — não está incluída:
    # exigiria configurar um EMAIL_BACKEND e templates de e-mail que o
    # projeto não tem hoje, e nada na interface linka para essas telas. Se
    # precisar desse fluxo no futuro, adicione aqui.)
    path('auth/password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('auth/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # Troca de idioma (manual) — funciona em qualquer página via POST
    path('idioma/<str:codigo>/', views_farmacontrol.mudar_idioma, name='mudar_idioma'),
]

