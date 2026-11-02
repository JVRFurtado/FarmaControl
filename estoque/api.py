"""
API JSON somente leitura do FarmaControl.

Pensada para integração com outros sistemas (painéis, planilhas, scripts):
devolve os mesmos dados das telas, com as mesmas regras de acesso.

- Autenticação: a mesma sessão do site (faça login em /usuarios/login/ e
  reaproveite o cookie). Sem login → 401 em JSON (não redireciona).
- Apenas GET (outros métodos → 405). A API não altera nada no banco.
- Listas paginadas: ?page= e ?por_pagina= (padrão 50, máximo 100).
- Datas em ISO 8601 (AAAA-MM-DD).
"""
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from .models import (
    DIAS_AVISO_VENCIMENTO, Categoria, Entrega, MovimentacaoEstoque, Produto,
    ProdutoQuerySet,
)

POR_PAGINA_PADRAO = 50
POR_PAGINA_MAXIMO = 100
LIMITE_ALERTAS = 50


def _json(dados, status=200):
    return JsonResponse(dados, status=status, json_dumps_params={'ensure_ascii': False})


def _erro(status, mensagem):
    return _json({'erro': mensagem}, status=status)


def api_view(view):
    """Só GET, só usuário autenticado e ativo; erros sempre em JSON."""
    @require_GET
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _erro(401, 'Autenticação necessária. Faça login em /usuarios/login/.')
        try:
            return view(request, *args, **kwargs)
        except Http404 as exc:
            return _erro(404, str(exc) or 'Não encontrado.')
    return _wrapped


# --- Serialização ----------------------------------------------------------

def _numero(valor):
    return float(valor) if valor is not None else None


def _data(valor):
    return valor.isoformat() if valor else None


def serializar_produto(p):
    medicamento = getattr(p, 'medicamento', None)
    return {
        'id': p.pk,
        'tipo': 'medicamento' if medicamento else 'produto',
        'nome': p.nome,
        'dosagem': medicamento.dosagem if medicamento else None,
        'categoria': p.categoria.nome if p.categoria else None,
        'categoria_id': p.categoria_id,
        'quantidade': p.quantidade,
        'estoque_minimo': p.estoque_minimo,
        'estoque_baixo': p.estoque_baixo,
        'data_validade': _data(p.data_validade),
        'dias_para_vencer': p.dias_para_vencer,
        'status_validade': p.status_validade,  # 'normal' | 'aviso' | 'vencido' | null
        'ultima_compra': _data(p.ultima_compra),
        'altura_cm': _numero(p.altura),
        'largura_cm': _numero(p.largura),
        'comprimento_cm': _numero(p.comprimento),
    }


def serializar_entrega(e):
    return {
        'id': e.pk,
        'produto_id': e.produto_id,
        'produto': e.produto_nome,
        'paciente': e.paciente,
        'quantidade': e.quantidade,
        'data_entrega': _data(e.data_entrega),
        'responsavel': e.usuario.username if e.usuario else None,
        'registrado_em': e.registrado_em.isoformat(),
    }


def serializar_movimentacao(m):
    return {
        'id': m.pk,
        'produto_id': m.produto_id,
        'produto': m.produto_nome,
        'tipo': m.tipo,  # 'ENTRADA' | 'SAIDA'
        'quantidade': m.quantidade,
        'motivo': m.motivo,
        'motivo_codigo': m.motivo_codigo,
        'motivo_detalhe': m.motivo_detalhe,
        'responsavel': m.usuario.username if m.usuario else None,
        'data': m.data.isoformat(),
    }


def _inteiro_positivo(valor, padrao):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if numero > 0 else padrao


def _resposta_paginada(request, queryset, serializador):
    por_pagina = min(
        _inteiro_positivo(request.GET.get('por_pagina'), POR_PAGINA_PADRAO),
        POR_PAGINA_MAXIMO,
    )
    paginador = Paginator(queryset, por_pagina)
    pagina = paginador.get_page(request.GET.get('page'))
    return _json({
        'count': paginador.count,
        'page': pagina.number,
        'pages': paginador.num_pages,
        'por_pagina': por_pagina,
        'results': [serializador(obj) for obj in pagina.object_list],
    })


