from django.urls import path

from . import api

urlpatterns = [
    path('', api.indice, name='api_indice'),
    path('produtos/', api.produtos, name='api_produtos'),
    path('produtos/<int:pk>/', api.produto, name='api_produto'),
    path('alertas/', api.alertas, name='api_alertas'),
    path('categorias/', api.categorias, name='api_categorias'),
    path('entregas/', api.entregas, name='api_entregas'),
    path('movimentacoes/', api.movimentacoes, name='api_movimentacoes'),
]
