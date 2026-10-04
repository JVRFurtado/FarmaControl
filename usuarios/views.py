from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.contrib.auth.views import LoginView  
from django.urls import reverse_lazy
from .models import Users
from .forms import UserCreationForm, UserChargeForm
from estoque.models import Produto, DIAS_AVISO_VENCIMENTO
from estoque.views import gestor_required
from farmacontrol.i18n import TRANSLATIONS, IDIOMA_PADRAO
from farmacontrol.context_processors import idioma_da_requisicao



# view de login com redirecionamento
class LoginRedirecionadoView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        form.add_error(None, "Usuário ou senha incorretos. Por favor, tente novamente.")
        return self.render_to_response(self.get_context_data(form=form))


@login_required
def dashboard(request):
    is_gestor = request.user.cargo == 'G'
    is_temporarily_atendente = request.user.is_temporarily_atendente

    idioma = idioma_da_requisicao(request)
    tr_dash = TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO])['dashboard']

    def _data_fmt(valor):
        if idioma == 'en':
            return valor.strftime('%b %d, %Y')
        return valor.strftime('%d/%m/%Y')

    hoje = date.today()
    limite_aviso = hoje + timedelta(days=DIAS_AVISO_VENCIMENTO)

    produtos = Produto.objects.all()
    total_produtos = produtos.count()

    produtos_estoque_baixo = produtos.filter(quantidade__isnull=False, quantidade__lte=F('estoque_minimo'))
    produtos_vencidos = produtos.filter(data_validade__isnull=False, data_validade__lt=hoje)
    produtos_vencendo = produtos.filter(data_validade__gte=hoje, data_validade__lte=limite_aviso)

    # Lista de alertas recentes para o painel: vencidos primeiro, depois vencendo em breve,
    # depois estoque baixo — limitada para não sobrecarregar o dashboard.
    alertas = []
    for produto in produtos_vencidos.order_by('data_validade')[:10]:
        alertas.append({
            'produto': produto,
            'tipo': 'vencido',
            'mensagem': f'{tr_dash["alerta_vencido_em"]} {_data_fmt(produto.data_validade)}',
        })
    for produto in produtos_vencendo.order_by('data_validade')[:10]:
        alertas.append({
            'produto': produto,
            'tipo': 'aviso',
            'mensagem': f'{tr_dash["alerta_vence_em"]} {produto.dias_para_vencer} {tr_dash["alerta_dia"]} ({_data_fmt(produto.data_validade)})',
        })
    for produto in produtos_estoque_baixo.order_by('quantidade')[:10]:
        alertas.append({
            'produto': produto,
            'tipo': 'estoque_baixo',
            'mensagem': f'{tr_dash["alerta_estoque_baixo_texto"]} {produto.quantidade} {tr_dash["alerta_unidade"]} ({tr_dash["alerta_minimo"]} {produto.estoque_minimo})',
        })

    return render(request, 'usuarios/dashboard.html', {
        'is_gestor': is_gestor,
        'is_temporarily_atendente': is_temporarily_atendente,
        'total_produtos': total_produtos,
        'total_estoque_baixo': produtos_estoque_baixo.count(),
        'total_vencidos': produtos_vencidos.count(),
        'total_vencendo': produtos_vencendo.count(),
        'alertas': alertas[:15],
    })

@login_required
def perfil_gestor(request):
    # Só permite acesso se for gestor (cargo G)
    if request.user.cargo != 'G':
        # Se não for gestor, pode redirecionar para dashboard 
        return redirect('dashboard')
    
    return render(request, 'usuarios/perfil_gestor.html', {
        'user': request.user,
    })

# View para alternar o cargo de Gestor para Atendente
@login_required
def alternar_para_atendente(request):
    if request.user.cargo == 'G':
       request.user.is_temporarily_atendente = not request.user.is_temporarily_atendente
       request.user.save()
       return redirect('dashboard') 
    return redirect('login')



@login_required
def configuracoes(request):
    return render(request, 'usuarios/configuracoes.html')


# --- Gerenciamento de usuários (Fase 4) — restrito ao Gestor ---

@gestor_required
def lista_usuarios(request):
    usuarios = Users.objects.all().order_by('username')
    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios,
        'usuario_atual_id': request.user.id,
    })


@gestor_required
def adicionar_usuario(request):
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, tr['usuario_cadastrado'])
            return redirect('lista_usuarios')
    else:
        form = UserCreationForm()

    return render(request, 'usuarios/adicionar_usuario.html', {'form': form})


@gestor_required
def editar_usuario(request, pk):
    usuario_editado = get_object_or_404(Users, pk=pk)
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = UserChargeForm(request.POST, instance=usuario_editado)
        if form.is_valid():
            form.save()
            messages.success(request, tr['usuario_atualizado'])
            return redirect('lista_usuarios')
    else:
        form = UserChargeForm(instance=usuario_editado)

    return render(request, 'usuarios/editar_usuario.html', {
        'form': form,
        'usuario_editado': usuario_editado,
    })


@gestor_required
def alternar_status_usuario(request, pk):
    usuario = get_object_or_404(Users, pk=pk)
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if usuario.pk == request.user.pk:
        messages.error(request, tr['nao_pode_alterar_propria_conta'])
        return redirect('lista_usuarios')

    if request.method != 'POST':
        return render(request, 'usuarios/confirmar_status_usuario.html', {'usuario': usuario})

    usuario.is_active = not usuario.is_active
    usuario.save()
    chave = 'usuario_ativado' if usuario.is_active else 'usuario_desativado'
    messages.success(request, tr[chave].format(usuario=usuario.username))
    return redirect('lista_usuarios')



# Create your views here.