def _produtos_base():
    return Produto.objects.select_related('categoria', 'medicamento')


# --- Endpoints -------------------------------------------------------------

@api_view
def indice(request):
    return _json({
        'nome': 'FarmaControl API',
        'versao': 1,
        'somente_leitura': True,
        'endpoints': {
            'produtos': reverse('api_produtos'),
            'produto (detalhe)': reverse('api_produto', args=[0]).replace('/0/', '/{id}/'),
            'alertas': reverse('api_alertas'),
            'categorias': reverse('api_categorias'),
            'entregas': reverse('api_entregas'),
            'movimentacoes': reverse('api_movimentacoes'),
        },
    })


@api_view
def produtos(request):
    """Filtros: ?buscar= · ?categoria=<id> · ?filtro=estoque_baixo|vencendo|vencidos|normal"""
    qs = _produtos_base()

    busca = request.GET.get('buscar')
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(categoria__nome__icontains=busca))

    categoria = request.GET.get('categoria')
    if categoria and categoria.isdigit():
        qs = qs.filter(categoria_id=int(categoria))

    filtro = request.GET.get('filtro')
    if filtro:
        if filtro not in ProdutoQuerySet.FILTROS:
            return _erro(400, f"Filtro inválido. Use: {', '.join(ProdutoQuerySet.FILTROS)}.")
        qs = qs.por_filtro(filtro)

    return _resposta_paginada(request, qs.order_by('nome', 'pk'), serializar_produto)


@api_view
def produto(request, pk):
    try:
        obj = _produtos_base().get(pk=pk)
    except Produto.DoesNotExist:
        raise Http404('Produto não encontrado.')
    return _json(serializar_produto(obj))


@api_view
def alertas(request):
    """Resumo dos alertas (mesma regra do dashboard) com os itens afetados."""
    base = _produtos_base()
    vencidos = base.vencidos().order_by('data_validade', 'nome')
    vencendo = base.vencendo().order_by('data_validade', 'nome')
    baixo = base.estoque_baixo().order_by('quantidade', 'nome')

    def lista(qs):
        return [serializar_produto(p) for p in qs[:LIMITE_ALERTAS]]

    return _json({
        'dias_aviso_vencimento': DIAS_AVISO_VENCIMENTO,
        'limite_por_lista': LIMITE_ALERTAS,
        'totais': {
            'produtos': Produto.objects.count(),
            'estoque_baixo': baixo.count(),
            'vencendo': vencendo.count(),
            'vencidos': vencidos.count(),
        },
        'vencidos': lista(vencidos),
        'vencendo': lista(vencendo),
        'estoque_baixo': lista(baixo),
    })


@api_view
def categorias(request):
    return _json({
        'results': [{'id': c.pk, 'nome': c.nome} for c in Categoria.objects.all()],
    })


@api_view
def entregas(request):
    """Filtros: ?produto=<id> · ?buscar= (produto ou paciente)"""
    qs = Entrega.objects.select_related('usuario')
    produto_id = request.GET.get('produto')
    if produto_id and produto_id.isdigit():
        qs = qs.filter(produto_id=int(produto_id))
    busca = request.GET.get('buscar')
    if busca:
        qs = qs.filter(Q(produto_nome__icontains=busca) | Q(paciente__icontains=busca))
    return _resposta_paginada(request, qs, serializar_entrega)


@api_view
def movimentacoes(request):
    """Filtros: ?produto=<id> · ?tipo=ENTRADA|SAIDA"""
    qs = MovimentacaoEstoque.objects.select_related('usuario')
    produto_id = request.GET.get('produto')
    if produto_id and produto_id.isdigit():
        qs = qs.filter(produto_id=int(produto_id))
    tipo = request.GET.get('tipo')
    if tipo:
        tipo = tipo.upper()
        if tipo not in (MovimentacaoEstoque.ENTRADA, MovimentacaoEstoque.SAIDA):
            return _erro(400, 'Tipo inválido. Use: ENTRADA ou SAIDA.')
        qs = qs.filter(tipo=tipo)
    return _resposta_paginada(request, qs, serializar_movimentacao)
