from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.LoginRedirecionadoView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil-gestor/', views.perfil_gestor, name='perfil_gestor'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),

    # Gerenciamento de usuários (Gestor/Admin)
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/adicionar/', views.adicionar_usuario, name='adicionar_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/senha/', views.redefinir_senha_usuario, name='redefinir_senha_usuario'),
    path('usuarios/<int:pk>/status/', views.alternar_status_usuario, name='alternar_status_usuario'),
]
