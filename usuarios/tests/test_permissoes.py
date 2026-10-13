"""
Testes unitários da matriz de permissões (usuarios/permissoes.py).

Especificação coberta:
- Admin: troca senha de qualquer um; muda cargo de qualquer um; tem todo
  privilégio do Gestor.
- Gestor: cria usuários (Atendente ou Gestor); troca a própria senha e a
  de Atendentes (não a de outros Gestores); promove Atendente a Gestor;
  NÃO rebaixa ninguém; NÃO ativa/desativa ninguém; NÃO mexe em outro
  Gestor de forma alguma.
- Atendente: nenhum acesso a gerenciamento de usuários.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from usuarios import permissoes

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


class PermissoesTestCase(TestCase):
    def setUp(self):
        self.admin = _criar_usuario('admin1', cargo='G', is_superuser=True)
        self.gestor = _criar_usuario('gestor1', cargo='G')
        self.outro_gestor = _criar_usuario('gestor2', cargo='G')
        self.atendente = _criar_usuario('atendente1', cargo='A')
        self.outro_atendente = _criar_usuario('atendente2', cargo='A')


class PodeGerenciarUsuariosTests(PermissoesTestCase):
    def test_admin_pode_gerenciar_usuarios(self):
        self.assertTrue(permissoes.pode_gerenciar_usuarios(self.admin))

    def test_gestor_pode_gerenciar_usuarios(self):
        self.assertTrue(permissoes.pode_gerenciar_usuarios(self.gestor))

    def test_atendente_nao_pode_gerenciar_usuarios(self):
        self.assertFalse(permissoes.pode_gerenciar_usuarios(self.atendente))


class PodeVerOuEditarPerfilTests(PermissoesTestCase):
    def test_admin_pode_editar_qualquer_um(self):
        self.assertTrue(permissoes.pode_ver_ou_editar_perfil(self.admin, self.gestor))
        self.assertTrue(permissoes.pode_ver_ou_editar_perfil(self.admin, self.atendente))

    def test_gestor_pode_editar_a_propria_conta(self):
        self.assertTrue(permissoes.pode_ver_ou_editar_perfil(self.gestor, self.gestor))

    def test_gestor_pode_editar_atendente(self):
        self.assertTrue(permissoes.pode_ver_ou_editar_perfil(self.gestor, self.atendente))

    def test_gestor_nao_pode_editar_outro_gestor(self):
        self.assertFalse(permissoes.pode_ver_ou_editar_perfil(self.gestor, self.outro_gestor))

    def test_atendente_nao_pode_editar_ninguem(self):
        self.assertFalse(permissoes.pode_ver_ou_editar_perfil(self.atendente, self.atendente))
        self.assertFalse(permissoes.pode_ver_ou_editar_perfil(self.atendente, self.outro_atendente))


class PodeAlterarCargoTests(PermissoesTestCase):
    def test_admin_pode_alterar_cargo_de_qualquer_um(self):
        self.assertTrue(permissoes.pode_alterar_cargo(self.admin, self.gestor))
        self.assertTrue(permissoes.pode_alterar_cargo(self.admin, self.atendente))

    def test_gestor_pode_promover_atendente(self):
        self.assertTrue(permissoes.pode_alterar_cargo(self.gestor, self.atendente))

    def test_gestor_nao_pode_alterar_o_proprio_cargo(self):
        self.assertFalse(permissoes.pode_alterar_cargo(self.gestor, self.gestor))

    def test_gestor_nao_pode_alterar_cargo_de_outro_gestor(self):
        self.assertFalse(permissoes.pode_alterar_cargo(self.gestor, self.outro_gestor))

    def test_atendente_nao_pode_alterar_cargo_de_ninguem(self):
        self.assertFalse(permissoes.pode_alterar_cargo(self.atendente, self.outro_atendente))


class PodeTrocarSenhaTests(PermissoesTestCase):
    def test_admin_pode_trocar_senha_de_qualquer_um(self):
        self.assertTrue(permissoes.pode_trocar_senha(self.admin, self.gestor))
        self.assertTrue(permissoes.pode_trocar_senha(self.admin, self.outro_gestor))
        self.assertTrue(permissoes.pode_trocar_senha(self.admin, self.atendente))

    def test_gestor_pode_trocar_a_propria_senha(self):
        self.assertTrue(permissoes.pode_trocar_senha(self.gestor, self.gestor))

    def test_gestor_pode_trocar_senha_de_atendente(self):
        self.assertTrue(permissoes.pode_trocar_senha(self.gestor, self.atendente))
        self.assertTrue(permissoes.pode_trocar_senha(self.gestor, self.outro_atendente))

    def test_gestor_nao_pode_trocar_senha_de_outro_gestor(self):
        self.assertFalse(permissoes.pode_trocar_senha(self.gestor, self.outro_gestor))

    def test_atendente_nao_pode_trocar_senha_de_outro_atendente(self):
        self.assertFalse(permissoes.pode_trocar_senha(self.atendente, self.outro_atendente))


class PodeAtivarOuDesativarTests(PermissoesTestCase):
    def test_somente_admin_pode_ativar_ou_desativar(self):
        self.assertTrue(permissoes.pode_ativar_ou_desativar(self.admin, self.atendente))
        self.assertTrue(permissoes.pode_ativar_ou_desativar(self.admin, self.gestor))

    def test_gestor_nao_pode_ativar_ou_desativar_ninguem(self):
        self.assertFalse(permissoes.pode_ativar_ou_desativar(self.gestor, self.atendente))
        self.assertFalse(permissoes.pode_ativar_ou_desativar(self.gestor, self.outro_gestor))

    def test_atendente_nao_pode_ativar_ou_desativar_ninguem(self):
        self.assertFalse(permissoes.pode_ativar_ou_desativar(self.atendente, self.outro_atendente))
