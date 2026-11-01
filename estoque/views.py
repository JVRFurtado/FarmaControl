import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from farmacontrol.context_processors import idioma_da_requisicao, traducoes_da_requisicao
from farmacontrol.formularios import dados_do_post
from farmacontrol.paginacao import paginar, querystring_sem_pagina
from usuarios.decorators import gestor_required

from . import relatorios as rel
from .forms import CategoriaForm, EntregaForm, MedicamentoForm, ProdutoForm
from .models import (
    DIAS_AVISO_VENCIMENTO, Categoria, Entrega, Medicamento, MovimentacaoEstoque,
    Produto, ProdutoQuerySet,
)
from .movimentacoes import motivo_traduzido, registrar_movimentacao

ENTRADA = MovimentacaoEstoque.ENTRADA
SAIDA = MovimentacaoEstoque.SAIDA


# --- Produtos --------------------------------------------------------------

@login_required
def lista_produtos(request):
    produtos = Produto.objects.select_related('categoria')

    busca = request.GET.get('buscar')
    if busca:
        produtos = produtos.filter(Q(nome__icontains=busca) | Q(categoria__nome__icontains=busca))

    categoria_id = request.GET.get('categoria') or ''
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)

    # Filtro de situação (cartões do dashboard e seletor da tabela); valor
    # desconhecido é ignorado. A consulta roda no banco.
    filtro = request.GET.get('filtro')
    if filtro not in ProdutoQuerySet.FILTROS:
        filtro = ''
    produtos = produtos.por_filtro(filtro).order_by('nome')

    return render(request, 'estoque/lista_produtos.html', {
        'produtos': paginar(request, produtos),
        'querystring': querystring_sem_pagina(request),
        'filtro_ativo': filtro,
        'categoria_selecionada': categoria_id,
        'categorias': Categoria.objects.all(),
    })


# Configuração do cadastro de cada tipo de item. Produto e medicamento
# seguem exatamente o mesmo fluxo (validar → barrar duplicado → salvar →
# registrar entrada inicial no histórico); só mudam estes parâmetros.
CADASTRO_PRODUTO = {
    'form': ProdutoForm,
    'modelo': Produto,
    'campos_duplicidade': ('nome', 'altura', 'largura', 'comprimento', 'categoria',
                           'data_validade', 'ultima_compra'),
    'template': 'estoque/adicionar_produto.html',
    'motivo_texto': 'Cadastro inicial do produto',
    'motivo_codigo': MovimentacaoEstoque.MOTIVO_CADASTRO_PRODUTO,
    'msg_ok': 'produto_cadastrado',
    'msg_duplicado': 'produto_duplicado',
    'msg_erro': 'erro_produto_existe',
}
CADASTRO_MEDICAMENTO = {
    'form': MedicamentoForm,
    'modelo': Medicamento,
    'campos_duplicidade': ('nome', 'dosagem', 'categoria', 'data_validade', 'ultima_compra'),
    'template': 'estoque/adicionar_medicamento.html',
    'motivo_texto': 'Cadastro inicial do medicamento',
    'motivo_codigo': MovimentacaoEstoque.MOTIVO_CADASTRO_MEDICAMENTO,
    'msg_ok': 'medicamento_cadastrado',
    'msg_duplicado': 'medicamento_duplicado',
    'msg_erro': 'erro_medicamento_existe',
}


def _cadastrar_item(request, cfg):
    mensagens = traducoes_da_requisicao(request)['mensagens']
    form = cfg['form'](dados_do_post(request))

    if request.method == 'POST' and form.is_valid():
        dados = form.cleaned_data
        ja_existe = cfg['modelo'].objects.filter(
            **{campo: dados[campo] for campo in cfg['campos_duplicidade']}
        ).exists()

        if ja_existe:
            messages.error(request, mensagens[cfg['msg_duplicado']])
        else:
            try:
                with transaction.atomic():
                    item = form.save()
                    registrar_movimentacao(
                        item, ENTRADA, item.quantidade, cfg['motivo_texto'], request.user,
                        motivo_codigo=cfg['motivo_codigo'],
                    )
            except IntegrityError:
                messages.error(request, mensagens[cfg['msg_erro']])
            else:
                messages.success(request, mensagens[cfg['msg_ok']])
                return redirect('lista_produtos')

    return render(request, cfg['template'], {'form': form})


@login_required
def adicionar_produto(request):
    return _cadastrar_item(request, CADASTRO_PRODUTO)


@login_required
def adicionar_medicamento(request):
    return _cadastrar_item(request, CADASTRO_MEDICAMENTO)


