"""
Regras de permissão para gerenciamento de usuários.

Hierarquia de papéis:
- Admin: o superusuário do Django (`is_superuser=True`). Tem todos os
  privilégios do Gestor, mais a capacidade de mexer em qualquer usuário,
  inclusive outros Gestores.
- Gestor: cargo 'G'.
- Atendente: cargo 'A'.

Regras:
- Admin: troca a senha de qualquer usuário; altera o cargo de qualquer
  usuário; tem todo privilégio do Gestor (criar/gerenciar usuários).
- Gestor: cria novos usuários (Atendente ou Gestor); troca a própria senha
  e a de Atendentes (não a de outros Gestores nem a do Admin); promove
  Atendente a Gestor; NÃO rebaixa ninguém, NÃO desativa/remove ninguém,
  NÃO mexe em outro Gestor de forma alguma.
- Atendente: nenhum acesso a gerenciamento de usuários.
"""

def eh_admin(usuario):
    return bool(usuario.is_superuser)


def eh_gestor(usuario):
    return usuario.cargo == 'G'


def pode_gerenciar_usuarios(ator):
    """Quem pode acessar a área de gerenciamento de usuários (listar, criar)."""
    return eh_admin(ator) or eh_gestor(ator)


def pode_ver_ou_editar_perfil(ator, alvo):
    """Quem pode abrir a tela de edição de dados (usuário/email/cargo) de `alvo`."""
    if eh_admin(ator):
        return True
    if eh_gestor(ator):
        # Gestor só edita a própria conta ou a de um Atendente — nunca a de
        # outro Gestor (mesmo que seja só para olhar o formulário).
        return alvo.pk == ator.pk or alvo.cargo == 'A'
    return False


def pode_alterar_cargo(ator, alvo):
    """Quem pode mudar o campo `cargo` de `alvo` (a tela decide os valores
    permitidos com base nisso; a view também revalida ao salvar)."""
    if eh_admin(ator):
        return True
    if eh_gestor(ator):
        # Só promove Atendente a Gestor; nunca mexe no próprio cargo nem
        # rebaixa um Gestor (e nunca chega a editar outro Gestor, ver acima).
        return alvo.pk != ator.pk and alvo.cargo == 'A'
    return False


def pode_trocar_senha(ator, alvo):
    """Quem pode definir uma nova senha para `alvo` (sem precisar da senha
    atual — é um reset administrativo, não uma troca de senha de si mesmo
    pelo fluxo padrão do Django)."""
    if eh_admin(ator):
        return True
    if eh_gestor(ator):
        return alvo.pk == ator.pk or alvo.cargo == 'A'
    return False


def pode_ativar_ou_desativar(ator, alvo):
    """Só o Admin pode ativar/desativar (ou, no vocabulário do pedido,
    'remover') uma conta. Gestor não tem essa permissão para ninguém,
    nem para Atendentes."""
    return eh_admin(ator)
