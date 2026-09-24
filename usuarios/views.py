from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import F
from rolepermissions.decorators import has_permission_decorator
from django.contrib.auth.views import LoginView  
from django.urls import reverse_lazy
from .models import Users
from estoque.models import Produto, DIAS_AVISO_VENCIMENTO



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
            'mensagem': f'Vencido em {produto.data_validade.strftime("%d/%m/%Y")}',
        })
    for produto in produtos_vencendo.order_by('data_validade')[:10]:
        alertas.append({
            'produto': produto,
            'tipo': 'aviso',
            'mensagem': f'Vence em {produto.dias_para_vencer} dia(s) ({produto.data_validade.strftime("%d/%m/%Y")})',
        })
    for produto in produtos_estoque_baixo.order_by('quantidade')[:10]:
        alertas.append({
            'produto': produto,
            'tipo': 'estoque_baixo',
            'mensagem': f'Estoque baixo: {produto.quantidade} unidade(s) (mínimo {produto.estoque_minimo})',
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



@has_permission_decorator ('cadastrar_atendente')
def cadastrar_atendente(request):
    return render(request, 'cadastrar_atendente.html')



# Create your views here.
