"""Paginação simples e reutilizável para as telas de listagem."""
from django.core.paginator import Paginator

ITENS_POR_PAGINA = 50


def paginar(request, queryset, por_pagina=ITENS_POR_PAGINA):
    """Devolve a página pedida em `?page=` (valor inválido cai na página 1,
    página além do fim cai na última) — o objeto devolvido itera como lista."""
    return Paginator(queryset, por_pagina).get_page(request.GET.get('page'))


def querystring_sem_pagina(request):
    """Parâmetros atuais de busca/filtro sem o `page`, para montar os links
    de próxima/anterior preservando os filtros ativos."""
    parametros = request.GET.copy()
    parametros.pop('page', None)
    return parametros.urlencode()
