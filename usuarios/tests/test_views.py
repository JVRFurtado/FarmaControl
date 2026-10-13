"""
Testes de integração: requisições reais via Client, confirmando que as
views de gerenciamento de usuários aplicam de fato as regras definidas em
usuarios/permissoes.py.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

Users = get_user_model()


def _criar_usuario(username, cargo='A', is_superuser=False):
    usuario = Users.objects.create_user(
        username=username, email=f'{username}@teste.com', password='SenhaForte123', cargo=cargo,
    )
    if is_superuser:
        usuario.is_superuser = True
        usuario.is_staff = True
        usuario.save()
    return usuario


class AcessoAGerenciamentoDeUsuariosTests(TestCase):
    def setUp(self):
        self.gestor = _criar_usuario('gestor1', cargo='G')
        self.atendente = _criar_usuario('atendente1', cargo='A')

    def test_atendente_recebe_403_ao_tentar_acessar_lista_de_usuarios(self):
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(resposta.status_code, 403)

    def test_gestor_acessa_lista_de_usuarios(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(resposta.status_code, 200)

    def test_usuario_anonimo_e_redirecionado(self):
        resposta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(resposta.status_code, 302)


class EdicaoDeUsuarioTests(TestCase):
    def setUp(self):
        self.admin = _criar_usuario('admin1', cargo='G', is_superuser=True)
        self.gestor = _criar_usuario('gestor1', cargo='G')
        self.outro_gestor = _criar_usuario('gestor2', cargo='G')
        self.atendente = _criar_usuario('atendente1', cargo='A')

    def test_gestor_nao_acessa_tela_de_edicao_de_outro_gestor(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse('editar_usuario', args=[self.outro_gestor.id]))
        self.assertEqual(resposta.status_code, 403)

    def test_gestor_acessa_tela_de_edicao_de_atendente(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse('editar_usuario', args=[self.atendente.id]))
        self.assertEqual(resposta.status_code, 200)

    def test_admin_acessa_tela_de_edicao_de_qualquer_gestor(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse('editar_usuario', args=[self.outro_gestor.id]))
        self.assertEqual(resposta.status_code, 200)

    def test_gestor_consegue_promover_atendente_a_gestor(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse('editar_usuario', args=[self.atendente.id]), {
            'username': self.atendente.username,
            'email': self.atendente.email,
            'cargo': 'G',
        })
        self.assertEqual(resposta.status_code, 302)
        self.atendente.refresh_from_db()
        self.assertEqual(self.atendente.cargo, 'G')

    def test_gestor_nao_consegue_alterar_o_proprio_cargo_mesmo_forcando_o_post(self):
        # O campo vem desabilitado no formulário (ver editar_usuario na view);
        # mesmo que alguém monte um POST manual tentando virar 'A', o Django
        # ignora o valor enviado em campos disabled e mantém o da instância.
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse('editar_usuario', args=[self.gestor.id]), {
            'username': self.gestor.username,
            'email': self.gestor.email,
            'cargo': 'A',
        })
        self.assertEqual(resposta.status_code, 302)
        self.gestor.refresh_from_db()
        self.assertEqual(self.gestor.cargo, 'G')


class RedefinicaoDeSenhaTests(TestCase):
    def setUp(self):
        self.admin = _criar_usuario('admin1', cargo='G', is_superuser=True)
        self.gestor = _criar_usuario('gestor1', cargo='G')
        self.outro_gestor = _criar_usuario('gestor2', cargo='G')
        self.atendente = _criar_usuario('atendente1', cargo='A')

    def _payload_senha(self, senha='NovaSenhaForte456'):
        return {'new_password1': senha, 'new_password2': senha}

    def test_gestor_pode_redefinir_senha_de_atendente(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(
            reverse('redefinir_senha_usuario', args=[self.atendente.id]), self._payload_senha()
        )
        self.assertEqual(resposta.status_code, 302)
        self.atendente.refresh_from_db()
        self.assertTrue(self.atendente.check_password('NovaSenhaForte456'))

    def test_gestor_nao_pode_redefinir_senha_de_outro_gestor(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(
            reverse('redefinir_senha_usuario', args=[self.outro_gestor.id]), self._payload_senha()
        )
        self.assertEqual(resposta.status_code, 403)

    def test_gestor_pode_redefinir_a_propria_senha_por_essa_tela(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(
            reverse('redefinir_senha_usuario', args=[self.gestor.id]), self._payload_senha()
        )
        self.assertEqual(resposta.status_code, 302)

    def test_admin_pode_redefinir_senha_de_qualquer_gestor(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(
            reverse('redefinir_senha_usuario', args=[self.outro_gestor.id]), self._payload_senha()
        )
        self.assertEqual(resposta.status_code, 302)
        self.outro_gestor.refresh_from_db()
        self.assertTrue(self.outro_gestor.check_password('NovaSenhaForte456'))


class AtivarDesativarUsuarioTests(TestCase):
    def setUp(self):
        self.admin = _criar_usuario('admin1', cargo='G', is_superuser=True)
        self.gestor = _criar_usuario('gestor1', cargo='G')
        self.atendente = _criar_usuario('atendente1', cargo='A')

    def test_gestor_nao_pode_desativar_atendente(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse('alternar_status_usuario', args=[self.atendente.id]))
        self.assertEqual(resposta.status_code, 403)
        self.atendente.refresh_from_db()
        self.assertTrue(self.atendente.is_active)

    def test_admin_pode_desativar_atendente(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('alternar_status_usuario', args=[self.atendente.id]))
        self.assertEqual(resposta.status_code, 302)
        self.atendente.refresh_from_db()
        self.assertFalse(self.atendente.is_active)

    def test_admin_nao_pode_desativar_a_propria_conta(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('alternar_status_usuario', args=[self.admin.id]))
        self.assertEqual(resposta.status_code, 302)  # redireciona com mensagem de erro
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class CriacaoDeUsuarioTests(TestCase):
    def setUp(self):
        self.gestor = _criar_usuario('gestor1', cargo='G')
        self.client.force_login(self.gestor)

    def test_gestor_pode_criar_atendente(self):
        resposta = self.client.post(reverse('adicionar_usuario'), {
            'username': 'novoatendente',
            'email': 'novoatendente@teste.com',
            'cargo': 'A',
            'password1': 'SenhaForte123',
            'password2': 'SenhaForte123',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Users.objects.filter(username='novoatendente', cargo='A').exists())

    def test_gestor_pode_criar_outro_gestor(self):
        resposta = self.client.post(reverse('adicionar_usuario'), {
            'username': 'novogestor',
            'email': 'novogestor@teste.com',
            'cargo': 'G',
            'password1': 'SenhaForte123',
            'password2': 'SenhaForte123',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Users.objects.filter(username='novogestor', cargo='G').exists())
