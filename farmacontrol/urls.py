from django.contrib import admin
from django.urls import path, include
from usuarios.views import LoginRedirecionadoView
from usuarios import views 

urlpatterns = [
    # Página inicial o login
    path('', LoginRedirecionadoView.as_view(), name='login'),

    # Pagina admin e outras rotas
    path('admin/', admin.site.urls),
    path('estoque/', include('estoque.urls')),
    path('usuarios/', include('usuarios.urls')),

    #rotas de autenticação padrão do django
    path('auth/', include('django.contrib.auth.urls')),

    
]

