from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.contrib.auth.views import LoginView  
from django.urls import reverse_lazy
from .models import Users
from .forms import UserCreationForm, UserChargeForm
from . import permissoes
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
    # Só permite acesso a Gestor ou Admin (mesma regra de gestor_required)
    if not (request.user.is_superuser or request.user.cargo == 'G'):
        # Se não for gestor nem admin, redireciona para o dashboard
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


# --- Gerenciamento de usuários — restrito a Gestor/Admin, com regras finas
# de permissão por ação (veja usuarios/permissoes.py para a matriz completa) ---

@gestor_required
def lista_usuarios(request):
    usuarios = Users.objects.all().order_by('username')
    # Calcula, por usuário da lista, o que o ator logado pode fazer com ele —
    # assim o template só decide o que MOSTRAR, nunca o que é PERMITIDO (essa
    # decisão fica só em permissoes.py, testável isoladamente).
    for usuario in usuarios:
        usuario.pode_editar = permissoes.pode_ver_ou_editar_perfil(request.user, usuario)
        usuario.pode_trocar_senha = permissoes.pode_trocar_senha(request.user, usuario)
        usuario.pode_status = permissoes.pode_ativar_ou_desativar(request.user, usuario) and usuario.pk != request.user.pk

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

    # Gestor não pode sequer abrir a tela de outro Gestor (só Admin pode).
    if not permissoes.pode_ver_ou_editar_perfil(request.user, usuario_editado):
        raise PermissionDenied('Você não tem permissão para editar este usuário.')

    if request.method == 'POST':
        form = UserChargeForm(request.POST, instance=usuario_editado)
    else:
        form = UserChargeForm(instance=usuario_editado)

    # Quando o ator não pode mudar o cargo deste alvo, o campo fica
    # `disabled`: o Django ignora qualquer valor enviado nele e sempre usa
    # o valor original da instância ao salvar, é a própria validação de
    # segurança (não dá pra burlar enviando o campo manualmente no POST).
    if not permissoes.pode_alterar_cargo(request.user, usuario_editado):
        form.fields['cargo'].disabled = True

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, tr['usuario_atualizado'])
        return redirect('lista_usuarios')

    return render(request, 'usuarios/editar_usuario.html', {
        'form': form,
        'usuario_editado': usuario_editado,
        'pode_trocar_senha': permissoes.pode_trocar_senha(request.user, usuario_editado),
    })


@gestor_required
def redefinir_senha_usuario(request, pk):
    """Define uma nova senha para outro usuário, sem precisar da senha atual
    dele — é um reset administrativo (Admin, ou Gestor sobre um Atendente ou
    sobre a própria conta). Para a pessoa trocar a PRÓPRIA senha sabendo a
    senha atual, use o fluxo padrão em /auth/password_change/."""
    usuario_alvo = get_object_or_404(Users, pk=pk)

    if not permissoes.pode_trocar_senha(request.user, usuario_alvo):
        raise PermissionDenied('Você não tem permissão para trocar a senha deste usuário.')

    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if request.method == 'POST':
        form = SetPasswordForm(usuario_alvo, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, tr['senha_redefinida'].format(usuario=usuario_alvo.username))
            return redirect('lista_usuarios')
    else:
        form = SetPasswordForm(usuario_alvo)

    for campo in form.fields.values():
        campo.widget.attrs.update({'class': 'input-form', 'required': 'required'})

    return render(request, 'usuarios/redefinir_senha.html', {
        'form': form,
        'usuario_alvo': usuario_alvo,
    })


@gestor_required
def alternar_status_usuario(request, pk):
    usuario = get_object_or_404(Users, pk=pk)
    tr = TRANSLATIONS.get(idioma_da_requisicao(request), TRANSLATIONS[IDIOMA_PADRAO])['mensagens']

    if usuario.pk == request.user.pk:
        messages.error(request, tr['nao_pode_alterar_propria_conta'])
        return redirect('lista_usuarios')

    # Só o Admin ativa/desativa contas — Gestor não tem essa permissão para
    # ninguém (nem para Atendentes).
    if not permissoes.pode_ativar_ou_desativar(request.user, usuario):
        raise PermissionDenied('Apenas o Admin pode ativar ou desativar usuários.')

    if request.method != 'POST':
        return render(request, 'usuarios/confirmar_status_usuario.html', {'usuario': usuario})

    usuario.is_active = not usuario.is_active
    usuario.save()
    chave = 'usuario_ativado' if usuario.is_active else 'usuario_desativado'
    messages.success(request, tr[chave].format(usuario=usuario.username))
    return redirect('lista_usuarios')