@gestor_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    mensagens = traducoes_da_requisicao(request)['mensagens']
    quantidade_antes = produto.quantidade  # antes do form: is_valid() altera a instância
    form = ProdutoForm(dados_do_post(request), instance=produto)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            produto = form.save()
            if quantidade_antes is not None and produto.quantidade is not None:
                delta = produto.quantidade - quantidade_antes
                registrar_movimentacao(
                    produto, ENTRADA if delta > 0 else SAIDA, abs(delta),
                    'Ajuste manual na edição do produto', request.user,
                    motivo_codigo=MovimentacaoEstoque.MOTIVO_AJUSTE_MANUAL,
                )
        messages.success(request, mensagens['produto_editado'])
        return redirect('lista_produtos')

    # O template de cadastro também serve para edição.
    return render(request, 'estoque/adicionar_produto.html', {'form': form, 'editar': True})


@gestor_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    if request.method != 'POST':
        # GET só mostra a confirmação — nunca exclui (evita exclusão por link/robô).
        return render(request, 'estoque/confirmar_exclusao.html', {'produto': produto})

    with transaction.atomic():
        # Registra a saída ANTES de excluir, para não perder o rastro do estoque.
        registrar_movimentacao(
            produto, SAIDA, produto.quantidade, 'Produto excluído do sistema', request.user,
            motivo_codigo=MovimentacaoEstoque.MOTIVO_EXCLUSAO_PRODUTO,
        )
        produto.delete()

    messages.success(request, traducoes_da_requisicao(request)['mensagens']['produto_excluido'])
    return redirect('lista_produtos')


def _registrar_entrega(request, produto, form, mensagens):
    """Baixa o estoque e grava Entrega + movimentação. Devolve True se deu certo."""
    quantidade = form.cleaned_data['quantidade']
    paciente = form.cleaned_data['paciente']

    if quantidade > (produto.quantidade or 0):
        messages.error(request, mensagens['estoque_insuficiente'])
        return False

    produto.quantidade -= quantidade
    produto.save(update_fields=['quantidade'])
    Entrega.objects.create(
        produto=produto,
        produto_nome=produto.nome,
        paciente=paciente,
        quantidade=quantidade,
        data_entrega=form.cleaned_data['data_entrega'],
        usuario=request.user,
    )
    registrar_movimentacao(
        produto, SAIDA, quantidade, f'Entrega para {paciente}', request.user,
        motivo_codigo=MovimentacaoEstoque.MOTIVO_ENTREGA, motivo_detalhe=paciente,
    )
    messages.success(request, mensagens['entrega_registrada'].format(
        paciente=paciente, quantidade=quantidade))
    return True


@login_required
def entregar_produto(request, produto_id):
    mensagens = traducoes_da_requisicao(request)['mensagens']
    form = EntregaForm(dados_do_post(request))

    if request.method == 'POST':
        with transaction.atomic():
            # select_for_update: duas entregas simultâneas do mesmo produto
            # não conseguem ler o mesmo saldo e entregar estoque que não existe.
            produto = get_object_or_404(Produto.objects.select_for_update(), id=produto_id)
            if form.is_valid() and _registrar_entrega(request, produto, form, mensagens):
                return redirect('lista_produtos')
    else:
        produto = get_object_or_404(Produto, id=produto_id)

    return render(request, 'estoque/entregar_produto.html', {'produto': produto, 'form': form})


# --- Categorias ------------------------------------------------------------

@login_required
def lista_categorias(request):
    return render(request, 'estoque/lista_categorias.html', {'categorias': Categoria.objects.all()})


@login_required
def adicionar_categoria(request):
    # `next` permite voltar direto para o formulário de produto/medicamento
    # que a pessoa estava preenchendo quando percebeu que faltava a categoria.
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('lista_categorias')
    form = CategoriaForm(dados_do_post(request))

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, traducoes_da_requisicao(request)['mensagens']['categoria_cadastrada'])
        return redirect(next_url)

    return render(request, 'estoque/adicionar_categoria.html', {'form': form, 'next': next_url})


@gestor_required
def excluir_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method != 'POST':
        return render(request, 'estoque/confirmar_exclusao_categoria.html', {'categoria': categoria})

    categoria.delete()
    messages.success(request, traducoes_da_requisicao(request)['mensagens']['categoria_excluida'])
    return redirect('lista_categorias')


# --- Históricos ------------------------------------------------------------

@login_required
def historico_entregas(request):
    entregas = Entrega.objects.select_related('produto', 'usuario')

    produto_id = request.GET.get('produto')
    if produto_id:
        entregas = entregas.filter(produto_id=produto_id)

    busca = request.GET.get('buscar')
    if busca:
        entregas = entregas.filter(Q(produto_nome__icontains=busca) | Q(paciente__icontains=busca))

    return render(request, 'estoque/historico_entregas.html', {
        'entregas': paginar(request, entregas),
        'querystring': querystring_sem_pagina(request),
        'busca': busca or '',
    })


