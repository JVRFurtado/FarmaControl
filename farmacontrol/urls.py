from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from usuarios.views import LoginRedirecionadoView
from usuarios import views 
from . import views as views_farmacontrol

urlpatterns = [
    # Página inicial o login
    path('', LoginRedirecionadoView.as_view(), name='login'),

    # Pagina admin e outras rotas
    path('admin/', admin.site.urls),
    path('estoque/', include('estoque.urls')),
    path('usuarios/', include('usuarios.urls')),

    # Rotas de troca/recuperação de senha do Django.
    path('auth/password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('auth/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # Troca de idioma (manual) — funciona em qualquer página via POST
    path('idioma/<str:codigo>/', views_farmacontrol.mudar_idioma, name='mudar_idioma'),
]

