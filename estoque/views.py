from datetime import date, timedelta, datetime
import csv
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils.text import slugify
from django.db.models import Sum
from .models import Produto, Medicamento, Categoria, Entrega, MovimentacaoEstoque
from .forms import ProdutoForm, MedicamentoForm, EntregaForm, CategoriaForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Q
from functools import wraps
from farmacontrol.i18n import TRANSLATIONS, IDIOMA_PADRAO
from farmacontrol.context_processors import idioma_da_requisicao


def gestor_required(view_func):
    """Só permite acesso a usuários com cargo 'Gestor'. Atendentes recebem 403."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.cargo != 'G':
            raise PermissionDenied('Apenas o Gestor pode realizar esta ação.')
        return view_func(request, *args, **kwargs)
    return _wrapped


def registrar_movimentacao(produto, tipo, quantidade, motivo, usuario, motivo_codigo='', motivo_detalhe=''):
    """Registra uma entrada ou saída no histórico de movimentações de estoque.
    Não registra nada se a quantidade for zero ou negativa.

    `motivo` guarda o texto em português (histórico bruto / fallback para
    motivos que não têm um código conhecido). `motivo_codigo` identifica um
    motivo "padrão" para que a exibição possa traduzir o texto conforme o
    idioma da pessoa (veja `_motivo_traduzido` mais abaixo)."""
    if not quantidade or quantidade <= 0:
        return
    MovimentacaoEstoque.objects.create(
        produto=produto,
        produto_nome=produto.nome,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
        motivo_codigo=motivo_codigo,
        motivo_detalhe=motivo_detalhe,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
    )


def _motivo_traduzido(motivo_codigo, motivo_detalhe, motivo_bruto, tr):
    """Traduz o motivo de uma movimentação para o idioma atual, quando o
    motivo tiver um código conhecido. Registros antigos (sem código) ou
    motivos livres caem no texto bruto salvo em português."""
    m_t = tr['movimentacoes_hist']
    mapa = {
        MovimentacaoEstoque.MOTIVO_CADASTRO_PRODUTO: m_t['motivo_cadastro_produto'],
        MovimentacaoEstoque.MOTIVO_CADASTRO_MEDICAMENTO: m_t['motivo_cadastro_medicamento'],
        MovimentacaoEstoque.MOTIVO_AJUSTE_MANUAL: m_t['motivo_ajuste_manual'],
        MovimentacaoEstoque.MOTIVO_EXCLUSAO_PRODUTO: m_t['motivo_exclusao_produto'],
    }
    if motivo_codigo == MovimentacaoEstoque.MOTIVO_ENTREGA:
        return f"{m_t['motivo_entrega_prefixo']} {motivo_detalhe}"
    if motivo_codigo in mapa:
        return mapa[motivo_codigo]
    return motivo_bruto


# Página inicial
def pagina_inicial(request):
    return render(request, 'estoque/home.html')

# Lista de produtos com busca
@login_required
def lista_produtos(request):
    produtos = Produto.objects.select_related('categoria').all()
    busca = request.GET.get('buscar')
    filtro = request.GET.get('filtro')
    categoria_id = request.GET.get('categoria') or ''

    if busca:
        produtos = produtos.filter(
            Q(nome__icontains=busca) | Q(categoria__nome__icontains=busca)
        )

    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)

    produtos = produtos.order_by('nome')

    # Filtro de status: vem tanto dos cartões do dashboard (estoque baixo /
    # vencendo / vencidos) quanto do próprio seletor da tabela.
    # `estoque_baixo`, `vencimento_proximo`, `esta_vencido` e `status_validade`
    # são propriedades calculadas no modelo (não colunas no banco), então o
    # filtro é aplicado em Python depois de buscar os produtos.
    if filtro == 'estoque_baixo':
        produtos = [p for p in produtos if p.estoque_baixo]
    elif filtro == 'vencendo':
        produtos = [p for p in produtos if p.vencimento_proximo]
    elif filtro == 'vencidos':
        produtos = [p for p in produtos if p.esta_vencido]
    elif filtro == 'normal':
        produtos = [p for p in produtos if p.status_validade == 'normal']
    else:
        filtro = ''

    return render(request, 'estoque/lista_produtos.html', {
        'produtos': produtos,
        'is_gestor': request.user.cargo == 'G',
        'filtro_ativo': filtro,
        'categoria_selecionada': categoria_id,
        'categorias': Categoria.objects.all(),
    })

# Adicionar produto
@login_required
def adicionar_produto(request):
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            altura = form.cleaned_data['altura']
            largura = form.cleaned_data['largura']
            comprimento = form.cleaned_data['comprimento']
            categoria = form.cleaned_data['categoria']
            data_validade = form.cleaned_data['data_validade']
            ultima_compra = form.cleaned_data['ultima_compra']

            # Verifica se já existe produto exatamente igual
            if Produto.objects.filter(
                nome=nome, 
                altura=altura,
                largura=largura,
                comprimento=comprimento,
                categoria=categoria,
                data_validade=data_validade,
                ultima_compra=ultima_compra
            ).exists():
                messages.error(request, tr['produto_duplicado'])
            else:
                try:
                    produto_salvo = form.save()
                    if produto_salvo.quantidade and produto_salvo.quantidade > 0:
                        registrar_movimentacao(
                            produto_salvo, MovimentacaoEstoque.ENTRADA, produto_salvo.quantidade,
                            'Cadastro inicial do produto', request.user,
                            motivo_codigo=MovimentacaoEstoque.MOTIVO_CADASTRO_PRODUTO,
                        )
                    messages.success(request, tr['produto_cadastrado'])
                    return redirect('lista_produtos')
                except IntegrityError:
                    messages.error(request, tr['erro_produto_existe'])
    else:
        form = ProdutoForm()

    return render(request, 'estoque/adicionar_produto.html', {'form': form})

# Adicionar medicamento
@login_required
def adicionar_medicamento(request):
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            dosagem = form.cleaned_data['dosagem']
            categoria = form.cleaned_data['categoria']
            data_validade = form.cleaned_data['data_validade']
            ultima_compra = form.cleaned_data['ultima_compra']
            
            # Verifica se já existe medicamento exatamente igual
            if Medicamento.objects.filter(
                nome=nome,
                dosagem=dosagem,
                categoria=categoria,
                data_validade=data_validade,
                ultima_compra=ultima_compra,
                
            ).exists():
                messages.error(request, tr['medicamento_duplicado'])
            else:
                try:
                    medicamento_salvo = form.save()
                    if medicamento_salvo.quantidade and medicamento_salvo.quantidade > 0:
                        registrar_movimentacao(
                            medicamento_salvo, MovimentacaoEstoque.ENTRADA, medicamento_salvo.quantidade,
                            'Cadastro inicial do medicamento', request.user,
                            motivo_codigo=MovimentacaoEstoque.MOTIVO_CADASTRO_MEDICAMENTO,
                        )
                    messages.success(request, tr['medicamento_cadastrado'])
                    return redirect('lista_produtos')
                except IntegrityError:
                    messages.error(request, tr['erro_medicamento_existe'])
    else:
        form = MedicamentoForm()

    categorias = Categoria.objects.all()

    return render(request, 'estoque/adicionar_medicamento.html', {
        'form': form,
        'categorias': categorias
    })

# Editar produto
@login_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        quantidade_antes = produto.quantidade
        form = ProdutoForm(request.POST, instance=produto)  # instância passada para edição
        if form.is_valid():
            produto_editado = form.save()
            quantidade_depois = produto_editado.quantidade

            if quantidade_antes is not None and quantidade_depois is not None and quantidade_antes != quantidade_depois:
                delta = quantidade_depois - quantidade_antes
                tipo = MovimentacaoEstoque.ENTRADA if delta > 0 else MovimentacaoEstoque.SAIDA
                registrar_movimentacao(
                    produto_editado, tipo, abs(delta),
                    'Ajuste manual na edição do produto', request.user,
                    motivo_codigo=MovimentacaoEstoque.MOTIVO_AJUSTE_MANUAL,
                )

            messages.success(request, tr['produto_editado'])
            return redirect('lista_produtos')  # volta para a lista depois de salvar
    else:
        form = ProdutoForm(instance=produto)  # preenche o formulário com dados existentes
    
    # Reaproveitando o template de adicionar (por exemplo: 'estoque/adicionar_produto.html')
    return render(request, 'estoque/adicionar_produto.html', {'form': form, 'editar': True})


# Excluir produto
# Restrito a Gestor e exige POST (evita exclusão via link direto/GET e por Atendentes).
@gestor_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    if request.method != 'POST':
        # Mostra uma página de confirmação em vez de excluir direto no GET.
        return render(request, 'estoque/confirmar_exclusao.html', {'produto': produto})

    if produto.quantidade:
        registrar_movimentacao(
            produto, MovimentacaoEstoque.SAIDA, produto.quantidade,
            'Produto excluído do sistema', request.user,
            motivo_codigo=MovimentacaoEstoque.MOTIVO_EXCLUSAO_PRODUTO,
        )

    produto.delete()
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']
    messages.success(request, tr['produto_excluido'])
    return redirect('lista_produtos')

#Baixar estoque
@login_required
def entregar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = EntregaForm(request.POST)
        if form.is_valid():
            quantidade_entregue = form.cleaned_data['quantidade']
            paciente = form.cleaned_data['paciente']
            data_entrega = form.cleaned_data['data_entrega']
            
            if quantidade_entregue > produto.quantidade:
                messages.error(request, tr['estoque_insuficiente'])
            else:
                produto.quantidade -= quantidade_entregue
                produto.save()

                Entrega.objects.create(
                    produto=produto,
                    produto_nome=produto.nome,
                    paciente=paciente,
                    quantidade=quantidade_entregue,
                    data_entrega=data_entrega,
                    usuario=request.user if request.user.is_authenticated else None,
                )
                registrar_movimentacao(
                    produto, MovimentacaoEstoque.SAIDA, quantidade_entregue,
                    f'Entrega para {paciente}', request.user,
                    motivo_codigo=MovimentacaoEstoque.MOTIVO_ENTREGA, motivo_detalhe=paciente,
                )

                messages.success(request, tr['entrega_registrada'].format(paciente=paciente, quantidade=quantidade_entregue))
                return redirect('lista_produtos')
    else:
        form = EntregaForm()
        
    return render(request, 'estoque/entregar_produto.html', {'produto': produto, 'form': form})


# --- Categorias ---

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'estoque/lista_categorias.html', {
        'categorias': categorias,
        'is_gestor': request.user.cargo == 'G',
    })


@login_required
def adicionar_categoria(request):
    # `next` permite voltar direto para o formulário de produto/medicamento
    # que o usuário estava preenchendo quando percebeu que faltava a categoria.
    from django.urls import reverse
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('lista_categorias')
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, tr['categoria_cadastrada'])
            return redirect(next_url)
    else:
        form = CategoriaForm()

    return render(request, 'estoque/adicionar_categoria.html', {'form': form, 'next': next_url})


@gestor_required
def excluir_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method != 'POST':
        return render(request, 'estoque/confirmar_exclusao_categoria.html', {'categoria': categoria})

    categoria.delete()
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']
    messages.success(request, tr['categoria_excluida'])
    return redirect('lista_categorias')


# --- Históricos ---

@login_required
def historico_entregas(request):
    entregas = Entrega.objects.select_related('produto', 'usuario').all()

    produto_id = request.GET.get('produto')
    if produto_id:
        entregas = entregas.filter(produto_id=produto_id)

    busca = request.GET.get('buscar')
    if busca:
        entregas = entregas.filter(
            Q(produto_nome__icontains=busca) | Q(paciente__icontains=busca)
        )

    return render(request, 'estoque/historico_entregas.html', {
        'entregas': entregas,
        'busca': busca or '',
    })


@login_required
def historico_movimentacoes(request):
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto', 'usuario').all()

    produto_id = request.GET.get('produto')
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)

    tipo = request.GET.get('tipo')
    if tipo in (MovimentacaoEstoque.ENTRADA, MovimentacaoEstoque.SAIDA):
        movimentacoes = movimentacoes.filter(tipo=tipo)

    idioma = idioma_da_requisicao(request)
    tr = TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO])

    # Anexa o motivo já traduzido a cada objeto (sem alterar o banco), para
    # o template só precisar exibir `mov.motivo_exibicao`.
    movimentacoes = list(movimentacoes)
    for mov in movimentacoes:
        mov.motivo_exibicao = _motivo_traduzido(mov.motivo_codigo, mov.motivo_detalhe, mov.motivo, tr)

    return render(request, 'estoque/historico_movimentacoes.html', {
        'movimentacoes': movimentacoes,
        'tipo_selecionado': tipo or '',
    })


# --- Relatórios (Fase 4) ---

TIPOS_RELATORIO_VALIDOS = {
    'estoque', 'estoque_baixo', 'vencendo', 'vencidos', 'entregas', 'movimentacoes',
}


def _parse_data(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except ValueError:
        return None


def _formatar_data(valor, idioma):
    if not valor:
        return '—'
    if idioma == 'en':
        return valor.strftime('%b %d, %Y')
    return valor.strftime('%d/%m/%Y')


def _formatar_data_hora(valor, idioma):
    if not valor:
        return '—'
    if idioma == 'en':
        return valor.strftime('%b %d, %Y %I:%M %p')
    return valor.strftime('%d/%m/%Y %H:%M')


def _montar_relatorio(tipo, categoria_id, data_inicio, data_fim, idioma):
    """Monta (colunas, linhas) para o tipo de relatório pedido, já filtrado
    e com os cabeçalhos de coluna no idioma atual da pessoa."""
    tr = TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO])
    colunas, linhas = [], []

    if tipo in ('estoque', 'estoque_baixo', 'vencendo', 'vencidos'):
        produtos = Produto.objects.select_related('categoria').order_by('nome')
        if categoria_id:
            produtos = produtos.filter(categoria_id=categoria_id)

        if tipo == 'estoque_baixo':
            produtos = [p for p in produtos if p.estoque_baixo]
        elif tipo == 'vencendo':
            produtos = [p for p in produtos if p.vencimento_proximo]
        elif tipo == 'vencidos':
            produtos = [p for p in produtos if p.esta_vencido]

        p_t = tr['produtos']
        status_labels = {
            'vencido': p_t['status_vencido'],
            'aviso': p_t['status_aviso'],
            'normal': p_t['status_normal'],
        }
        colunas = [p_t['col_nome'], p_t['col_categoria'], p_t['col_quantidade'],
                   p_t['col_estoque_minimo'], p_t['col_validade'], p_t['col_status']]
        for p in produtos:
            linhas.append([
                p.nome,
                p.categoria.nome if p.categoria else '—',
                p.quantidade if p.quantidade is not None else '—',
                p.estoque_minimo,
                _formatar_data(p.data_validade, idioma),
                status_labels.get(p.status_validade, '—'),
            ])

    elif tipo == 'entregas':
        entregas = Entrega.objects.select_related('produto', 'usuario').all()
        if data_inicio:
            entregas = entregas.filter(data_entrega__gte=data_inicio)
        if data_fim:
            entregas = entregas.filter(data_entrega__lte=data_fim)
        if categoria_id:
            entregas = entregas.filter(produto__categoria_id=categoria_id)

        e_t = tr['entregas_hist']
        colunas = [e_t['col_data'], e_t['col_produto'], e_t['col_paciente'],
                   e_t['col_quantidade'], e_t['col_registrado_por']]
        for e in entregas:
            linhas.append([
                _formatar_data(e.data_entrega, idioma),
                e.produto_nome,
                e.paciente,
                e.quantidade,
                e.usuario.username if e.usuario else '—',
            ])

    elif tipo == 'movimentacoes':
        movs = MovimentacaoEstoque.objects.select_related('produto', 'usuario').all()
        if data_inicio:
            movs = movs.filter(data__date__gte=data_inicio)
        if data_fim:
            movs = movs.filter(data__date__lte=data_fim)
        if categoria_id:
            movs = movs.filter(produto__categoria_id=categoria_id)

        m_t = tr['movimentacoes_hist']
        tipo_labels = {'ENTRADA': m_t['tipo_entrada'], 'SAIDA': m_t['tipo_saida']}
        colunas = [m_t['col_data'], m_t['col_produto'], m_t['col_tipo'],
                   m_t['col_quantidade'], m_t['col_motivo'], m_t['col_usuario']]
        for m in movs:
            linhas.append([
                _formatar_data_hora(m.data, idioma),
                m.produto_nome,
                tipo_labels.get(m.tipo, m.get_tipo_display()),
                m.quantidade,
                _motivo_traduzido(m.motivo_codigo, m.motivo_detalhe, m.motivo, tr),
                m.usuario.username if m.usuario else '—',
            ])

    return colunas, linhas


def _exportar_csv(titulo, colunas, linhas):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{slugify(titulo)}.csv"'
    response.write('\ufeff')  # BOM: garante que o Excel abra acentuação corretamente
    writer = csv.writer(response)
    writer.writerow(colunas)
    writer.writerows(linhas)
    return response


def _exportar_xlsx(titulo, colunas, linhas):
    import openpyxl
    from openpyxl.styles import Font
    from io import BytesIO

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = titulo[:31]  # limite de 31 caracteres do Excel para nome de aba

    ws.append(colunas)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for linha in linhas:
        ws.append(linha)

    for coluna in ws.columns:
        largura = max((len(str(c.value)) for c in coluna if c.value is not None), default=10)
        ws.column_dimensions[coluna[0].column_letter].width = min(largura + 2, 40)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{slugify(titulo)}.xlsx"'
    return response


@login_required
def relatorios(request):
    idioma = idioma_da_requisicao(request)
    tr = TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO])['relatorios']

    tipo = request.GET.get('tipo', 'estoque')
    if tipo not in TIPOS_RELATORIO_VALIDOS:
        tipo = 'estoque'

    rotulos_tipo = {
        'estoque': tr['tipo_estoque'],
        'estoque_baixo': tr['tipo_estoque_baixo'],
        'vencendo': tr['tipo_vencendo'],
        'vencidos': tr['tipo_vencidos'],
        'entregas': tr['tipo_entregas'],
        'movimentacoes': tr['tipo_movimentacoes'],
    }

    categoria_id = request.GET.get('categoria') or ''
    data_inicio_str = request.GET.get('data_inicio', '')
    data_fim_str = request.GET.get('data_fim', '')
    data_inicio = _parse_data(data_inicio_str)
    data_fim = _parse_data(data_fim_str)
    formato = request.GET.get('formato', 'html')

    colunas, linhas = _montar_relatorio(tipo, categoria_id, data_inicio, data_fim, idioma)

    if formato == 'csv':
        return _exportar_csv(rotulos_tipo[tipo], colunas, linhas)
    if formato == 'xlsx':
        return _exportar_xlsx(rotulos_tipo[tipo], colunas, linhas)

    return render(request, 'estoque/relatorios.html', {
        'tipo_selecionado': tipo,
        'tipo_rotulo': rotulos_tipo[tipo],
        'mostrar_periodo': tipo in ('entregas', 'movimentacoes'),
        'categorias': Categoria.objects.all(),
        'categoria_selecionada': categoria_id,
        'data_inicio': data_inicio_str,
        'data_fim': data_fim_str,
        'colunas': colunas,
        'linhas': linhas,
        'total_linhas': len(linhas),
    })


# --- Análises / Gráficos (Fase 4) ---

@login_required
@login_required
def analises(request):
    idioma = idioma_da_requisicao(request)
    p_t = TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO])['produtos']

    # Estoque total por categoria
    labels_categoria, dados_categoria = [], []
    for cat in Categoria.objects.all():
        total = Produto.objects.filter(categoria=cat).aggregate(total=Sum('quantidade'))['total'] or 0
        labels_categoria.append(cat.nome)
        dados_categoria.append(total)

    # Distribuição por status de validade
    contagem = {'normal': 0, 'aviso': 0, 'vencido': 0, 'sem_validade': 0}
    for p in Produto.objects.all():
        status = p.status_validade
        contagem['sem_validade' if status is None else status] += 1

    # Movimentações (entrada x saída) dos últimos 30 dias
    hoje = date.today()
    dias = [hoje - timedelta(days=i) for i in range(29, -1, -1)]
    entradas_por_dia = {d: 0 for d in dias}
    saidas_por_dia = {d: 0 for d in dias}

    movs = MovimentacaoEstoque.objects.filter(data__date__gte=dias[0])
    for m in movs:
        d = m.data.date()
        if d in entradas_por_dia:
            if m.tipo == MovimentacaoEstoque.ENTRADA:
                entradas_por_dia[d] += m.quantidade
            else:
                saidas_por_dia[d] += m.quantidade

    contexto = {
        'labels_categoria': json.dumps(labels_categoria),
        'dados_categoria': json.dumps(dados_categoria),
        'labels_status': json.dumps([
            p_t['status_normal'], p_t['status_aviso'], p_t['status_vencido'], p_t['status_sem_validade'],
        ]),
        'dados_status': json.dumps([contagem['normal'], contagem['aviso'], contagem['vencido'], contagem['sem_validade']]),
        'labels_dias': json.dumps([d.strftime('%d/%m') for d in dias]),
        'dados_entrada': json.dumps([entradas_por_dia[d] for d in dias]),
        'dados_saida': json.dumps([saidas_por_dia[d] for d in dias]),
        'sem_dados': not Produto.objects.exists(),
    }
    return render(request, 'estoque/analises.html', contexto)
