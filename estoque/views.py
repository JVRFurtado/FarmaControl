from django.shortcuts import render, redirect, get_object_or_404
from .models import Produto, Medicamento, Categoria
from .forms import ProdutoForm, MedicamentoForm, EntregaForm
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
            tamanho = form.cleaned_data['tamanho']
            categoria = form.cleaned_data['categoria']
            data_validade = form.cleaned_data['data_validade']
            ultima_compra = form.cleaned_data['ultima_compra']

            # Verifica se já existe produto exatamente igual
            if Produto.objects.filter(
                nome=nome, 
                tamanho=tamanho,
                categoria=categoria,
                data_validade=data_validade,
                ultima_compra=ultima_compra
            ).exists():
                messages.error(request, 'Produto já cadastrado com todas as mesmas informações!')
            else:
                try:
                    form.save()
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
                    form.save()
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
        form = ProdutoForm(request.POST, instance=produto)  # instância passada para edição
        if form.is_valid():
            form.save()
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
                
                # Aqui você pode salvar os dados da entrega em um modelo, se quiser (não obrigatório)
                messages.success(request, f'Entrega registrada para {paciente} ({quantidade_entregue} unidades).')
                return redirect('lista_produtos')
    else:
        form = EntregaForm()
        
    return render(request, 'estoque/entregar_produto.html', {'produto': produto, 'form': form})
