from django.shortcuts import render, redirect, get_object_or_404
from .models import Produto, Medicamento, Categoria, Entrega, MovimentacaoEstoque
from .forms import ProdutoForm, MedicamentoForm, EntregaForm, CategoriaForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Q
from functools import wraps


def gestor_required(view_func):
    """Só permite acesso a usuários com cargo 'Gestor'. Atendentes recebem 403."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.cargo != 'G':
            raise PermissionDenied('Apenas o Gestor pode realizar esta ação.')
        return view_func(request, *args, **kwargs)
    return _wrapped


def registrar_movimentacao(produto, tipo, quantidade, motivo, usuario):
    """Registra uma entrada ou saída no histórico de movimentações de estoque.
    Não registra nada se a quantidade for zero ou negativa (nada de fato mudou)."""
    if not quantidade or quantidade <= 0:
        return
    MovimentacaoEstoque.objects.create(
        produto=produto,
        produto_nome=produto.nome,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
    )


# Página inicial
def pagina_inicial(request):
    return render(request, 'estoque/home.html')

# Lista de produtos com busca
@login_required
def lista_produtos(request):
    produtos = Produto.objects.all()
    busca = request.GET.get('buscar')

    if busca:
        produtos = produtos.filter(
            Q(nome__icontains=busca) | Q(categoria__nome__icontains=busca)
        )

    produtos = produtos.order_by('nome')
    return render(request, 'estoque/lista_produtos.html', {
        'produtos': produtos,
        'is_gestor': request.user.cargo == 'G',
    })

# Adicionar produto
@login_required
def adicionar_produto(request):
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
                messages.error(request, 'Produto já cadastrado com todas as mesmas informações!')
            else:
                try:
                    produto_salvo = form.save()
                    if produto_salvo.quantidade and produto_salvo.quantidade > 0:
                        registrar_movimentacao(
                            produto_salvo, MovimentacaoEstoque.ENTRADA, produto_salvo.quantidade,
                            'Cadastro inicial do produto', request.user,
                        )
                    messages.success(request, 'Produto cadastrado com sucesso!')
                    return redirect('lista_produtos')
                except IntegrityError:
                    messages.error(request, 'Erro ao salvar: produto já existe.')
    else:
        form = ProdutoForm()

    return render(request, 'estoque/adicionar_produto.html', {'form': form})

# Adicionar medicamento
@login_required
def adicionar_medicamento(request):
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
                messages.error(request, 'Medicamento já cadastrado com todas as mesmas informações!')
            else:
                try:
                    medicamento_salvo = form.save()
                    if medicamento_salvo.quantidade and medicamento_salvo.quantidade > 0:
                        registrar_movimentacao(
                            medicamento_salvo, MovimentacaoEstoque.ENTRADA, medicamento_salvo.quantidade,
                            'Cadastro inicial do medicamento', request.user,
                        )
                    messages.success(request, 'Medicamento cadastrado com sucesso!')
                    return redirect('lista_produtos')
                except IntegrityError:
                    messages.error(request, 'Erro ao salvar: medicamento já existe.')
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
                )

            messages.success(request, 'Produto editado com sucesso!')
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
        )

    produto.delete()
    messages.success(request, 'Produto excluído com sucesso!')
    return redirect('lista_produtos')

#Baixar estoque
@login_required
def entregar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    
    if request.method == 'POST':
        form = EntregaForm(request.POST)
        if form.is_valid():
            quantidade_entregue = form.cleaned_data['quantidade']
            paciente = form.cleaned_data['paciente']
            data_entrega = form.cleaned_data['data_entrega']
            
            if quantidade_entregue > produto.quantidade:
                messages.error(request, 'Não há estoque suficiente para essa entrega.')
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
                )

                messages.success(request, f'Entrega registrada para {paciente} ({quantidade_entregue} unidades).')
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

    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria cadastrada com sucesso!')
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
    messages.success(request, 'Categoria excluída. Produtos dessa categoria ficaram sem categoria definida.')
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

    return render(request, 'estoque/historico_movimentacoes.html', {
        'movimentacoes': movimentacoes,
        'tipo_selecionado': tipo or '',
    })