@login_required
def historico_movimentacoes(request):
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto', 'usuario')

    produto_id = request.GET.get('produto')
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)

    tipo = request.GET.get('tipo')
    if tipo in (ENTRADA, SAIDA):
        movimentacoes = movimentacoes.filter(tipo=tipo)

    pagina = paginar(request, movimentacoes)
    pagina.object_list = list(pagina.object_list)  # materializa uma vez; os atributos abaixo persistem
    tr = traducoes_da_requisicao(request)
    # Anexa o motivo já traduzido a cada objeto (sem tocar no banco) para o
    # template só exibir `mov.motivo_exibicao`.
    for mov in pagina:
        mov.motivo_exibicao = motivo_traduzido(mov.motivo_codigo, mov.motivo_detalhe, mov.motivo, tr)

    return render(request, 'estoque/historico_movimentacoes.html', {
        'movimentacoes': pagina,
        'querystring': querystring_sem_pagina(request),
        'tipo_selecionado': tipo or '',
    })


# --- Relatórios ------------------------------------------------------------

@login_required
def relatorios(request):
    idioma = idioma_da_requisicao(request)
    rotulos = rel.rotulos_dos_tipos(traducoes_da_requisicao(request))

    tipo = request.GET.get('tipo', 'estoque')
    if tipo not in rel.TIPOS_RELATORIO_VALIDOS:
        tipo = 'estoque'

    categoria_id = request.GET.get('categoria') or ''
    data_inicio_str = request.GET.get('data_inicio', '')
    data_fim_str = request.GET.get('data_fim', '')

    colunas, linhas = rel.montar_relatorio(
        tipo, categoria_id, rel.parse_data(data_inicio_str), rel.parse_data(data_fim_str), idioma,
    )

    formato = request.GET.get('formato', 'html')
    if formato == 'csv':
        return rel.exportar_csv(rotulos[tipo], colunas, linhas)
    if formato == 'xlsx':
        return rel.exportar_xlsx(rotulos[tipo], colunas, linhas)

    return render(request, 'estoque/relatorios.html', {
        'tipo_selecionado': tipo,
        'tipo_rotulo': rotulos[tipo],
        'mostrar_periodo': tipo in rel.TIPOS_COM_PERIODO,
        'categorias': Categoria.objects.all(),
        'categoria_selecionada': categoria_id,
        'data_inicio': data_inicio_str,
        'data_fim': data_fim_str,
        'colunas': colunas,
        'linhas': linhas,
        'total_linhas': len(linhas),
    })


# --- Análises / gráficos ---------------------------------------------------

@login_required
def analises(request):
    p_t = traducoes_da_requisicao(request)['produtos']
    hoje = date.today()

    # Estoque total por categoria — uma consulta só (antes era uma por categoria).
    por_categoria = Categoria.objects.annotate(total=Sum('produto__quantidade'))
    labels_categoria = [c.nome for c in por_categoria]
    dados_categoria = [c.total or 0 for c in por_categoria]

    # Situação de validade — uma consulta com contagens condicionais.
    limite_aviso = hoje + timedelta(days=DIAS_AVISO_VENCIMENTO)
    contagem = Produto.objects.aggregate(
        normal=Count('pk', filter=Q(data_validade__gt=limite_aviso)),
        aviso=Count('pk', filter=Q(data_validade__gte=hoje, data_validade__lte=limite_aviso)),
        vencido=Count('pk', filter=Q(data_validade__lt=hoje)),
        sem_validade=Count('pk', filter=Q(data_validade__isnull=True)),
    )

    # Entradas x saídas dos últimos 30 dias, agrupadas por dia no banco.
    dias = [hoje - timedelta(days=i) for i in range(29, -1, -1)]
    totais = (
        MovimentacaoEstoque.objects.filter(data__date__gte=dias[0])
        .annotate(dia=TruncDate('data'))
        .values('dia', 'tipo')
        .annotate(total=Sum('quantidade'))
        .order_by()
    )
    por_dia = {(t['dia'], t['tipo']): t['total'] for t in totais}

    return render(request, 'estoque/analises.html', {
        'labels_categoria': json.dumps(labels_categoria),
        'dados_categoria': json.dumps(dados_categoria),
        'labels_status': json.dumps([
            p_t['status_normal'], p_t['status_aviso'], p_t['status_vencido'], p_t['status_sem_validade'],
        ]),
        'dados_status': json.dumps([
            contagem['normal'], contagem['aviso'], contagem['vencido'], contagem['sem_validade'],
        ]),
        'labels_dias': json.dumps([d.strftime('%d/%m') for d in dias]),
        'dados_entrada': json.dumps([por_dia.get((d, ENTRADA), 0) for d in dias]),
        'dados_saida': json.dumps([por_dia.get((d, SAIDA), 0) for d in dias]),
        'sem_dados': not Produto.objects.exists(),
    })
