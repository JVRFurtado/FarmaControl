from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from estoque.models import Produto
from farmacontrol.context_processors import idioma_da_requisicao, traducoes_da_requisicao
from farmacontrol.formatacao import formatar_data
from farmacontrol.formularios import dados_do_post

from . import permissoes
from .decorators import gestor_required
from .forms import UserChargeForm, UserCreationForm
from .models import Users

ALERTAS_POR_TIPO = 10  
ALERTAS_NO_PAINEL = 15


class LoginRedirecionadoView(LoginView):
    template_name = 'registration/login.html'

    def form_invalid(self, form):
        form.errors.pop('__all__', None)
        form.add_error(None, traducoes_da_requisicao(self.request)['login']['erro_credenciais'])
        return self.render_to_response(self.get_context_data(form=form))


@login_required
def dashboard(request):
    idioma = idioma_da_requisicao(request)
    tr = traducoes_da_requisicao(request)['dashboard']

    produtos = Produto.objects.all()
    estoque_baixo = produtos.estoque_baixo()
    vencidos = produtos.vencidos()
    vencendo = produtos.vencendo()

    alertas = (
        [{'produto': p, 'tipo': 'vencido',
          'mensagem': f'{tr["alerta_vencido_em"]} {formatar_data(p.data_validade, idioma)}'}
         for p in vencidos.order_by('data_validade')[:ALERTAS_POR_TIPO]]
        + [{'produto': p, 'tipo': 'aviso',
            'mensagem': (f'{tr["alerta_vence_em"]} {p.dias_para_vencer} {tr["alerta_dia"]} '
                         f'({formatar_data(p.data_validade, idioma)})')}
           for p in vencendo.order_by('data_validade')[:ALERTAS_POR_TIPO]]
        + [{'produto': p, 'tipo': 'estoque_baixo',
            'mensagem': (f'{tr["alerta_estoque_baixo_texto"]} {p.quantidade} {tr["alerta_unidade"]} '
                         f'({tr["alerta_minimo"]} {p.estoque_minimo})')}
           for p in estoque_baixo.order_by('quantidade')[:ALERTAS_POR_TIPO]]
    )

    return render(request, 'usuarios/dashboard.html', {
        'total_produtos': produtos.count(),
        'total_estoque_baixo': estoque_baixo.count(),
        'total_vencidos': vencidos.count(),
        'total_vencendo': vencendo.count(),
        'alertas': alertas[:ALERTAS_NO_PAINEL],
    })


@login_required
def perfil_gestor(request):
    
    if not permissoes.eh_gestor_ou_admin(request.user):
        return redirect('dashboard')
    return render(request, 'usuarios/perfil_gestor.html', {'user': request.user})


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
        usuario.pode_status = (
            permissoes.pode_ativar_ou_desativar(request.user, usuario)
            and usuario.pk != request.user.pk
        )

    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios,
        'usuario_atual_id': request.user.id,
    })


@gestor_required
def adicionar_usuario(request):
    form = UserCreationForm(dados_do_post(request))

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, traducoes_da_requisicao(request)['mensagens']['usuario_cadastrado'])
        return redirect('lista_usuarios')

    return render(request, 'usuarios/adicionar_usuario.html', {'form': form})


@gestor_required
def editar_usuario(request, pk):
    usuario_editado = get_object_or_404(Users, pk=pk)

    # Gestor não pode sequer abrir a tela de outro Gestor (só Admin pode).
    if not permissoes.pode_ver_ou_editar_perfil(request.user, usuario_editado):
        raise PermissionDenied('Você não tem permissão para editar este usuário.')

    form = UserChargeForm(dados_do_post(request), instance=usuario_editado)

    # Quando o ator não pode mudar o cargo deste alvo, o campo fica
    # `disabled`: o Django ignora qualquer valor enviado nele e sempre usa
    # o valor original da instância ao salvar — não é só cosmético, é a
    # própria validação de segurança (não dá pra burlar enviando o campo
    # manualmente no POST).
    if not permissoes.pode_alterar_cargo(request.user, usuario_editado):
        form.fields['cargo'].disabled = True

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, traducoes_da_requisicao(request)['mensagens']['usuario_atualizado'])
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

    form = SetPasswordForm(usuario_alvo, dados_do_post(request))

    if request.method == 'POST' and form.is_valid():
        form.save()
        mensagem = traducoes_da_requisicao(request)['mensagens']['senha_redefinida']
        messages.success(request, mensagem.format(usuario=usuario_alvo.username))
        return redirect('lista_usuarios')

    for campo in form.fields.values():
        campo.widget.attrs.update({'class': 'input-form', 'required': 'required'})

    return render(request, 'usuarios/redefinir_senha.html', {
        'form': form,
        'usuario_alvo': usuario_alvo,
    })


@gestor_required
def alternar_status_usuario(request, pk):
    usuario = get_object_or_404(Users, pk=pk)
    mensagens = traducoes_da_requisicao(request)['mensagens']

    if usuario.pk == request.user.pk:
        messages.error(request, mensagens['nao_pode_alterar_propria_conta'])
        return redirect('lista_usuarios')

    # Só o Admin ativa/desativa contas — Gestor não tem essa permissão para
    # ninguém (nem para Atendentes), conforme a regra de segurança definida.
    if not permissoes.pode_ativar_ou_desativar(request.user, usuario):
        raise PermissionDenied('Apenas o Admin pode ativar ou desativar usuários.')

    if request.method != 'POST':
        return render(request, 'usuarios/confirmar_status_usuario.html', {'usuario': usuario})

    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    chave = 'usuario_ativado' if usuario.is_active else 'usuario_desativado'
    messages.success(request, mensagens[chave].format(usuario=usuario.username))
    return redirect('lista_usuarios')
