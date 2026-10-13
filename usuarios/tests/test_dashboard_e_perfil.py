"""
Testes das views que faltavam em usuarios/views.py: login, dashboard
(e os alertas que ele monta), perfil do gestor e configurações.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import Categoria, Produto

Users = get_user_model()


def _criar_usuario(username, cargo='A'):
    return Users.objects.create_user(username=username, email=f'{username}@teste.com', password='SenhaForte123', cargo=cargo)


class LoginTests(TestCase):
    def setUp(self):
        self.usuario = _criar_usuario('usuariologin', cargo='A')

    def test_login_com_credenciais_corretas_redireciona_ao_dashboard(self):
        resposta = self.client.post(reverse('login'), {'username': 'usuariologin', 'password': 'SenhaForte123'})
        self.assertRedirects(resposta, reverse('dashboard'))

    def test_login_com_senha_errada_mostra_erro_e_nao_autentica(self):
        resposta = self.client.post(reverse('login'), {'username': 'usuariologin', 'password': 'senha-errada'})
        self.assertEqual(resposta.status_code, 200)  # não redireciona
        self.assertContains(resposta, 'incorret')

    def test_usuario_inativo_nao_consegue_logar(self):
        self.usuario.is_active = False
        self.usuario.save()
        resposta = self.client.post(reverse('login'), {'username': 'usuariologin', 'password': 'SenhaForte123'})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)


class DashboardTests(TestCase):
    def setUp(self):
        self.usuario = _criar_usuario('usuariodash', cargo='A')
        self.categoria = Categoria.objects.create(nome='Analgésicos')
        self.client.force_login(self.usuario)

    def test_dashboard_carrega_para_usuario_logado(self):
        resposta = self.client.get(reverse('dashboard'))
        self.assertEqual(resposta.status_code, 200)

    def test_produto_com_estoque_baixo_aparece_no_total_e_nos_alertas(self):
        Produto.objects.create(nome='Dipirona', categoria=self.categoria, quantidade=2, estoque_minimo=10)
        resposta = self.client.get(reverse('dashboard'))
        self.assertEqual(resposta.context['total_estoque_baixo'], 1)
        tipos_alerta = [a['tipo'] for a in resposta.context['alertas']]
        self.assertIn('estoque_baixo', tipos_alerta)

    def test_produto_vencido_aparece_no_total_de_vencidos(self):
        Produto.objects.create(
            nome='Xarope', categoria=self.categoria, quantidade=10,
            data_validade=date.today() - timedelta(days=5),
        )
        resposta = self.client.get(reverse('dashboard'))
        self.assertEqual(resposta.context['total_vencidos'], 1)

    def test_sem_produtos_nenhum_alerta_e_gerado(self):
        resposta = self.client.get(reverse('dashboard'))
        self.assertEqual(resposta.context['alertas'], [])


class PerfilGestorTests(TestCase):
    def setUp(self):
        self.gestor = _criar_usuario('gestorperfil', cargo='G')
        self.atendente = _criar_usuario('atendenteperfil', cargo='A')

    def test_gestor_acessa_o_proprio_perfil(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse('perfil_gestor'))
        self.assertEqual(resposta.status_code, 200)

    def test_atendente_e_redirecionado_para_o_dashboard(self):
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse('perfil_gestor'))
        self.assertRedirects(resposta, reverse('dashboard'))


class ConfiguracoesTests(TestCase):
    def test_qualquer_usuario_logado_acessa_configuracoes(self):
        usuario = _criar_usuario('usuarioconfig', cargo='A')
        self.client.force_login(usuario)
        resposta = self.client.get(reverse('configuracoes'))
        self.assertEqual(resposta.status_code, 200)

    def test_anonimo_e_redirecionado(self):
        resposta = self.client.get(reverse('configuracoes'))
        self.assertEqual(resposta.status_code, 302)
